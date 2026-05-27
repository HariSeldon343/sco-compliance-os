// SCO Compliance OS — Settings Tab "Avanzate"
// v0.8.1: card Modello AI (disclaimer SCO read-only), card Connettori OAuth
// (status + link), card Diagnostica (export log + reset + clear cache),
// card Info app (versione + build + crediti).

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ServerCog,
  Plug,
  Wrench,
  Info,
  Download,
  RotateCcw,
  Trash2,
  ExternalLink,
  ShieldCheck,
  Compass,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";

import { useIntegrationsStore } from "@/store/integrations-store";
import { useLicenseStore } from "@/store/license-store";
import { useWalkthroughStore } from "@/store/walkthrough-store";
import { resetWalkthroughFlag } from "@/components/WalkthroughTour";
import { cn } from "@/lib/cn";

// v0.13.6 fix Antonio feedback 27/05: pattern Sidebar.tsx con __APP_VERSION__
// iniettato da Vite da pkg.version (single source of truth Conv. 47).
// Pre-fix: hardcoded "0.8.1" mai bumpato → card Aggiornamenti app + Info app
// mostravano "v0.8.1" anche su app v0.13.5 installata.
const APP_VERSION_FALLBACK =
  (typeof __APP_VERSION__ !== "undefined" && __APP_VERSION__) || "0.13.7";

