// SCO Compliance OS — schermata Integrazioni: grid di 5 connettori demo con badge status
import { useState } from "react";
import { Mail, Calendar, HardDrive, MessageSquare, Github } from "lucide-react";

import { cn } from "@/lib/cn";
import { toast } from "sonner";

type ConnectorStatus = "connected" | "disconnected" | "error";

interface Connector {
  id: string;
  name: string;
  description: string;
  icon: typeof Mail;
  status: ConnectorStatus;
  account?: string;
}

// 5 connettori demo stub
const INITIAL_CONNECTORS: Connector[] = [
  {
    id: "gmail",
    name: "Gmail",
    description: "Leggi email, crea bozze, gestisci label.",
    icon: Mail,
    status: "disconnected",
  },
  {
    id: "google-calendar",
    name: "Google Calendar",
    description: "Crea eventi, gestisci appuntamenti, suggerisci slot.",
    icon: Calendar,
    status: "disconnected",
  },
  {
    id: "google-drive",
    name: "Google Drive",
    description: "Cerca, leggi, scarica file dal tuo Drive.",
    icon: HardDrive,
    status: "connected",
    account: "a.oedoma@gmail.com",
  },
  {
    id: "slack",
    name: "Slack",
    description: "Leggi e invia messaggi nei canali del workspace.",
    icon: MessageSquare,
    status: "disconnected",
  },
  {
    id: "github",
    name: "GitHub",
    description: "Issue, PR, file da repo personali e organizzazioni.",
    icon: Github,
    status: "error",
  },
];

const STATUS_LABELS: Record<ConnectorStatus, string> = {
  connected: "Connesso",
  disconnected: "Non connesso",
  error: "Errore",
};

const STATUS_COLORS: Record<ConnectorStatus, string> = {
  connected: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  disconnected: "bg-sco-muted text-sco-muted-foreground",
  error: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

export function IntegrationsScreen() {
  const [connectors, setConnectors] =
    useState<Connector[]>(INITIAL_CONNECTORS);

  const toggleConnector = (id: string) => {
    setConnectors((prev) =>
      prev.map((c) =>
        c.id === id
          ? {
              ...c,
              status:
                c.status === "connected" ? "disconnected" : "connected",
              account:
                c.status === "connected" ? undefined : "a.oedoma@gmail.com",
            }
          : c,
      ),
    );
    toast.success(`Connettore "${id}" aggiornato (stub).`);
  };

  return (
    <div className="h-full overflow-y-auto px-8 py-6">
      <div className="mx-auto max-w-5xl">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold text-sco-navy dark:text-sco-text-dark">
            Integrazioni
          </h1>
          <p className="mt-1 text-sm text-sco-muted-foreground">
            Collega i tuoi servizi. Le credenziali vivono in keyring di sistema,
            mai in chiaro.
          </p>
        </header>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {connectors.map((c) => {
            const Icon = c.icon;
            return (
              <div
                key={c.id}
                className="flex flex-col rounded-lg border border-sco-border bg-sco-surface-elevated p-5"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-sco-navy/10 text-sco-navy">
                      <Icon size={20} />
                    </div>
                    <div>
                      <div className="font-semibold">{c.name}</div>
                      {c.account && (
                        <div className="text-xs text-sco-muted-foreground">
                          {c.account}
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
                  onClick={() => toggleConnector(c.id)}
                  className={cn(
                    "mt-4 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    c.status === "connected"
                      ? "border border-sco-border hover:bg-sco-muted"
                      : "bg-sco-navy text-white hover:bg-sco-blue",
                  )}
                >
                  {c.status === "connected" ? "Disconnetti" : "Connetti"}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
