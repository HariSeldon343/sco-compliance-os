// SCO Compliance OS — Schermata Skills (v0.8.1 DEV-SUBAGENT-BUILDER)
//
// Goal v0.8.1: punto unico dove l'utente vede tutte le skill installate
// (Legacy bundled + Project + User), ne crea di nuove con Wizard semplice o
// con Advanced editor, modifica/elimina le proprie skill custom.
//
// Layout:
//   Header: titolo + 2 CTA "Crea nuovo (Wizard)" / "Crea nuovo (Avanzato)"
//   Body 2 colonne:
//     - left: lista skill raggruppate per scope (badge colorato)
//     - right: detail panel con preview SKILL.md + action Edit / Delete
//
// Pattern Conv. 47 single source of truth: GET /api/skills/list re-run a ogni
// mount + refresh post-create/edit/delete.
// Pattern Conv. 48: stato selezione skill vive solo lato React (non persistito).

import { useCallback, useEffect, useState } from "react";
import {
  Sparkles,
  Code2,
  Pencil,
  Trash2,
  Lock,
  FolderTree,
  Database,
  User,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";

import { SkillBuilderWizard } from "@/components/SkillBuilderWizard";
import { SkillBuilderAdvanced } from "@/components/SkillBuilderAdvanced";
import { cn } from "@/lib/cn";

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";

interface SkillSummary {
  name: string;
  description: string;
  scope: "user" | "project" | "legacy";
  path: string;
  auto_trigger: string | null;
  language: string;
}

type Mode = "list" | "wizard" | "advanced" | "edit";

const SCOPE_META: Record<
  SkillSummary["scope"],
  { label: string; color: string; icon: typeof Database }
> = {
  user: {
    label: "Tue skill",
    color: "bg-sco-blue/10 text-sco-blue border-sco-blue/30",
    icon: User,
  },
  project: {
    label: "Vault",
    color: "bg-purple-500/10 text-purple-700 border-purple-500/30 dark:text-purple-300",
    icon: FolderTree,
  },
  legacy: {
    label: "Predefinite",
    color: "bg-gray-500/10 text-gray-700 border-gray-500/30 dark:text-gray-300",
    icon: Database,
  },
};

export function SkillsScreen() {
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("list");
  const [skillBody, setSkillBody] = useState<string>("");

  const fetchSkills = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/skills/list`);
      if (!res.ok) {
        toast.error(`Errore caricamento: HTTP ${res.status}`);
        setSkills([]);
        return;
      }
      const data: SkillSummary[] = await res.json();
      setSkills(data);
    } catch (e) {
      toast.error(
        `Backend irraggiungibile: ${e instanceof Error ? e.message : "?"}`,
      );
      setSkills([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchSkills();
  }, [fetchSkills]);

  // Carica body SKILL.md quando seleziono una skill (preview detail panel)
  useEffect(() => {
    if (!selected) {
      setSkillBody("");
      return;
    }
    const skill = skills.find((s) => s.name === selected);
    if (!skill) return;
    // No endpoint dedicato per body raw: fallback su file:// fetch impossibile
    // dal renderer Tauri. Preview riassuntiva da description.
    setSkillBody(
      `# ${skill.name}\n\n**Scope:** ${skill.scope}\n**Path:** ${skill.path}\n\n${skill.description}`,
    );
  }, [selected, skills]);

  async function handleDelete(slug: string) {
    if (!confirm(`Eliminare la skill "${slug}"? Non e' reversibile.`)) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/skills/${slug}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        toast.error(`Errore eliminazione: ${body || res.status}`);
        return;
      }
      toast.success(`Skill "${slug}" eliminata.`);
      if (selected === slug) setSelected(null);
      void fetchSkills();
    } catch (e) {
      toast.error(`Errore: ${e instanceof Error ? e.message : "?"}`);
    }
  }

  if (mode === "wizard") {
    return (
      <div className="h-full">
        <SkillBuilderWizard
          onCreated={() => {
            setMode("list");
            void fetchSkills();
          }}
          onCancel={() => setMode("list")}
        />
      </div>
    );
  }

  if (mode === "advanced") {
    return (
      <div className="h-full">
        <SkillBuilderAdvanced
          onCreated={() => {
            setMode("list");
            void fetchSkills();
          }}
          onCancel={() => setMode("list")}
        />
      </div>
    );
  }

  if (mode === "edit" && selected) {
    const skill = skills.find((s) => s.name === selected);
    if (skill?.scope !== "user") {
      // Safety: solo user-scope editabile (backend enforcement, ma UI guard)
      setMode("list");
      return null;
    }
    return (
      <div className="h-full">
        <SkillBuilderAdvanced
          editSlug={selected}
          initialSpec={{
            name: skill.name,
            description: skill.description,
            slug: selected,
          }}
          onCreated={() => {
            setMode("list");
            void fetchSkills();
          }}
          onCancel={() => setMode("list")}
        />
      </div>
    );
  }

  // ----- Mode "list" -----

  const userSkills = skills.filter((s) => s.scope === "user");
  const projectSkills = skills.filter((s) => s.scope === "project");
  const legacySkills = skills.filter((s) => s.scope === "legacy");

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-sco-border bg-sco-surface-elevated px-8 py-6">
        <div className="mx-auto max-w-6xl">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="flex items-center gap-2 text-2xl font-semibold text-sco-navy dark:text-sco-text-dark">
                <Sparkles size={22} className="text-sco-blue" />
                Skills
              </h1>
              <p className="mt-1 text-sm text-sco-muted-foreground">
                Agenti specializzati su misura. Crea nuovi agenti con poche
                domande o con l'editor avanzato.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setMode("wizard")}
                className="flex items-center gap-2 rounded-md bg-sco-blue px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-sco-navy"
              >
                <Wand2 size={14} />
                Crea nuovo (Wizard)
              </button>
              <button
                type="button"
                onClick={() => setMode("advanced")}
                className="flex items-center gap-2 rounded-md border border-sco-border px-4 py-2 text-sm font-medium hover:border-sco-blue/60"
              >
                <Code2 size={14} />
                Crea nuovo (Avanzato)
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Body 2-col */}
      <div className="mx-auto grid h-full w-full max-w-6xl flex-1 grid-cols-[1fr_400px] gap-6 overflow-hidden px-8 py-6">
        {/* Lista skill */}
        <div className="overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-sm text-sco-muted-foreground">
              Caricamento skill...
            </div>
          ) : skills.length === 0 ? (
            <div className="rounded-lg border border-dashed border-sco-border p-12 text-center text-sm text-sco-muted-foreground">
              Nessuna skill installata. Crea il tuo primo agente.
            </div>
          ) : (
            <div className="space-y-6">
              {userSkills.length > 0 && (
                <SkillGroup
                  title="Tue skill"
                  scope="user"
                  skills={userSkills}
                  selected={selected}
                  onSelect={setSelected}
                />
              )}
              {projectSkills.length > 0 && (
                <SkillGroup
                  title="Vault"
                  scope="project"
                  skills={projectSkills}
                  selected={selected}
                  onSelect={setSelected}
                />
              )}
              {legacySkills.length > 0 && (
                <SkillGroup
                  title="Predefinite"
                  scope="legacy"
                  skills={legacySkills}
                  selected={selected}
                  onSelect={setSelected}
                />
              )}
            </div>
          )}
        </div>

        {/* Detail panel */}
        <div className="overflow-y-auto rounded-lg border border-sco-border bg-sco-surface-elevated">
          {selected ? (
            (() => {
              const skill = skills.find((s) => s.name === selected);
              if (!skill) return null;
              const meta = SCOPE_META[skill.scope];
              const Icon = meta.icon;
              const isUserOwned = skill.scope === "user";
              return (
                <div className="p-5">
                  <div className="mb-3 flex items-center justify-between">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                        meta.color,
                      )}
                    >
                      <Icon size={10} />
                      {meta.label}
                    </span>
                    {!isUserOwned && (
                      <span
                        className="flex items-center gap-1 text-xs text-sco-muted-foreground"
                        title="Solo le tue skill sono modificabili. Predefinite e Vault sono protette."
                      >
                        <Lock size={11} />
                        Protetta
                      </span>
                    )}
                  </div>

                  <h3 className="text-base font-semibold">{skill.name}</h3>
                  <p className="mt-1 text-xs text-sco-muted-foreground">
                    {skill.description}
                  </p>

                  <div className="mt-4 space-y-2 text-xs">
                    <DetailRow label="Path" value={skill.path} mono />
                    <DetailRow label="Lingua" value={skill.language} />
                    {skill.auto_trigger && (
                      <DetailRow label="Auto trigger" value={skill.auto_trigger} />
                    )}
                  </div>

                  <div className="mt-5 border-t border-sco-border pt-4">
                    <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
                      Preview
                    </div>
                    <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-md bg-sco-bg p-3 font-mono text-[11px] leading-relaxed">
                      {skillBody}
                    </pre>
                  </div>

                  {isUserOwned && (
                    <div className="mt-4 flex gap-2 border-t border-sco-border pt-4">
                      <button
                        type="button"
                        onClick={() => setMode("edit")}
                        className="flex flex-1 items-center justify-center gap-1.5 rounded-md border border-sco-border px-3 py-2 text-xs font-medium hover:border-sco-blue/60"
                      >
                        <Pencil size={12} />
                        Modifica
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(skill.name)}
                        className="flex flex-1 items-center justify-center gap-1.5 rounded-md border border-red-300 px-3 py-2 text-xs font-medium text-red-700 hover:bg-red-50 dark:border-red-900 dark:text-red-300 dark:hover:bg-red-950"
                      >
                        <Trash2 size={12} />
                        Elimina
                      </button>
                    </div>
                  )}
                </div>
              );
            })()
          ) : (
            <div className="flex h-full items-center justify-center p-6 text-center text-xs italic text-sco-muted-foreground">
              Seleziona una skill per vedere i dettagli.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ----- Sub-components -----

function SkillGroup({
  title,
  scope,
  skills,
  selected,
  onSelect,
}: {
  title: string;
  scope: SkillSummary["scope"];
  skills: SkillSummary[];
  selected: string | null;
  onSelect: (name: string) => void;
}) {
  const meta = SCOPE_META[scope];
  const Icon = meta.icon;
  return (
    <div>
      <div className="mb-2 flex items-center gap-2 px-1">
        <Icon size={13} className="text-sco-muted-foreground" />
        <span className="text-xs font-semibold uppercase tracking-wider text-sco-muted-foreground">
          {title}
        </span>
        <span className="text-[10px] text-sco-muted-foreground">
          ({skills.length})
        </span>
      </div>
      <ul className="space-y-1.5">
        {skills.map((s) => {
          const isActive = selected === s.name;
          return (
            <li key={s.name}>
              <button
                type="button"
                onClick={() => onSelect(s.name)}
                className={cn(
                  "flex w-full flex-col gap-1 rounded-md border px-3 py-2.5 text-left transition-all",
                  isActive
                    ? "border-sco-blue bg-sco-blue/10"
                    : "border-sco-border bg-sco-surface-elevated hover:border-sco-blue/60",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-mono text-sm font-medium">
                    {s.name}
                  </span>
                  {scope !== "user" && (
                    <Lock
                      size={10}
                      className="shrink-0 text-sco-muted-foreground"
                    />
                  )}
                </div>
                <p className="line-clamp-2 text-xs text-sco-muted-foreground">
                  {s.description}
                </p>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function DetailRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex gap-2">
      <span className="shrink-0 text-sco-muted-foreground">{label}:</span>
      <span
        className={cn("min-w-0 break-all", mono && "font-mono text-[10px]")}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}
