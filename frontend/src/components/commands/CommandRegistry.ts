// SCO Compliance OS — Command Registry (Zustand singleton, runtime command registration)
//
// Clean-room implementation Linear/Raycast pattern:
// - registry singleton in-memory + Zustand reactivity
// - registerCommand / unregisterCommand API per moduli che injettano comandi runtime
// - command groups (category) per rendering organizzato nel CommandPalette
// - keywords[] per fuzzy matching extra (cmdk filtra anche su questi)
//
// Nessuna copia da OpenHuman GPL. Architettura derivata dalla doc cmdk (MIT)
// + pattern Zustand store standard.

import { create } from "zustand";
import type { LucideIcon } from "lucide-react";

export type CommandCategory =
  | "navigation"
  | "actions"
  | "search"
  | "vault"
  | "skills"
  | "settings";

export interface CommandDef {
  /** ID univoco runtime (es. "nav.chat", "action.new-conv", "skill.audit-iso27001") */
  id: string;
  /** Etichetta visibile (italiano) */
  label: string;
  /** Categoria per grouping render */
  category: CommandCategory;
  /** Icona lucide-react (opzionale) */
  icon?: LucideIcon;
  /** Parole chiave extra per matching fuzzy (cmdk usa label + keywords) */
  keywords?: string[];
  /** Sotto-label opzionale (es. shortcut, descrizione) */
  hint?: string;
  /** Azione invocata su select. Riceve callback close per chiudere la palette */
  action: (close: () => void) => void | Promise<void>;
}

interface CommandRegistryState {
  commands: Record<string, CommandDef>;
  registerCommand: (cmd: CommandDef) => void;
  registerCommands: (cmds: CommandDef[]) => void;
  unregisterCommand: (id: string) => void;
  clear: () => void;
  getCommandsByCategory: () => Record<CommandCategory, CommandDef[]>;
}

const CATEGORY_LABELS: Record<CommandCategory, string> = {
  navigation: "Naviga",
  actions: "Azioni",
  search: "Cerca",
  vault: "Vault",
  skills: "Skill",
  settings: "Impostazioni",
};

const CATEGORY_ORDER: CommandCategory[] = [
  "navigation",
  "actions",
  "search",
  "vault",
  "skills",
  "settings",
];

export const useCommandRegistry = create<CommandRegistryState>()((set, get) => ({
  commands: {},

  registerCommand: (cmd) =>
    set((state) => ({
      commands: { ...state.commands, [cmd.id]: cmd },
    })),

  registerCommands: (cmds) =>
    set((state) => {
      const next = { ...state.commands };
      for (const cmd of cmds) {
        next[cmd.id] = cmd;
      }
      return { commands: next };
    }),

  unregisterCommand: (id) =>
    set((state) => {
      if (!(id in state.commands)) return state;
      const next = { ...state.commands };
      delete next[id];
      return { commands: next };
    }),

  clear: () => set({ commands: {} }),

  getCommandsByCategory: () => {
    const grouped: Record<CommandCategory, CommandDef[]> = {
      navigation: [],
      actions: [],
      search: [],
      vault: [],
      skills: [],
      settings: [],
    };
    for (const cmd of Object.values(get().commands)) {
      grouped[cmd.category].push(cmd);
    }
    return grouped;
  },
}));

export { CATEGORY_LABELS, CATEGORY_ORDER };
