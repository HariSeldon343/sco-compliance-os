// SCO Compliance OS — input bottom polished: textarea arrotondata + attachments + mode dropdown
// Mode dropdown ora persistito nello store chatMode (Conv. 47 single source of truth).
// Le descrizioni sono in linguaggio semplice (regola 14/05).
import { useRef, useState, type KeyboardEvent, type ChangeEvent } from "react";
import {
  Send,
  Paperclip,
  Slash,
  ChevronDown,
  Check,
  ListChecks,
  HelpCircle,
  Rocket,
} from "lucide-react";
import { toast } from "sonner";

import { useChatStore, useChatModeStore, type ChatMode } from "@/store/chat-store";
import { cn } from "@/lib/cn";
import { MicButton } from "@/components/voice/MicButton";

const MAX_CHARS = 8000;

interface ModeConfig {
  value: ChatMode;
  label: string;
  shortLabel: string;
  description: string;
  icon: typeof ListChecks;
}

// Tre modalita di interazione con l'agente. Linguaggio semplice 14/05.
// Backend non cabla ancora `permission_mode` (carry-over v0.2.0): per ora
// la scelta vive lato frontend come preferenza utente persistita.
const MODES: ModeConfig[] = [
  {
    value: "plan",
    label: "Pianifica prima",
    shortLabel: "Pianifica",
    description: "Prima ti mostra il piano. Poi parte solo se sei d'accordo.",
    icon: ListChecks,
  },
  {
    value: "ask",
    label: "Chiedi conferma a ogni passo",
    shortLabel: "Chiedi",
    description: "Si ferma e ti chiede prima di fare cose importanti.",
    icon: HelpCircle,
  },
  {
    value: "auto",
    label: "Procedi in autonomia",
    shortLabel: "Autonomo",
    description:
      "Va dritto fino al risultato finale. Default consigliato.",
    icon: Rocket,
  },
];

