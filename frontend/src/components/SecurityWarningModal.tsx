import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle, X } from "lucide-react";

import { cn } from "@/lib/cn";

interface SecurityWarningModalProps {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function SecurityWarningModal({ open, onConfirm, onCancel }: SecurityWarningModalProps) {
  return (
    <Dialog.Root
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          onCancel();
        }
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn(
            "fixed inset-0 z-50",
            "bg-black/60 backdrop-blur-sm",
            "data-[state=open]:animate-fade-in data-[state=closed]:opacity-0",
          )}
        />
        <Dialog.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2",
            "w-[420px] max-w-[92vw]",
            "rounded-2xl border border-sco-border bg-sco-surface-elevated",
            "p-6 shadow-xl outline-none",
            "data-[state=open]:animate-scale-in",
          )}
        >
          <div className="mb-4 flex items-start justify-between gap-3">
            <div className="flex gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/15 text-red-600 dark:text-red-400">
                <AlertTriangle size={20} />
              </div>
              <div>
                <Dialog.Title className="text-base font-semibold text-sco-text dark:text-sco-text-dark">
                  Stai per abilitare la modalita senza autorizzazioni
                </Dialog.Title>
                <Dialog.Description className="mt-1 text-sm text-sco-muted-foreground">
                  L'agente potra leggere, scrivere e cancellare file sul tuo PC senza chiederti conferma. Usare solo se sai cosa stai facendo. Vuoi davvero attivare?
                </Dialog.Description>
              </div>
            </div>
            <button
              type="button"
              onClick={onCancel}
              className="rounded-md p-1 text-sco-muted-foreground transition-colors hover:bg-sco-muted"
              aria-label="Chiudi"
            >
              <X size={16} />
            </button>
          </div>

          <div className="mt-6 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="rounded-md px-4 py-2 text-sm font-medium text-sco-muted-foreground transition-colors hover:bg-sco-muted"
            >
              Annulla
            </button>
            <button
              type="button"
              onClick={onConfirm}
              className={cn(
                "rounded-md px-4 py-2 text-sm font-semibold text-white transition-all duration-150",
                "bg-red-600 hover:bg-red-700 hover:shadow",
              )}
              autoFocus
            >
              Si, abilita
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
