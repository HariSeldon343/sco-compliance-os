// SCO Compliance OS — top header con brand, theme toggle, user menu, tagline
import { useState } from "react";
import { Moon, Sun, Monitor, ChevronDown, LogOut, Cog } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useThemeStore, type Theme } from "@/store/theme-store";
import { cn } from "@/lib/cn";

// Stub utente loggato — verrà sostituito da auth reale via backend
const STUB_USER = {
  name: "Antonio Amodeo",
  email: "a.oedoma@gmail.com",
};

const THEME_OPTIONS: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Chiaro", icon: Sun },
  { value: "dark", label: "Scuro", icon: Moon },
  { value: "system", label: "Sistema", icon: Monitor },
];

export function Header() {
  const navigate = useNavigate();
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const currentThemeIcon = THEME_OPTIONS.find((t) => t.value === theme)?.icon ?? Monitor;
  const ThemeIcon = currentThemeIcon;

  const cycleTheme = () => {
    const order: Theme[] = ["light", "dark", "system"];
    const next = order[(order.indexOf(theme) + 1) % order.length];
    setTheme(next!);
  };

  return (
    <header className="flex items-center justify-between border-b border-sco-border bg-sco-bg px-6 py-3">
      {/* Brand + claim */}
      <div className="flex items-baseline gap-3">
        <h1 className="text-lg font-semibold text-sco-navy dark:text-sco-text-dark">
          SCO Compliance OS
        </h1>
        <span className="hidden text-xs text-sco-muted-foreground md:inline">
          Personal AI for Italian Compliance
        </span>
      </div>

      {/* Right cluster: tagline + theme + user */}
      <div className="flex items-center gap-4">
        <span className="hidden text-xs font-medium italic text-sco-amber lg:inline">
          Privato. Tuo. Italiano.
        </span>

        {/* Theme toggle (ciclico) */}
        <button
          type="button"
          onClick={cycleTheme}
          className="rounded-md p-2 text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
          aria-label={`Tema corrente: ${theme}. Click per cambiare.`}
          title={`Tema: ${theme}`}
        >
          <ThemeIcon size={16} />
        </button>

        {/* User menu */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="flex items-center gap-2 rounded-md px-2 py-1 hover:bg-sco-muted"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-sco-blue text-xs font-semibold text-white">
              {STUB_USER.name
                .split(" ")
                .map((p) => p[0])
                .join("")
                .slice(0, 2)}
            </div>
            <span className="hidden text-sm md:inline">{STUB_USER.name}</span>
            <ChevronDown
              size={14}
              className={cn(
                "text-sco-muted-foreground transition-transform",
                userMenuOpen && "rotate-180",
              )}
            />
          </button>

          {userMenuOpen && (
            <div className="absolute right-0 z-50 mt-1 w-56 rounded-md border border-sco-border bg-sco-surface-elevated p-1 shadow-lg">
              <div className="border-b border-sco-border px-3 py-2">
                <div className="text-sm font-medium">{STUB_USER.name}</div>
                <div className="text-xs text-sco-muted-foreground">
                  {STUB_USER.email}
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setUserMenuOpen(false);
                  navigate("/settings");
                }}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-sco-muted"
              >
                <Cog size={14} />
                Impostazioni
              </button>
              <button
                type="button"
                onClick={() => setUserMenuOpen(false)}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-red-600 hover:bg-sco-muted"
              >
                <LogOut size={14} />
                Esci (stub)
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
