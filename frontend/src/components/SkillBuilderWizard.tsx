// SCO Compliance OS — Wizard semplice per creare sub-agent in 7 step
//
// Goal v0.8.1: "chiunque puo' costruire un sub-agent specializzato semplicemente
// rispondendo a 7 domande in chat". Pattern Ask Question Card riusato per
// uniformita' visiva con la chat (regola 14/05 linguaggio semplice chiaro).
//
// Pipeline 7 step:
//   1. Nome del nuovo agente (input testo)
//   2. Descrizione di cosa fa (textarea)
//   3. Tipo agente (single-select: auditor / consulente / analista / scrittore /
//      ricercatore / altro)
//   4. Ambito (multi-select: cybersecurity / compliance-sanitaria / qualita /
//      sicurezza-lavoro / multi-dominio)
//   5. Tool ammessi (multi-select: Read / Write / Edit / Bash / Glob / Grep /
//      WebSearch / WebFetch / Task / TodoWrite)
//   6. Tone (single-select: amodeo-formale / neutro-tecnico / divulgativo)
//   7. Esempio domanda gestita bene (input testo, opzionale)
//
// Submit -> POST /api/skills/builder/wizard -> toast success + onCreated callback.
//
// Pattern Conv. 48: stato wizard vive in React state locale (non persistito DB).
// L'output finale (creazione skill) e' single source of truth backend.

import { useState } from "react";
import { Check, ChevronRight, Sparkles, X } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/cn";

type AgentType =
  | "auditor"
  | "consulente"
  | "analista"
  | "scrittore"
  | "ricercatore"
  | "altro";

type Ambito =
  | "cybersecurity"
  | "compliance-sanitaria"
  | "qualita"
  | "sicurezza-lavoro"
  | "multi-dominio";

type Tone = "amodeo-formale" | "neutro-tecnico" | "divulgativo";

const AGENT_TYPES: { value: AgentType; label: string; desc: string }[] = [
  { value: "auditor", label: "Auditor", desc: "Conduce audit, formula NC/SM/OSS." },
  { value: "consulente", label: "Consulente", desc: "Gap analysis, policy, piani di adeguamento." },
  { value: "analista", label: "Analista", desc: "Estrae pattern e produce sintesi gerarchiche." },
  { value: "scrittore", label: "Scrittore", desc: "Procedure, manuali, atti formali italiani." },
  { value: "ricercatore", label: "Ricercatore", desc: "Verifica fonti vault + WebSearch istituzionali." },
  { value: "altro", label: "Altro", desc: "Caso non coperto dagli archetipi." },
];

const AMBITI: { value: Ambito; label: string }[] = [
  { value: "cybersecurity", label: "Cybersecurity" },
  { value: "compliance-sanitaria", label: "Compliance sanitaria" },
  { value: "qualita", label: "Qualita'" },
  { value: "sicurezza-lavoro", label: "Sicurezza lavoro" },
  { value: "multi-dominio", label: "Multi-dominio" },
];

const TOOLS = [
  { value: "Read", label: "Read file", desc: "Legge file dal vault." },
  { value: "Write", label: "Write file", desc: "Scrive nuovi file." },
  { value: "Edit", label: "Edit file", desc: "Modifica file esistenti." },
  { value: "Bash", label: "Bash", desc: "Esegue comandi shell." },
  { value: "Glob", label: "Glob", desc: "Cerca file per pattern (es. *.md)." },
  { value: "Grep", label: "Grep", desc: "Cerca testo nei file." },
  { value: "WebSearch", label: "Web search", desc: "Cerca su internet." },
  { value: "WebFetch", label: "Web fetch", desc: "Scarica una pagina web." },
  { value: "Task", label: "Task (subagent)", desc: "Lancia un sub-agente in parallelo." },
  { value: "TodoWrite", label: "Todo list", desc: "Gestisce una lista di task." },
];

