// SCO Compliance OS — schermata Vault: lista vault registrati REALI da backend
// Conv. 47 enforcement v0.5.0: nessun hardcoded INITIAL_VAULTS, fonte unica = useVaultStore.
// Conv. 48 enforcement: backend single source of truth tramite GET /api/vault/list.

import { useEffect } from "react";
import { Database, FolderPlus, Check, AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/cn";
import { useVaultStore } from "@/store/vault-store";
import { EmptyState } from "@/components/ui/EmptyState";

export function VaultScreen() {
  const vaults = useVaultStore((s) => s.vaults);
  const selectedVaultId = useVaultStore((s) => s.selectedVaultId);
  const loading = useVaultStore((s) => s.loading);
  const errorMessage = useVaultStore((s) => s.errorMessage);
  const initialFetchDone = useVaultStore((s) => s.initialFetchDone);
  const fetchVaults = useVaultStore((s) => s.fetchVaults);
  const addVault = useVaultStore((s) => s.addVault);
  const selectVault = useVaultStore((s) => s.selectVault);
  const removeVault = useVaultStore((s) => s.removeVault);

  useEffect(() => {
    if (!initialFetchDone) {
      fetchVaults();
    }
  }, [initialFetchDone, fetchVaults]);

  const activeVault = vaults.find((v) => v.id === selectedVaultId) ?? null;

  const handleAddVault = async () => {
    try {
      const dialogModule = await import("@tauri-apps/plugin-dialog");
      const selected = await dialogModule.open({
        directory: true,
        multiple: false,
        title: "Scegli la cartella del vault",
      });
      if (typeof selected !== "string") {
        return;
      }
      const entry = await addVault(selected);
      if (entry) {
        toast.success(`Vault "${entry.name}" registrato.`);
        selectVault(entry.id);
      } else {
        toast.error(errorMessage || "Aggiunta vault fallita.");
      }
    } catch (err) {
      toast.error(`Aggiunta vault fallita: ${(err as Error).message}`);
    }
  };

  const handleSetActive = (id: string) => {
    selectVault(id);
    toast.success("Vault attivo aggiornato.");
  };

  const handleRemove = async (id: string) => {
    const ok = await removeVault(id);
    if (ok) {
      toast.success("Vault rimosso dal registry locale.");
    } else {
      toast.error(errorMessage || "Rimozione vault fallita.");
    }
  };

  if (loading && !initialFetchDone) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 size={32} className="animate-spin text-sco-blue" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto px-8 py-6">
      <div className="mx-auto max-w-5xl">
        <header className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-sco-navy dark:text-sco-text-dark">
              Vault
            </h1>
            <p className="mt-1 text-sm text-sco-muted-foreground">
              Le tue cartelle SCO collegate. Struttura SCO applicata.
            </p>
          </div>
          <button
            type="button"
            onClick={handleAddVault}
            className="flex items-center gap-2 rounded-md bg-sco-navy px-3 py-2 text-sm font-medium text-white hover:bg-sco-blue"
          >
            <FolderPlus size={16} />
            Aggiungi vault
          </button>
        </header>

        {errorMessage && (
          <div className="mb-4 flex items-center gap-2 rounded-md border border-sco-amber/40 bg-sco-amber/10 px-3 py-2 text-sm text-sco-amber">
            <AlertCircle size={16} />
            {errorMessage}
          </div>
        )}

        {vaults.length === 0 ? (
          <EmptyState
            icon={Database}
            tone="neutral"
            title="Nessun vault registrato"
            description="Un vault è una cartella sul tuo disco dove l'agente trova i tuoi documenti SCO (CLAUDE.md, wiki/, raw/). Aggiungine uno per iniziare a far rispondere l'agente con i tuoi dati."
            ctaLabel="Aggiungi vault"
            ctaAction={handleAddVault}
          />
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_2fr]">
            <div className="space-y-2">
              {vaults.map((v) => (
                <div
                  key={v.id}
                  className={cn(
                    "rounded-md border p-3 transition-colors",
                    selectedVaultId === v.id
                      ? "border-sco-blue bg-sco-blue/5"
                      : "border-sco-border hover:border-sco-blue",
                  )}
                >
                  <button
                    type="button"
                    onClick={() => handleSetActive(v.id)}
                    className="flex w-full items-center gap-3 text-left"
                  >
                    <Database size={18} className="text-sco-blue" />
                    <div className="flex-1 truncate">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{v.name}</span>
                        {selectedVaultId === v.id && (
                          <span className="rounded-full bg-sco-amber/20 px-2 py-0.5 text-xs font-medium text-sco-amber">
                            Attivo
                          </span>
                        )}
                      </div>
                      <div className="truncate text-xs text-sco-muted-foreground">
                        {v.path}
                      </div>
                    </div>
                  </button>
                  <div className="mt-2 flex items-center justify-between text-xs text-sco-muted-foreground">
                    <span>{v.mdFilesCount} file .md</span>
                    <button
                      type="button"
                      onClick={() => handleRemove(v.id)}
                      className="text-coral-500 hover:underline"
                    >
                      Rimuovi
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {activeVault && (
              <div className="rounded-lg border border-sco-border bg-sco-surface-elevated p-5 text-sco-text">
                <h2 className="text-lg font-semibold text-sco-navy dark:text-sco-text-dark">
                  {activeVault.name}
                </h2>
                <p className="mt-1 truncate text-xs text-sco-muted-foreground">
                  {activeVault.path}
                </p>
                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-sco-muted-foreground">File .md</div>
                    <div className="font-medium text-sco-text">{activeVault.mdFilesCount}</div>
                  </div>
                  <div>
                    <div className="text-sco-muted-foreground">CLAUDE.md</div>
                    <div className="font-medium text-sco-text">
                      {activeVault.hasClaudeMd ? (
                        <Check size={16} className="text-sage-500" />
                      ) : (
                        "Mancante"
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-sco-muted-foreground">wiki/</div>
                    <div className="font-medium text-sco-text">
                      {activeVault.hasWikiDir ? (
                        <Check size={16} className="text-sage-500" />
                      ) : (
                        "Mancante"
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-sco-muted-foreground">raw/</div>
                    <div className="font-medium text-sco-text">
                      {activeVault.hasRawDir ? (
                        <Check size={16} className="text-sage-500" />
                      ) : (
                        "Mancante"
                      )}
                    </div>
                  </div>
                </div>
                {!activeVault.isScoStructure && (
                  <div className="mt-4 rounded-md border border-sco-amber/40 bg-sco-amber/10 px-3 py-2 text-xs text-sco-amber">
                    Struttura SCO parziale o assente. L'agente avra meno
                    contesto strutturato.
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
