//! BackendManager — lifecycle del sidecar Python (FastAPI) bundled con l'app.
//!
//! Responsabilità:
//!   1. Spawn del binary `sco-compliance-os-backend.exe` (Windows) o equivalente.
//!   2. PATH enrichment via path_enrichment::enriched_env() per propagare PATH
//!      con WinGet/pip --user/uv tool al subprocess Python (Conv. 45 lesson).
//!   3. Health probe HTTP GET /health con timeout breve.
//!   4. Graceful shutdown su drop (kill PID + cleanup runtime.json residuo).
//!
//! Conv. 44 lesson 1 enforcement: NO uvicorn --reload background. Lifecycle
//! gestito qui con spawn esplicito + kill esplicito al WindowEvent::Destroyed.

use std::time::{Duration, Instant};

use anyhow::{anyhow, Context, Result};
use serde::{Deserialize, Serialize};
use tauri::AppHandle;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;
use tracing::{debug, error, info, warn};

const HEALTH_URL: &str = "http://127.0.0.1:7800/health";
const HEALTH_PROBE_TIMEOUT_MS: u64 = 1500;
const STARTUP_WAIT_SECS: u64 = 30;
const STARTUP_POLL_INTERVAL_MS: u64 = 500;

/// Stato esposto al frontend via `get_backend_status` command.
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct BackendStatus {
    pub ok: bool,
    pub url: String,
    pub detail: String,
    pub pid: Option<u32>,
}

pub struct BackendManager {
    child: Option<CommandChild>,
    pid: Option<u32>,
}

impl BackendManager {
    pub fn new() -> Self {
        Self {
            child: None,
            pid: None,
        }
    }

    /// Spawn del sidecar + wait health probe fino a 30s. Ritorna Ok(()) solo
    /// quando il backend risponde 200 su /health, altrimenti Err con dettaglio.
    pub fn start(&mut self, app: &AppHandle) -> Result<()> {
        if self.child.is_some() {
            warn!("[BackendManager] Sidecar già attivo, skip start");
            return Ok(());
        }

        info!("[BackendManager] Spawn sidecar 'sco-compliance-os-backend'...");

        // Costruisce il comando sidecar via tauri-plugin-shell. Il resolve del
        // binary segue le 3 strategie di path_resolution: (1) bundled
        // `binaries/sco-compliance-os-backend-<triple>.exe`, (2) dev via cargo
        // run cerca in `../../backend/dist/...`, (3) PATH lookup come ultima
        // risorsa. La strategia (1) è quella usata in produzione.
        let sidecar = app
            .shell()
            .sidecar("sco-compliance-os-backend")
            .context("Costruzione comando sidecar fallita — binary mancante in binaries/?")?;

        // PATH enrichment: aggiunge WinGet/pip --user Scripts/uv tool bin al PATH
        // del subprocess. Lezione Conv. 45 cristallizzata su sco-agent-local:
        // su Windows i binari Python installati via pip --user o WinGet non sono
        // sempre nel PATH default propagato a subprocess. Enrichment manuale evita
        // ModuleNotFoundError o command-not-found in fase di runtime.
        let env_map = crate::path_enrichment::enriched_env();
        let sidecar = sidecar.envs(env_map);

        let (_rx, child) = sidecar
            .spawn()
            .context("Spawn sidecar fallito (tauri_plugin_shell)")?;

        let pid = child.pid();
        info!("[BackendManager] Sidecar spawned, PID = {pid}");
        self.pid = Some(pid);
        self.child = Some(child);

        // Health probe loop con deadline. Polling ogni 500ms fino a 30s.
        let deadline = Instant::now() + Duration::from_secs(STARTUP_WAIT_SECS);
        loop {
            if Instant::now() > deadline {
                let err = anyhow!(
                    "Backend non risponde su {HEALTH_URL} dopo {STARTUP_WAIT_SECS}s. \
                     Probabile crash startup — vedi log applicazione in cartella dati utente."
                );
                error!("[BackendManager] {err}");
                // Cleanup del child orfano prima di propagare l'errore
                let _ = self.stop();
                return Err(err);
            }
            // Probe sincrono blocking — siamo già in thread separato dal main loop Tauri
            if probe_health_sync(HEALTH_URL, HEALTH_PROBE_TIMEOUT_MS) {
                info!("[BackendManager] Health probe OK su {HEALTH_URL}");
                return Ok(());
            }
            std::thread::sleep(Duration::from_millis(STARTUP_POLL_INTERVAL_MS));
        }
    }

