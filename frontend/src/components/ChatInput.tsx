// SCO Compliance OS — input bottom polished: textarea arrotondata + attachments + mode dropdown
// Mode dropdown ora persistito nello store chatMode (Conv. 47 single source of truth).
// Le descrizioni sono in linguaggio semplice (regola 14/05).
// v0.13.0 PSI: send button con shine ripple effect + Framer Motion whileTap microinteraction.
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from "react";
import { motion } from "framer-motion";
import {
  Send,
  Paperclip,
  Slash,
  ChevronDown,
  Check,
  ListChecks,
  HelpCircle,
  Rocket,
  ShieldOff,
} from "lucide-react";
import { toast } from "sonner";

import { useChatStore, useChatModeStore } from "@/store/chat-store";
import type { ChatMode } from "@/types/api";
import { cn } from "@/lib/cn";
import { MicButton } from "@/components/voice/MicButton";
import { SecurityWarningModal } from "@/components/SecurityWarningModal";
import { apiClient } from "@/api/client";
import { SlashCommandsPopover, type SlashCommandsPopoverHandle } from "@/components/SlashCommandsPopover";
import type { SkillSummary } from "@/types/api";


// v0.11.0: rimosso hard cap 8000 char. Anthropic API supporta fino a ~200k
// token input + il prompt caching nel proxy SaaS ammortizza messaggi lunghi.
// Mantengo MAX_CHARS solo come WARN soft (display contatore in rosso oltre).
const MAX_CHARS = Number.POSITIVE_INFINITY;
const SOFT_WARN_CHARS = 32000;

interface ModeConfig {
  value: ChatMode;
  label: string;
  shortLabel: string;
  description: string;
  icon: typeof ListChecks;
}

// Tre modalita di interazione con l'agente. Linguaggio semplice 14/05.
// Backend v0.14.0 persiste agent_mode per conversation e propaga
// permission_mode verso l'LLM.
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
  {
    value: "yolo",
    label: "Senza autorizzazioni - tutti i permessi",
    shortLabel: "Libero",
    description: "L'agente fa tutto da solo, senza chiedere.",
    icon: ShieldOff,
  },
];

interface SlashTokenContext {
  start: number;
  query: string;
}

function findSlashToken(text: string, cursor: number): SlashTokenContext | null {
  if (cursor <= 0 || cursor > text.length) {
    return null;
  }

  const whitespace = /\s/;
  let index = cursor - 1;
  while (index >= 0) {
    const char = text[index];
    if (char === "/") {
      const prevChar = index > 0 ? text[index - 1] : "";
      if (index > 0 && !whitespace.test(prevChar)) {
        return null;
      }
      const query = text.slice(index + 1, cursor);
      if (whitespace.test(query)) {
        return null;
      }
      return { start: index, query };
    }
    if (whitespace.test(char)) {
      return null;
    }
    index -= 1;
  }

  return null;
}

