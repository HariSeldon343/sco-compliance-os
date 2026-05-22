//! SCO Compliance OS — core Rust application.
//!
//! Architettura:
//!   - `lib.rs` (questo file): Tauri Builder setup + plugin registration + invoke handler
//!   - `backend_manager.rs`: lifecycle del sidecar Python (spawn/health/graceful shutdown)
//!   - `path_resolution.rs`: risoluzione path binary sidecar (bundled / dev / PATH)
//!   - `path_enrichment.rs`: PATH propagation cross-OS (Conv. 45 lesson 3 enforcement)
//!
//! Lezioni cristallizzate applicate (sco-agent-local Conv. 44/45):
//!   - NON usare `uvicorn --reload` in background: lifecycle gestito da Rust con
//!     spawn pulito + kill su WindowEvent::Destroyed (Conv. 44 lesson 1).
//!   - Tauri 2 WebView2 Windows origin = `http://tauri.localhost` (Conv. 44 lesson 2):
//!     gestito lato backend CORS, qui non serve override.
//!   - PyInstaller transitive deps: gestiti dal .spec del backend, qui solo PATH
//!     enrichment per propagare environment al subprocess (Conv. 45 lesson PATH).

use std::sync::{Arc, Mutex};

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager, WindowEvent};
use tracing::{error, info, warn};

mod backend_manager;
mod path_enrichment;
mod path_resolution;

use backend_manager::{BackendManager, BackendStatus};

/// Stato condiviso del backend manager. Avvolto in Arc<Mutex<>> per accesso
/// cross-thread sicuro (Tauri commands sono async ma BackendManager mantiene
/// PID e child handle che richiedono mutex).
struct AppState {
    backend: Arc<Mutex<BackendManager>>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct UpdateInfo {
    available: bool,
    current_version: String,
    latest_version: Option<String>,
    notes: Option<String>,
}

// ────────────────────────────────────────────────────────────────────────────
// Tauri Commands esposti al frontend via @tauri-apps/api invoke()
// ────────────────────────────────────────────────────────────────────────────

/// URL canonico del backend locale. Hardcoded a 7800 perché il backend Python
/// fa bind esplicito su questa porta (single source of truth, Conv. 47).
#[tauri::command]
fn get_backend_url() -> String {
    "http://127.0.0.1:7800".to_string()
}

/// HTTP GET /health del backend. Ritorna `BackendStatus` con flag ok + dettaglio.
/// Usato dal frontend per StatusBar (verde/giallo/rosso indicator).
#[tauri::command]
async fn get_backend_status(state: tauri::State<'_, AppState>) -> Result<BackendStatus, String> {
    let manager = state.backend.lock().map_err(|e| e.to_string())?;
    Ok(manager.health_probe().await)
}

/// Kill + respawn del sidecar. Usato dal pannello impostazioni quando il
/// backend è in stato error e l'utente vuole forzare il restart senza
/// chiudere l'app intera.
#[tauri::command]
async fn restart_backend(
    app: AppHandle,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    info!("[SCO] Restart backend richiesto dall'utente");
    let mut manager = state.backend.lock().map_err(|e| e.to_string())?;
    manager.restart(&app).map_err(|e| e.to_string())?;
    Ok(())
}

/// File picker nativo per scegliere la cartella del vault Karpathy.
/// Ritorna None se l'utente cancella, Some(path) se conferma.
/// Plugin tauri-plugin-dialog gestisce la modal cross-OS.
#[tauri::command]
async fn open_vault_dialog(app: AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;
    let (tx, rx) = std::sync::mpsc::channel::<Option<String>>();
    app.dialog()
        .file()
        .set_title("Seleziona cartella del vault SCO Compliance OS")
        .pick_folder(move |folder_path| {
            let result = folder_path.map(|p| p.to_string());
            let _ = tx.send(result);
        });
    rx.recv().map_err(|e| e.to_string())
}

/// Versione corrente dell'app letta da CARGO_PKG_VERSION (compile-time).
/// Usata in About dialog + telemetry headers verso il backend.
#[tauri::command]
fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

/// Check auto-update via tauri-plugin-updater. Probe verso endpoint
/// `latest.json` configurato in tauri.conf.json. Ritorna UpdateInfo con
/// available=true se nuova versione disponibile.
///
/// Nota: la signature del plugin updater richiede `.updater()` su AppHandle.
/// Se il plugin non è inizializzato (pubkey placeholder), il check ritorna
/// available=false senza errore (graceful degradation).
#[tauri::command]
async fn check_for_updates(app: AppHandle) -> Result<UpdateInfo, String> {
    use tauri_plugin_updater::UpdaterExt;
    let current = env!("CARGO_PKG_VERSION").to_string();
    match app.updater() {
        Ok(updater) => match updater.check().await {
            Ok(Some(update)) => Ok(UpdateInfo {
                available: true,
                current_version: current,
                latest_version: Some(update.version.clone()),
                notes: update.body.clone(),
            }),
            Ok(None) => Ok(UpdateInfo {
                available: false,
                current_version: current,
                latest_version: None,
                notes: None,
            }),
            Err(e) => {
                warn!("[SCO] Update check fallito (graceful): {e}");
                Ok(UpdateInfo {
                    available: false,
                    current_version: current,
                    latest_version: None,
                    notes: Some(format!("Check fallito: {e}")),
                })
            }
        },
        Err(e) => {
            warn!("[SCO] Updater non inizializzato: {e}");
            Ok(UpdateInfo {
                available: false,
                current_version: current,
                latest_version: None,
                notes: Some("Updater non configurato".to_string()),
            })
        }
    }
}

/// Cartella dati app utente. Su Windows: `%APPDATA%\sco-compliance-os\`.
/// Su Mac: `~/Library/Application Support/sco-compliance-os/`. Su Linux:
/// `~/.config/sco-compliance-os/`. Usata per cache locale, log, store JSON.
#[tauri::command]
fn get_app_data_dir() -> Result<String, String> {
    dirs::config_dir()
        .map(|p| p.join("sco-compliance-os").to_string_lossy().to_string())
        .ok_or_else(|| "Impossibile determinare config_dir() di sistema".to_string())
}

/// Lettura file di testo dal filesystem locale. Lo scope è enforced dalle
/// capabilities di tauri-plugin-fs (vedi capabilities/default.json) — qui
/// la lettura passa solo se il path rientra in $APPCONFIG/$APPDATA/$HOME.
#[tauri::command]
fn read_text_file(path: String) -> Result<String, String> {
    std::fs::read_to_string(&path)
        .map_err(|e| format!("Impossibile leggere {path}: {e}"))
}

/// Scrittura file di testo. Stesso scope enforcement della read_text_file.
/// Crea parent directory se non esiste (idempotente).
#[tauri::command]
fn write_text_file(path: String, content: String) -> Result<(), String> {
    let p = std::path::PathBuf::from(&path);
    if let Some(parent) = p.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("Impossibile creare parent dir di {path}: {e}"))?;
    }
    std::fs::write(&p, content).map_err(|e| format!("Impossibile scrivere {path}: {e}"))
}

