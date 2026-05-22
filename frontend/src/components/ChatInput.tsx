// SCO Compliance OS — input bottom: textarea auto-grow + send + attach + mode selector
import { useRef, useState, type KeyboardEvent, type ChangeEvent } from "react";
import { Send, Paperclip, Slash, ChevronDown } from "lucide-react";
import { toast } from "sonner";

import { useChatStore } from "@/store/chat-store";
import { cn } from "@/lib/cn";

const MAX_CHARS = 8000;

type ChatMode = "plan" | "ask" | "auto";

const MODES: { value: ChatMode; label: string; description: string }[] = [
  {
    value: "plan",
    label: "Pianifica",
    description: "Espone il piano prima di agire",
  },
  {
    value: "ask",
    label: "Chiedi",
    description: "Conferma ogni azione con AskUserQuestion",
  },
  {
    value: "auto",
    label: "Senza autorizzazioni",
    description: "Procede in autonomia (default GOAL persistence)",
  },
];

export function ChatInput() {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [value, setValue] = useState("");
  const [mode, setMode] = useState<ChatMode>("ask");
  const [modeOpen, setModeOpen] = useState(false);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const sendMessage = useChatStore((s) => s.sendMessage);

  const charCount = value.length;
  const overLimit = charCount > MAX_CHARS;

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

  const currentMode = MODES.find((m) => m.value === mode)!;

  return (
    <div className="border-t border-sco-border bg-sco-bg px-6 py-4">
      <div className="mx-auto max-w-chat">
        <div
          className={cn(
            "flex flex-col rounded-lg border bg-sco-surface-elevated focus-within:border-sco-blue",
            overLimit ? "border-red-500" : "border-sco-border",
          )}
        >
          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Scrivi un messaggio... (Invio per inviare, Shift+Invio per nuova riga)"
            rows={1}
            className="resize-none border-0 bg-transparent px-4 py-3 text-sm text-sco-text placeholder:text-sco-muted-foreground focus:outline-none dark:text-sco-text-dark"
            disabled={isStreaming}
          />

          {/* Toolbar inferiore */}
          <div className="flex items-center justify-between border-t border-sco-border px-3 py-2">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleAttach}
                className="rounded-md p-1.5 text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
                title="Allega file"
              >
                <Paperclip size={16} />
              </button>
              <button
                type="button"
                onClick={handleSlashCommand}
                className="rounded-md p-1.5 text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
                title="Slash commands"
              >
                <Slash size={16} />
              </button>

              {/* Mode selector */}
              <div className="relative ml-2">
                <button
                  type="button"
                  onClick={() => setModeOpen(!modeOpen)}
                  className="flex items-center gap-1 rounded-md border border-sco-border px-2 py-1 text-xs hover:border-sco-blue"
                >
                  <span className="font-medium">{currentMode.label}</span>
                  <ChevronDown
                    size={12}
                    className={cn(
                      "transition-transform",
                      modeOpen && "rotate-180",
                    )}
                  />
                </button>

                {modeOpen && (
                  <div className="absolute bottom-full left-0 z-50 mb-1 w-64 rounded-md border border-sco-border bg-sco-surface-elevated p-1 shadow-lg">
                    {MODES.map((m) => (
                      <button
                        key={m.value}
                        type="button"
                        onClick={() => {
                          setMode(m.value);
                          setModeOpen(false);
                        }}
                        className={cn(
                          "w-full rounded-md px-3 py-2 text-left text-xs hover:bg-sco-muted",
                          mode === m.value && "bg-sco-muted",
                        )}
                      >
                        <div className="font-medium">{m.label}</div>
                        <div className="text-sco-muted-foreground">
                          {m.description}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "text-xs",
                  overLimit ? "text-red-500" : "text-sco-muted-foreground",
                )}
              >
                {charCount}/{MAX_CHARS}
              </span>
              <button
                type="button"
                onClick={handleSend}
                disabled={!value.trim() || isStreaming || overLimit}
                className="flex h-8 w-8 items-center justify-center rounded-md bg-sco-navy text-white transition-colors hover:bg-sco-blue disabled:cursor-not-allowed disabled:bg-sco-border disabled:text-sco-muted-foreground"
                title="Invia (Invio)"
              >
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>

        <p className="mt-2 text-center text-xs text-sco-muted-foreground">
          Privato. Tuo. Italiano. — Nessun dato lascia il tuo dispositivo senza
          conferma.
        </p>
      </div>
    </div>
  );
}
