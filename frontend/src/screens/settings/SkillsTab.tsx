// SCO Compliance OS — Settings Tab "Skills"
// v0.8.1: link a /skills screen builder (gestione skill custom + wizard).
// Tab leggero: redirect informativo, niente logica duplicata.

import { Link } from "react-router-dom";
import { Sparkles, ExternalLink, Wand2, BookOpen } from "lucide-react";

export function SkillsTab() {
  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-sco-border bg-sco-surface-elevated p-6">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles size={18} className="text-sco-blue" />
          <h2 className="text-base font-semibold">Skill custom</h2>
        </div>
        <p className="mb-4 text-sm text-sco-muted-foreground">
          Le skill sono moduli specializzati che insegnano all'agente
          competenze verticali (es. "Auditor ISO 27001", "Redattore perizie
          CTU", "Tutor accreditamento sanitario"). Puoi creare nuove skill,
          modificare quelle esistenti o importarle dal catalogo.
        </p>

        <div className="grid gap-3 sm:grid-cols-2">
          <Link
            to="/skills"
            className="group flex items-start gap-3 rounded-lg border border-sco-border bg-sco-bg p-4 transition-all hover:border-sco-blue/60 hover:bg-sco-blue/5"
          >
            <div className="rounded-md bg-sco-blue/10 p-2">
              <BookOpen size={16} className="text-sco-blue" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">Gestisci skill</p>
              <p className="mt-0.5 text-xs text-sco-muted-foreground">
                Vedi la lista delle skill attive, abilita/disabilita, modifica.
              </p>
              <span className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-sco-blue group-hover:underline">
                Apri catalogo
                <ExternalLink size={12} />
              </span>
            </div>
          </Link>

          <Link
            to="/skills"
            className="group flex items-start gap-3 rounded-lg border border-sco-border bg-sco-bg p-4 transition-all hover:border-sco-blue/60 hover:bg-sco-blue/5"
          >
            <div className="rounded-md bg-sco-amber/10 p-2">
              <Wand2 size={16} className="text-sco-amber" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">Crea nuova skill</p>
              <p className="mt-0.5 text-xs text-sco-muted-foreground">
                Wizard guidato per costruire skill verticali ad alto valore.
              </p>
              <span className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-sco-amber group-hover:underline">
                Apri wizard
                <ExternalLink size={12} />
              </span>
            </div>
          </Link>
        </div>
      </section>
    </div>
  );
}
