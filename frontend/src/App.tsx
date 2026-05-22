// SCO Compliance OS — root App con LicenseGate + layout sidebar + header + outlet router
import { useEffect } from "react";
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

  const licenseStatus = useLicenseStore((s) => s.status);
  const licenseValid = useLicenseStore((s) => s.isValid);
  const fetchLicenseStatus = useLicenseStore((s) => s.fetchStatus);

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

  // License gate: fetch status all'avvio + polling 5 min per revoche server-side
  useEffect(() => {
    fetchLicenseStatus();
    const id = setInterval(() => fetchLicenseStatus(), 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [fetchLicenseStatus]);

  // Mostra LicenseScreen finché non si conferma valida
  // (status "unknown" significa fetch iniziale non ancora completato)
  if (!licenseValid && licenseStatus !== "unknown") {
    return <LicenseScreen />;
  }
  // Fetch iniziale in corso: spinner minimale (no flash di contenuto)
  if (licenseStatus === "unknown") {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="text-sm text-slate-500 dark:text-slate-400">
          Verifica license...
        </div>
      </div>
    );
  }

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