export function AdvancedTab() {
  const integrations = useIntegrationsStore((s) => s.integrations);
  const initialFetchDone = useIntegrationsStore((s) => s.initialFetchDone);
  const fetchIntegrations = useIntegrationsStore((s) => s.fetchIntegrations);
  const triggerTour = useWalkthroughStore((s) => s.triggerTour);

  const backendVersionLicense = useLicenseStore((s) => s.backendVersion);
  const [backendVersion, setBackendVersion] = useState<string>(
    backendVersionLicense || APP_VERSION_FALLBACK,
  );

  // v0.13.5 Antonio feedback 27/05: card "Aggiornamenti app" in Settings/Avanzate
  // con bottone Controlla aggiornamenti che chiama tauri-plugin-updater JS API.
  // Backend Rust check_for_updates esisteva gia (lib.rs:107) ma non era wire dal
  // frontend → utente non poteva triggerare auto-update manualmente, install
  // manuale UNA volta inevitabile per arrivare a v0.13.5. Da v0.13.5 in poi:
  // bottone UI gestisce tutto end-to-end (check → download → install → restart
  // auto via installMode basicUi di tauri.conf.json).
  type UpdateStatus =
    | "idle"
    | "checking"
    | "available"
    | "no-update"
    | "downloading"
    | "installing"
    | "error";
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus>("idle");
  const [availableUpdate, setAvailableUpdate] = useState<{
    version: string;
    notes?: string;
  } | null>(null);
  const [downloadProgress, setDownloadProgress] = useState<{
    downloaded: number;
    total: number;
  } | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const handleCheckForUpdates = async () => {
    setUpdateStatus("checking");
    setUpdateError(null);
    setAvailableUpdate(null);
    try {
      const { check } = await import("@tauri-apps/plugin-updater");
      const update = await check();
      if (update) {
        setAvailableUpdate({
          version: update.version,
          notes: update.body ?? undefined,
        });
        setUpdateStatus("available");
      } else {
        setUpdateStatus("no-update");
        const { toast } = await import("sonner");
        toast.success("Sei alla versione piu` recente.");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setUpdateError(message);
      setUpdateStatus("error");
      const { toast } = await import("sonner");
      toast.error(`Errore controllo aggiornamenti: ${message}`);
    }
  };

  const handleDownloadAndInstall = async () => {
    if (!availableUpdate) return;
    setUpdateStatus("downloading");
    setDownloadProgress(null);
    setUpdateError(null);
    try {
      const { check } = await import("@tauri-apps/plugin-updater");
      const update = await check();
      if (!update) {
        const { toast } = await import("sonner");
        toast.warning("Update non piu` disponibile, riprova check.");
        setUpdateStatus("idle");
        return;
      }
      let downloaded = 0;
      let total = 0;
      await update.downloadAndInstall((event) => {
        if (event.event === "Started") {
          total = event.data.contentLength ?? 0;
          setDownloadProgress({ downloaded: 0, total });
        } else if (event.event === "Progress") {
          downloaded += event.data.chunkLength;
          setDownloadProgress({ downloaded, total });
        } else if (event.event === "Finished") {
          setUpdateStatus("installing");
        }
      });
      // installMode: basicUi in tauri.conf.json -> restart automatico
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setUpdateError(message);
      setUpdateStatus("error");
      const { toast } = await import("sonner");
      toast.error(`Errore installazione aggiornamento: ${message}`);
    }
  };

  const isUpdateInFlight =
    updateStatus === "checking" ||
    updateStatus === "downloading" ||
    updateStatus === "installing";

  useEffect(() => {
    if (!initialFetchDone) {
      void fetchIntegrations();
    }
  }, [initialFetchDone, fetchIntegrations]);

  useEffect(() => {
    const BACKEND_URL =
      import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";
    fetch(`${BACKEND_URL}/health`)
      .then((r) => r.json())
      .then((data: { backend_version?: string }) => {
        if (data.backend_version) setBackendVersion(data.backend_version);
      })
      .catch(() => {
        // backend offline: mantieni fallback license-store o costante
      });
  }, []);

  const connectedCount = integrations.filter(
    (i) => i.status === "connected",
  ).length;
  const totalCount = integrations.length;

  const handleClearCache = async () => {
    if (
      !window.confirm(
        "Vuoi davvero svuotare la cache locale? Le chat e le preferenze persistite saranno cancellate. Le impostazioni del backend (vault, license, conversazioni) restano intatte.",
      )
    ) {
      return;
    }
    try {
      const keys = [
        "sco-chat",
        "sco-chat-mode",
        "sco-voice-prefs",
        "sco-theme",
        "sco-layout",
        "sco-mascot",
        "sco-profile",
        "sco-team",
        "sco-vault-settings",
      ];
      keys.forEach((k) => {
        try {
          localStorage.removeItem(k);
        } catch {
          // ignore
        }
      });
      const { toast } = await import("sonner");
      toast.success("Cache svuotata. Ricarica la pagina per applicare.", {
        duration: 5000,
        action: {
          label: "Ricarica ora",
          onClick: () => window.location.reload(),
        },
      });
    } catch (err) {
      const { toast } = await import("sonner");
      toast.error(
        `Errore svuotamento cache: ${err instanceof Error ? err.message : err}`,
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Modello AI SCO (read-only disclaimer) */}
      <Card icon={ServerCog} title="Modello AI gestito da SCO Solution Consulting">
        <div className="space-y-3 text-sm text-sco-muted-foreground">
          <p>
            Il modello linguistico attivo per il tuo tenant e` configurato e
            mantenuto centralmente da SCO. Non e` modificabile dall'app per
            garantire stabilita`, sicurezza e conformita` contrattuale.
          </p>
          <p>
            Per modifiche o richieste, contatta{" "}
            <a
              href="mailto:info@scosolution.it"
              className="font-medium text-sco-blue hover:underline"
            >
              info@scosolution.it
            </a>
            .
          </p>
        </div>
      </Card>

      {/* Connettori OAuth */}
      <Card icon={Plug} title="Connettori OAuth">
        <p className="mb-3 text-xs text-sco-muted-foreground">
          Stato dei connettori OAuth registrati. Per gestire le connessioni,
          vai alla pagina dedicata.
        </p>
        {totalCount === 0 ? (
          <div className="rounded-lg border border-dashed border-sco-border bg-sco-bg p-4 text-center text-xs text-sco-muted-foreground">
            Nessun connettore disponibile.
          </div>
        ) : (
          <div className="mb-3 flex flex-wrap gap-2">
            {integrations.map((i) => (
              <div
                key={i.slug}
                className={cn(
                  "flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs",
                  i.status === "connected"
                    ? "border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-400"
                    : "border-sco-border bg-sco-bg text-sco-muted-foreground",
                )}
              >
                <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
                <span className="font-medium">{i.name}</span>
              </div>
            ))}
          </div>
        )}
        <Link
          to="/integrations"
          className="inline-flex items-center gap-1 text-sm font-medium text-sco-blue hover:underline"
        >
          Gestisci connettori ({connectedCount}/{totalCount} attivi)
          <ExternalLink size={12} />
        </Link>
      </Card>

      {/* Diagnostica */}
      <Card icon={Wrench} title="Diagnostica">
        <p className="mb-3 text-xs text-sco-muted-foreground">
          Strumenti di diagnosi per supporto tecnico. Usa con cautela: alcune
          azioni cancellano dati locali.
        </p>
        <div className="space-y-3">
          <button
            type="button"
            onClick={async () => {
              const { toast } = await import("sonner");
              toast.info(
                "Export log: funzionalita` in arrivo nella v0.8.2 (necessita endpoint backend /api/diagnostics/export).",
                { duration: 4000 },
              );
            }}
            className="inline-flex w-full items-center gap-2 rounded-md border border-sco-border bg-sco-bg px-4 py-2.5 text-sm transition-colors hover:border-sco-blue hover:bg-sco-blue/5"
          >
            <Download size={14} className="text-sco-blue" />
            <span className="flex-1 text-left">Esporta log diagnostici</span>
            <span className="text-xs text-sco-muted-foreground">
              v0.8.2
            </span>
          </button>

          <button
            type="button"
            onClick={handleClearCache}
            className="inline-flex w-full items-center gap-2 rounded-md border border-sco-border bg-sco-bg px-4 py-2.5 text-sm transition-colors hover:border-sco-amber hover:bg-sco-amber/5"
          >
            <Trash2 size={14} className="text-sco-amber" />
            <span className="flex-1 text-left">Svuota cache locale</span>
            <span className="text-xs text-sco-muted-foreground">
              preferenze UI
            </span>
          </button>

          <button
            type="button"
            onClick={async () => {
              const { toast } = await import("sonner");
              toast.warning(
                "Reset dati: funzionalita` distruttiva, richiede conferma backend (in arrivo v0.9.x).",
                { duration: 4000 },
              );
            }}
            className="inline-flex w-full items-center gap-2 rounded-md border border-sco-border bg-sco-bg px-4 py-2.5 text-sm transition-colors hover:border-red-500/60 hover:bg-red-500/5"
          >
            <RotateCcw size={14} className="text-red-500" />
            <span className="flex-1 text-left">
              Reset completo dati applicazione
            </span>
            <span className="text-xs text-sco-muted-foreground">
              v0.9.x
            </span>
          </button>
        </div>
      </Card>

      {/* v0.13.2 PSI-2: Tour guidato on-demand */}
      <Card icon={Compass} title="Tour guidato">
        <p className="mb-3 text-xs text-sco-muted-foreground">
          Rivedi il walkthrough delle 10 funzionalita` principali dell'app:
          chat, wiki, grafo, skills, vault, memoria, impostazioni, fine
          sessione, input chat, invio. Utile per orientarsi se hai saltato il
          tour al primo avvio o vuoi rivederlo dopo un update.
        </p>
        <button
          type="button"
          onClick={() => {
            resetWalkthroughFlag();
            triggerTour();
          }}
          className="inline-flex w-full items-center gap-2 rounded-md border border-sco-border bg-sco-bg px-4 py-2.5 text-sm transition-colors hover:border-sco-blue hover:bg-sco-blue/5"
        >
          <Compass size={14} className="text-sco-blue" />
          <span className="flex-1 text-left">Mostra tour guidato</span>
          <span className="text-xs text-sco-muted-foreground">10 step</span>
        </button>
      </Card>

      {/* v0.13.5 Antonio feedback 27/05: card Aggiornamenti app */}
      <Card icon={RefreshCw} title="Aggiornamenti app">
        <p className="mb-3 text-xs text-sco-muted-foreground">
          Controlla manualmente la disponibilita` di aggiornamenti. Gli
          aggiornamenti sono firmati Ed25519 e verificati prima dell&apos;install.
          L&apos;app si riavvia in automatico al termine.
        </p>
        <div className="space-y-3">
          <button
            type="button"
            onClick={handleCheckForUpdates}
            disabled={isUpdateInFlight}
            className={cn(
              "inline-flex w-full items-center gap-2 rounded-md border bg-sco-bg px-4 py-2.5 text-sm transition-colors",
              isUpdateInFlight
                ? "cursor-not-allowed border-sco-border opacity-60"
                : "border-sco-border hover:border-sco-blue hover:bg-sco-blue/5",
            )}
          >
            {updateStatus === "checking" ? (
              <Loader2 size={14} className="animate-spin text-sco-blue" />
            ) : (
              <RefreshCw size={14} className="text-sco-blue" />
            )}
            <span className="flex-1 text-left">
              {updateStatus === "checking"
                ? "Controllo in corso..."
                : "Controlla aggiornamenti"}
            </span>
            <span className="text-xs text-sco-muted-foreground">
              v{APP_VERSION_FALLBACK}
            </span>
          </button>

          {updateStatus === "available" && availableUpdate && (
            <div className="space-y-2 rounded-lg border border-sco-blue/30 bg-sco-blue/5 p-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-sco-text dark:text-sco-text-dark">
                <CheckCircle2 size={14} className="text-sco-blue" />
                Versione v{availableUpdate.version} disponibile
              </div>
              {availableUpdate.notes && (
                <div className="whitespace-pre-wrap rounded border border-sco-border bg-sco-bg p-2 text-xs text-sco-muted-foreground">
                  {availableUpdate.notes.slice(0, 500)}
                  {availableUpdate.notes.length > 500 ? "..." : ""}
                </div>
              )}
              <button
                type="button"
                onClick={handleDownloadAndInstall}
                disabled={isUpdateInFlight}
                className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-sco-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-sco-navy disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Download size={14} />
                Scarica e installa v{availableUpdate.version}
              </button>
            </div>
          )}

          {updateStatus === "downloading" && downloadProgress && (
            <div className="space-y-2 rounded-lg border border-sco-blue/30 bg-sco-blue/5 p-3">
              <div className="flex items-center gap-2 text-sm">
                <Loader2 size={14} className="animate-spin text-sco-blue" />
                <span>Download in corso...</span>
              </div>
              <progress
                max={downloadProgress.total || 100}
                value={downloadProgress.downloaded || 0}
                className="h-2 w-full"
              />
              <div className="text-xs text-sco-muted-foreground">
                {(downloadProgress.downloaded / 1024 / 1024).toFixed(1)} /{" "}
                {(downloadProgress.total / 1024 / 1024).toFixed(1)} MB
              </div>
            </div>
          )}

          {updateStatus === "installing" && (
            <div className="flex items-center gap-2 rounded-lg border border-sco-amber/30 bg-sco-amber/5 p-3 text-sm">
              <Loader2 size={14} className="animate-spin text-sco-amber" />
              <span>
                Installazione in corso. L&apos;app si riavviera` automaticamente.
              </span>
            </div>
          )}

          {updateStatus === "no-update" && (
            <div className="flex items-center gap-2 rounded-lg border border-green-500/30 bg-green-500/5 p-3 text-sm text-green-700 dark:text-green-300">
              <CheckCircle2 size={14} />
              <span>Sei alla versione piu` recente.</span>
            </div>
          )}

          {updateStatus === "error" && updateError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-700 dark:text-red-300">
              <AlertCircle size={14} className="mt-0.5 shrink-0" />
              <div className="flex-1">
                <div className="font-medium">Errore aggiornamento</div>
                <div className="mt-1 break-all font-mono text-xs">
                  {updateError}
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Info app */}
      <Card icon={Info} title="Informazioni applicazione">
        <div className="space-y-2 text-sm">
          <InfoRow label="Versione frontend" value={APP_VERSION_FALLBACK} />
          <InfoRow label="Versione backend" value={backendVersion} />
          <InfoRow label="Build" value="alpha" />
          <InfoRow
            label="Crediti"
            value="SCO Solution Consulting · 2025-2026"
          />
        </div>
        <div className="mt-4 rounded-lg border border-sco-blue/30 bg-sco-blue/5 p-3">
          <div className="flex items-start gap-2 text-xs text-sco-muted-foreground">
            <ShieldCheck size={14} className="mt-0.5 shrink-0 text-sco-blue" />
            <span>
              SCO Compliance OS opera localmente sul tuo dispositivo. Le
              chiamate al modello AI passano attraverso un proxy gestito da
              SCO, che valida la tua licenza e inoltra le richieste al
              fornitore del modello.
            </span>
          </div>
        </div>
      </Card>
    </div>
  );
}

interface CardProps {
  icon: typeof ServerCog;
  title: string;
  children: React.ReactNode;
}

function Card({ icon: Icon, title, children }: CardProps) {
  return (
    <section className="rounded-xl border border-sco-border bg-sco-surface-elevated p-6">
      <div className="mb-4 flex items-center gap-2">
        <Icon size={18} className="text-sco-blue" />
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      {children}
    </section>
  );
}

interface InfoRowProps {
  label: string;
  value: string;
}

function InfoRow({ label, value }: InfoRowProps) {
  return (
    <div className="flex items-center justify-between rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-xs">
      <span className="font-medium text-sco-muted-foreground">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  );
}
