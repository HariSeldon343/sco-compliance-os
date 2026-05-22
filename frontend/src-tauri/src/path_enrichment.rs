//! PATH enrichment cross-OS per il subprocess sidecar Python.
//!
//! Conv. 45 lesson cristallizzata su sco-agent-local: su Windows i binari
//! installati via WinGet, pip --user, uv tool non sono sempre presenti nel
//! PATH propagato di default a un subprocess Rust. Senza enrichment manuale,
//! il backend Python può fallire ModuleNotFoundError quando importa pacchetti
//! installati user-level (es. email-validator transitive di pydantic.EmailStr,
//! dns.resolver, idna — Conv. 44 lesson 3 enforcement lato build,
//! qui enforcement lato runtime).
//!
//! Strategia:
//!   1. Parti dall'env corrente (std::env::vars()).
//!   2. Su Windows, append a PATH:
//!      - `%LOCALAPPDATA%\Microsoft\WinGet\Links`
//!      - `%LOCALAPPDATA%\Microsoft\WinGet\Packages\*\*` (glob expand best-effort)
//!      - `%APPDATA%\Python\Python3xx\Scripts` (pip --user)
//!      - `%LOCALAPPDATA%\uv\tools\*\bin` (uv tool)
//!   3. Su Mac/Linux append a PATH:
//!      - `$HOME/.local/bin` (pip --user XDG)
//!      - `$HOME/.cargo/bin`
//!      - `$HOME/Library/Python/3.*/bin` (Mac framework)
//!      - `/opt/homebrew/bin` (Mac Apple Silicon)
//!
//! L'enrichment è best-effort: directory inesistenti vengono saltate silently.

use std::collections::HashMap;
use std::path::PathBuf;

use tracing::debug;

/// Costruisce HashMap env enriched da passare a Command::envs().
pub fn enriched_env() -> HashMap<String, String> {
    let mut env: HashMap<String, String> = std::env::vars().collect();

    // Estrae PATH corrente, fa append delle directory aggiuntive specifiche per OS
    let path_sep = if cfg!(target_os = "windows") { ';' } else { ':' };
    let current_path = env.get("PATH").cloned().unwrap_or_default();
    let mut path_parts: Vec<String> = current_path
        .split(path_sep)
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .collect();

    for extra in os_specific_path_extensions() {
        let s = extra.to_string_lossy().to_string();
        if !path_parts.iter().any(|p| p.eq_ignore_ascii_case(&s)) {
            debug!("[path_enrichment] Append a PATH: {s}");
            path_parts.push(s);
        }
    }

    env.insert("PATH".to_string(), path_parts.join(&path_sep.to_string()));

    // Forza UTF-8 nel subprocess Python su Windows (evita UnicodeDecodeError
    // su path Italian con accenti come "Università" o "Forniture È")
    env.insert("PYTHONIOENCODING".to_string(), "utf-8".to_string());
    env.insert("PYTHONUTF8".to_string(), "1".to_string());

    env
}

/// Restituisce le directory candidate da aggiungere al PATH per la piattaforma
/// corrente. Filtrate per esistenza: solo directory effettivamente presenti
/// vengono aggiunte.
fn os_specific_path_extensions() -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = Vec::new();

    #[cfg(target_os = "windows")]
    {
        if let Ok(localappdata) = std::env::var("LOCALAPPDATA") {
            let base = PathBuf::from(&localappdata);
            out.push(base.join("Microsoft").join("WinGet").join("Links"));
            // WinGet Packages: gli eseguibili stanno in sotto-cartelle versione-specifiche.
            // Aggiungiamo la root, l'utente normalmente ha shim in Links/ che è
            // sufficiente per i tool installati via winget.
            out.push(base.join("Microsoft").join("WinGet").join("Packages"));
            // uv tool installa shim qui (uv tool install <pkg>)
            out.push(base.join("uv").join("tools"));
            // Python embeddable / py launcher / pip --user
            out.push(base.join("Programs").join("Python"));
        }
        if let Ok(appdata) = std::env::var("APPDATA") {
            // pip --user Scripts dir (Python 3.11+, varia per minor version)
            let pyroot = PathBuf::from(&appdata).join("Python");
            if pyroot.exists() {
                if let Ok(entries) = std::fs::read_dir(&pyroot) {
                    for entry in entries.flatten() {
                        let scripts = entry.path().join("Scripts");
                        if scripts.exists() {
                            out.push(scripts);
                        }
                    }
                }
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        if let Some(home) = dirs::home_dir() {
            out.push(home.join(".local").join("bin"));
            out.push(home.join(".cargo").join("bin"));
            // pip --user su Mac: ~/Library/Python/3.xx/bin
            let pyroot = home.join("Library").join("Python");
            if pyroot.exists() {
                if let Ok(entries) = std::fs::read_dir(&pyroot) {
                    for entry in entries.flatten() {
                        let bin = entry.path().join("bin");
                        if bin.exists() {
                            out.push(bin);
                        }
                    }
                }
            }
        }
        out.push(PathBuf::from("/opt/homebrew/bin"));
        out.push(PathBuf::from("/usr/local/bin"));
    }

    #[cfg(target_os = "linux")]
    {
        if let Some(home) = dirs::home_dir() {
            out.push(home.join(".local").join("bin"));
            out.push(home.join(".cargo").join("bin"));
        }
        out.push(PathBuf::from("/usr/local/bin"));
    }

    out.into_iter().filter(|p| p.exists()).collect()
}
