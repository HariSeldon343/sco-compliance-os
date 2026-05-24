// SCO Compliance OS — Settings Tab "Voce"
// v0.8.1: card STT (toggle + modello dropdown lingua + hotkey PTT) + card TTS
// (toggle + voce IT/EN preview + speed slider).
// Single source of truth: voice-store (persist locale).

import { useState } from "react";
import { Mic, Volume2 } from "lucide-react";

import {
  useVoiceStore,
  type SttLanguage,
  type PiperVoice,
} from "@/store/voice-store";
import { cn } from "@/lib/cn";

export function VoiceTab() {
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

  // Speed slider: UX placeholder, non cabla backend (piper non supporta speed
  // runtime; richiede re-rendering chunk-by-chunk).
  const [ttsSpeed, setTtsSpeed] = useState(1.0);

  return (
    <div className="space-y-6">
      {/* Card STT (microfono) */}
      <Card icon={Mic} title="Microfono (parla per scrivere)">
        <label className="mb-3 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={sttEnabled}
            onChange={(e) => setSttEnabled(e.target.checked)}
            className="h-4 w-4 accent-sco-blue"
          />
          Abilita STT (microfono nella chat)
        </label>
        <p className="mb-4 text-xs text-sco-muted-foreground">
          Mostra un bottone microfono nella chat. Tieni Ctrl+Shift+Space per
          parlare. La trascrizione avviene on-device via whisper.cpp, nessun
          audio viene caricato in cloud. Il modello (~140 MB base, ~430 MB
          medium) viene scaricato al primo utilizzo.
        </p>

        {sttEnabled && (
          <div className="space-y-4 border-t border-sco-border pt-4">
            <Field label="Lingua trascrizione">
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    { value: "it", label: "Italiano" },
                    { value: "en", label: "Inglese" },
                    { value: "auto", label: "Auto-detect" },
                  ] as Array<{ value: SttLanguage; label: string }>
                ).map((opt) => {
                  const active = sttLanguage === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setSttLanguage(opt.value)}
                      className={cn(
                        "rounded-md border px-3 py-1.5 text-xs transition-colors",
                        active
                          ? "border-sco-blue bg-sco-blue/10 text-sco-navy dark:text-sco-text-dark"
                          : "border-sco-border hover:border-sco-blue",
                      )}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </Field>

            <Field label="Modello whisper">
              <select
                defaultValue="base"
                className="w-full max-w-sm rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
              >
                <option value="base">Base (~140 MB, veloce)</option>
                <option value="medium">Medium (~430 MB, piu` accurato)</option>
              </select>
              <p className="mt-1 text-xs text-sco-muted-foreground">
                Base e` sufficiente per dettature brevi. Medium consigliato per
                trascrizioni lunghe in italiano professionale.
              </p>
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
          </div>
        )}
      </Card>

      {/* Card TTS (lettura risposte) */}
      <Card icon={Volume2} title="Lettura risposte (TTS)">
        <label className="mb-3 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={ttsEnabled}
            onChange={(e) => setTtsEnabled(e.target.checked)}
            className="h-4 w-4 accent-sco-blue"
          />
          Abilita TTS (pulsante lettura su ogni risposta)
        </label>
        <p className="mb-4 text-xs text-sco-muted-foreground">
          Mostra un pulsante "leggi ad alta voce" sotto le risposte
          dell'agente. La sintesi avviene on-device via piper, nessun testo
          lascia il computer. Le voci (~60-120 MB ciascuna) vengono scaricate
          al primo utilizzo.
        </p>

        {ttsEnabled && (
          <div className="space-y-4 border-t border-sco-border pt-4">
            <Field label="Voce italiana">
              <select
                value={ttsVoiceIt}
                onChange={(e) => setTtsVoiceIt(e.target.value as PiperVoice)}
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
                onChange={(e) => setTtsVoiceEn(e.target.value as PiperVoice)}
                className="w-full max-w-sm rounded-md border border-sco-border bg-sco-bg px-3 py-2 text-sm focus:border-sco-blue focus:outline-none"
              >
                <option value="en_US-libritts-high">
                  LibriTTS (high, ~120 MB)
                </option>
              </select>
            </Field>

            <Field label={`Velocita di lettura: ${ttsSpeed.toFixed(2)}x`}>
              <input
                type="range"
                min="0.5"
                max="2.0"
                step="0.05"
                value={ttsSpeed}
                onChange={(e) => setTtsSpeed(parseFloat(e.target.value))}
                className="w-full max-w-sm accent-sco-blue"
              />
              <div className="mt-1 flex max-w-sm justify-between text-[11px] text-sco-muted-foreground">
                <span>0.5x lenta</span>
                <span>1.0x normale</span>
                <span>2.0x veloce</span>
              </div>
            </Field>
          </div>
        )}
      </Card>
    </div>
  );
}

interface CardProps {
  icon: typeof Mic;
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
