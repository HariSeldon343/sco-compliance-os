// SCO Compliance OS — Settings Tab "Profilo"
// v0.8.1: card "Chi sei" (nome / email / ruolo / ambito) + card "Team" (se modalita`
// team) + bottone "Modifica profilo" (TODO: trigger riapertura os-setup wizard).
// Single source of truth: license-store per email/tenant, profile-store per
// nome/ruolo/ambito, team-store per modalita` team.

import { User, Users, Edit3 } from "lucide-react";

import { useLicenseStore } from "@/store/license-store";
import { useProfileStore } from "@/store/profile-store";
import { useTeamStore } from "@/store/team-store";

export function ProfileTab() {
  const email = useLicenseStore((s) => s.email);
  const plan = useLicenseStore((s) => s.plan);

  const nome = useProfileStore((s) => s.nome);
  const ruolo = useProfileStore((s) => s.ruolo);
  const ambito = useProfileStore((s) => s.ambito);
  const setNome = useProfileStore((s) => s.setNome);
  const setRuolo = useProfileStore((s) => s.setRuolo);
  const setAmbito = useProfileStore((s) => s.setAmbito);

  const teamMode = useTeamStore((s) => s.mode);
  const teamNome = useTeamStore((s) => s.teamNome);
  const membri = useTeamStore((s) => s.membri);
  const mioRuolo = useTeamStore((s) => s.mioRuolo);

  return (
    <div className="space-y-6">
      {/* Card "Chi sei" */}
      <section className="rounded-xl border border-sco-border bg-sco-surface-elevated p-6">
        <div className="mb-4 flex items-center gap-2">
          <User size={18} className="text-sco-blue" />
          <h2 className="text-base font-semibold">Chi sei</h2>
        </div>
        <p className="mb-4 text-xs text-sco-muted-foreground">
          Le informazioni del tuo profilo professionale. Vengono usate per
          personalizzare le risposte dell'agente e le firme dei deliverable.
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Nome">
            <input
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Es. Antonio Amodeo"
              className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
            />
          </Field>
          <Field label="Email (licenza)">
            <input
              type="email"
              value={email || "—"}
              readOnly
              className="w-full rounded-md border border-sco-border bg-sco-muted px-3 py-2 text-sm text-sco-muted-foreground"
            />
          </Field>
          <Field label="Ruolo professionale">
            <input
              type="text"
              value={ruolo}
              onChange={(e) => setRuolo(e.target.value)}
              placeholder="Es. Consulente Senior NIS 2"
              className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
            />
          </Field>
          <Field label="Ambito di competenza">
            <input
              type="text"
              value={ambito}
              onChange={(e) => setAmbito(e.target.value)}
              placeholder="Es. Cybersecurity, ISO 27001, Sanita`"
              className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
            />
          </Field>
        </div>
        <div className="mt-4 flex items-center gap-3 text-xs text-sco-muted-foreground">
          <span className="rounded-md border border-sco-border bg-sco-bg px-2 py-1 font-mono">
            Plan: {plan || "—"}
          </span>
        </div>
      </section>

      {/* Card "Team" (solo se modalita` team) */}
      {teamMode === "team" && (
        <section className="rounded-xl border border-sco-border bg-sco-surface-elevated p-6">
          <div className="mb-4 flex items-center gap-2">
            <Users size={18} className="text-sco-blue" />
            <h2 className="text-base font-semibold">Team</h2>
          </div>
          <p className="mb-4 text-xs text-sco-muted-foreground">
            Membri del tuo team con cui condividi questo agente. Configura ruoli
            e membri nel tab "Team".
          </p>

          <div className="space-y-3">
            <div className="rounded-lg border border-sco-border bg-sco-bg p-3">
              <p className="text-xs uppercase tracking-wide text-sco-muted-foreground">
                Nome team
              </p>
              <p className="mt-0.5 text-sm font-medium">
                {teamNome || "Non impostato"}
              </p>
            </div>
            <div className="rounded-lg border border-sco-border bg-sco-bg p-3">
              <p className="text-xs uppercase tracking-wide text-sco-muted-foreground">
                Il tuo ruolo nel team
              </p>
              <p className="mt-0.5 text-sm font-medium">
                {mioRuolo || "Non impostato"}
              </p>
            </div>
            <div className="rounded-lg border border-sco-border bg-sco-bg p-3">
              <p className="text-xs uppercase tracking-wide text-sco-muted-foreground">
                Membri visibili
              </p>
              <p className="mt-0.5 text-sm font-medium">
                {membri.length === 0
                  ? "Nessun membro aggiunto"
                  : `${membri.length} membr${membri.length === 1 ? "o" : "i"}`}
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Bottone "Modifica profilo" → riapertura wizard os-setup */}
      <section className="rounded-xl border border-sco-border bg-sco-surface-elevated p-6">
        <p className="mb-3 text-sm text-sco-muted-foreground">
          Vuoi rifare l'onboarding guidato per riconfigurare profilo, vault e
          integrazioni da zero?
        </p>
        <button
          type="button"
          onClick={() => {
            // TODO v0.8.2: trigger AuthGate phase reset → wizard os-setup riapre.
            // Placeholder: log + toast per non bloccare la build.
            // Vedi components/AuthGate.tsx per FSM cumulativa 7 fasi.
            // Pattern Conv. 41 tracciatura: pulsante UX, non azione distruttiva.
            void (async () => {
              const { toast } = await import("sonner");
              toast.info(
                "Modifica profilo: wizard di riapertura in arrivo nella v0.8.2",
                { duration: 4000 },
              );
            })();
          }}
          className="inline-flex items-center gap-2 rounded-md border border-sco-border bg-sco-bg px-4 py-2 text-sm font-medium transition-colors hover:border-sco-blue hover:bg-sco-blue/10"
        >
          <Edit3 size={14} />
          Modifica profilo
        </button>
      </section>
    </div>
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
