// SCO Compliance OS — sidebar 280px collapsible stile Claude Desktop / OpenHuman
import { useState, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  MessageSquare,
  Database,
  Plug,
  Brain,
  Settings,
  Plus,
  PanelLeftClose,
  PanelLeftOpen,
  ChevronDown,
  Pin,
  Sparkles,
  FolderTree,
  Network,
} from "lucide-react";

import { useChatStore } from "@/store/chat-store";
import { useVaultStore } from "@/store/vault-store";
import { cn } from "@/lib/cn";

// Fallback version se backend /health non risponde. Conv. 47 enforcement:
// fonte autoritativa = backend_version da GET /health (vedi useBackendVersion hook).
// v0.10.0: import diretto da package.json via Vite define __APP_VERSION__.
const APP_VERSION_FALLBACK =
  (typeof __APP_VERSION__ !== "undefined" && __APP_VERSION__) || "0.13.2";

interface NavItem {
  to: string;
  label: string;
  icon: typeof MessageSquare;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Chat", icon: MessageSquare },
  // Wave 2 OpenHuman replica — Wiki Memory Tree gerarchico L0/L1/L2
  { to: "/wiki", label: "Wiki", icon: FolderTree },
  // v0.12.0 GAMMA design: visualizza vault come rete force-directed 2D
  { to: "/grafo", label: "Grafo", icon: Network },
  // v0.8.1 DEV-SUBAGENT-BUILDER: gestione skill + wizard creazione
  { to: "/skills", label: "Skills", icon: Sparkles },
  { to: "/integrations", label: "Integrazioni", icon: Plug },
  { to: "/vault", label: "Vault", icon: Database },
  { to: "/memory", label: "Memoria", icon: Brain },
  { to: "/settings", label: "Impostazioni", icon: Settings },
];

/**
 * Timestamp relativo italiano: "8 min fa", "2h fa", "ieri", "l'altro ieri",
 * "lun scorso", "3 giorni fa", "12 mag", ...
 * Pattern Claude Desktop / WhatsApp.
 */
