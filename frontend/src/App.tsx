// SCO Compliance OS — root App con LicenseGate + layout sidebar + header + outlet router
import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { LicenseScreen } from "@/screens/LicenseScreen";
import { useThemeStore } from "@/store/theme-store";
import { useLicenseStore } from "@/store/license-store";

/**
 * Root App layout.
 *
 * Struttura a 3 zone:
 *   - LicenseGate full-page se license non valida
 *   - Altrimenti: Sidebar (280px) + Header + Outlet
 *
 * Conv. 47 + 48 enforcement: il backend è single source of truth per status license.
 * Polling /api/license/status ogni 5 min per intercettare revoche server-side.
 */
export default function App() {
  const theme = useThemeStore((s) => s.theme);
  const applyTheme = useThemeStore((s) => s.applyTheme);

  const licenseValid = useLicenseStore((s) => s.isValid);
  const fetchLicenseStatus = useLicenseStore((s) => s.fetchStatus);

  // Flag: true dopo che il primo fetch è terminato (success o fail).
  // Necessario per distinguere "fetch in corso" da "no license attivata" —
  // entrambi danno status="unknown" nello store iniziale e nel backend response.
  const [initialFetchDone, setInitialFetchDone] = useState(false);

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

  // License gate: fetch status all'avvio (con flag initialFetchDone) + polling 5 min
  useEffect(() => {
    fetchLicenseStatus().finally(() => setInitialFetchDone(true));
    const id = setInterval(() => fetchLicenseStatus(), 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [fetchLicenseStatus]);

  // Fetch iniziale ancora in corso: spinner minimale (no flash di contenuto).
  // Bg sco-bg per rispettare dark mode default — niente flash bianco.
  if (!initialFetchDone) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-sco-bg">
        <div className="flex items-center gap-3 text-sm text-sco-muted-foreground">
          <span className="h-2 w-2 animate-pulse-soft rounded-full bg-sco-blue" />
          <span>Verifica license...</span>
        </div>
      </div>
    );
  }

  // Fetch completato + license non valida → mostra LicenseScreen
  if (!licenseValid) {
    return <LicenseScreen />;
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-sco-bg text-sco-text dark:text-sco-text-dark">
      {/* Sidebar sinistra ricca stile Claude Desktop */}
      <Sidebar />

      {/* Colonna destra: header minimale + content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />

        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
