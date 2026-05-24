// SCO Compliance OS — schermata Impostazioni (aspetto, layout, privacy)
// Pattern Conv. 47 single source of truth: il modello LLM e l'API key Anthropic
// vivono lato server SCO per tenant. L'app desktop NON deve far scegliere il modello
// al cliente — è gestito centralmente da SCO Solution Consulting via license + proxy.

import {
  Palette,
  ShieldCheck,
  ServerCog,
  LayoutPanelLeft,
  Navigation,
  Smile,
  Mic as MicIcon,
} from "lucide-react";

import { useThemeStore, type Theme } from "@/store/theme-store";
import { useLayoutStore, type LayoutMode } from "@/store/layout-store";
import {
  useMascotStore,
  type MascotVariant,
} from "@/store/mascot-store";
import {
  useVoiceStore,
  type SttLanguage,
  type PiperVoice,
} from "@/store/voice-store";
import { MascotCharacter } from "@/components/mascot/MascotCharacter";
import { cn } from "@/lib/cn";

export function SettingsScreen() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const layoutMode = useLayoutStore((s) => s.mode);
  const setLayoutMode = useLayoutStore((s) => s.setMode);
  const mascotEnabled = useMascotStore((s) => s.enabled);
  const mascotVariant = useMascotStore((s) => s.variant);
  const setMascotEnabled = useMascotStore((s) => s.setEnabled);
  const setMascotVariant = useMascotStore((s) => s.setVariant);
  // Voice (STT + TTS on-device)
  const sttEnabled = useVoiceStore((s) => s.sttEnabled);
  const ttsEnabled = useVoiceStore((s) => s.ttsEnabled);
  const sttLanguage = useVoiceStore((s) => s.sttLanguage);
  const ttsVoiceIt = useVoiceStore((s) => s.ttsVoiceIt);
  const ttsVoiceEn = useVoiceStore((s) => s.ttsVoiceEn);
  const hotkeyEnabled = useVoiceStore((s) => s.hotkeyEnabled);
  const setSttEnabled = useVoiceStore((s) => s.setSttEnabled);
  const setTtsEnabled = useVoiceStore((s) => s.setTtsEnabled);
  const setSttLanguage = useVoiceStore((s) => s.setSttLanguage);
  const setTtsVoiceIt = useVoiceStore((s) => s.setTtsVoiceIt);
  const setTtsVoiceEn = useVoiceStore((s) => s.setTtsVoiceEn);
  const setHotkeyEnabled = useVoiceStore((s) => s.setHotkeyEnabled);

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

          {/* Mascot sub-section: opt-in 2D SVG floating overlay */}
          <div className="border-t border-sco-border pt-4">
            <div className="mb-3 flex items-center gap-2">
              <Smile size={16} className="text-sco-blue" />
              <h3 className="text-sm font-semibold">Mascot</h3>
            </div>
            <Field label="Mostra il mascot in alto a destra">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={mascotEnabled}
                  onChange={(e) => setMascotEnabled(e.target.checked)}
                  className="h-4 w-4 accent-sco-blue"
                />
                Abilita mascot animato (opt-in, default disattivato)
              </label>
              <p className="mt-1 text-xs text-sco-muted-foreground">
                Il mascot è una piccola illustrazione che reagisce a quello che
                fa l'agente: si muove durante il pensiero, sorride in ascolto,
                "parla" quando legge la risposta. Decorativo. Puoi spegnerlo
                quando vuoi.
              </p>
            </Field>
            {mascotEnabled && (
              <Field label="Variante palette">
                <div className="grid gap-3 sm:grid-cols-3">
                  {(
                    [
                      {
                        value: "blue",
                        label: "SCO blu",
                        desc: "Antenna blu, palette brand core.",
                      },
                      {
                        value: "amber",
                        label: "SCO ambra",
                        desc: "Antenna ambra, accent caldo.",
                      },
                      {
                        value: "minimal",
                        label: "Minimal",
                        desc: "Antenna bianca, look sobrio.",
                      },
                    ] as Array<{
                      value: MascotVariant;
                      label: string;
                      desc: string;
                    }>
                  ).map((opt) => {
                    const active = mascotVariant === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setMascotVariant(opt.value)}
                        className={cn(
                          "flex flex-col items-center gap-2 rounded-lg border p-3 text-center transition-all",
                          active
                            ? "border-sco-blue bg-sco-blue/10 ring-1 ring-sco-blue"
                            : "border-sco-border hover:border-sco-blue/60",
                        )}
                      >
                        <MascotCharacter
                          state="idle"
                          variant={opt.value}
                          size={64}
                        />
                        <span className="text-xs font-medium">{opt.label}</span>
                        <span className="text-[11px] text-sco-muted-foreground">
                          {opt.desc}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </Field>
            )}
          </div>

          {/* Voce: STT (mic) + TTS (lettura risposte) on-device */}
          <div className="border-t border-sco-border pt-4">
            <div className="mb-3 flex items-center gap-2">
              <MicIcon size={16} className="text-sco-blue" />
              <h3 className="text-sm font-semibold">Voce</h3>
            </div>
            <Field label="Microfono (parla per scrivere)">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={sttEnabled}
                  onChange={(e) => setSttEnabled(e.target.checked)}
                  className="h-4 w-4 accent-sco-blue"
                />
                Abilita STT (microfono nella chat)
              </label>
              <p className="mt-1 text-xs text-sco-muted-foreground">
                Mostra un bottone microfono nella chat. Tieni Ctrl+Shift+Space
                per parlare. La trascrizione avviene on-device via whisper.cpp,
                nessun audio viene caricato in cloud. Il modello (~140 MB) viene
                scaricato al primo utilizzo.
              </p>
            </Field>
            {sttEnabled && (
              <>
                <Field label="Lingua trascrizione">
                  <div className="flex gap-2">
                    {(
                      [
                        { value: "it", label: "Italiano" },
                        { value: "en", label: "Inglese" },
                        { value: "auto", label: "Auto" },
                      ] as Array<{ value: SttLanguage; label: string }>
                    ).map((opt) => {
                      const active = sttLanguage === opt.value;
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() => setSttLanguage(opt.value)}
                          className={cn(
                            "rounded-md border px-3 py-1.5 text-xs",
                            active
                              ? "border-sco-blue bg-sco-blue/10 text-sco-navy"
                              : "border-sco-border hover:border-sco-blue",
                          )}
                        >
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                </Field>
                <Field label="Hotkey push-to-talk">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={hotkeyEnabled}
                      onChange={(e) => setHotkeyEnabled(e.target.checked)}
                      className="h-4 w-4 accent-sco-blue"
                    />
                    Ctrl+Shift+Space attiva/disattiva la registrazione
                  </label>
                </Field>
              </>
            )}

            <Field label="Lettura risposte (TTS)">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={ttsEnabled}
                  onChange={(e) => setTtsEnabled(e.target.checked)}
                  className="h-4 w-4 accent-sco-blue"
                />
                Abilita TTS (pulsante lettura su ogni risposta)
              </label>
              <p className="mt-1 text-xs text-sco-muted-foreground">
                Mostra un pulsante "leggi ad alta voce" sotto le risposte
                dell'agente. La sintesi avviene on-device via piper, nessun
                testo lascia il computer. Le voci (~60-120 MB ciascuna) vengono
                scaricate al primo utilizzo.
              </p>
            </Field>
            {ttsEnabled && (
              <>
                <Field label="Voce italiana">
                  <select
                    value={ttsVoiceIt}
                    onChange={(e) =>
                      setTtsVoiceIt(e.target.value as PiperVoice)
                    }
                    className="w-full max-w-sm rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
                  >
                    <option value="it_IT-paola-medium">
                      Paola (medium, ~60 MB)
                    </option>
                  </select>
                </Field>
                <Field label="Voce inglese">
                  <select
                    value={ttsVoiceEn}
                    onChange={(e) =>
                      setTtsVoiceEn(e.target.value as PiperVoice)
                    }
                    className="w-full max-w-sm rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
                  >
                    <option value="en_US-libritts-high">
                      LibriTTS (high, ~120 MB)
                    </option>
                  </select>
                </Field>
              </>
            )}
          </div>
        </Section>

        {/* Layout di navigazione */}
        <Section icon={Navigation} title="Layout di navigazione">
          <Field label="Modalità">
            <div className="grid gap-3 sm:grid-cols-2">
              {(
                [
                  {
                    value: "sidebar",
                    label: "Sidebar laterale",
                    desc: "Pannello sinistro 280px con conversazioni e navigazione.",
                    icon: LayoutPanelLeft,
                  },
                  {
                    value: "bottom-tab",
                    label: "Barra inferiore",
                    desc: "Pill flottante in basso, più spazio per la chat.",
                    icon: Navigation,
                  },
                ] as Array<{
                  value: LayoutMode;
                  label: string;
                  desc: string;
                  icon: typeof LayoutPanelLeft;
                }>
              ).map((opt) => {
                const Icon = opt.icon;
                const active = layoutMode === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setLayoutMode(opt.value)}
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
                    <p className="text-xs text-sco-muted-foreground">
                      {opt.desc}
                    </p>
                  </button>
                );
              })}
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
