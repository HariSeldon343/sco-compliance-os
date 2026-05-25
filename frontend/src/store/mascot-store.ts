// SCO Compliance OS — mascot store Zustand 5 persistente.
//
// Stato del mascot 2D SVG procedurale clean-room (no Remotion, no Lottie).
// Cinque stati visuali mutuamente esclusivi: idle | listening | thinking | speaking | celebrating.
// Toggle `enabled` di opt-in (default OFF per UX professionale consulenza).
// Variante visiva opzionale per palette: blue (navy + blue) | amber (navy + amber) |
// minimal (navy + bianco senza accent caldo).
//
// Pattern Conv. 47 single source of truth: lo stato vive in store dedicato,
// l'overlay legge da qui, i componenti chat (ChatInput, ChatArea, futuro TTS)
// pubblicano transizioni di stato via setState. Persistenza solo di `enabled`
// + `variant`: lo `state` runtime resetta su 'idle' a ogni avvio app.
//
// v0.13.0 PSI: stato `celebrating` aggiunto come 5° state per task completati,
// onboarding completato, success toast events. Animation: jump up + sparkles.

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type MascotState =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "celebrating";
export type MascotVariant = "blue" | "amber" | "minimal";

interface MascotStore {
  /** Stato visuale corrente — NON persistito, ricalcolato a ogni sessione. */
  state: MascotState;
  /** Toggle utente opt-in. Default OFF — il consulente abilita dalla pagina Impostazioni. */
  enabled: boolean;
  /** Variante palette. Default blue (brand SCO core). */
  variant: MascotVariant;
  /** Cambia stato runtime (chiamato da listener chat / mic / TTS). */
  setState: (state: MascotState) => void;
  /** Abilita o disabilita l'overlay. */
  setEnabled: (enabled: boolean) => void;
  /** Cambia variante palette. */
  setVariant: (variant: MascotVariant) => void;
  /** Reset rapido a idle (es. al cambio conversation). */
  resetToIdle: () => void;
  /**
   * Trigger celebration one-shot (v0.13.0 PSI).
   * Setta state=celebrating per `durationMs` poi auto-reset a idle.
   * Usabile in success toast events (task completed, vault created,
   * onboarding done). Default 2500ms = jump + sparkle cycle completo.
   */
  celebrate: (durationMs?: number) => void;
}

export const useMascotStore = create<MascotStore>()(
  persist(
    (set, get) => ({
      state: "idle",
      enabled: false,
      variant: "blue",
      setState: (state) => set({ state }),
      setEnabled: (enabled) => set({ enabled }),
      setVariant: (variant) => set({ variant }),
      resetToIdle: () => set({ state: "idle" }),
      celebrate: (durationMs = 2500) => {
        // v0.13.0 PSI: celebration one-shot con auto-reset.
        // Se mascot disabled, no-op (rispetta preferenza utente).
        if (!get().enabled) return;
        set({ state: "celebrating" });
        setTimeout(() => {
          // Solo se nel frattempo non e' cambiato a un'altra cosa (es. mic on).
          if (get().state === "celebrating") {
            set({ state: "idle" });
          }
        }, durationMs);
      },
    }),
    {
      name: "sco-mascot",
      // Persistiamo solo le preferenze utente. Lo stato runtime resetta a 'idle'
      // ad ogni avvio app (evita di restare bloccati su 'thinking' se l'app
      // viene chiusa durante uno streaming).
      partialize: (s) => ({ enabled: s.enabled, variant: s.variant }),
      version: 1,
    },
  ),
);
