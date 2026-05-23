// SCO Compliance OS — top header minimale 56px stile Claude Desktop
import { useState } from "react";
import { Moon, Sun, Monitor, ChevronDown, LogOut, Cog } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useThemeStore, type Theme } from "@/store/theme-store";
import { useChatStore } from "@/store/chat-store";
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

  // Titolo della conversation attiva — mostrato come breadcrumb minimale.
  const activeId = useChatStore((s) => s.activeConversationId);
  const conversations = useChatStore((s) => s.conversations);
  const activeTitle =
    activeId && conversations[activeId]
      ? conversations[activeId].title
      : "Nuova conversazione";

  const currentThemeIcon =
    THEME_OPTIONS.find((t) => t.value === theme)?.icon ?? Moon;
  const ThemeIcon = currentThemeIcon;

  const cycleTheme = () => {
    const order: Theme[] = ["light", "dark", "system"];
    const next = order[(order.indexOf(theme) + 1) % order.length];
    setTheme(next!);
  };

  const initials = STUB_USER.name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-sco-border bg-sco-bg px-6">
      {/* Breadcrumb sinistro: titolo conversation attiva */}
      <div className="flex min-w-0 items-center gap-2">
        <h1
          className="truncate text-sm font-medium text-sco-text dark:text-sco-text-dark"
          title={activeTitle}
        >
          {activeTitle}
        </h1>
      </div>

      {/* Cluster destro: theme toggle + user menu */}
      <div className="flex items-center gap-1">
        {/* Theme toggle (ciclico, compatto) */}
        <button
          type="button"
          onClick={cycleTheme}
          className="rounded-md p-2 text-sco-muted-foreground transition-colors hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
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
            className={cn(
              "flex items-center gap-2 rounded-md px-2 py-1 transition-colors",
              userMenuOpen ? "bg-sco-muted" : "hover:bg-sco-muted",
            )}
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-sco-navy to-sco-blue text-xs font-semibold text-white">
              {initials}
            </div>
            <span className="hidden text-sm font-medium md:inline">
              {STUB_USER.name}
            </span>
            <ChevronDown
              size={13}
              className={cn(
                "text-sco-muted-foreground transition-transform",
                userMenuOpen && "rotate-180",
              )}
            />
          </button>

          {userMenuOpen && (
            <>
              {/* Backdrop click-out */}
              <div
                className="fixed inset-0 z-40"
                onClick={() => setUserMenuOpen(false)}
              />
              <div className="absolute right-0 z-50 mt-1.5 w-60 overflow-hidden rounded-lg border border-sco-border bg-sco-surface-elevated p-1 shadow-xl">
                <div className="border-b border-sco-border px-3 py-2.5">
                  <div className="text-sm font-semibold text-sco-text dark:text-sco-text-dark">
                    {STUB_USER.name}
                  </div>
                  <div className="truncate text-xs text-sco-muted-foreground">
                    {STUB_USER.email}
                  </div>
                </div>
                <div className="py-1">
                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false);
                      navigate("/settings");
                    }}
                    className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm text-sco-text transition-colors hover:bg-sco-muted dark:text-sco-text-dark"
                  >
                    <Cog size={14} className="text-sco-muted-foreground" />
                    Impostazioni
                  </button>
                  <button
                    type="button"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm text-red-500 transition-colors hover:bg-sco-muted"
                  >
                    <LogOut size={14} />
                    Esci
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