export function ChatInput() {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [value, setValue] = useState("");
  const [modeOpen, setModeOpen] = useState(false);
  const mode = useChatModeStore((s) => s.mode);
  const setMode = useChatModeStore((s) => s.setMode);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const sendMessage = useChatStore((s) => s.sendMessage);

  const charCount = value.length;
  const overLimit = charCount > MAX_CHARS;
  const canSend = value.trim().length > 0 && !isStreaming && !overLimit;

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    // Auto-grow textarea
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const handleSend = async () => {
    const text = value.trim();
    if (!text || isStreaming || overLimit) return;
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    await sendMessage(text);
  };

  const handleAttach = () => {
    // TODO: integrare @tauri-apps/plugin-dialog `open({ multiple: true })`
    // per ora stub con toast
    toast.info("Allegato file: in arrivo (Tauri dialog stub)");
  };

  const handleSlashCommand = () => {
    toast.info("Slash commands: in arrivo (skill registry stub)");
  };

  // Callback STT: appende il testo trascritto al contenuto corrente del textarea.
  // Pattern: se input vuoto, sostituisce; se gia' contenuto, appende con spazio.
  const handleTranscript = (text: string) => {
    setValue((cur) => {
      const trimmed = cur.trim();
      const next = trimmed ? `${cur}${cur.endsWith(" ") ? "" : " "}${text}` : text;
      // Auto-grow textarea dopo l'append
      requestAnimationFrame(() => {
        const el = textareaRef.current;
        if (el) {
          el.style.height = "auto";
          el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
          el.focus();
          el.setSelectionRange(next.length, next.length);
        }
      });
      return next;
    });
  };

  const currentMode = MODES.find((m) => m.value === mode) ?? MODES[2];
  const CurrentModeIcon = currentMode.icon;

  return (
    <div className="shrink-0 bg-sco-bg px-6 pb-4 pt-2">
      <div className="mx-auto max-w-chat">
        {/* Composer container arrotondato 2xl con focus ring blu */}
        <div
          className={cn(
            "flex flex-col overflow-hidden rounded-2xl border bg-sco-surface-elevated shadow-sm transition-all duration-150 focus-within:border-sco-blue focus-within:shadow-md focus-within:ring-2 focus-within:ring-sco-blue/20",
            overLimit ? "border-red-500" : "border-sco-border",
          )}
        >
          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Scrivi un messaggio..."
            rows={1}
            className="resize-none border-0 bg-transparent px-4 pt-3.5 pb-2 text-sm leading-relaxed text-sco-text placeholder:text-sco-muted-foreground/70 focus:outline-none dark:text-sco-text-dark"
            disabled={isStreaming}
          />

          {/* Toolbar inferiore */}
          <div className="flex items-center justify-between px-2.5 py-2">
            <div className="flex items-center gap-0.5">
              {/* Attach */}
              <button
                type="button"
                onClick={handleAttach}
                className="rounded-md p-1.5 text-sco-muted-foreground transition-colors hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
                title="Allega file"
                aria-label="Allega file"
              >
                <Paperclip size={16} />
              </button>
              {/* Slash command */}
              <button
                type="button"
                onClick={handleSlashCommand}
                className="rounded-md p-1.5 text-sco-muted-foreground transition-colors hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
                title="Slash commands"
                aria-label="Slash commands"
              >
                <Slash size={16} />
              </button>

              {/* Separator */}
              <span className="mx-1 h-5 w-px bg-sco-border" aria-hidden="true" />

              {/* Mode selector */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setModeOpen(!modeOpen)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium transition-colors",
                    modeOpen
                      ? "bg-sco-muted text-sco-text dark:text-sco-text-dark"
                      : "text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark",
                  )}
                  title={currentMode.description}
                  aria-haspopup="listbox"
                  aria-expanded={modeOpen}
                >
                  <CurrentModeIcon size={13} />
                  <span>{currentMode.shortLabel}</span>
                  <ChevronDown
                    size={12}
                    className={cn(
                      "transition-transform",
                      modeOpen && "rotate-180",
                    )}
                  />
                </button>

                {modeOpen && (
                  <>
                    {/* Backdrop click-out */}
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setModeOpen(false)}
                    />
                    <div
                      role="listbox"
                      aria-label="Modalita interazione agente"
                      className="absolute bottom-full left-0 z-50 mb-1.5 w-80 max-h-96 overflow-y-auto rounded-lg border border-sco-border bg-sco-surface-elevated p-1 shadow-xl"
                    >
                      <div className="border-b border-sco-border px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-sco-muted-foreground">
                        Come deve comportarsi l'agente
                      </div>
                      {MODES.map((m) => {
                        const ModeIcon = m.icon;
                        const selected = mode === m.value;
                        return (
                          <button
                            key={m.value}
                            type="button"
                            role="option"
                            aria-selected={selected}
                            onClick={() => {
                              setMode(m.value);
                              setModeOpen(false);
                            }}
                            className={cn(
                              "flex w-full items-start gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors",
                              selected
                                ? "bg-sco-blue/10"
                                : "hover:bg-sco-muted",
                            )}
                          >
                            <ModeIcon
                              size={14}
                              className={cn(
                                "mt-0.5 shrink-0",
                                selected
                                  ? "text-sco-blue"
                                  : "text-sco-muted-foreground",
                              )}
                            />
                            <div className="flex-1">
                              <div className="flex items-center gap-1.5">
                                <div
                                  className={cn(
                                    "text-xs font-semibold",
                                    selected
                                      ? "text-sco-blue"
                                      : "text-sco-text dark:text-sco-text-dark",
                                  )}
                                >
                                  {m.label}
                                </div>
                                {selected && (
                                  <Check
                                    size={12}
                                    className="text-sco-blue"
                                    aria-label="selezionato"
                                  />
                                )}
                              </div>
                              <div className="mt-0.5 text-[11px] leading-snug text-sco-muted-foreground">
                                {m.description}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "text-[11px] tabular-nums",
                  overLimit
                    ? "font-semibold text-red-500"
                    : "text-sco-muted-foreground",
                )}
                aria-live="polite"
              >
                {charCount}/{MAX_CHARS}
              </span>
              {/* Microfono push-to-talk (visibile solo se sttEnabled in Settings).
                  Hotkey globale Ctrl+Shift+Space gestito internamente. */}
              <MicButton
                onTranscript={handleTranscript}
                disabled={isStreaming}
              />
              <button
                type="button"
                onClick={handleSend}
                disabled={!canSend}
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-lg transition-all duration-150",
                  canSend
                    ? "bg-sco-blue text-white shadow-sm hover:bg-sco-navy hover:shadow"
                    : "cursor-not-allowed bg-sco-muted text-sco-muted-foreground",
                )}
                title="Invia (Invio)"
                aria-label="Invia messaggio"
              >
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>

        {/* Privacy footer */}
        <p className="mt-2 text-center text-[11px] text-sco-muted-foreground">
          <span className="italic">Privato. Tuo. Italiano.</span> — Nessun dato
          lascia il tuo dispositivo senza conferma.
        </p>
      </div>
    </div>
  );
}
