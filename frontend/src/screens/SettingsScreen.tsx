// SCO Compliance OS — schermata Impostazioni (API keys, modelli, aspetto, privacy)
// Stub: form base, validazione e persistenza arriveranno in iterazioni successive.

import { Key, Cpu, Palette, ShieldCheck } from "lucide-react";

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
            Configura API key, modelli LLM, aspetto e privacy.
          </p>
        </header>

        {/* API Keys */}
        <Section icon={Key} title="API Keys">
          <Field label="Anthropic API Key">
            <input
              type="password"
              placeholder="____________________"
              className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
            />
            <p className="mt-1 text-xs text-sco-muted-foreground">
              Conservata in keyring di sistema (Windows Credential Manager).
            </p>
          </Field>
          <Field label="OpenAI API Key (opzionale)">
            <input
              type="password"
              placeholder="____________________"
              className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
            />
          </Field>
        </Section>

        {/* Modelli LLM */}
        <Section icon={Cpu} title="Modelli LLM">
          <Field label="Modello primario">
            <select className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none">
              <option>claude-opus-4-7-1m</option>
              <option>claude-sonnet-4-7</option>
              <option>claude-haiku-4-7</option>
              <option>gpt-5</option>
            </select>
          </Field>
          <Field label="Modello fallback">
            <select className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none">
              <option>claude-haiku-4-7</option>
            </select>
          </Field>
        </Section>

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
            SCO Compliance OS opera localmente. Nessun dato lascia il
            dispositivo senza conferma esplicita. Le chiamate ai modelli LLM
            esterni sono opt-in per messaggio.
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
  icon: typeof Key;
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
