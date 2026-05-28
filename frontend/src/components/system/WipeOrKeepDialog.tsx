// SCO Compliance OS — WipeOrKeepDialog: scelta "Mantieni / Riparti da zero".
// Feature 1 v0.15.0. Compare UNA volta dopo un install/aggiornamento (quando la
// versione e' cambiata rispetto all'ultima vista) SE ci sono dati reali.
// "Mantieni": salva la versione vista e non ricompare. "Riparti da zero": apre
// il ResetDataDialog (conferma digita-RESET) che cancella tutto e riavvia.
// Linguaggio semplice 14/05.
import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { DatabaseZap, ArchiveRestore, Trash2 } from "lucide-react";

import { apiClient } from "@/api/client";
import type { DataStatus } from "@/types/api";
import { cn } from "@/lib/cn";
import { ResetDataDialog } from "@/components/system/ResetDataDialog";

const LAST_SEEN_KEY = "sco-last-seen-version";

function currentVersion(): string {
  return (typeof __APP_VERSION__ !== "undefined" && __APP_VERSION__) || "0.0.0";
}

export function WipeOrKeepDialog() {
  const [open, setOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [status, setStatus] = useState<DataStatus | null>(null);

  // Check una sola volta al mount: versione cambiata + dati presenti -> mostra.
  useEffect(() => {
    const version = currentVersion();
    let lastSeen: string | null = null;
    try {
      lastSeen = localStorage.getItem(LAST_SEEN_KEY);
    } catch {
      lastSeen = null;
    }
    if (lastSeen === version) {
      return; // stessa versione gia' vista: niente da chiedere
    }

    let cancelled = false;
    apiClient.system
      .dataStatus()
      .then((s) => {
        if (cancelled) return;
        if (s.has_data) {
          setStatus(s);
          setOpen(true);
        } else {
          // Install pulito: nessun dato, registra la versione e non chiedere.
          try {
            localStorage.setItem(LAST_SEEN_KEY, version);
          } catch {
            // localStorage non disponibile: riproveremo al prossimo avvio.
          }
        }
      })
      .catch(() => {
        // Backend non pronto o errore: non bloccare l'app, riproveremo dopo.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const markSeen = () => {
    try {
      localStorage.setItem(LAST_SEEN_KEY, currentVersion());
    } catch {
      // ignore
    }
  };

  const handleKeep = () => {
    markSeen();
    setOpen(false);
  };

  const handleWipe = () => {
    // Chiude questo dialog e apre la conferma forte (digita-RESET).
    setOpen(false);
    setResetOpen(true);
  };

  const counts: string[] = [];
  if (status) {
    if (status.conversations > 0) {
      counts.push(
        `${status.conversations} ${status.conversations === 1 ? "conversazione" : "conversazioni"}`,
      );
    }
    if (status.vaults > 0) {
      counts.push(`${status.vaults} ${status.vaults === 1 ? "vault" : "vault"}`);
    }
  }

  return (
    <>
      <Dialog.Root
        open={open}
        onOpenChange={(o) => {
          // Chiusura via ESC/overlay = equivale a "Mantieni" (scelta sicura).
          if (!o) {
            handleKeep();
            return;
          }
          setOpen(o);
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
              "w-[500px] max-w-[92vw]",
              "rounded-2xl border border-sco-border bg-sco-surface-elevated",
              "p-6 shadow-2xl outline-none",
              "data-[state=open]:animate-scale-in",
            )}
          >
            <div className="mb-4 flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sco-blue/10 text-sco-blue">
                <DatabaseZap size={18} />
              </div>
              <div>
                <Dialog.Title className="text-base font-semibold text-sco-text dark:text-sco-text-dark">
                  Vuoi tenere i tuoi dati o ripartire da zero?
                </Dialog.Title>
                <Dialog.Description className="mt-1 text-sm text-sco-muted-foreground">
                  Hai appena aggiornato l&apos;app.{" "}
                  {counts.length > 0
                    ? `Sul tuo computer trovo ${counts.join(" e ")}.`
                    : "Sul tuo computer ci sono dati salvati."}{" "}
                  Puoi tenerli oppure cancellare tutto e cominciare pulito.
                </Dialog.Description>
              </div>
            </div>

            <div className="mt-5 flex flex-col gap-2">
              <button
                type="button"
                onClick={handleKeep}
                autoFocus
                className={cn(
                  "flex items-center gap-3 rounded-lg border px-4 py-3 text-left transition-all duration-150",
                  "border-sco-blue/40 bg-sco-blue/5 hover:border-sco-blue hover:bg-sco-blue/10",
                )}
              >
                <ArchiveRestore size={18} className="shrink-0 text-sco-blue" />
                <span className="flex-1">
                  <span className="block text-sm font-semibold text-sco-text dark:text-sco-text-dark">
                    Mantieni i dati
                  </span>
                  <span className="block text-xs text-sco-muted-foreground">
                    Continua con le tue conversazioni, i vault e le impostazioni di prima.
                  </span>
                </span>
              </button>

              <button
                type="button"
                onClick={handleWipe}
                className={cn(
                  "flex items-center gap-3 rounded-lg border px-4 py-3 text-left transition-all duration-150",
                  "border-sco-border hover:border-red-500/60 hover:bg-red-500/5",
                )}
              >
                <Trash2 size={18} className="shrink-0 text-red-500" />
                <span className="flex-1">
                  <span className="block text-sm font-semibold text-sco-text dark:text-sco-text-dark">
                    Riparti da zero
                  </span>
                  <span className="block text-xs text-sco-muted-foreground">
                    Cancella tutto e torna come appena installato. Non si può annullare.
                  </span>
                </span>
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Conferma forte digita-RESET. onResetDone registra la versione vista
          prima del reload, cosi' al riavvio non viene riproposto il dialog. */}
      <ResetDataDialog
        open={resetOpen}
        onOpenChange={setResetOpen}
        onResetDone={markSeen}
      />
    </>
  );
}
