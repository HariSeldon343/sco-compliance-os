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
// v0.13.0 PSI:
// - Page transitions: AnimatePresence wrapper su <Outlet /> con fade+slide-up
// - key = location.pathname per re-mount animato a ogni navigation
//
// Sequenza onboarding (gestita da AuthGate, vedi components/AuthGate.tsx):
//   License → EULA → Privacy → Demo → Vault picker REALE → Tutorial → Chat (ready)

import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";

import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { AuthGate } from "@/components/AuthGate";
import { AppBackground } from "@/components/AppBackground";
import { MascotOverlay } from "@/components/mascot/MascotOverlay";
import { CommandPalette } from "@/components/commands/CommandPalette";
import { useDefaultCommands } from "@/components/commands/useDefaultCommands";
import { BottomTabBar } from "@/components/nav/BottomTabBar";
import { WalkthroughTour } from "@/components/WalkthroughTour";
import { WipeOrKeepDialog } from "@/components/system/WipeOrKeepDialog";
import { useThemeStore } from "@/store/theme-store";
import { useLayoutStore } from "@/store/layout-store";
import { useWalkthroughStore } from "@/store/walkthrough-store";

export default function App() {
  const theme = useThemeStore((s) => s.theme);
  const applyTheme = useThemeStore((s) => s.applyTheme);
  const layoutMode = useLayoutStore((s) => s.mode);
  const location = useLocation();

  // v0.13.2 PSI-2: walkthrough first-launch (auto) + on-demand (forceRun)
  const walkthroughForceRun = useWalkthroughStore((s) => s.forceRun);
  const resetWalkthroughTrigger = useWalkthroughStore((s) => s.resetTrigger);

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
            {/* Page transitions v0.13.0 PSI: AnimatePresence con mode="wait"
                attende che la route uscente completi exit prima di entrare
                la nuova. key = pathname garantisce re-mount per ciascuna
                route. Subtle fade+slide-up 240ms ease-out-expo. */}
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{
                  duration: 0.24,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="h-full"
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </main>
        </div>

        {/* BottomTabBar pill floating (alternative layout) */}
        {layoutMode === "bottom-tab" && <BottomTabBar />}
      </div>

      {/* v0.13.2 PSI-2: Walkthrough first-launch joyride 10-step.
          Auto-trigger se flag localStorage assente; on-demand via store. */}
      <WalkthroughTour
        forceRun={walkthroughForceRun}
        onFinish={resetWalkthroughTrigger}
      />

      {/* Feature 1 v0.15.0: scelta Mantieni/Riparti dopo un aggiornamento.
          Compare una sola volta quando la versione cambia e ci sono dati. */}
      <WipeOrKeepDialog />
    </AuthGate>
  );
}
