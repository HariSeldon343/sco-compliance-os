// SCO Compliance OS — root App: AuthGate FSM cumulativo 7 fasi + layout sidebar/header + outlet router
//
// Refactor v0.4.0: la logica multi-fase di onboarding vive in AuthGate (componente dedicato).
// App.tsx si limita a: tema, layout, outlet. Nessuna logica di phase machine qui.
//
// Sequenza onboarding (gestita da AuthGate, vedi components/AuthGate.tsx):
//   License → EULA → Privacy → Demo → Vault picker REALE → Tutorial → Chat (ready)

import { useEffect } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { AuthGate } from "@/components/AuthGate";
import { useThemeStore } from "@/store/theme-store";

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
    <AuthGate>
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
    </AuthGate>
  );
}
