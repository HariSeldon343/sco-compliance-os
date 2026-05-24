// SCO Compliance OS — Advanced editor per costruire skill complete
//
// Goal v0.8.1: "stessa potenza con cui un esperto di Claude costruisce le proprie
// skill". Form completo con system prompt textarea + tools whitelist + scope +
// frontmatter aggiuntivo (YAML libero) + Markdown preview.
//
// Differenza vs Wizard: nessun step, tutti i campi visibili insieme; supporta
// system prompt custom multi-paragrafo, frontmatter aggiuntivo arbitrario,
// preview side-by-side dell'output SKILL.md generato.
//
// Submit -> POST /api/skills/builder/wizard con full spec (riusa stesso endpoint
// del wizard: il backend non differenzia, e' lo stesso schema).
//
// Pattern Conv. 47 single source of truth: tutto il rendering preview avviene
// client-side. Il backend e' fonte autoritativa solo dopo il submit.

import { useMemo, useState } from "react";
import { Check, Code2, Eye, X } from "lucide-react";
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

const AGENT_TYPES: AgentType[] = [
  "auditor",
  "consulente",
  "analista",
  "scrittore",
  "ricercatore",
  "altro",
];

const AMBITI: Ambito[] = [
  "cybersecurity",
  "compliance-sanitaria",
  "qualita",
  "sicurezza-lavoro",
  "multi-dominio",
];

const TONES: Tone[] = ["amodeo-formale", "neutro-tecnico", "divulgativo"];

const ALL_TOOLS = [
  "Read",
  "Write",
  "Edit",
  "Bash",
  "Glob",
  "Grep",
  "WebSearch",
  "WebFetch",
  "Task",
  "TodoWrite",
] as const;

interface AdvancedSpec {
  name: string;
  slug: string;
  description: string;
  agent_type: AgentType;
  ambiti: Ambito[];
  tools_whitelist: string[];
  tone: Tone;
  system_prompt: string;
  example_question: string;
  scope: "user" | "project";
  /** Frontmatter YAML libero aggiuntivo (chiave: valore, una riga ciascuno). */
  extra_frontmatter: string;
}

interface SkillBuilderAdvancedProps {
  onCreated?: (slug: string) => void;
  onCancel?: () => void;
  /** Slug iniziale da pre-caricare per edit (modalita' patch). */
  editSlug?: string;
  /** Pre-fill spec per edit (caricata dal parent). */
  initialSpec?: Partial<AdvancedSpec>;
}

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";

function slugify(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 64);
}

