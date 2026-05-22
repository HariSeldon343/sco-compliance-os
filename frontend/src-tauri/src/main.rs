// Entry point della binary Tauri. Su Windows in release build, nasconde la console
// finestra (windows_subsystem = "windows") — utente vede solo la WebView, niente
// CMD lampeggia. In debug build la console resta visibile per i tracing log.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // Delega alla lib: la logica vive in lib.rs per essere testabile + per
    // permettere builds mobile (cfg_attr(mobile, ...)) in futuro.
    sco_compliance_os_app_lib::run()
}