const TONES: { value: Tone; label: string; desc: string }[] = [
  {
    value: "amodeo-formale",
    label: "Amodeo formale",
    desc: "Lessico tecnico, virgolette dritte, 'al punto', humanizer.",
  },
  {
    value: "neutro-tecnico",
    label: "Neutro tecnico",
    desc: "Sobrio, sintetico, senza filler.",
  },
  {
    value: "divulgativo",
    label: "Divulgativo",
    desc: "Semplice, chiaro, immediato. Comprensibile a un bambino.",
  },
];

const TOTAL_STEPS = 7;

interface WizardState {
  name: string;
  description: string;
  agent_type: AgentType | null;
  ambiti: Ambito[];
  tools: string[];
  tone: Tone | null;
  example_question: string;
}

interface SkillBuilderWizardProps {
  /** Callback dopo creazione skill OK (riceve slug). */
  onCreated?: (slug: string) => void;
  /** Callback per chiudere il wizard senza creare. */
  onCancel?: () => void;
}

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";

export function SkillBuilderWizard({
  onCreated,
  onCancel,
}: SkillBuilderWizardProps) {
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [state, setState] = useState<WizardState>({
    name: "",
    description: "",
    agent_type: null,
    ambiti: [],
    tools: [],
    tone: null,
    example_question: "",
  });

  const canAdvance = (() => {
    switch (step) {
      case 1:
        return state.name.trim().length >= 2;
      case 2:
        return state.description.trim().length >= 10;
      case 3:
        return state.agent_type !== null;
      case 4:
        return state.ambiti.length > 0;
      case 5:
        return true; // tool whitelist opzionale, default empty (loader injecta default)
      case 6:
        return state.tone !== null;
      case 7:
        return true; // example_question opzionale
      default:
        return false;
    }
  })();

  async function submit() {
    setSubmitting(true);
    const loadingId = toast.loading("Creo il nuovo agente...");
    try {
      const body = {
        name: state.name.trim(),
        description: state.description.trim(),
        agent_type: state.agent_type ?? "altro",
        ambiti: state.ambiti,
        tools_whitelist: state.tools,
        tone: state.tone ?? "amodeo-formale",
        example_question: state.example_question.trim() || null,
        scope: "user" as const,
      };
      const res = await fetch(`${BACKEND_URL}/api/skills/builder/wizard`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      toast.dismiss(loadingId);
      if (!res.ok) {
        const errBody = await res.text().catch(() => "");
        toast.error(`Errore: HTTP ${res.status} ${errBody}`);
        return;
      }
      const data = await res.json();
      toast.success(`Agente "${data.name}" creato. Disponibile in Skills.`);
      onCreated?.(data.slug);
    } catch (e) {
      toast.dismiss(loadingId);
      toast.error(`Backend irraggiungibile: ${e instanceof Error ? e.message : "?"}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-sco-border bg-sco-surface-elevated px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sco-blue/10">
            <Sparkles size={18} className="text-sco-blue" />
          </div>
          <div>
            <h2 className="text-base font-semibold">Crea un nuovo agente</h2>
            <p className="text-xs text-sco-muted-foreground">
              Step {step} di {TOTAL_STEPS}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md p-1.5 text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
          aria-label="Annulla wizard"
          title="Annulla"
        >
          <X size={18} />
        </button>
      </div>

      {/* Progress bar */}
      <div className="h-1 w-full bg-sco-muted">
        <div
          className="h-1 bg-sco-blue transition-all duration-300"
          style={{ width: `${(step / TOTAL_STEPS) * 100}%` }}
        />
      </div>

      {/* Step body */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto max-w-xl">
          {step === 1 && (
            <StepContainer
              title="Come si chiama il nuovo agente?"
              hint="Scrivi un nome breve e chiaro (es. 'Auditor ISO 27001 sanita')."
            >
              <input
                type="text"
                autoFocus
                value={state.name}
                onChange={(e) => setState({ ...state, name: e.target.value })}
                placeholder="Es. Auditor ISO 27001 sanita"
                className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none focus:ring-1 focus:ring-sco-blue"
              />
            </StepContainer>
          )}

          {step === 2 && (
            <StepContainer
              title="Cosa fa questo agente?"
              hint="Descrivi in 1-2 frasi cosa sa fare e quando lo chiameresti."
            >
              <textarea
                autoFocus
                value={state.description}
                onChange={(e) =>
                  setState({ ...state, description: e.target.value })
                }
                placeholder="Es. Lead Auditor ISO 27001 per audit di parte terza in strutture sanitarie. Conduce audit, formula NC/SM/OSS, prepara PVV e PDV stile CSQA."
                rows={5}
                className="w-full resize-none rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none focus:ring-1 focus:ring-sco-blue"
              />
              <div className="mt-1 text-right text-xs text-sco-muted-foreground">
                {state.description.length} caratteri (min 10)
              </div>
            </StepContainer>
          )}

          {step === 3 && (
            <StepContainer
              title="Che tipo di agente e'?"
              hint="Scegli l'archetipo piu' vicino. Definisce il tono e i tool consigliati."
            >
              <div className="grid grid-cols-1 gap-2">
                {AGENT_TYPES.map((opt) => (
                  <SelectCard
                    key={opt.value}
                    label={opt.label}
                    desc={opt.desc}
                    active={state.agent_type === opt.value}
                    onClick={() => setState({ ...state, agent_type: opt.value })}
                  />
                ))}
              </div>
            </StepContainer>
          )}

          {step === 4 && (
            <StepContainer
              title="Su quali ambiti lavora?"
              hint="Selezione multipla. 'Multi-dominio' se non e' specialistico."
            >
              <div className="grid grid-cols-1 gap-2">
                {AMBITI.map((opt) => {
                  const active = state.ambiti.includes(opt.value);
                  return (
                    <SelectCard
                      key={opt.value}
                      label={opt.label}
                      multi
                      active={active}
                      onClick={() =>
                        setState({
                          ...state,
                          ambiti: active
                            ? state.ambiti.filter((a) => a !== opt.value)
                            : [...state.ambiti, opt.value],
                        })
                      }
                    />
                  );
                })}
              </div>
            </StepContainer>
          )}

          {step === 5 && (
            <StepContainer
              title="Quali strumenti deve poter usare?"
              hint="Selezione multipla. Lascia vuoto per il set predefinito."
            >
              <div className="grid grid-cols-1 gap-2">
                {TOOLS.map((opt) => {
                  const active = state.tools.includes(opt.value);
                  return (
                    <SelectCard
                      key={opt.value}
                      label={opt.label}
                      desc={opt.desc}
                      multi
                      active={active}
                      onClick={() =>
                        setState({
                          ...state,
                          tools: active
                            ? state.tools.filter((t) => t !== opt.value)
                            : [...state.tools, opt.value],
                        })
                      }
                    />
                  );
                })}
              </div>
            </StepContainer>
          )}

          {step === 6 && (
            <StepContainer
              title="Quale tono deve usare?"
              hint="Scegli il registro comunicativo."
            >
              <div className="grid grid-cols-1 gap-2">
                {TONES.map((opt) => (
                  <SelectCard
                    key={opt.value}
                    label={opt.label}
                    desc={opt.desc}
                    active={state.tone === opt.value}
                    onClick={() => setState({ ...state, tone: opt.value })}
                  />
                ))}
              </div>
            </StepContainer>
          )}

          {step === 7 && (
            <StepContainer
              title="Esempio di domanda che dovrebbe gestire bene"
              hint="Aiuta a definire meglio l'agente. Opzionale."
            >
              <textarea
                autoFocus
                value={state.example_question}
                onChange={(e) =>
                  setState({ ...state, example_question: e.target.value })
                }
                placeholder="Es. 'Prepara la checklist audit ISO 27001 Annex A.5.1 per un ospedale di 350 dipendenti.'"
                rows={4}
                className="w-full resize-none rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none focus:ring-1 focus:ring-sco-blue"
              />
              {/* Summary recap */}
              <div className="mt-6 rounded-lg border border-sco-border bg-sco-surface-elevated p-4 text-sm">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-sco-muted-foreground">
                  Riepilogo
                </div>
                <RecapRow label="Nome" value={state.name || "—"} />
                <RecapRow label="Tipo" value={state.agent_type ?? "—"} />
                <RecapRow
                  label="Ambiti"
                  value={state.ambiti.length ? state.ambiti.join(", ") : "—"}
                />
                <RecapRow
                  label="Tool"
                  value={state.tools.length ? state.tools.join(", ") : "(predefinito)"}
                />
                <RecapRow label="Tono" value={state.tone ?? "—"} />
              </div>
            </StepContainer>
          )}
        </div>
      </div>

      {/* Footer nav */}
      <div className="flex items-center justify-between border-t border-sco-border bg-sco-surface-elevated px-6 py-4">
        <button
          type="button"
          disabled={step === 1 || submitting}
          onClick={() => setStep((s) => Math.max(1, s - 1))}
          className="rounded-md px-3 py-2 text-sm text-sco-muted-foreground hover:text-sco-text dark:hover:text-sco-text-dark disabled:cursor-not-allowed disabled:opacity-40"
        >
          Indietro
        </button>
        {step < TOTAL_STEPS ? (
          <button
            type="button"
            disabled={!canAdvance}
            onClick={() => setStep((s) => Math.min(TOTAL_STEPS, s + 1))}
            className="flex items-center gap-1.5 rounded-md bg-sco-blue px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-sco-navy disabled:cursor-not-allowed disabled:opacity-40"
          >
            Avanti
            <ChevronRight size={14} />
          </button>
        ) : (
          <button
            type="button"
            disabled={submitting || !state.name || !state.description || !state.agent_type || !state.tone || state.ambiti.length === 0}
            onClick={submit}
            className="flex items-center gap-1.5 rounded-md bg-sco-blue px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-sco-navy disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Check size={14} />
            {submitting ? "Creo..." : "Crea agente"}
          </button>
        )}
      </div>
    </div>
  );
}

// ----- Sub-components -----

function StepContainer({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-lg font-semibold text-sco-text dark:text-sco-text-dark">
        {title}
      </h3>
      {hint && (
        <p className="mb-4 mt-1 text-sm text-sco-muted-foreground">{hint}</p>
      )}
      <div className="mt-4">{children}</div>
    </div>
  );
}

function SelectCard({
  label,
  desc,
  active,
  onClick,
  multi = false,
}: {
  label: string;
  desc?: string;
  active: boolean;
  onClick: () => void;
  multi?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-start gap-3 rounded-lg border p-3 text-left transition-all",
        active
          ? "border-sco-blue bg-sco-blue/10 ring-1 ring-sco-blue"
          : "border-sco-border bg-sco-bg hover:border-sco-blue/60",
      )}
    >
      <span
        className={cn(
          "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center border",
          multi ? "rounded-sm" : "rounded-full",
          active
            ? "border-sco-blue bg-sco-blue text-white"
            : "border-sco-border bg-sco-bg",
        )}
      >
        {active && <Check size={12} strokeWidth={3} />}
      </span>
      <div className="flex-1">
        <div className="text-sm font-medium text-sco-text dark:text-sco-text-dark">
          {label}
        </div>
        {desc && (
          <div className="mt-0.5 text-xs text-sco-muted-foreground">{desc}</div>
        )}
      </div>
    </button>
  );
}

function RecapRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 py-1">
      <span className="text-xs uppercase tracking-wider text-sco-muted-foreground">
        {label}
      </span>
      <span className="text-right text-sm font-medium">{value}</span>
    </div>
  );
}