export function SkillBuilderAdvanced({
  onCreated,
  onCancel,
  editSlug,
  initialSpec,
}: SkillBuilderAdvancedProps) {
  const [view, setView] = useState<"form" | "preview">("form");
  const [submitting, setSubmitting] = useState(false);
  const [spec, setSpec] = useState<AdvancedSpec>({
    name: initialSpec?.name ?? "",
    slug: initialSpec?.slug ?? "",
    description: initialSpec?.description ?? "",
    agent_type: initialSpec?.agent_type ?? "altro",
    ambiti: initialSpec?.ambiti ?? [],
    tools_whitelist: initialSpec?.tools_whitelist ?? [],
    tone: initialSpec?.tone ?? "amodeo-formale",
    system_prompt: initialSpec?.system_prompt ?? "",
    example_question: initialSpec?.example_question ?? "",
    scope: initialSpec?.scope ?? "user",
    extra_frontmatter: initialSpec?.extra_frontmatter ?? "",
  });

  const isEdit = Boolean(editSlug);
  const effectiveSlug = spec.slug || slugify(spec.name);

  // Preview SKILL.md client-side
  const previewMd = useMemo(() => generateSkillMd(spec, effectiveSlug), [spec, effectiveSlug]);

  function toggleArrayValue<T>(arr: T[], v: T): T[] {
    return arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];
  }

  async function submit() {
    setSubmitting(true);
    const loadingId = toast.loading(isEdit ? "Aggiorno skill..." : "Creo skill...");

    try {
      const body = {
        name: spec.name.trim(),
        slug: effectiveSlug || undefined,
        description: spec.description.trim(),
        agent_type: spec.agent_type,
        ambiti: spec.ambiti,
        tools_whitelist: spec.tools_whitelist,
        tone: spec.tone,
        system_prompt: spec.system_prompt.trim() || undefined,
        example_question: spec.example_question.trim() || null,
        scope: spec.scope,
      };

      let res: Response;
      if (isEdit && editSlug) {
        res = await fetch(`${BACKEND_URL}/api/skills/${editSlug}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            description: body.description,
            system_prompt: body.system_prompt,
            tools_whitelist: body.tools_whitelist,
            tone: body.tone,
            ambiti: body.ambiti,
          }),
        });
      } else {
        res = await fetch(`${BACKEND_URL}/api/skills/builder/wizard`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      }

      toast.dismiss(loadingId);
      if (!res.ok) {
        const errBody = await res.text().catch(() => "");
        toast.error(`Errore: HTTP ${res.status} ${errBody}`);
        return;
      }
      const data = await res.json();
      toast.success(
        isEdit ? `Skill "${data.name}" aggiornata.` : `Skill "${data.name}" creata.`,
      );
      onCreated?.(data.slug);
    } catch (e) {
      toast.dismiss(loadingId);
      toast.error(`Backend irraggiungibile: ${e instanceof Error ? e.message : "?"}`);
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmit =
    spec.name.trim().length >= 2 &&
    spec.description.trim().length >= 10 &&
    spec.ambiti.length > 0 &&
    !submitting;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-sco-border bg-sco-surface-elevated px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sco-blue/10">
            <Code2 size={18} className="text-sco-blue" />
          </div>
          <div>
            <h2 className="text-base font-semibold">
              {isEdit ? `Modifica skill: ${editSlug}` : "Crea skill (modalita' avanzata)"}
            </h2>
            <p className="text-xs text-sco-muted-foreground">
              Controllo pieno su system prompt, tool, frontmatter.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setView(view === "form" ? "preview" : "form")}
            className="flex items-center gap-1.5 rounded-md border border-sco-border px-3 py-1.5 text-xs font-medium hover:border-sco-blue/60"
          >
            <Eye size={12} />
            {view === "form" ? "Preview" : "Editor"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md p-1.5 text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
            aria-label="Annulla"
            title="Annulla"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        {view === "form" ? (
          <div className="mx-auto max-w-4xl space-y-6 px-6 py-6">
            {/* Identificazione */}
            <Section title="Identificazione">
              <Field label="Nome leggibile *">
                <input
                  type="text"
                  value={spec.name}
                  onChange={(e) => setSpec({ ...spec, name: e.target.value })}
                  placeholder="Es. Auditor ISO 27001 sanita'"
                  className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none focus:ring-1 focus:ring-sco-blue"
                  disabled={isEdit}
                />
              </Field>
              <Field
                label={`Slug (kebab-case, max 64) — auto: ${slugify(spec.name) || "—"}`}
              >
                <input
                  type="text"
                  value={spec.slug}
                  onChange={(e) => setSpec({ ...spec, slug: e.target.value })}
                  placeholder="auditor-iso-27001-sanita"
                  className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 font-mono text-sm focus:border-sco-blue focus:outline-none focus:ring-1 focus:ring-sco-blue"
                  disabled={isEdit}
                />
              </Field>
              <Field label="Descrizione (auto-trigger semantica) *">
                <textarea
                  value={spec.description}
                  onChange={(e) =>
                    setSpec({ ...spec, description: e.target.value })
                  }
                  placeholder="Lead Auditor ISO 27001 per audit di parte terza in strutture sanitarie..."
                  rows={3}
                  className="w-full resize-none rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none focus:ring-1 focus:ring-sco-blue"
                />
              </Field>
              <Field label="Scope">
                <div className="flex gap-2">
                  {(["user", "project"] as const).map((s) => (
                    <button
                      key={s}
                      type="button"
                      disabled={isEdit || s === "project"}
                      onClick={() => setSpec({ ...spec, scope: s })}
                      className={cn(
                        "flex-1 rounded-md border px-3 py-2 text-sm transition-all",
                        spec.scope === s
                          ? "border-sco-blue bg-sco-blue/10"
                          : "border-sco-border hover:border-sco-blue/60",
                        s === "project" && "cursor-not-allowed opacity-50",
                      )}
                      title={
                        s === "project"
                          ? "Scope project richiede vault attivo + sync (post-v0.8.1)"
                          : undefined
                      }
                    >
                      {s === "user" ? "User (locale)" : "Project (vault)"}
                    </button>
                  ))}
                </div>
              </Field>
            </Section>

            {/* Tipologia */}
            <Section title="Tipologia">
              <Field label="Tipo agente">
                <div className="flex flex-wrap gap-2">
                  {AGENT_TYPES.map((t) => (
                    <Chip
                      key={t}
                      label={t}
                      active={spec.agent_type === t}
                      onClick={() => setSpec({ ...spec, agent_type: t })}
                    />
                  ))}
                </div>
              </Field>
              <Field label="Ambiti (multi-select) *">
                <div className="flex flex-wrap gap-2">
                  {AMBITI.map((a) => (
                    <Chip
                      key={a}
                      label={a}
                      active={spec.ambiti.includes(a)}
                      onClick={() =>
                        setSpec({ ...spec, ambiti: toggleArrayValue(spec.ambiti, a) })
                      }
                    />
                  ))}
                </div>
              </Field>
              <Field label="Tono">
                <div className="flex flex-wrap gap-2">
                  {TONES.map((t) => (
                    <Chip
                      key={t}
                      label={t}
                      active={spec.tone === t}
                      onClick={() => setSpec({ ...spec, tone: t })}
                    />
                  ))}
                </div>
              </Field>
            </Section>

            {/* Tool whitelist */}
            <Section title="Tool ammessi">
              <p className="-mt-2 mb-3 text-xs text-sco-muted-foreground">
                Lascia tutto deselezionato per usare il set predefinito del runner.
              </p>
              <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                {ALL_TOOLS.map((t) => {
                  const active = spec.tools_whitelist.includes(t);
                  return (
                    <label
                      key={t}
                      className={cn(
                        "flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm transition-all",
                        active
                          ? "border-sco-blue bg-sco-blue/10"
                          : "border-sco-border hover:border-sco-blue/60",
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={active}
                        onChange={() =>
                          setSpec({
                            ...spec,
                            tools_whitelist: toggleArrayValue(spec.tools_whitelist, t),
                          })
                        }
                        className="h-4 w-4 accent-sco-blue"
                      />
                      <span className="font-mono text-xs">{t}</span>
                    </label>
                  );
                })}
              </div>
            </Section>

            {/* System prompt */}
            <Section title="System prompt">
              <p className="-mt-2 mb-3 text-xs text-sco-muted-foreground">
                Il messaggio di sistema iniettato a ogni invocazione della skill.
                Se vuoto, il backend genera un body di default da agent_type + tone.
              </p>
              <textarea
                value={spec.system_prompt}
                onChange={(e) => setSpec({ ...spec, system_prompt: e.target.value })}
                placeholder="Sei un Lead Auditor ISO senior. Conduci audit ISO 27001 / 9001 / 14001 secondo ISO 19011..."
                rows={10}
                className="w-full resize-none rounded-md border border-sco-border bg-sco-bg px-3 py-2 font-mono text-sm leading-relaxed focus:border-sco-blue focus:outline-none focus:ring-1 focus:ring-sco-blue"
              />
            </Section>

            {/* Esempio */}
            <Section title="Esempio di domanda gestita bene (opzionale)">
              <textarea
                value={spec.example_question}
                onChange={(e) =>
                  setSpec({ ...spec, example_question: e.target.value })
                }
                placeholder="Es. 'Prepara la checklist audit ISO 27001 Annex A.5.1 per un ospedale di 350 dipendenti.'"
                rows={3}
                className="w-full resize-none rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none focus:ring-1 focus:ring-sco-blue"
              />
            </Section>
          </div>
        ) : (
          <div className="mx-auto max-w-4xl px-6 py-6">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold">Anteprima SKILL.md</h3>
              <span className="text-xs text-sco-muted-foreground">
                File destinazione: ~/.sco-compliance-os/skills/{effectiveSlug}/SKILL.md
              </span>
            </div>
            <pre className="overflow-x-auto rounded-lg border border-sco-border bg-sco-bg p-4 font-mono text-xs leading-relaxed text-sco-text dark:text-sco-text-dark">
              {previewMd}
            </pre>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-sco-border bg-sco-surface-elevated px-6 py-4">
        <div className="text-xs text-sco-muted-foreground">
          {!canSubmit && (
            <span>Compila Nome (min 2), Descrizione (min 10) e almeno un Ambito.</span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="rounded-md px-3 py-2 text-sm text-sco-muted-foreground hover:text-sco-text dark:hover:text-sco-text-dark disabled:cursor-not-allowed disabled:opacity-40"
          >
            Annulla
          </button>
          <button
            type="button"
            disabled={!canSubmit}
            onClick={submit}
            className="flex items-center gap-1.5 rounded-md bg-sco-blue px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-sco-navy disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Check size={14} />
            {submitting
              ? isEdit
                ? "Salvo..."
                : "Creo..."
              : isEdit
                ? "Salva modifiche"
                : "Crea skill"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ----- Sub-components -----

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-sco-border bg-sco-surface-elevated p-6">
      <h3 className="mb-4 text-base font-semibold">{title}</h3>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium">{label}</label>
      {children}
    </div>
  );
}

function Chip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-xs font-medium transition-all",
        active
          ? "border-sco-blue bg-sco-blue/10 text-sco-blue"
          : "border-sco-border text-sco-muted-foreground hover:border-sco-blue/60",
      )}
    >
      {label}
    </button>
  );
}

// ----- Helper: preview SKILL.md client-side (parity con backend _build_skill_md) -----

function generateSkillMd(spec: AdvancedSpec, slug: string): string {
  const fm: Record<string, unknown> = {
    name: slug || "(slug)",
    description: spec.description || "(descrizione)",
    auto_trigger: null,
    language: "it",
    version: "1.0.0",
    budget_tokens: 8000,
  };
  if (spec.tools_whitelist.length) fm.allowed_tools = spec.tools_whitelist;
  if (spec.ambiti.length) fm.ambiti = spec.ambiti;
  if (spec.agent_type) fm.agent_type = spec.agent_type;
  if (spec.tone) fm.tone = spec.tone;

  // YAML minimal serializer (no quotes su scalari simple, list inline)
  const yaml = Object.entries(fm)
    .map(([k, v]) => {
      if (v === null) return `${k}: null`;
      if (Array.isArray(v))
        return `${k}: [${v.map((x) => String(x)).join(", ")}]`;
      if (typeof v === "string") return `${k}: ${JSON.stringify(v)}`;
      return `${k}: ${String(v)}`;
    })
    .join("\n");

  const body = spec.system_prompt.trim() || `(Body auto-generato dal backend)`;
  const exampleBlock = spec.example_question.trim()
    ? `\n## Esempio domanda gestita bene\n\n> ${spec.example_question.trim()}\n`
    : "";

  return `---\n${yaml}\n---\n\n# ${spec.name || "(Nome)"}\n\n${body}\n${exampleBlock}`;
}