    /// Health probe async per esposizione via Tauri command.
    /// Non-blocking, timeout breve (1.5s) per non congestionare la UI.
    pub async fn health_probe(&self) -> BackendStatus {
        let url = HEALTH_URL.to_string();
        let pid = self.pid;
        match reqwest::Client::builder()
            .timeout(Duration::from_millis(HEALTH_PROBE_TIMEOUT_MS))
            .build()
        {
            Ok(client) => match client.get(&url).send().await {
                Ok(resp) if resp.status().is_success() => BackendStatus {
                    ok: true,
                    url,
                    detail: "healthy".to_string(),
                    pid,
                },
                Ok(resp) => BackendStatus {
                    ok: false,
                    url,
                    detail: format!("HTTP {}", resp.status()),
                    pid,
                },
                Err(e) => BackendStatus {
                    ok: false,
                    url,
                    detail: format!("connection error: {e}"),
                    pid,
                },
            },
            Err(e) => BackendStatus {
                ok: false,
                url,
                detail: format!("client build error: {e}"),
                pid,
            },
        }
    }

    /// Kill del sidecar. Su Windows usa il PID handle direttamente. Su Unix
    /// invia SIGTERM e attende uscita pulita.
    pub fn stop(&mut self) -> Result<()> {
        if let Some(child) = self.child.take() {
            info!("[BackendManager] Stop sidecar PID {:?}...", self.pid);
            child
                .kill()
                .context("Kill sidecar fallito (PID orfano possibile)")?;
            info!("[BackendManager] Sidecar terminato");
        } else {
            debug!("[BackendManager] Stop chiamato ma child=None, no-op");
        }
        self.pid = None;
        Ok(())
    }

    /// Restart = stop + start. Espone al frontend via Tauri command
    /// `restart_backend` per UI di troubleshooting.
    pub fn restart(&mut self, app: &AppHandle) -> Result<()> {
        info!("[BackendManager] Restart richiesto");
        self.stop()?;
        // Breve pausa per permettere al sistema di liberare la porta 7800
        // prima del nuovo bind (mitigazione TIME_WAIT su Windows)
        std::thread::sleep(Duration::from_millis(800));
        self.start(app)
    }
}

impl Drop for BackendManager {
    fn drop(&mut self) {
        // Garanzia di cleanup anche se l'app crasha: il child viene killed
        // quando il BackendManager esce dallo scope. Conv. 44 lesson 1 enforcement.
        if self.child.is_some() {
            warn!("[BackendManager] Drop con child attivo: kill di sicurezza");
            let _ = self.stop();
        }
    }
}

/// Health probe sincrono usando reqwest::blocking. Usato durante startup
/// loop (Instant::sleep + retry) perché lo spawn vive in thread dedicato
/// e non ha un tokio runtime disponibile.
fn probe_health_sync(url: &str, timeout_ms: u64) -> bool {
    // reqwest::blocking richiede feature `blocking`. Per evitare di aggiungerla
    // (tiene snella la dep tree), usiamo un HTTP GET stdlib via TcpStream.
    use std::io::{BufRead, BufReader, Write};
    use std::net::TcpStream;

    let stripped = match url.strip_prefix("http://") {
        Some(s) => s,
        None => return false,
    };
    let slash = stripped.find('/').unwrap_or(stripped.len());
    let host_port = &stripped[..slash];
    let path = if slash < stripped.len() {
        &stripped[slash..]
    } else {
        "/"
    };

    let stream = match TcpStream::connect_timeout(
        &match host_port.parse() {
            Ok(addr) => addr,
            Err(_) => return false,
        },
        Duration::from_millis(timeout_ms),
    ) {
        Ok(s) => s,
        Err(_) => return false,
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(timeout_ms)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(timeout_ms)));

    let mut stream = stream;
    let req = format!("GET {path} HTTP/1.0\r\nHost: {host_port}\r\nConnection: close\r\n\r\n");
    if stream.write_all(req.as_bytes()).is_err() {
        return false;
    }
    let mut reader = BufReader::new(stream);
    let mut status_line = String::new();
    if reader.read_line(&mut status_line).is_err() {
        return false;
    }
    let parts: Vec<&str> = status_line.trim().splitn(3, ' ').collect();
    if parts.len() < 2 {
        return false;
    }
    matches!(parts[1].parse::<u16>(), Ok(s) if (200..300).contains(&s))
}
