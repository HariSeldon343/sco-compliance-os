// SCO Compliance OS — SubconsciousScreen: pannello del Subconscio (v0.15.0).
// Mostra stato del "battito" in background, cosa ha fatto/proposto, e permette
// di accendere/spegnere + eseguire un battito manuale. Linguaggio semplice 14/05.
import { useCallback, useEffect, useState } from "react";
import {
  Brain,
  Power,
  PowerOff,
  Play,
  RefreshCw,
  Loader2,
  CheckCircle2,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

import { apiClient } from "@/api/client";
import type { SubconsciousActivityEntry, SubconsciousStatus } from "@/types/api";
import { cn } from "@/lib/cn";

function decisionLabel(decision: string | null): string {
  switch (decision) {
    case "SKIP":
      return "Ha lasciato perdere";
    case "ACT":
      return "Ha fatto un'azione";
    case "ESCALATE":
      return "Ti ha proposto qualcosa";
    default:
      return "—";
  }
}

function formatTs(ts: string | null): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString("it-IT", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

export function SubconsciousScreen() {
  const [status, setStatus] = useState<SubconsciousStatus | null>(null);
  const [activity, setActivity] = useState<SubconsciousActivityEntry[]>([]);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [s, a] = await Promise.all([
        apiClient.subconscious.status(),
        apiClient.subconscious.activity(50),
      ]);
      setStatus(s);
      // piu' recenti in cima
      setActivity(a.entries.slice().reverse());
    } catch {
      // backend non pronto: riproviamo al prossimo poll
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), 10_000);
    return () => clearInterval(id);
  }, [refresh]);

  const handleToggle = async () => {
    if (!status || busy) return;
    setBusy(true);
    try {
      if (status.running) {
        await apiClient.subconscious.disable();
        toast.success("Subconscio spento.");
      } else {
        await apiClient.subconscious.enable();
        toast.success("Subconscio acceso. Lavora in background ogni 5 minuti.");
      }
      await refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Operazione non riuscita: ${msg}`);
    } finally {
      setBusy(false);
    }
  };

  const handleTick = async () => {
    if (busy) return;
    setBusy(true);
    const loadingId = toast.loading("Eseguo un battito ora...");
    try {
      const r = await apiClient.subconscious.tick();
      toast.dismiss(loadingId);
      toast.success(`Battito eseguito: ${decisionLabel(r.decision)}.`);
      await refresh();
    } catch (err) {
      toast.dismiss(loadingId);
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Battito non riuscito: ${msg}`);
    } finally {
      setBusy(false);
    }
  };

  const running = status?.running ?? false;

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      {/* Intestazione */}
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sco-blue/10 text-sco-blue">
          <Brain size={22} />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-sco-text dark:text-sco-text-dark">
            Subconscio
          </h1>
          <p className="mt-1 text-sm text-sco-muted-foreground">
            Un assistente che lavora in background ogni 5 minuti: tiene d&apos;occhio
            le scadenze dei tuoi vault e riordina la memoria. Fa da solo solo cose
            sicure; per il resto ti propone e decidi tu.
          </p>
        </div>
      </div>

      {/* Stato + controlli */}
      <section className="rounded-xl border border-sco-border bg-sco-surface-elevated p-6">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "flex h-3 w-3 rounded-full",
                running ? "bg-green-500" : "bg-sco-muted-foreground/40",
              )}
            />
            <div>
              <div className="text-base font-semibold text-sco-text dark:text-sco-text-dark">
                {running ? "Acceso" : "Spento"}
              </div>
              <div className="text-xs text-sco-muted-foreground">
                {status?.enabled
                  ? "Si avvia da solo all'apertura dell'app"
                  : "Avvio automatico disattivato (opt-in nelle impostazioni)"}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleTick}
              disabled={busy || !running}
              title={running ? "Esegui un battito ora" : "Accendi prima il Subconscio"}
              className="inline-flex items-center gap-2 rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm transition-colors hover:border-sco-blue hover:bg-sco-blue/5 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              Battito ora
            </button>
            <button
              type="button"
              onClick={handleToggle}
              disabled={busy}
              className={cn(
                "inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-white transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                running ? "bg-red-600 hover:bg-red-700" : "bg-sco-blue hover:bg-sco-navy",
              )}
            >
              {running ? <PowerOff size={14} /> : <Power size={14} />}
              {running ? "Spegni" : "Accendi"}
            </button>
          </div>
        </div>

        {/* Metriche rapide */}
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Metric label="Ultima decisione" value={decisionLabel(status?.last_tick_decision ?? null)} />
          <Metric label="Battiti oggi" value={String(status?.ticks_today ?? 0)} />
          <Metric label="Ultimo battito" value={formatTs(status?.last_tick_completed_at ?? null)} />
        </div>

        {status?.last_tick_rationale && (
          <div className="mt-3 rounded-lg border border-sco-border bg-sco-bg p-3 text-xs text-sco-muted-foreground">
            <span className="font-medium">Perche&apos;:</span> {status.last_tick_rationale}
            {status.last_tick_action_executed && status.last_tick_action_detail && (
              <div className="mt-1 flex items-center gap-1 text-green-600 dark:text-green-400">
                <CheckCircle2 size={12} />
                {status.last_tick_action_detail}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Registro attivita */}
      <section className="rounded-xl border border-sco-border bg-sco-surface-elevated p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-sco-text dark:text-sco-text-dark">
            Cosa ha fatto
          </h2>
          <button
            type="button"
            onClick={() => void refresh()}
            className="inline-flex items-center gap-1.5 rounded-md border border-sco-border bg-sco-bg px-2.5 py-1.5 text-xs transition-colors hover:border-sco-blue hover:bg-sco-blue/5"
          >
            <RefreshCw size={12} />
            Aggiorna
          </button>
        </div>

        {activity.length === 0 ? (
          <div className="rounded-lg border border-dashed border-sco-border bg-sco-bg p-6 text-center text-sm text-sco-muted-foreground">
            Ancora nessuna attivita. Quando il Subconscio e&apos; acceso, qui compaiono
            i suoi battiti.
          </div>
        ) : (
          <ul className="space-y-2">
            {activity.map((e, i) => (
              <li
                key={`${e.ts}-${i}`}
                className="flex items-start gap-3 rounded-lg border border-sco-border bg-sco-bg p-3"
              >
                <span className="mt-0.5 shrink-0">
                  {e.action_executed ? (
                    <CheckCircle2 size={15} className="text-green-500" />
                  ) : e.decision === "ESCALATE" ? (
                    <AlertTriangle size={15} className="text-sco-amber" />
                  ) : (
                    <Clock size={15} className="text-sco-muted-foreground" />
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-sco-text dark:text-sco-text-dark">
                      {decisionLabel(e.decision)}
                    </span>
                    <span className="shrink-0 text-xs text-sco-muted-foreground">
                      {formatTs(e.ts)}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-sco-muted-foreground">{e.rationale}</p>
                  {e.action_executed && e.action_detail && (
                    <p className="mt-1 text-xs text-green-600 dark:text-green-400">
                      {e.action_detail}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-sco-border bg-sco-bg px-3 py-2">
      <div className="text-[11px] font-medium uppercase tracking-wide text-sco-muted-foreground">
        {label}
      </div>
      <div className="mt-0.5 truncate text-sm text-sco-text dark:text-sco-text-dark" title={value}>
        {value}
      </div>
    </div>
  );
}
