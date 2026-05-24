// SCO Compliance OS — Settings Tab "Team"
// v0.8.1: mode toggle Solo/Team + (se Team) nome team + lista membri (manual
// entry) + tuo ruolo. Cross-device team sync = carry-over post-v0.8.x (oggi
// vive locale per macchina).

import { useState } from "react";
import { Users, UserPlus, Trash2, User as UserIcon } from "lucide-react";

import { useTeamStore, type TeamMode } from "@/store/team-store";
import { cn } from "@/lib/cn";

export function TeamTab() {
  const mode = useTeamStore((s) => s.mode);
  const teamNome = useTeamStore((s) => s.teamNome);
  const mioRuolo = useTeamStore((s) => s.mioRuolo);
  const membri = useTeamStore((s) => s.membri);
  const setMode = useTeamStore((s) => s.setMode);
  const setTeamNome = useTeamStore((s) => s.setTeamNome);
  const setMioRuolo = useTeamStore((s) => s.setMioRuolo);
  const addMembro = useTeamStore((s) => s.addMembro);
  const removeMembro = useTeamStore((s) => s.removeMembro);

  const [newMemberNome, setNewMemberNome] = useState("");
  const [newMemberRuolo, setNewMemberRuolo] = useState("");
  const [newMemberEmail, setNewMemberEmail] = useState("");

  const handleAddMembro = () => {
    if (!newMemberNome.trim()) return;
    addMembro({
      nome: newMemberNome.trim(),
      ruolo: newMemberRuolo.trim(),
      email: newMemberEmail.trim(),
    });
    setNewMemberNome("");
    setNewMemberRuolo("");
    setNewMemberEmail("");
  };

  return (
    <div className="space-y-6">
      {/* Modalita` Solo/Team */}
      <Card icon={Users} title="Modalita` di lavoro">
        <p className="mb-4 text-xs text-sco-muted-foreground">
          Stai usando l'agente da solo o in team con altri colleghi? La
          modalita` team abilita la condivisione di profili, ruoli e contesto.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          {(
            [
              {
                value: "solo",
                label: "Solo",
                desc: "Lavori da solo. Profilo singolo, niente condivisione team.",
                icon: UserIcon,
              },
              {
                value: "team",
                label: "Team",
                desc: "Lavori con altri colleghi. Profilo team + ruoli + membri visibili.",
                icon: Users,
              },
            ] as Array<{
              value: TeamMode;
              label: string;
              desc: string;
              icon: typeof Users;
            }>
          ).map((opt) => {
            const Icon = opt.icon;
            const active = mode === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setMode(opt.value)}
                className={cn(
                  "flex flex-col gap-2 rounded-lg border p-4 text-left transition-all",
                  active
                    ? "border-sco-blue bg-sco-blue/10 ring-1 ring-sco-blue"
                    : "border-sco-border hover:border-sco-blue/60",
                )}
              >
                <div className="flex items-center gap-2">
                  <Icon
                    size={16}
                    className={cn(
                      active ? "text-sco-blue" : "text-sco-muted-foreground",
                    )}
                  />
                  <span className="text-sm font-medium">{opt.label}</span>
                </div>
                <p className="text-xs text-sco-muted-foreground">{opt.desc}</p>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Sezione Team — solo se mode === "team" */}
      {mode === "team" && (
        <>
          {/* Nome team + tuo ruolo */}
          <Card icon={Users} title="Configurazione team">
            <div className="space-y-4">
              <Field label="Nome team">
                <input
                  type="text"
                  value={teamNome}
                  onChange={(e) => setTeamNome(e.target.value)}
                  placeholder="Es. SCO Solution Consulting"
                  className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
                />
              </Field>
              <Field label="Il tuo ruolo nel team">
                <input
                  type="text"
                  value={mioRuolo}
                  onChange={(e) => setMioRuolo(e.target.value)}
                  placeholder="Es. Lead Auditor, Senior Consultant"
                  className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
                />
              </Field>
            </div>
          </Card>

          {/* Membri */}
          <Card icon={UserPlus} title="Membri del team">
            <p className="mb-4 text-xs text-sco-muted-foreground">
              Aggiungi i colleghi con cui condividi questo agente. La sync
              cross-device dei membri sara` disponibile nella v0.9.x — oggi i
              membri vivono solo su questa macchina.
            </p>

            {/* Lista membri */}
            {membri.length > 0 && (
              <ul className="mb-4 space-y-2">
                {membri.map((m) => (
                  <li
                    key={m.id}
                    className="flex items-center justify-between rounded-lg border border-sco-border bg-sco-bg p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{m.nome}</p>
                      <p className="text-xs text-sco-muted-foreground">
                        {m.ruolo}
                        {m.email && ` · ${m.email}`}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeMembro(m.id)}
                      className="rounded-md p-1.5 text-sco-muted-foreground hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
                      aria-label="Rimuovi membro"
                    >
                      <Trash2 size={14} />
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {/* Form add membro */}
            <div className="space-y-3 rounded-lg border border-dashed border-sco-border p-4">
              <p className="text-xs font-medium text-sco-muted-foreground">
                Aggiungi nuovo membro
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <input
                  type="text"
                  value={newMemberNome}
                  onChange={(e) => setNewMemberNome(e.target.value)}
                  placeholder="Nome (obbligatorio)"
                  className="rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
                />
                <input
                  type="text"
                  value={newMemberRuolo}
                  onChange={(e) => setNewMemberRuolo(e.target.value)}
                  placeholder="Ruolo (es. RSPP)"
                  className="rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
                />
                <input
                  type="email"
                  value={newMemberEmail}
                  onChange={(e) => setNewMemberEmail(e.target.value)}
                  placeholder="Email (opzionale)"
                  className="rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none sm:col-span-2"
                />
              </div>
              <button
                type="button"
                onClick={handleAddMembro}
                disabled={!newMemberNome.trim()}
                className="inline-flex items-center gap-1.5 rounded-md bg-sco-blue px-3 py-1.5 text-xs font-medium text-white shadow-sm transition-colors hover:bg-sco-navy disabled:cursor-not-allowed disabled:opacity-50"
              >
                <UserPlus size={12} />
                Aggiungi membro
              </button>
            </div>
          </Card>
        </>
      )}

      {mode === "solo" && (
        <div className="rounded-lg border border-dashed border-sco-border bg-sco-bg p-6 text-center text-xs text-sco-muted-foreground">
          Modalita` Solo attiva. Passa a Team per configurare membri e ruoli
          condivisi.
        </div>
      )}
    </div>
  );
}

interface CardProps {
  icon: typeof Users;
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
