// SCO Compliance OS — root App con layout sidebar + header + outlet router
import { useEffect } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { useThemeStore } from "@/store/theme-store";

/**
 * Root App layout.
 *
 * Struttura a 3 zone:
 *   - Sidebar a sinistra (collapsible, 280px)
 *   - Header in alto (brand SCO + claim + theme toggle)
 *   - Outlet centrale che renderizza la route attiva (chat / settings / ...)
 *
 * Conv. 48 enforcement: il frontend NON hardcoda stati versione (LEGAL_VERSION,
 * PRIVACY_VERSION, DEMO_VERSION). Quando servirà onboarding/EULA, le costanti
 * arriveranno da backend via /api/onboarding/status.
 */
export default function App() {
  const theme = useThemeStore((s) => s.theme);
  const applyTheme = useThemeStore((s) => s.applyTheme);

  // Sync classe `dark` su <html> all'avvio + ai cambi di tema
  useEffect(() => {
    applyTheme();
  }, [theme, applyTheme]);

  // Listener sistema (per theme = "system")
  useEffect(() => {
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => applyTheme();
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme, applyTheme]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-sco-bg text-sco-text">
      {/* Sidebar sinistra */}
      <Sidebar />

      {/* Colonna destra: header + content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />

        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
