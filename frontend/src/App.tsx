// SCO Compliance OS — root App: AuthGate FSM cumulativo 7 fasi + layout sidebar/header + outlet router
//
// Refactor v0.4.0: la logica multi-fase di onboarding vive in AuthGate (componente dedicato).
// App.tsx si limita a: tema, layout, outlet. Nessuna logica di phase machine qui.
//
// Refactor v0.6.0 (clean-room OpenHuman parity):
// - <AppBackground /> WebGL MeshGradient layer fixed inset-0 z-0 (visual depth)
// - <CommandPalette /> overlay globale Cmd/Ctrl+K (Linear/Raycast pattern)
// - useDefaultCommands() registra comandi navigation + theme + chat
// - Layout switch sidebar/bottom-tab via useLayoutStore
//
// Sequenza onboarding (gestita da AuthGate, vedi components/AuthGate.tsx):
//   License → EULA → Privacy → Demo → Vault picker REALE → Tutorial → Chat (ready)

import { useEffect } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { AuthGate } from "@/components/AuthGate";
import { AppBackground } from "@/components/AppBackground";
import { MascotOverlay } from "@/components/mascot/MascotOverlay";
import { CommandPalette } from "@/components/commands/CommandPalette";
import { useDefaultCommands } from "@/components/commands/useDefaultCommands";
import { BottomTabBar } from "@/components/nav/BottomTabBar";
import { useThemeStore } from "@/store/theme-store";
import { useLayoutStore } from "@/store/layout-store";

export default function App() {
  const theme = useThemeStore((s) => s.theme);
  const applyTheme = useThemeStore((s) => s.applyTheme);
  const layoutMode = useLayoutStore((s) => s.mode);

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

  // Registra comandi default Command Palette (navigation + theme + chat actions)
  useDefaultCommands();

  return (
    <AuthGate>
      {/* MeshGradient WebGL background — fixed inset-0 z-0, opacity bassa, no interaction */}
      <AppBackground opacity={0.08} />

      {/* Mascot 2D SVG floating overlay top-right — opt-in da Settings, default OFF */}
      <MascotOverlay />

      {/* Command Palette overlay globale ⌘K/Ctrl+K */}
      <CommandPalette />

      <div className="relative z-10 flex h-screen w-screen overflow-hidden bg-sco-bg/85 text-sco-text dark:text-sco-text-dark">
        {/* Sidebar sinistra ricca stile Claude Desktop (default layout) */}
        {layoutMode === "sidebar" && <Sidebar />}

        {/* Colonna destra: header minimale + content */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />

          <main className="flex-1 overflow-hidden">
            <Outlet />
          </main>
        </div>

        {/* BottomTabBar pill floating (alternative layout) */}
        {layoutMode === "bottom-tab" && <BottomTabBar />}
      </div>
    </AuthGate>
  );
}
