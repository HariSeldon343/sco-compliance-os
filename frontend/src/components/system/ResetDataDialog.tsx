// SCO Compliance OS — ResetDataDialog: conferma forte per il reset completo dati.
// Feature 1 v0.15.0. L'utente DEVE digitare "RESET" per abilitare il bottone
// distruttivo. Chiama POST /api/system/reset-data, poi ricarica l'app.
// Pattern Radix clonato da SessionEndDialog. Linguaggio semplice 14/05.
import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle, Loader2, Trash2, X } from "lucide-react";
import { toast } from "sonner";

import { apiClient } from "@/api/client";
import { cn } from "@/lib/cn";

interface ResetDataDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  // Chiamata dopo un reset andato a buon fine (prima del reload), per permettere
  // al chiamante di salvare stato (es. WipeOrKeepDialog aggiorna la versione vista).
  onResetDone?: () => void;
}

const CONFIRM_WORD = "RESET";

export function ResetDataDialog({ open, onOpenChange, onResetDone }: ResetDataDialogProps) {
  const [typed, setTyped] = useState("");
  const [running, setRunning] = useState(false);

  const canConfirm = typed.trim() === CONFIRM_WORD && !running;

  const closeAndReset = () => {
    setTyped("");
    onOpenChange(false);
  };

  const handleConfirm = async () => {
    if (!canConfirm) return;
    setRunning(true);
    const loadingId = toast.loading("Cancellazione di tutti i dati in corso...");
    try {
      const result = await apiClient.system.resetData(CONFIRM_WORD);
      toast.dismiss(loadingId);
      toast.success(
        `Dati cancellati (${result.deleted.length} ${
          result.deleted.length === 1 ? "elemento" : "elementi"
        }). Riavvio l'app...`,
      );
      onResetDone?.();
      // Breve attesa per far leggere il toast, poi reload completo.
      setTimeout(() => window.location.reload(), 900);
    } catch (err) {
      toast.dismiss(loadingId);
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`Errore durante il reset: ${message}`);
      setRunning(false);
    }
  };

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        if (running) return; // blocca chiusura durante l'operazione
        if (!o) {
          closeAndReset();
          return;
        }
        onOpenChange(o);
      }}
    >
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
          <div className="mb-4 flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/10 text-red-500">
                <AlertTriangle size={18} />
              </div>
              <div>
                <Dialog.Title className="text-base font-semibold text-sco-text dark:text-sco-text-dark">
                  Cancellare tutti i dati?
                </Dialog.Title>
                <Dialog.Description className="mt-1 text-sm text-sco-muted-foreground">
                  Questa azione cancella <strong>tutto</strong>: conversazioni, vault
                  collegati, profilo, memoria e impostazioni. L&apos;app ripartirà come
                  appena installata. <strong>Non si può annullare.</strong>
                </Dialog.Description>
              </div>
            </div>
            <button
              type="button"
              onClick={closeAndReset}
              disabled={running}
              className="rounded-md p-1 text-sco-muted-foreground transition-colors hover:bg-sco-muted disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Chiudi"
            >
              <X size={16} />
            </button>
          </div>

          {/* Campo conferma: digita RESET */}
          <label className="mb-1 block text-xs font-medium text-sco-muted-foreground">
            Per confermare, scrivi <span className="font-mono font-semibold">RESET</span> qui sotto:
          </label>
          <input
            type="text"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            disabled={running}
            autoFocus
            spellCheck={false}
            autoComplete="off"
            placeholder="RESET"
            className={cn(
              "mb-5 w-full rounded-md border bg-sco-bg px-3 py-2 text-sm outline-none transition-colors",
              "border-sco-border focus:border-red-500",
              "disabled:cursor-not-allowed disabled:opacity-60",
            )}
          />

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={closeAndReset}
              disabled={running}
              className="rounded-md px-4 py-2 text-sm font-medium text-sco-muted-foreground transition-colors hover:bg-sco-muted disabled:cursor-not-allowed disabled:opacity-50"
            >
              Annulla
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={!canConfirm}
              className={cn(
                "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-white transition-all duration-150",
                "bg-red-600 hover:bg-red-700 hover:shadow",
                "disabled:cursor-not-allowed disabled:opacity-50",
              )}
            >
              {running ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Cancellazione...
                </>
              ) : (
                <>
                  <Trash2 size={14} />
                  Cancella tutto
                </>
              )}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
