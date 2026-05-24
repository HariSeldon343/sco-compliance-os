// SCO Compliance OS — Settings Tab "Vault"
// v0.8.1: lista vault registrati (link → /vault) + auto-sync settings (interval
// polling + on-modify watcher) + auto-ingest settings (Conv. 43 Smart File
// Injection toggle chat attachments e web search).

import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Database, RefreshCw, Sparkles, FolderOpen, ExternalLink } from "lucide-react";

import { useVaultStore } from "@/store/vault-store";
import {
  useVaultSettingsStore,
  type AutoSyncInterval,
} from "@/store/vault-settings-store";
import { cn } from "@/lib/cn";

export function VaultTab() {
  const vaults = useVaultStore((s) => s.vaults);
  const selectedVaultId = useVaultStore((s) => s.selectedVaultId);
  const initialFetchDone = useVaultStore((s) => s.initialFetchDone);
  const fetchVaults = useVaultStore((s) => s.fetchVaults);
  const selectVault = useVaultStore((s) => s.selectVault);

  const autoSyncInterval = useVaultSettingsStore((s) => s.autoSyncInterval);
  const autoSyncOnModify = useVaultSettingsStore((s) => s.autoSyncOnModify);
  const autoIngestChat = useVaultSettingsStore(
    (s) => s.autoIngestChatAttachments,
  );
  const autoIngestWeb = useVaultSettingsStore((s) => s.autoIngestWebSearch);
  const setAutoSyncInterval = useVaultSettingsStore(
    (s) => s.setAutoSyncInterval,
  );
  const setAutoSyncOnModify = useVaultSettingsStore(
    (s) => s.setAutoSyncOnModify,
  );
  const setAutoIngestChat = useVaultSettingsStore(
    (s) => s.setAutoIngestChatAttachments,
  );
  const setAutoIngestWeb = useVaultSettingsStore(
    (s) => s.setAutoIngestWebSearch,
  );

  useEffect(() => {
    if (!initialFetchDone) {
      void fetchVaults();
    }
  }, [initialFetchDone, fetchVaults]);

  return (
    <div className="space-y-6">
      {/* Lista vault registrati */}
      <Card icon={Database} title="Vault registrati">
        <p className="mb-3 text-xs text-sco-muted-foreground">
          Cartelle locali registrate come knowledge base dell'agente. Il vault
          attivo viene mostrato nella sidebar.
        </p>
        {vaults.length === 0 ? (
          <div className="rounded-lg border border-dashed border-sco-border bg-sco-bg p-6 text-center">
            <p className="text-sm text-sco-muted-foreground">
              Nessun vault registrato.
            </p>
            <Link
              to="/vault"
              className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-sco-blue hover:underline"
            >
              <FolderOpen size={14} />
              Aggiungi vault
            </Link>
          </div>
        ) : (
          <ul className="space-y-2">
            {vaults.map((v) => {
              const isSelected = v.id === selectedVaultId;
              return (
                <li
                  key={v.id}
                  className={cn(
                    "flex items-center justify-between rounded-lg border p-3 transition-colors",
                    isSelected
                      ? "border-sco-blue bg-sco-blue/5"
                      : "border-sco-border bg-sco-bg",
                  )}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{v.name}</p>
                    <p className="truncate text-xs text-sco-muted-foreground">
                      {v.path}
                    </p>
                    <p className="mt-0.5 text-[11px] text-sco-muted-foreground">
                      {v.mdFilesCount} file MD ·{" "}
                      {v.isScoStructure
                        ? "struttura SCO"
                        : "struttura libera"}
                    </p>
                  </div>
                  {!isSelected && (
                    <button
                      type="button"
                      onClick={() => selectVault(v.id)}
                      className="rounded-md border border-sco-border bg-sco-surface px-3 py-1.5 text-xs font-medium hover:border-sco-blue"
                    >
                      Attiva
                    </button>
                  )}
                  {isSelected && (
                    <span className="rounded-md bg-sco-blue/10 px-2 py-1 text-xs font-medium text-sco-blue">
                      Attivo
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        <div className="mt-3">
          <Link
            to="/vault"
            className="inline-flex items-center gap-1 text-sm font-medium text-sco-blue hover:underline"
          >
            Gestisci vault
            <ExternalLink size={12} />
          </Link>
        </div>
      </Card>

      {/* Auto-sync */}
      <Card icon={RefreshCw} title="Sincronizzazione automatica">
        <p className="mb-3 text-xs text-sco-muted-foreground">
          Frequenza con cui l'agente controlla nuove conversazioni e file dal
          backend.
        </p>
        <div className="space-y-4">
          <Field label="Intervallo polling">
            <div className="flex flex-wrap gap-2">
              {(
                [
                  { value: "off", label: "Disattivato" },
                  { value: "5s", label: "5 secondi" },
                  { value: "15s", label: "15 secondi" },
                  { value: "30s", label: "30 secondi" },
                  { value: "60s", label: "1 minuto" },
                  { value: "5m", label: "5 minuti" },
                ] as Array<{ value: AutoSyncInterval; label: string }>
              ).map((opt) => {
                const active = autoSyncInterval === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setAutoSyncInterval(opt.value)}
                    className={cn(
                      "rounded-md border px-3 py-1.5 text-xs transition-colors",
                      active
                        ? "border-sco-blue bg-sco-blue/10 text-sco-navy dark:text-sco-text-dark"
                        : "border-sco-border hover:border-sco-blue",
                    )}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
            <p className="mt-1 text-xs text-sco-muted-foreground">
              Disattivare il polling significa ricaricare manualmente la lista
              chat. Default: 5 secondi (basso impatto, UX reattiva).
            </p>
          </Field>

          <Field label="Aggiorna su modifica file system">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoSyncOnModify}
                onChange={(e) => setAutoSyncOnModify(e.target.checked)}
                className="h-4 w-4 accent-sco-blue"
              />
              Rileva modifiche al vault e ricarica automaticamente
            </label>
            <p className="mt-1 text-xs text-sco-muted-foreground">
              Richiede file system watcher attivo lato backend (carry-over
              v0.9.0).
            </p>
          </Field>
        </div>
      </Card>

      {/* Auto-ingest */}
      <Card icon={Sparkles} title="Indicizzazione automatica">
        <p className="mb-3 text-xs text-sco-muted-foreground">
          Quando l'agente riceve allegati o risultati web, ti chiede se
          archiviarli nel vault (Convenzione 43 — Smart File Injection).
        </p>
        <div className="space-y-3">
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoIngestChat}
              onChange={(e) => setAutoIngestChat(e.target.checked)}
              className="mt-0.5 h-4 w-4 accent-sco-blue"
            />
            <span>
              <span className="font-medium">Allegati chat</span>
              <span className="ml-1 text-sco-muted-foreground">
                — popup smart inject quando trascini file nella chat
              </span>
            </span>
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoIngestWeb}
              onChange={(e) => setAutoIngestWeb(e.target.checked)}
              className="mt-0.5 h-4 w-4 accent-sco-blue"
            />
            <span>
              <span className="font-medium">Risultati web search</span>
              <span className="ml-1 text-sco-muted-foreground">
                — archivia automaticamente i contenuti web rilevanti
                (sperimentale)
              </span>
            </span>
          </label>
        </div>
      </Card>
    </div>
  );
}

interface CardProps {
  icon: typeof Database;
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

interface FieldProps {
  label: string;
  children: React.ReactNode;
}

function Field({ label, children }: FieldProps) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-sco-muted-foreground">
        {label}
      </label>
      {children}
    </div>
  );
}
