// SCO Compliance OS — SessionEndDialog: dialog conferma "Fine sessione"
// Trigger manutenzione vault via skill os-ottimizzatore.
// Conv. 47 + Conv. 48 enforcement: backend = single source of truth (skill
// runner + conversation persistita). Frontend solo orchestra UX + naviga al
// report. Linguaggio semplice 14/05.
//
// Pipeline UX:
// 1. Utente click "Fine sessione" -> dialog si apre
// 2. Conferma -> POST /api/skills/run streaming SSE
// 3. Toast loading "Manutenzione vault in corso..."
// 4. SSE termina -> toast success + auto-navigate alla conversation creata
//    dal backend (X-Conversation-Id response header).
import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { LogOut, Loader2, X } from "lucide-react";
import { toast } from "sonner";

import { useChatStore } from "@/store/chat-store";
import { useVaultStore } from "@/store/vault-store";
import { cn } from "@/lib/cn";

interface SessionEndDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SessionEndDialog({ open, onOpenChange }: SessionEndDialogProps) {
  const [running, setRunning] = useState(false);
  const endSession = useChatStore((s) => s.endSession);
  const selectedVault = useVaultStore((s) =>
    s.vaults.find((v) => v.id === s.selectedVaultId) ?? null,
  );

  const handleConfirm = async () => {
    if (running) return;
    setRunning(true);

    // Toast loading (id stabile per dismiss successivo)
    const loadingId = toast.loading(
      "Manutenzione vault in corso. Sto applicando os-ottimizzatore.",
    );

    try {
      const result = await endSession({
        vaultPath: selectedVault?.path,
      });
      toast.dismiss(loadingId);

      if (result.success) {
        toast.success(
          result.eventsCount > 0
            ? `Vault aggiornato. ${result.eventsCount} passi applicati.`
            : "Vault aggiornato.",
        );
      } else {
        toast.error(
          result.errorMessage ||
            "Manutenzione completata con avvisi. Apri la conversazione per i dettagli.",
        );
      }

      onOpenChange(false);
    } catch (err) {
      toast.dismiss(loadingId);
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`Errore manutenzione vault: ${message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleCancel = () => {
    if (running) return;
    onOpenChange(false);
  };

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !running && onOpenChange(o)}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn(
            "fixed inset-0 z-50",
            "bg-black/55 backdrop-blur-sm",
            "data-[state=open]:animate-fade-in data-[state=closed]:opacity-0",
          )}
        />
        <Dialog.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2",
            "w-[480px] max-w-[92vw]",
            "rounded-2xl border border-sco-border bg-sco-surface-elevated",
            "p-6 shadow-2xl outline-none",
            "data-[state=open]:animate-scale-in",
          )}
        >
          {/* Header con icona + titolo + close */}
          <div className="mb-4 flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sco-blue/10 text-sco-blue">
                <LogOut size={18} />
              </div>
              <div>
                <Dialog.Title className="text-base font-semibold text-sco-text dark:text-sco-text-dark">
                  Termina la sessione e aggiorna il vault?
                </Dialog.Title>
                <Dialog.Description className="mt-1 text-sm text-sco-muted-foreground">
                  Mando in esecuzione <span className="font-mono text-xs">os-ottimizzatore</span>:
                  controlla la struttura del vault, rileva cartelle o file mancanti
                  e propone i passi di manutenzione. Il report finisce in una
                  nuova conversazione che puoi rileggere quando vuoi.
                </Dialog.Description>
              </div>
            </div>
            <button
              type="button"
              onClick={handleCancel}
              disabled={running}
              className="rounded-md p-1 text-sco-muted-foreground transition-colors hover:bg-sco-muted disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Chiudi"
            >
              <X size={16} />
            </button>
          </div>

          {/* Box info vault attivo */}
          {selectedVault ? (
            <div className="mb-5 rounded-lg border border-sco-border bg-sco-muted/40 p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-sco-muted-foreground">
                Vault attivo
              </div>
              <div className="mt-1 text-sm font-medium text-sco-text dark:text-sco-text-dark">
                {selectedVault.name}
              </div>
              <div className="mt-0.5 truncate text-xs text-sco-muted-foreground" title={selectedVault.path}>
                {selectedVault.path}
              </div>
            </div>
          ) : (
            <div className="mb-5 rounded-lg border border-amber-300/60 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-700/50 dark:bg-amber-900/20 dark:text-amber-200">
              Nessun vault selezionato. La manutenzione girerà con il vault
              risolto dal backend (registry sco-first).
            </div>
          )}

          {/* Azioni */}
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={handleCancel}
              disabled={running}
              className="rounded-md px-4 py-2 text-sm font-medium text-sco-muted-foreground transition-colors hover:bg-sco-muted disabled:cursor-not-allowed disabled:opacity-50"
            >
              Annulla
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={running}
              className={cn(
                "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-white transition-all duration-150",
                "bg-sco-blue hover:bg-sco-navy hover:shadow",
                "disabled:cursor-not-allowed disabled:opacity-70",
              )}
            >
              {running ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  In corso...
                </>
              ) : (
                <>
                  <LogOut size={14} />
                  Conferma
                </>
              )}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
