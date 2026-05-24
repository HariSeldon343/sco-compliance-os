// SCO Compliance OS — Zustand store per profilo utente (nome, ruolo, ambito)
// v0.8.1: stub local-only finche backend non cabla endpoint /api/profile. Email e
// tenantId vivono in license-store (single source of truth, Conv. 47).

import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ProfileState {
  // Nome visualizzato (es. "Antonio Amodeo"). Default: vuoto, popolato da
  // os-setup wizard o manualmente in Settings.
  nome: string;
  // Ruolo professionale (es. "Consulente Senior", "Lead Auditor", "RSPP").
  ruolo: string;
  // Ambito di competenza primario (es. "Cybersecurity NIS2", "Sanità").
  ambito: string;

  // Actions
  setNome: (v: string) => void;
  setRuolo: (v: string) => void;
  setAmbito: (v: string) => void;
  reset: () => void;
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      nome: "",
      ruolo: "",
      ambito: "",

      setNome: (v) => set({ nome: v }),
      setRuolo: (v) => set({ ruolo: v }),
      setAmbito: (v) => set({ ambito: v }),

      reset: () => set({ nome: "", ruolo: "", ambito: "" }),
    }),
    {
      name: "sco-profile",
      version: 1,
    },
  ),
);
