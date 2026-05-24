// SCO Compliance OS — layout store Zustand 5 persistente
//
// Pattern Conv. 47 single source of truth: la modalità di navigazione
// (sidebar laterale vs barra inferiore) è una preferenza utente persistita
// in localStorage. Il componente App.tsx legge questo store e decide
// quale layout renderizzare.

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type LayoutMode = "sidebar" | "bottom-tab";

interface LayoutState {
  /** Modalità di navigazione attiva */
  mode: LayoutMode;
  /** Cambia modalità */
  setMode: (mode: LayoutMode) => void;
  /** Toggle rapido fra sidebar e bottom-tab */
  toggleMode: () => void;
}

export const useLayoutStore = create<LayoutState>()(
  persist(
    (set, get) => ({
      // Default sidebar — pattern Claude Desktop / OpenHuman.
      // BottomTabBar è alternativa per setup minimal / mobile-feel.
      mode: "sidebar",

      setMode: (mode) => set({ mode }),

      toggleMode: () =>
        set({
          mode: get().mode === "sidebar" ? "bottom-tab" : "sidebar",
        }),
    }),
    {
      name: "sco-layout",
      // Persiste solo il valore `mode`, non le azioni
      partialize: (state) => ({ mode: state.mode }),
      version: 1,
    },
  ),
);
