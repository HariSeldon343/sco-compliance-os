// SCO Compliance OS — theme store persistente (light/dark/system) Zustand 5
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark" | "system";

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  // Applica la classe `dark` su <html> in base allo stato + preferenza OS
  applyTheme: () => void;
}

function resolveSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      // Default dark mode — reference Claude Desktop / OpenHuman.
      // L'utente può sempre passare a light/system dal selettore in Settings.
      theme: "dark",

      setTheme: (theme) => {
        set({ theme });
        get().applyTheme();
      },

      applyTheme: () => {
        if (typeof document === "undefined") return;
        const { theme } = get();
        const effective = theme === "system" ? resolveSystemTheme() : theme;
        const root = document.documentElement;
        if (effective === "dark") {
          root.classList.add("dark");
        } else {
          root.classList.remove("dark");
        }
      },
    }),
    {
      name: "sco-theme",
      // Persiste solo il valore `theme`, non l'azione
      partialize: (state) => ({ theme: state.theme }),
      // Bump version per invalidare LocalStorage di utenti early-access:
      // chi aveva "system" persistito prima del 23/05/2026 viene ri-defaultato su "dark".
      version: 2,
      migrate: (persisted: unknown, fromVersion: number) => {
        if (fromVersion < 2) {
          return { theme: "dark" } as { theme: Theme };
        }
        return persisted as { theme: Theme };
      },
    },
  ),
);