function relativeTimestamp(iso: string): string {
  const now = Date.now();
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const diffMs = now - t;
  const diffMin = Math.round(diffMs / 60_000);
  const diffH = Math.round(diffMs / 3_600_000);
  const diffD = Math.round(diffMs / 86_400_000);

  if (diffMin < 1) return "ora";
  if (diffMin < 60) return `${diffMin} min fa`;
  if (diffH < 24) return `${diffH}h fa`;
  if (diffD === 1) return "ieri";
  if (diffD === 2) return "l'altro ieri";
  if (diffD < 7) return `${diffD} giorni fa`;
  if (diffD < 30) return `${Math.floor(diffD / 7)} sett fa`;

  const d = new Date(iso);
  const months = [
    "gen",
    "feb",
    "mar",
    "apr",
    "mag",
    "giu",
    "lug",
    "ago",
    "set",
    "ott",
    "nov",
    "dic",
  ];
  return `${d.getDate()} ${months[d.getMonth()]}`;
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [vaultMenuOpen, setVaultMenuOpen] = useState(false);
  const [backendVersion, setBackendVersion] = useState<string>(APP_VERSION_FALLBACK);
  const navigate = useNavigate();

  const conversations = useChatStore((s) => s.conversations);
  const activeId = useChatStore((s) => s.activeConversationId);
  const setActive = useChatStore((s) => s.setActiveConversation);
  const createConv = useChatStore((s) => s.createConversation);
  const fetchConversations = useChatStore((s) => s.fetchConversations);
  // v0.8.1 fix auto-navigation: track lastAutoNavigated per intercettare
  // auto-select dello store e triggera react-router navigate('/'). Lo store
  // non puo` chiamare useNavigate (e' un hook), quindi il pattern e' "store
  // marca, sidebar reagisce con effect".
  const lastAutoNavigated = useChatStore((s) => s.lastAutoNavigated);

  // v1.0.2 fix sidebar visibility: auto-fetch al mount + polling 5s.
  // Backend è single source of truth (Conv. 47): la sidebar deve riflettere
  // SEMPRE lo stato corrente del DB, anche per conversation auto-create dal
  // skill loader post-vault.registered (os-setup → "Configurazione iniziale del vault X").
  useEffect(() => {
    // Mount immediato: silent=false per mostrare toast su nuove "Configurazione iniziale"
    void fetchConversations({ silent: false });
    // Polling 5s: silent=true per non bombardare di toast (solo merge state).
    const intervalId = setInterval(() => {
      void fetchConversations({ silent: false });
    }, 5000);
    return () => clearInterval(intervalId);
  }, [fetchConversations]);

  // v0.8.1 fix auto-navigation: quando store auto-seleziona una nuova
  // "Configurazione iniziale" (lastAutoNavigated cambia), forza navigate('/')
  // cosi` l'utente vede subito il contenuto della chat invece di restare
  // su /vault o /settings o /integrations. Pattern: store marca, sidebar
  // reagisce con effect.
  useEffect(() => {
    if (lastAutoNavigated && activeId === lastAutoNavigated) {
      // Verifica che siamo effettivamente atterrati sulla welcome chat
      // dell'auto-nav (no race con manuali setActive concorrenti).
      if (window.location.pathname !== "/") {
        navigate("/");
      }
    }
  }, [lastAutoNavigated, activeId, navigate]);

  // v0.8.1 fix auto-navigation: fallback ridondante per assicurare auto-select
  // anche in scenari edge dove fetchConversations potrebbe non aver scattato.
  // Watch conversations dictionary: se compare nuova "Configurazione iniziale"
  // o "Ottimizzazione iniziale" (v0.13.2 DEV-AUTO-OPTIMIZER) non ancora
  // auto-naviata E utente e' su welcome screen → seleziona + naviga.
  // Pattern Conv. 47/48 single source of truth: deduce dallo store.
  useEffect(() => {
    const optimizerWelcome = Object.values(conversations).find((c) =>
      c.title.startsWith("Ottimizzazione iniziale del vault"),
    );
    const configWelcome = Object.values(conversations).find((c) =>
      c.title.startsWith("Configurazione iniziale del vault"),
    );
    // Priorita: optimizer ha priorita su config welcome quando entrambe attive.
    const welcomeCandidate = optimizerWelcome ?? configWelcome;
    if (!welcomeCandidate) return;
    // Salta se gia` auto-naviata (rispetta scelta utente di muoversi altrove)
    if (lastAutoNavigated === welcomeCandidate.id) return;
    // Salta se l'utente sta gia` su una conv (no preempt: utente lavora altrove)
    if (activeId && activeId !== welcomeCandidate.id) return;
    // Tutte condizioni OK → auto-select + naviga
    setActive(welcomeCandidate.id);
    useChatStore.setState({ lastAutoNavigated: welcomeCandidate.id });
    if (window.location.pathname !== "/") {
      navigate("/");
    }
  }, [conversations, activeId, lastAutoNavigated, setActive, navigate]);

  // Conv. 47 enforcement v0.7.1: vault attivo + versione = single source of truth.
  // Vault da useVaultStore (era hardcoded "Second Brain" pre-v0.7.1).
  // Versione da backend /health (era hardcoded "0.3.0" pre-v0.7.1, drift cumulativo
  // 4 release v0.4/v0.5/v0.6/v0.7 con display sbagliato).
  const vaults = useVaultStore((s) => s.vaults);
  const selectedVaultId = useVaultStore((s) => s.selectedVaultId);
  const activeVaultName =
    vaults.find((v) => v.id === selectedVaultId)?.name ?? "Nessun vault";

  useEffect(() => {
    const BACKEND_URL =
      import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";
    fetch(`${BACKEND_URL}/health`)
      .then((r) => r.json())
      .then((data: { backend_version?: string }) => {
        if (data.backend_version) setBackendVersion(data.backend_version);
      })
      .catch(() => {
        // backend offline o /health non risponde: mantieni fallback
      });
  }, []);

  const conversationList = Object.values(conversations).sort((a, b) =>
    b.updated_at.localeCompare(a.updated_at),
  );

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-sco-border bg-sco-surface transition-[width] duration-200 ease-out",
        collapsed ? "w-[60px]" : "w-[280px]",
      )}
    >
      {/* === Brand row === */}
      <div
        className={cn(
          "flex items-center border-b border-sco-border",
          collapsed ? "justify-center px-2 py-3" : "justify-between px-4 py-3",
        )}
      >
        {!collapsed ? (
          <>
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-sco-navy to-sco-blue text-white shadow-sm">
                <span className="text-sm font-bold tracking-tight">S</span>
              </div>
              <div className="flex flex-col leading-tight">
                <span className="text-sm font-semibold text-sco-text dark:text-sco-text-dark">
                  SCO Compliance
                </span>
                <span className="text-[11px] text-sco-muted-foreground">
                  Personal AI
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setCollapsed(true)}
              className="rounded-md p-1.5 text-sco-muted-foreground transition-colors hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
              aria-label="Comprimi sidebar"
              title="Comprimi sidebar"
            >
              <PanelLeftClose size={16} />
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => setCollapsed(false)}
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-sco-navy to-sco-blue text-white shadow-sm transition-transform hover:scale-105"
            aria-label="Espandi sidebar"
            title="Espandi sidebar"
          >
            <PanelLeftOpen size={16} />
          </button>
        )}
      </div>

      {/* === Nuova chat (CTA primary) === */}
      <div className={cn("px-3 pt-3", collapsed && "px-2")}>
        <button
          type="button"
          onClick={() => {
            createConv();
            navigate("/");
          }}
          className={cn(
            "group flex w-full items-center gap-2 rounded-lg bg-sco-blue px-3 py-2.5 text-sm font-medium text-white shadow-sm transition-all duration-150 hover:bg-sco-navy hover:shadow",
            collapsed && "justify-center px-0",
          )}
          title="Nuova chat"
        >
          <Plus
            size={16}
            className="transition-transform group-hover:rotate-90"
          />
          {!collapsed && <span>Nuova chat</span>}
        </button>
      </div>

      {/* === Vault picker (solo expanded) === */}
      {!collapsed && (
        <div className="px-3 pt-3">
          <button
            type="button"
            onClick={() => setVaultMenuOpen(!vaultMenuOpen)}
            className="flex w-full items-center justify-between rounded-lg border border-sco-border bg-sco-bg px-3 py-2 text-xs transition-colors hover:border-sco-blue/60"
          >
            <span className="flex items-center gap-2 truncate">
              <Database
                size={13}
                className="shrink-0 text-sco-blue"
                aria-hidden="true"
              />
              <span className="truncate font-medium">{activeVaultName}</span>
            </span>
            <ChevronDown
              size={13}
              className={cn(
                "shrink-0 text-sco-muted-foreground transition-transform",
                vaultMenuOpen && "rotate-180",
              )}
            />
          </button>
          {vaultMenuOpen && (
            <div className="mt-2 rounded-lg border border-sco-border bg-sco-surface-elevated p-3 text-xs text-sco-muted-foreground">
              Nessun altro vault collegato.{" "}
              <NavLink
                to="/vault"
                className="font-medium text-sco-blue hover:underline"
                onClick={() => setVaultMenuOpen(false)}
              >
                Aggiungi vault
              </NavLink>
              .
            </div>
          )}
        </div>
      )}

      {/* === Pinned (sezione futura, mostrata vuota come placeholder) === */}
      {!collapsed && (
        <div className="px-3 pt-4">
          <div className="flex items-center gap-1.5 px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
            <Pin size={10} />
            <span>Pinned</span>
          </div>
          <div className="rounded-md px-2 py-1.5 text-[11px] italic text-sco-muted-foreground/70">
            Nessuna chat fissata
          </div>
        </div>
      )}

      {/* === Conversazioni recenti === */}
      {!collapsed && (
        <div className="mt-2 flex-1 overflow-y-auto px-2">
          <div className="flex items-center gap-1.5 px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
            <Sparkles size={10} />
            <span>Recenti</span>
          </div>
          <ul className="space-y-0.5">
            {conversationList.map((c) => {
              const isActive = activeId === c.id;
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setActive(c.id);
                      navigate("/");
                    }}
                    className={cn(
                      "group flex w-full flex-col gap-0.5 rounded-md px-3 py-2 text-left transition-colors duration-150",
                      isActive
                        ? "bg-sco-blue/10 text-sco-text dark:text-sco-text-dark"
                        : "hover:bg-sco-muted",
                    )}
                    title={c.title}
                  >
                    <span
                      className={cn(
                        "truncate text-sm leading-tight",
                        isActive
                          ? "font-medium text-sco-blue dark:text-sco-text-dark"
                          : "text-sco-text dark:text-sco-text-dark",
                      )}
                    >
                      {c.title}
                    </span>
                    <span
                      className={cn(
                        "text-[10px] uppercase tracking-wide",
                        isActive
                          ? "text-sco-blue/70"
                          : "text-sco-muted-foreground",
                      )}
                    >
                      {relativeTimestamp(c.updated_at)}
                    </span>
                  </button>
                </li>
              );
            })}
            {conversationList.length === 0 && (
              <li className="px-3 py-2 text-xs italic text-sco-muted-foreground">
                Nessuna conversazione.
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Spacer per collapsed (le conversation list non si mostrano in collapsed) */}
      {collapsed && <div className="flex-1" />}

      {/* === Nav items (bottom) === */}
      <nav
        className={cn(
          "border-t border-sco-border py-2",
          collapsed ? "px-2" : "px-2",
        )}
      >
        <ul className="space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            // v0.13.2 PSI-2: data-tour stable selectors per react-joyride walkthrough
            // first-launch. Stessi attributi compatibili anche con futuri snapshot test.
            const tourId = `sidebar-${item.to === "/" ? "chat" : item.to.replace("/", "")}`;
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === "/"}
                  data-tour={tourId}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2.5 rounded-md text-sm transition-colors duration-150",
                      collapsed
                        ? "justify-center px-2 py-2"
                        : "px-3 py-2",
                      isActive
                        ? "bg-sco-blue/15 font-medium text-sco-blue dark:text-sco-text-dark"
                        : "text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark",
                    )
                  }
                  title={collapsed ? item.label : undefined}
                >
                  <Icon size={15} className="shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* === Footer versione === */}
      <div
        className={cn(
          "border-t border-sco-border text-[10px] uppercase tracking-wider text-sco-muted-foreground/70",
          collapsed ? "px-2 py-2 text-center" : "px-4 py-2",
        )}
      >
        v{backendVersion}
      </div>
    </aside>
  );
}
