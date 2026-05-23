// SCO Compliance OS — sidebar 280px collapsible con logo + vault dropdown + conversations + nav
import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  MessageSquare,
  Database,
  Plug,
  Brain,
  Settings,
  Plus,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
} from "lucide-react";

import { useChatStore } from "@/store/chat-store";
import { cn } from "@/lib/cn";

// Versione app — bumped manualmente con bump version script ogni release Conv. 47.
// TODO v0.2.0: fetch dinamico da backend /health endpoint (rimuove hardcode).
const APP_VERSION_PLACEHOLDER = "0.1.2";

interface NavItem {
  to: string;
  label: string;
  icon: typeof MessageSquare;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Chat", icon: MessageSquare },
  { to: "/integrations", label: "Integrazioni", icon: Plug },
  { to: "/vault", label: "Vault", icon: Database },
  { to: "/memory", label: "Memoria", icon: Brain },
  { to: "/settings", label: "Impostazioni", icon: Settings },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [vaultMenuOpen, setVaultMenuOpen] = useState(false);
  const navigate = useNavigate();

  const conversations = useChatStore((s) => s.conversations);
  const activeId = useChatStore((s) => s.activeConversationId);
  const setActive = useChatStore((s) => s.setActiveConversation);
  const createConv = useChatStore((s) => s.createConversation);

  const conversationList = Object.values(conversations).sort((a, b) =>
    b.updated_at.localeCompare(a.updated_at),
  );

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-sco-border bg-sco-surface transition-all duration-200",
        collapsed ? "w-16" : "w-[280px]",
      )}
    >
      {/* Logo + toggle */}
      <div className="flex items-center justify-between border-b border-sco-border px-4 py-3">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-sco-navy text-white font-bold">
              S
            </div>
            <div className="flex flex-col leading-tight">
              <span className="text-sm font-semibold text-sco-navy dark:text-sco-text-dark">
                SCO Compliance OS
              </span>
              <span className="text-xs text-sco-muted-foreground">
                Personal AI
              </span>
            </div>
          </div>
        )}
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          className="rounded-md p-1 text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
          aria-label={collapsed ? "Espandi sidebar" : "Comprimi sidebar"}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Vault dropdown (stub) */}
      {!collapsed && (
        <div className="border-b border-sco-border px-3 py-3">
          <button
            type="button"
            onClick={() => setVaultMenuOpen(!vaultMenuOpen)}
            className="flex w-full items-center justify-between rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm hover:border-sco-blue"
          >
            <span className="flex items-center gap-2 truncate">
              <Database size={14} className="text-sco-blue" />
              <span className="truncate">Vault: Second Brain</span>
            </span>
            <ChevronDown
              size={14}
              className={cn(
                "text-sco-muted-foreground transition-transform",
                vaultMenuOpen && "rotate-180",
              )}
            />
          </button>
          {vaultMenuOpen && (
            <div className="mt-2 rounded-md border border-sco-border bg-sco-surface-elevated p-2 text-xs text-sco-muted-foreground">
              Nessun altro vault collegato. Vai a{" "}
              <NavLink to="/vault" className="text-sco-blue hover:underline">
                Vault
              </NavLink>{" "}
              per aggiungerne uno.
            </div>
          )}
        </div>
      )}

      {/* Nuova chat */}
      <div className="px-3 py-3">
        <button
          type="button"
          onClick={() => {
            createConv();
            navigate("/");
          }}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-sco-navy px-3 py-2 text-sm font-medium text-white hover:bg-sco-blue"
        >
          <Plus size={16} />
          {!collapsed && <span>Nuova chat</span>}
        </button>
      </div>

      {/* Conversazioni recenti */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto px-2">
          <div className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-sco-muted-foreground">
            Recenti
          </div>
          <ul className="space-y-1">
            {conversationList.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => {
                    setActive(c.id);
                    navigate("/");
                  }}
                  className={cn(
                    "w-full truncate rounded-md px-3 py-2 text-left text-sm hover:bg-sco-muted",
                    activeId === c.id &&
                      "bg-sco-muted font-medium text-sco-navy",
                  )}
                  title={c.title}
                >
                  {c.title}
                </button>
              </li>
            ))}
            {conversationList.length === 0 && (
              <li className="px-3 py-2 text-xs text-sco-muted-foreground">
                Nessuna conversazione.
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Nav items */}
      <nav className="border-t border-sco-border px-2 py-2">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-sco-muted",
                      isActive && "bg-sco-muted font-medium text-sco-navy",
                    )
                  }
                >
                  <Icon size={16} />
                  {!collapsed && <span>{item.label}</span>}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer versione */}
      {!collapsed && (
        <div className="border-t border-sco-border px-4 py-2 text-xs text-sco-muted-foreground">
          v{APP_VERSION_PLACEHOLDER}
        </div>
      )}
    </aside>
  );
}
