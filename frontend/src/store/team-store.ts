// SCO Compliance OS — Zustand store per modalita` team (Solo / Team) + membri
// v0.8.1: stub local-only finche backend non cabla endpoint /api/team. Cross-device
// team sync e` carry-over post-v0.8.x (oggi solo locale per macchina).

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type TeamMode = "solo" | "team";

export interface TeamMember {
  id: string;
  nome: string;
  ruolo: string;
  email: string;
}

export interface TeamState {
  mode: TeamMode;
  teamNome: string;
  membri: TeamMember[];
  mioRuolo: string;

  // Actions
  setMode: (m: TeamMode) => void;
  setTeamNome: (v: string) => void;
  setMioRuolo: (v: string) => void;
  addMembro: (m: Omit<TeamMember, "id">) => void;
  removeMembro: (id: string) => void;
  updateMembro: (id: string, patch: Partial<Omit<TeamMember, "id">>) => void;
  reset: () => void;
}

export const useTeamStore = create<TeamState>()(
  persist(
    (set) => ({
      mode: "solo",
      teamNome: "",
      membri: [],
      mioRuolo: "",

      setMode: (m) => set({ mode: m }),
      setTeamNome: (v) => set({ teamNome: v }),
      setMioRuolo: (v) => set({ mioRuolo: v }),

      addMembro: (m) =>
        set((s) => ({
          membri: [
            ...s.membri,
            {
              ...m,
              id: `mem-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            },
          ],
        })),

      removeMembro: (id) =>
        set((s) => ({
          membri: s.membri.filter((m) => m.id !== id),
        })),

      updateMembro: (id, patch) =>
        set((s) => ({
          membri: s.membri.map((m) => (m.id === id ? { ...m, ...patch } : m)),
        })),

      reset: () =>
        set({ mode: "solo", teamNome: "", membri: [], mioRuolo: "" }),
    }),
    {
      name: "sco-team",
      version: 1,
    },
  ),
);