/// Apertura URL esterno nel browser di default. Usato per link a documentazione,
/// release notes, fonti normative cliccabili dalla UI. Scope CSP via opener plugin.
#[tauri::command]
async fn open_external_url(app: AppHandle, url: String) -> Result<(), String> {
    use tauri_plugin_opener::OpenerExt;
    app.opener()
        .open_url(&url, None::<&str>)
        .map_err(|e| format!("Impossibile aprire URL {url}: {e}"))
}

// ────────────────────────────────────────────────────────────────────────────
// Entry point — costruisce e avvia Tauri Builder
// ────────────────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Setup tracing strutturato. Sui release build niente console su Windows
    // (vedi main.rs windows_subsystem) — log vanno in file via tracing-appender.
    // Per ora init basic, in futuro file appender + log rotation.
    let _ = tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info,tauri=info")),
        )
        .with_target(true)
        .try_init();

    info!("[SCO] Compliance OS startup, version {}", env!("CARGO_PKG_VERSION"));

    let backend_manager = Arc::new(Mutex::new(BackendManager::new()));
    let backend_for_setup = Arc::clone(&backend_manager);
    let backend_for_window = Arc::clone(&backend_manager);

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            None,
        ))
        .manage(AppState {
            backend: Arc::clone(&backend_manager),
        })
        .setup(move |app| {
            let app_handle = app.handle().clone();

            // SCO_SKIP_SIDECAR=1 disabilita lo spawn del backend bundled.
            // Utile in dev quando l'utente lancia il backend manualmente
            // tramite `uv run uvicorn` per debug step-by-step.
            // (Conv. 44 lesson 1: NIENTE uvicorn --reload in background da shell ephemeral,
            // ma in dev locale l'utente può tenerlo aperto in terminale dedicato.)
            if std::env::var("SCO_SKIP_SIDECAR").ok().as_deref() == Some("1") {
                info!("[SCO] SCO_SKIP_SIDECAR=1: backend bundled non avviato. Lancia manualmente uvicorn.");
                return Ok(());
            }

            // Spawn backend in thread separato per non bloccare il main loop Tauri.
            // Il thread monitora startup health probe e emette evento `backend-ready`
            // o `backend-error` verso il frontend per aggiornare la UI di stato.
            let manager_clone = Arc::clone(&backend_for_setup);
            std::thread::spawn(move || {
                let mut manager = match manager_clone.lock() {
                    Ok(m) => m,
                    Err(e) => {
                        error!("[SCO] BackendManager mutex poisoned: {e}");
                        return;
                    }
                };
                match manager.start(&app_handle) {
                    Ok(()) => {
                        info!("[SCO] Backend sidecar avviato con successo");
                        let _ = app_handle.emit(
                            "backend-ready",
                            serde_json::json!({ "url": "http://127.0.0.1:7800" }),
                        );
                    }
                    Err(err) => {
                        error!("[SCO] Backend sidecar FALLITO: {err}");
                        let _ = app_handle.emit(
                            "backend-error",
                            serde_json::json!({ "error": err.to_string() }),
                        );
                    }
                }
            });

            Ok(())
        })
        .on_window_event(move |window, event| {
            // Graceful shutdown del sidecar quando l'utente chiude la finestra
            // principale. Tauri 2 emette WindowEvent::Destroyed dopo CloseRequested:
            // a quel punto il backend Python deve essere killed in modo pulito,
            // altrimenti il processo orfano lascia la porta in stato LISTENING zombie
            // (Conv. 44 lesson 1: socket zombie immune a taskkill su Windows).
            if matches!(event, WindowEvent::Destroyed) {
                info!("[SCO] Finestra '{}' chiusa: shutdown backend sidecar...", window.label());
                if let Ok(mut manager) = backend_for_window.lock() {
                    if let Err(e) = manager.stop() {
                        error!("[SCO] Stop backend fallito: {e}");
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_url,
            get_backend_status,
            restart_backend,
            open_vault_dialog,
            get_app_version,
            check_for_updates,
            get_app_data_dir,
            read_text_file,
            write_text_file,
            open_external_url,
        ])
        .run(tauri::generate_context!())
        .expect("Errore fatale nell'avvio di SCO Compliance OS");
}