export function ChatInput() {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [value, setValue] = useState("");
  const [modeOpen, setModeOpen] = useState(false);
  const [securityWarningOpen, setSecurityWarningOpen] = useState(false);
  const [pendingMode, setPendingMode] = useState<ChatMode | null>(null);
  const mode = useChatModeStore((s) => s.mode);
  const setMode = useChatModeStore((s) => s.setMode);
  const yoloAcknowledged = useChatModeStore((s) => s.yoloAcknowledged);
  const setYoloAcknowledged = useChatModeStore((s) => s.setYoloAcknowledged);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const setConversationMode = useChatStore((s) => s.setConversationMode);

  const slashPopoverRef = useRef<SlashCommandsPopoverHandle>(null);
  const [slashOpen, setSlashOpen] = useState(false);
  const [slashQuery, setSlashQuery] = useState("");
  const [slashTokenRange, setSlashTokenRange] = useState<{ start: number; end: number } | null>(null);
  const [slashSkills, setSlashSkills] = useState<SkillSummary[]>([]);
  const slashLoadedRef = useRef(false);
  const slashLoadErrorRef = useRef(false);

  const resizeTextarea = useCallback((el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
  }, []);

  const closeSlash = useCallback(() => {
    setSlashOpen(false);
    setSlashQuery("");
    setSlashTokenRange(null);
    slashPopoverRef.current?.resetSelection();
  }, []);

  const updateSlashContext = useCallback(
    (textValue: string, cursor: number) => {
      const context = findSlashToken(textValue, cursor);
      if (context) {
        setSlashTokenRange({ start: context.start, end: cursor });
        setSlashQuery(context.query);
        setSlashOpen(true);
      } else {
        if (slashOpen) {
          setSlashOpen(false);
        }
        setSlashTokenRange(null);
        setSlashQuery("");
        slashPopoverRef.current?.resetSelection();
      }
    },
    [slashOpen],
  );

  useEffect(() => {
    if (!slashOpen || slashLoadedRef.current) {
      return;
    }
    let cancelled = false;
    apiClient.skills
      .list()
      .then((skills) => {
        if (cancelled) return;
        setSlashSkills(skills);
        slashLoadedRef.current = true;
        if (!skills.length) {
          slashPopoverRef.current?.resetSelection();
        }
      })
      .catch((error) => {
        if (cancelled) return;
        if (!slashLoadErrorRef.current) {
          slashLoadErrorRef.current = true;
          toast.error("Impossibile caricare le skill disponibili.");
        }
        console.error("slash.commands.load_failed", error);
      });
    return () => {
      cancelled = true;
    };
  }, [slashOpen]);


  const charCount = value.length;
  const overLimit = charCount > MAX_CHARS;
  const canSend = value.trim().length > 0 && !isStreaming && !overLimit && !slashOpen;

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const nextValue = e.target.value;
    const cursor = e.target.selectionStart ?? nextValue.length;
    setValue(nextValue);
    const el = textareaRef.current;
    if (el) {
      resizeTextarea(el);
    }
    updateSlashContext(nextValue, cursor);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (slashOpen) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        slashPopoverRef.current?.highlightNext();
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        slashPopoverRef.current?.highlightPrevious();
        return;
      }
      if (e.key === "Tab") {
        e.preventDefault();
        if (e.shiftKey) {
          slashPopoverRef.current?.highlightPrevious();
        } else {
          const selected = slashPopoverRef.current?.selectCurrent();
          if (!selected) {
            closeSlash();
          }
        }
        return;
      }
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        const selected = slashPopoverRef.current?.selectCurrent();
        if (!selected) {
          closeSlash();
        }
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        closeSlash();
        return;
      }
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const handleSkillSelect = useCallback(
    (skill: SkillSummary) => {
      const insertion = `/${skill.name} `;
      setValue((current) => {
        const range = slashTokenRange ?? { start: current.length, end: current.length };
        const before = current.slice(0, range.start);
        const after = current.slice(range.end);
        const nextValue = `${before}${insertion}${after}`;
        requestAnimationFrame(() => {
          const el = textareaRef.current;
          if (!el) return;
          resizeTextarea(el);
          const caret = before.length + insertion.length;
          el.focus();
          el.setSelectionRange(caret, caret);
          updateSlashContext(nextValue, caret);
        });
        return nextValue;
      });
      closeSlash();
    },
    [closeSlash, resizeTextarea, slashTokenRange, updateSlashContext],
  );


  const handleConfirmSecurityWarning = useCallback(() => {
    if (pendingMode !== "yolo") {
      setSecurityWarningOpen(false);
      setPendingMode(null);
      return;
    }
    setYoloAcknowledged(true);
    setMode("yolo");
    if (activeConversationId) {
      setConversationMode(activeConversationId, "yolo");
    }
    setSecurityWarningOpen(false);
    setPendingMode(null);
    setModeOpen(false);
  }, [
    activeConversationId,
    pendingMode,
    setConversationMode,
    setMode,
    setModeOpen,
    setPendingMode,
    setSecurityWarningOpen,
    setYoloAcknowledged,
  ]);

  const handleCancelSecurityWarning = useCallback(() => {
    setSecurityWarningOpen(false);
    setPendingMode(null);
    setModeOpen(false);
  }, [setModeOpen, setPendingMode, setSecurityWarningOpen]);

  const handleSend = async () => {
    if (slashOpen) {
      return;
    }

    const textToSend = value.trim();
    if (!textToSend || isStreaming || overLimit) return;

    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    closeSlash();
    await sendMessage(textToSend);
  };



  const handleAttach = () => {
    // TODO: integrare @tauri-apps/plugin-dialog `open({ multiple: true })`
    // per ora stub con toast
    toast.info("Allegato file: in arrivo (Tauri dialog stub)");
  };

  const handleSlashCommand = () => {
    const el = textareaRef.current;
    const cursor = el?.selectionStart ?? value.length;
    setValue((current) => {
      const before = current.slice(0, cursor);
      const after = current.slice(cursor);
      const needsSpace = before.length > 0 && !/\s$/.test(before);
      const insertion = `${needsSpace ? " " : ""}/`;
      const nextValue = `${before}${insertion}${after}`;
      requestAnimationFrame(() => {
        const node = textareaRef.current;
        if (!node) return;
        resizeTextarea(node);
        const nextCursor = cursor + insertion.length;
        node.focus();
        node.setSelectionRange(nextCursor, nextCursor);
        updateSlashContext(nextValue, nextCursor);
      });
      return nextValue;
    });
  };

  // Callback STT: appende il testo trascritto al contenuto corrente del textarea.
  // Pattern: se input vuoto, sostituisce; se gia' contenuto, appende con spazio.
  const handleTranscript = (textChunk: string) => {
    setValue((current) => {
      const trimmed = current.trim();
      const needsSpace = trimmed.length > 0 && !current.endsWith(" ");
      const prefix = trimmed.length > 0 ? `${current}${needsSpace ? " " : ""}` : "";
      const nextValue = `${prefix}${textChunk}`;
      requestAnimationFrame(() => {
        const el = textareaRef.current;
        if (!el) return;
        resizeTextarea(el);
        el.focus();
        el.setSelectionRange(nextValue.length, nextValue.length);
        updateSlashContext(nextValue, nextValue.length);
      });
      return nextValue;
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
            // v0.13.2 PSI-2: inner-glow focus state per visual depth percepita
            "flex flex-col overflow-visible rounded-2xl border bg-sco-surface-elevated shadow-sm transition-all duration-150 focus-within:border-sco-blue focus-within:shadow-inner-glow focus-within:ring-2 focus-within:ring-sco-blue/20",
            overLimit ? "border-red-500" : "border-sco-border",
          )}
        >
          {/* Textarea */}
          <div className="relative">
            <SlashCommandsPopover
              ref={slashPopoverRef}
              open={slashOpen}
              query={slashQuery}
              skills={slashSkills}
              onSelect={handleSkillSelect}
              onClose={closeSlash}
              anchorRef={textareaRef}
            />
            <textarea
              ref={textareaRef}
              value={value}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder="Scrivi un messaggio..."
              rows={1}
              data-tour="chat-input-textarea"
              className="resize-none border-0 bg-transparent px-4 pt-3.5 pb-2 text-sm leading-relaxed text-sco-text placeholder:text-sco-muted-foreground/70 focus:outline-none dark:text-sco-text-dark"
              disabled={isStreaming}
            />
          </div>

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
                      className="fixed inset-0 z-[60]"
                      onClick={() => setModeOpen(false)}
                    />
                    {/* v0.8.2 fix dropdown clipping: bottom-full ancora ma con
                        z-index alto + position absolute relativo al wrapper
                        che e' relative. Aggiungo min-w per garantire 3 opzioni
                        visibili anche se viewport stretto. */}
                    <div
                      role="listbox"
                      aria-label="Modalita interazione agente"
                      className="absolute bottom-full left-0 z-[70] mb-2 w-80 min-w-[320px] max-h-[420px] overflow-y-auto rounded-lg border border-sco-border bg-sco-surface-elevated p-1 shadow-2xl"
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
                              if (m.value === "yolo") {
                                if (!yoloAcknowledged) {
                                  setPendingMode("yolo");
                                  setSecurityWarningOpen(true);
                                  setModeOpen(false);
                                  return;
                                }
                                setYoloAcknowledged(true);
                              }
                              setMode(m.value);
                              if (activeConversationId) {
                                setConversationMode(activeConversationId, m.value);
                              }
                              setPendingMode(null);
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
                  charCount > SOFT_WARN_CHARS
                    ? "font-semibold text-amber-500"
                    : "text-sco-muted-foreground",
                )}
                aria-live="polite"
                title={
                  charCount > SOFT_WARN_CHARS
                    ? `Messaggio molto lungo (${charCount} caratteri) — l'agente potrebbe richiedere piu' tempo`
                    : ""
                }
              >
                {charCount > 0 ? `${charCount.toLocaleString("it-IT")} caratteri` : ""}
              </span>
              {/* Microfono push-to-talk (visibile solo se sttEnabled in Settings).
                  Hotkey globale Ctrl+Shift+Space gestito internamente. */}
              <MicButton
                onTranscript={handleTranscript}
                disabled={isStreaming}
              />
              <motion.button
                type="button"
                onClick={handleSend}
                disabled={!canSend}
                data-tour="chat-send-button"
                whileHover={canSend ? { scale: 1.05 } : undefined}
                whileTap={canSend ? { scale: 0.92 } : undefined}
                transition={{ duration: 0.12, ease: "easeOut" }}
                className={cn(
                  // v0.13.2 PSI-2: shadow-crisp per definizione button (active state)
                  "relative flex h-8 w-8 items-center justify-center overflow-hidden rounded-lg transition-colors duration-150",
                  canSend
                    ? "bg-sco-blue text-white shadow-crisp hover:bg-sco-navy hover:shadow-medium"
                    : "cursor-not-allowed bg-sco-muted text-sco-muted-foreground",
                )}
                title="Invia (Invio)"
                aria-label="Invia messaggio"
              >
                {/* Shine ripple overlay sweep on hover when canSend */}
                {canSend && (
                  <span
                    aria-hidden="true"
                    className="pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/30 to-transparent transition-transform duration-500 ease-out hover:translate-x-full"
                  />
                )}
                <Send size={14} className="relative" />
              </motion.button>
            </div>
          </div>
        </div>

        {/* Privacy footer */}
        <p className="mt-2 text-center text-[11px] text-sco-muted-foreground">
          <span className="italic">Privato. Tuo. Italiano.</span> — Nessun dato
          lascia il tuo dispositivo senza conferma.
        </p>
      </div>
      <SecurityWarningModal
        open={securityWarningOpen}
        onConfirm={handleConfirmSecurityWarning}
        onCancel={handleCancelSecurityWarning}
      />
    </div>
  );
}








