// SCO Compliance OS — schermata Impostazioni (aspetto, privacy)
// Pattern Conv. 47 single source of truth: il modello LLM e l'API key Anthropic
// vivono lato server SCO per tenant. L'app desktop NON deve far scegliere il modello
// al cliente — è gestito centralmente da SCO Solution Consulting via license + proxy.

import { Palette, ShieldCheck, ServerCog } from "lucide-react";

import { useThemeStore, type Theme } from "@/store/theme-store";
import { cn } from "@/lib/cn";

export function SettingsScreen() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  return (
    <div className="h-full overflow-y-auto px-8 py-6">
      <div className="mx-auto max-w-3xl space-y-8">
        <header>
          <h1 className="text-2xl font-semibold text-sco-navy dark:text-sco-text-dark">
            Impostazioni
          </h1>
          <p className="mt-1 text-sm text-sco-muted-foreground">
            Aspetto, privacy e informazioni sul modello AI gestito da SCO.
          </p>
        </header>

        {/* Modello AI gestito da SCO (disclaimer, no scelta cliente) */}
        <section className="rounded-lg border border-sco-border bg-sco-surface-elevated p-6">
          <div className="mb-3 flex items-center gap-2">
            <ServerCog size={18} className="text-sco-blue" />
            <h2 className="text-base font-semibold">
              Modello AI gestito da SCO Solution Consulting
            </h2>
          </div>
          <div className="space-y-3 text-sm text-sco-muted-foreground">
            <p>
              Il modello linguistico attivo per il tuo tenant è configurato e
              mantenuto centralmente da SCO. Non è modificabile dall'app per
              garantire stabilità, sicurezza e conformità contrattuale.
            </p>
            <p>
              Per modifiche o richieste, contatta{" "}
              <a
                href="mailto:info@scosolution.it"
                className="font-medium text-sco-blue hover:underline"
              >
                info@scosolution.it
              </a>
              .
            </p>
          </div>
        </section>

        {/* Aspetto */}
        <Section icon={Palette} title="Aspetto">
          <Field label="Tema">
            <div className="flex gap-2">
              {(["light", "dark", "system"] as Theme[]).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTheme(t)}
                  className={cn(
                    "rounded-md border px-4 py-2 text-sm capitalize",
                    theme === t
                      ? "border-sco-blue bg-sco-blue/10 text-sco-navy"
                      : "border-sco-border hover:border-sco-blue",
                  )}
                >
                  {t === "light"
                    ? "Chiaro"
                    : t === "dark"
                      ? "Scuro"
                      : "Sistema"}
                </button>
              ))}
            </div>
          </Field>
        </Section>

        {/* Privacy */}
        <Section icon={ShieldCheck} title="Privacy">
          <p className="text-sm text-sco-muted-foreground">
            SCO Compliance OS opera localmente sul tuo dispositivo. Nessun dato
            personale lascia il computer senza conferma esplicita. Le chiamate
            al modello AI passano attraverso un proxy gestito da SCO Solution
            Consulting (architettura licenza + proxy), che valida la tua
            licenza e inoltra le richieste al fornitore del modello.
          </p>
          <label className="mt-3 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              defaultChecked
              className="h-4 w-4 accent-sco-blue"
            />
            Telemetria anonima per migliorare l'app
          </label>
        </Section>
      </div>
    </div>
  );
}

interface SectionProps {
  icon: typeof Palette;
  title: string;
  children: React.ReactNode;
}
function Section({ icon: Icon, title, children }: SectionProps) {
  return (
    <section className="rounded-lg border border-sco-border bg-sco-surface-elevated p-6">
      <div className="mb-4 flex items-center gap-2">
        <Icon size={18} className="text-sco-blue" />
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      <div className="space-y-4">{children}</div>
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
      <label className="mb-1 block text-sm font-medium">{label}</label>
      {children}
    </div>
  );
}
