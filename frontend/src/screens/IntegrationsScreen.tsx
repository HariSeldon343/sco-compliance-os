// SCO Compliance OS — schermata Integrazioni: grid connettori OAuth reali (Gmail / GCal / Drive / Slack / GitHub)
// Conv. 48 enforcement: stato connettori = backend single source of truth.
// Fetch reale da GET /api/integrations/available + connect/disconnect via store actions.
// OAuth flow: window.open via @tauri-apps/plugin-shell.open su oauth_url ricevuto dal backend.

import { useEffect, useMemo } from "react";
import {
  Mail,
  Calendar,
  HardDrive,
  MessageSquare,
  Github,
  Plug,
  Loader2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { open as openExternal } from "@tauri-apps/plugin-shell";

import { cn } from "@/lib/cn";
import { toast } from "sonner";
import {
  useIntegrationsStore,
  type IntegrationItem,
  type IntegrationStatus,
} from "@/store/integrations-store";
import { EmptyState } from "@/components/ui/EmptyState";

// Mappa slug → icona Lucide. Default Plug per slug nuovi non mappati.
const ICON_BY_SLUG: Record<string, typeof Mail> = {
  gmail: Mail,
  "google-calendar": Calendar,
  google_calendar: Calendar,
  "google-drive": HardDrive,
  google_drive: HardDrive,
  slack: MessageSquare,
  github: Github,
};

const STATUS_LABELS: Record<IntegrationStatus, string> = {
  connected: "Connesso",
  disconnected: "Non connesso",
  pending: "In attesa",
  error: "Errore",
};

const STATUS_COLORS: Record<IntegrationStatus, string> = {
  connected:
    "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  disconnected: "bg-sco-muted text-sco-muted-foreground",
  pending:
    "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  error: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

function ConnectorIcon({ slug }: { slug: string }) {
  const Icon = ICON_BY_SLUG[slug] ?? Plug;
  return <Icon size={20} />;
}

export function IntegrationsScreen() {
  const {
    integrations,
    loading,
    errorMessage,
    initialFetchDone,
    fetchIntegrations,
    connectIntegration,
    disconnectIntegration,
  } = useIntegrationsStore();

  // Fetch reale al mount. Conv. 48: backend è single source of truth.
  useEffect(() => {
    if (!initialFetchDone) {
      void fetchIntegrations();
    }
  }, [initialFetchDone, fetchIntegrations]);

  const sortedIntegrations = useMemo(() => {
    // Ordine canonico richiesto (Gmail / GCal / Drive / Slack / GitHub) — fallback alfabetico per slug nuovi.
    const order = [
      "gmail",
      "google-calendar",
      "google_calendar",
      "google-drive",
      "google_drive",
      "slack",
      "github",
    ];
    const indexOf = (slug: string) => {
      const i = order.indexOf(slug);
      return i === -1 ? 999 : i;
    };
    return [...integrations].sort((a, b) => indexOf(a.slug) - indexOf(b.slug));
  }, [integrations]);

  const handleConnect = async (item: IntegrationItem) => {
    const result = await connectIntegration(item.slug);
    if (!result) {
      toast.error(`Errore avvio OAuth per ${item.name}.`);
      return;
    }
    // OAuth flow: apri URL nel browser di sistema via Tauri shell.
    try {
      await openExternal(result.oauth_url);
      toast.info(
        `OAuth ${item.name} avviato. Completa l'autorizzazione nel browser.`,
      );
    } catch (err) {
      // Fallback: prova window.open puro (web preview / browser dev).
      try {
        window.open(result.oauth_url, "_blank", "noopener,noreferrer");
        toast.info(
          `OAuth ${item.name} avviato (fallback browser). Completa nel tab aperto.`,
        );
      } catch {
        toast.error(
          `Impossibile aprire il browser: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
    }
  };

  const handleDisconnect = async (item: IntegrationItem) => {
    const ok = await disconnectIntegration(item.slug);
    if (ok) {
      toast.success(`${item.name} disconnesso.`);
    } else {
      toast.error(`Disconnessione di ${item.name} fallita.`);
    }
  };

  return (
    <div className="h-full overflow-y-auto px-8 py-6">
      <div className="mx-auto max-w-5xl">
        <header className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-sco-navy dark:text-sco-text-dark">
              Integrazioni
            </h1>
            <p className="mt-1 text-sm text-sco-muted-foreground">
              Collega i tuoi servizi. Le credenziali vivono in keyring di
              sistema, mai in chiaro.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void fetchIntegrations()}
            disabled={loading}
            className="flex items-center gap-2 rounded-md border border-sco-border px-3 py-2 text-sm font-medium hover:bg-sco-muted disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw
              size={14}
              className={loading ? "animate-spin" : undefined}
            />
            Aggiorna
          </button>
        </header>

        {errorMessage && (
          <div className="mb-4 flex items-start gap-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {!initialFetchDone && loading && (
          <div className="flex items-center justify-center gap-2 py-12 text-sm text-sco-muted-foreground">
            <Loader2 size={16} className="animate-spin" />
            Caricamento integrazioni dal backend…
          </div>
        )}

        {initialFetchDone && sortedIntegrations.length === 0 && (
          <EmptyState
            icon={Plug}
            title="Nessuna integrazione attiva"
            description="Le integrazioni ti permettono di collegare Gmail, Calendar, Drive, Slack o GitHub all'agente. Quando saranno disponibili le vedrai qui. Nel frattempo aggiorna per ricontrollare."
            ctaLabel="Aggiorna"
            ctaAction={() => void fetchIntegrations()}
          />
        )}

        {sortedIntegrations.length > 0 && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {sortedIntegrations.map((c) => (
              <div
                key={c.slug}
                className="flex flex-col rounded-lg border border-sco-border bg-sco-surface-elevated p-5"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-sco-navy/10 text-sco-navy">
                      <ConnectorIcon slug={c.slug} />
                    </div>
                    <div>
                      <div className="font-semibold">{c.name}</div>
                      {c.account && (
                        <div className="text-xs text-sco-muted-foreground">
                          {c.account}
                        </div>
                      )}
                      {c.lastSyncAt && (
                        <div className="text-[11px] text-sco-muted-foreground">
                          Ultimo sync:{" "}
                          {new Date(c.lastSyncAt).toLocaleString("it-IT")}
                        </div>
                      )}
                    </div>
                  </div>
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-xs font-medium",
                      STATUS_COLORS[c.status],
                    )}
                  >
                    {STATUS_LABELS[c.status]}
                  </span>
                </div>

                <p className="mt-3 flex-1 text-sm text-sco-muted-foreground">
                  {c.description}
                </p>

                <button
                  type="button"
                  onClick={() =>
                    c.status === "connected"
                      ? void handleDisconnect(c)
                      : void handleConnect(c)
                  }
                  disabled={loading}
                  className={cn(
                    "mt-4 rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                    c.status === "connected"
                      ? "border border-sco-border hover:bg-sco-muted"
                      : "bg-sco-navy text-white hover:bg-sco-blue",
                  )}
                >
                  {c.status === "connected"
                    ? "Disconnetti"
                    : "Connetti via OAuth"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
