// SCO Compliance OS — area chat principale: WelcomeHero + bubbles + markdown + widget AskUserQuestion
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import {
  ShieldCheck,
  ScanSearch,
  HeartPulse,
  AlertTriangle,
  Sparkles,
} from "lucide-react";

import { useChatStore } from "@/store/chat-store";
import type { MessageItem } from "@/types/api";
import { cn } from "@/lib/cn";
import { ThinkingIndicator } from "@/components/ThinkingIndicator";

// 4 suggestion card branded compliance
const SUGGESTIONS = [
  {
    icon: ShieldCheck,
    title: "Audit ISO 27001",
    prompt:
      "Prepara una checklist audit ISO 27001:2022 Annex A per cliente sanitario, includendo i controlli A.5–A.18.",
    accent: "text-sco-navy",
  },
  {
    icon: ScanSearch,
    title: "Gap analysis NIS 2",
    prompt:
      "Esegui una gap analysis del D.Lgs. 138/2024 per un fornitore ICT verso PA, articolo per articolo.",
    accent: "text-sco-blue",
  },
  {
    icon: HeartPulse,
    title: "Procedura sanitaria",
    prompt:
      "Redigi una procedura SGQ ISO 9001:2015 per gestione cartelle cliniche in IRCCS, sezione 7 e 8.",
    accent: "text-sco-amber",
  },
  {
    icon: AlertTriangle,
    title: "Risk assessment",
    prompt:
      "Conduci un risk assessment ISO 27005:2022 su infrastruttura cloud Azure, con matrice probabilità × impatto.",
    accent: "text-red-600",
  },
];

export function ChatArea() {
  const activeId = useChatStore((s) => s.activeConversationId);
  const messagesByConv = useChatStore((s) => s.messagesByConv);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const sendMessage = useChatStore((s) => s.sendMessage);

  const messages = useMemo<MessageItem[]>(
    () => (activeId ? (messagesByConv[activeId] ?? []) : []),
    [activeId, messagesByConv],
  );

  // Welcome hero quando nessuna conversation o conversation vuota
  if (!activeId || messages.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-6">
        <div className="flex max-w-chat flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-sco-navy text-white">
            <Sparkles size={28} />
          </div>
          <h2 className="text-2xl font-semibold text-sco-navy dark:text-sco-text-dark">
            Cosa devi fare oggi?
          </h2>
          <p className="mt-2 text-sm text-sco-muted-foreground">
            Sono il tuo Personal AI di compliance italiana. Audit, gap analysis,
            procedure, risk assessment.
          </p>

          <div className="mt-8 grid w-full grid-cols-1 gap-3 md:grid-cols-2">
            {SUGGESTIONS.map((s) => {
              const Icon = s.icon;
              return (
                <button
                  key={s.title}
                  type="button"
                  onClick={() => sendMessage(s.prompt)}
                  className="group rounded-lg border border-sco-border bg-sco-surface-elevated p-4 text-left transition-all hover:border-sco-blue hover:shadow-md"
                >
                  <div className="flex items-center gap-2">
                    <Icon size={18} className={s.accent} />
                    <span className="text-sm font-semibold">{s.title}</span>
                  </div>
                  <p className="mt-2 line-clamp-2 text-xs text-sco-muted-foreground group-hover:text-sco-text">
                    {s.prompt}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // Lista messaggi
  return (
    <div className="flex h-full flex-col overflow-y-auto px-6 py-6">
      <div className="mx-auto flex w-full max-w-chat flex-col gap-6">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {isStreaming && (
          <div className="flex justify-start">
            <ThinkingIndicator />
          </div>
        )}
      </div>
    </div>
  );
}

interface MessageBubbleProps {
  message: MessageItem;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const answerAskUserQuestion = useChatStore((s) => s.answerAskUserQuestion);
  const isUser = message.role === "user";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-3 text-sm",
          isUser
            ? "bg-sco-navy text-white"
            : "border border-sco-border bg-sco-surface-elevated text-sco-text dark:text-sco-text-dark",
        )}
      >
        {/* Markdown body: user = plain text whitespace-pre, agent = full markdown */}
        {isUser ? (
          <div className="whitespace-pre-wrap break-words text-white">
            {message.content}
          </div>
        ) : (
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Tool calls inline (Read/Grep/Write ...) */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-3 space-y-1 border-t border-sco-border pt-2">
            {message.tool_calls.map((tc) => (
              <div
                key={tc.id}
                className="font-mono text-xs text-sco-muted-foreground"
              >
                <span className="text-sco-blue">[{tc.tool_name}]</span>{" "}
                {tc.display}
                {tc.status === "error" && tc.error && (
                  <span className="text-red-500"> — {tc.error}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Widget AskUserQuestion (Conv. 48 — persistito in DB lato backend) */}
        {message.ask_user_question && (
          <div className="mt-3 rounded-md border border-sco-blue/40 bg-sco-blue/5 p-3">
            <div className="mb-2 text-sm font-medium text-sco-navy dark:text-sco-text-dark">
              {message.ask_user_question.prompt}
            </div>
            <div className="flex flex-col gap-1">
              {message.ask_user_question.options.map((opt) => {
                const isAnswered =
                  message.ask_user_question?.state === "answered";
                const isSelected =
                  message.ask_user_question?.answer_id === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    disabled={isAnswered}
                    onClick={() => answerAskUserQuestion(message.id, opt.id)}
                    className={cn(
                      "rounded-md border px-3 py-2 text-left text-sm transition-colors",
                      isAnswered
                        ? "cursor-not-allowed border-sco-border bg-sco-muted text-sco-muted-foreground"
                        : "border-sco-border bg-sco-bg hover:border-sco-blue hover:bg-sco-blue/10",
                      isSelected && "border-sco-amber bg-sco-amber/10",
                    )}
                  >
                    <span className="font-medium">{opt.label}</span>
                    {opt.description && (
                      <span className="ml-2 text-xs text-sco-muted-foreground">
                        — {opt.description}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
