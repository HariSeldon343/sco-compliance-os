//! Risoluzione del path del binary sidecar `sco-compliance-os-backend` con
//! strategia tier multipla per supportare sia produzione (bundled) sia sviluppo.
//!
//! Conv. 45 lesson 1 enforcement: PyInstaller NON cross-compila — quindi il
//! binary sidecar è specifico per OS+architettura host. Tauri 2 usa Rust target
//! triple per disambiguare (es. `x86_64-pc-windows-msvc`, `aarch64-apple-darwin`).
//!
//! Strategie di lookup (in ordine):
//!   1. Bundled (produzione): `<resource_dir>/binaries/sco-compliance-os-backend-<triple>.exe`.
//!      Risolto automaticamente da tauri-plugin-shell::sidecar() — non serve
//!      logica esplicita qui, ma documentiamo la convenzione.
//!   2. Dev (cargo run / pnpm tauri dev): fallback a
//!      `../../backend/dist/sco-compliance-os-backend.exe` (output PyInstaller locale).
//!   3. PATH lookup (ultima risorsa, sviluppo avanzato): `which sco-compliance-os-backend`.
//!
//! In pratica per ora ci affidiamo al meccanismo built-in del plugin shell.
//! Questo modulo esiste come scaffolding per estensioni future (custom override,
//! variabile env SCO_BACKEND_PATH per puntare a build alternativa).

use std::path::PathBuf;

use tracing::debug;

/// Nome canonico del binary sidecar (senza estensione, senza triple suffix).
/// Tauri-plugin-shell aggiunge `-<triple>` + `.exe` automaticamente in fase
/// di bundle. In dev cerca lo stesso nome senza suffix nella cartella
/// `external_binaries` di tauri.conf.json.
pub const SIDECAR_NAME: &str = "sco-compliance-os-backend";

/// Override path via variabile env. Se settata, salta tutti i tier e usa
/// questo path direttamente. Utile per testing CI o build custom locali.
pub const ENV_OVERRIDE: &str = "SCO_BACKEND_PATH";

/// Risolve un path candidato dal env override. None se non settato o file
/// non esistente.
pub fn from_env_override() -> Option<PathBuf> {
    let raw = std::env::var(ENV_OVERRIDE).ok()?;
    let p = PathBuf::from(raw);
    if p.exists() {
        debug!("[path_resolution] Override env attivo: {}", p.display());
        Some(p)
    } else {
        debug!(
            "[path_resolution] Env {ENV_OVERRIDE} settato ma file non esiste: {}",
            p.display()
        );
        None
    }
}

/// Path di sviluppo: relativo alla cartella `frontend/src-tauri/` quando si
/// lancia `pnpm tauri dev` o `cargo run`. Cerca in
/// `../../backend/dist/<SIDECAR_NAME>(.exe)`. Su Windows aggiunge `.exe`.
pub fn dev_fallback_path() -> Option<PathBuf> {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let mut p = PathBuf::from(manifest_dir);
    p.push("..");
    p.push("..");
    p.push("backend");
    p.push("dist");

    #[cfg(target_os = "windows")]
    p.push(format!("{SIDECAR_NAME}.exe"));
    #[cfg(not(target_os = "windows"))]
    p.push(SIDECAR_NAME);

    if p.exists() {
        debug!("[path_resolution] Dev fallback trovato: {}", p.display());
        Some(p)
    } else {
        None
    }
}

/// Lookup nel PATH di sistema via stdlib. Iterazione su PATH split + check
/// esistenza file. Non usa external crate `which` per ridurre dep tree.
pub fn from_system_path() -> Option<PathBuf> {
    let path_var = std::env::var_os("PATH")?;
    for dir in std::env::split_paths(&path_var) {
        let mut candidate = dir.clone();
        #[cfg(target_os = "windows")]
        candidate.push(format!("{SIDECAR_NAME}.exe"));
        #[cfg(not(target_os = "windows"))]
        candidate.push(SIDECAR_NAME);
        if candidate.exists() {
            debug!("[path_resolution] PATH lookup trovato: {}", candidate.display());
            return Some(candidate);
        }
    }
    None
}

/// Strategia globale: env override → dev fallback → PATH → None.
/// Usata come ultimo recurso se tauri-plugin-shell::sidecar() fallisce.
#[allow(dead_code)]
pub fn resolve_any() -> Option<PathBuf> {
    from_env_override()
        .or_else(dev_fallback_path)
        .or_else(from_system_path)
}
