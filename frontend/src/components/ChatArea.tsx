// SCO Compliance OS — area chat principale: WelcomeHero centrato + bubbles polished + widget AskUserQuestion
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import {
  ShieldCheck,
  ScanSearch,
  HeartPulse,
  AlertTriangle,
  ArrowUpRight,
  Wrench,
  CheckCircle2,
  XCircle,
} from "lucide-react";

import { useChatStore } from "@/store/chat-store";
import type { MessageItem } from "@/types/api";
import { cn } from "@/lib/cn";
import { ThinkingIndicator } from "@/components/ThinkingIndicator";
import { AudioPlayer } from "@/components/voice/AudioPlayer";
import { AskQuestionCard } from "@/components/AskQuestionCard";
import { WikiIngestProposalCard } from "@/components/WikiIngestProposalCard";
import {
  parseInlineWidgets,
  type ContentSegment,
  type InlineToolCallPayload,
  type InlineToolResultPayload,
} from "@/lib/parseInlineWidgets";

// 4 suggestion card branded compliance — 2x2 grid stile OpenHuman / Claude Desktop
const SUGGESTIONS = [
  {
    icon: ShieldCheck,
    title: "Audit ISO 27001",
    description: "Checklist Annex A per cliente sanitario",
    prompt:
      "Prepara una checklist audit ISO 27001:2022 Annex A per cliente sanitario, includendo i controlli A.5–A.18.",
    accent: "text-sco-blue",
    iconBg: "bg-sco-blue/10",
  },
  {
    icon: ScanSearch,
    title: "Gap analysis NIS 2",
    description: "D.Lgs. 138/2024 art. per art. per fornitore PA",
    prompt:
      "Esegui una gap analysis del D.Lgs. 138/2024 per un fornitore ICT verso PA, articolo per articolo.",
    accent: "text-sco-navy dark:text-sco-text-dark",
    iconBg: "bg-sco-navy/10 dark:bg-sco-text-dark/10",
  },
  {
    icon: HeartPulse,
    title: "Procedura sanitaria",
    description: "ISO 9001:2015 cartelle cliniche IRCCS",
    prompt:
      "Redigi una procedura SGQ ISO 9001:2015 per gestione cartelle cliniche in IRCCS, sezione 7 e 8.",
    accent: "text-sco-amber",
    iconBg: "bg-sco-amber/10",
  },
  {
    icon: AlertTriangle,
    title: "Risk assessment cloud",
    description: "ISO 27005:2022 matrice probabilità × impatto",
    prompt:
      "Conduci un risk assessment ISO 27005:2022 su infrastruttura cloud Azure, con matrice probabilità × impatto.",
    accent: "text-red-500",
    iconBg: "bg-red-500/10",
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

  // ===== Welcome hero (state vuoto) =====
  if (!activeId || messages.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center overflow-y-auto px-6 py-12">
        <div className="flex w-full max-w-3xl flex-col items-center text-center animate-fade-up">
          {/* Logo accento decorativo (sfumatura discreta) con glow pulse */}
          <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-sco-navy via-sco-blue to-sco-amber shadow-lg animate-glow-pulse">
            <span className="text-2xl font-bold text-white">S</span>
          </div>

          {/* Titolo grande stile Claude Desktop */}
          <h1 className="font-display text-3xl font-semibold tracking-tight text-sco-text dark:text-sco-text-dark md:text-4xl">
            Cosa lavoriamo oggi?
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-sco-muted-foreground md:text-base">
            Scrivi una domanda nel campo qui sotto, oppure scegli un punto di
            partenza dalle quattro card. Posso aiutarti con audit, procedure,
            gap analysis e risk assessment.
          </p>

          {/* 4 card quick action — 2x2 grid */}
          <div className="mt-10 grid w-full grid-cols-1 gap-3 md:grid-cols-2">
            {SUGGESTIONS.map((s) => {
              const Icon = s.icon;
              return (
                <button
                  key={s.title}
                  type="button"
                  onClick={() => sendMessage(s.prompt)}
                  className="group relative flex items-start gap-3 overflow-hidden rounded-xl border border-sco-border bg-sco-surface-elevated p-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-sco-blue/60 hover:shadow-medium"
                >
                  <div
                    className={cn(
                      "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                      s.iconBg,
                    )}
                  >
                    <Icon size={20} className={s.accent} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-sco-text dark:text-sco-text-dark">
                        {s.title}
                      </span>
                      <ArrowUpRight
                        size={14}
                        className="shrink-0 text-sco-muted-foreground/0 transition-all duration-150 group-hover:text-sco-blue group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                      />
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-sco-muted-foreground">
                      {s.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Tagline footer */}
          <p className="mt-12 text-xs italic text-sco-muted-foreground/70">
            Privato. Tuo. Italiano.
          </p>
        </div>
      </div>
    );
  }

  // ===== Lista messaggi (state attivo) =====
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-chat flex-col gap-5 px-6 py-8">
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
  const answerInlineAskQuestion = useChatStore(
    (s) => s.answerInlineAskQuestion,
  );
  const inlineAskAnswers = useChatStore((s) => s.inlineAskAnswers);
  // v0.8.1 hook wiki ingest: proposal correlata a questo message_id e flag dismiss.
  const wikiProposal = useChatStore(
    (s) => s.wikiIngestProposals[message.id],
  );
  const wikiDismissed = useChatStore(
    (s) => s.wikiIngestDismissed[message.id] === true,
  );
  const isUser = message.role === "user";

  // Parser inline tag (v1.0.2 fix bug widget AskUserQuestion non renderizzato).
  // Esegui SOLO per messaggi assistant: i messaggi utente sono plain text e
  // non contengono tag emessi dal backend. Memoizzato sul content stringa.
  const segments = useMemo<ContentSegment[]>(
    () => (isUser ? [{ kind: "text", text: message.content }] : parseInlineWidgets(message.content)),
    [isUser, message.content],
  );

  // Testo "pulito" per il TTS (rimuove i tag inline, mantiene solo i text segments)
  const ttsText = useMemo(
    () =>
      segments
        .filter((s): s is { kind: "text"; text: string } => s.kind === "text")
        .map((s) => s.text)
        .join("")
        .trim(),
    [segments],
  );

  return (
    <div
      className={cn(
        "flex animate-fade-up",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "rounded-2xl px-4 py-3 text-sm shadow-sm transition-shadow duration-200",
          isUser
            ? "max-w-[80%] bg-sco-navy text-white hover:shadow-md"
            : "max-w-[85%] border border-sco-border bg-sco-surface-elevated text-sco-text hover:shadow-md dark:text-sco-text-dark",
        )}
      >
        {/* Markdown body: user = plain text whitespace-pre, agent = segmenti misti */}
        {isUser ? (
          <div className="whitespace-pre-wrap break-words leading-relaxed text-white">
            {message.content}
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {segments.map((seg, idx) => {
                if (seg.kind === "text") {
                  // Salta segmenti di solo whitespace (artefatto dello split fra tag)
                  if (!seg.text.trim()) return null;
                  return (
                    <div
                      key={`text-${idx}`}
                      className="prose prose-sm max-w-none leading-relaxed dark:prose-invert prose-p:my-2 prose-headings:mt-3 prose-headings:mb-2 prose-pre:my-2 prose-pre:bg-sco-bg prose-pre:border prose-pre:border-sco-border prose-code:text-sco-blue dark:prose-code:text-sco-amber"
                    >
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeHighlight]}
                      >
                        {seg.text}
                      </ReactMarkdown>
                    </div>
                  );
                }
                if (seg.kind === "ask") {
                  const key = `${message.id}__${seg.index}`;
                  const answer = inlineAskAnswers[key];
                  return (
                    <AskQuestionCard
                      key={`ask-${seg.index}`}
                      payload={seg.payload}
                      state={answer?.value ? "answered" : "pending"}
                      answer_value={answer?.value}
                      isSubmitting={!!answer?.submitting}
                      onAnswer={(value) => {
                        const opt = seg.payload.options.find(
                          (o) => o.value === value,
                        );
                        void answerInlineAskQuestion({
                          messageId: message.id,
                          segmentIndex: seg.index,
                          value,
                          label: opt?.label ?? value,
                        });
                      }}
                    />
                  );
                }
                if (seg.kind === "tool_call") {
                  return (
                    <InlineToolCallBadge
                      key={`tc-${seg.index}`}
                      payload={seg.payload}
                    />
                  );
                }
                if (seg.kind === "tool_result") {
                  return (
                    <InlineToolResultBadge
                      key={`tr-${seg.index}`}
                      payload={seg.payload}
                    />
                  );
                }
                return null;
              })}
            </div>
            {/* TTS player on-device (visibile solo se ttsEnabled in Settings) */}
            {ttsText.length > 0 && (
              <div className="mt-1 flex items-center gap-1">
                <AudioPlayer text={ttsText} />
              </div>
            )}
          </>
        )}

        {/* Tool calls inline (Read/Grep/Write ...) — payload strutturato Conv. 48 */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-3 space-y-1 border-t border-sco-border pt-2">
            {message.tool_calls.map((tc, tcIdx) => (
              <div
                key={tc.id ?? `tc-${tcIdx}`}
                className="flex items-start gap-1.5 font-mono text-[11px] text-sco-muted-foreground"
              >
                <span className="shrink-0 rounded bg-sco-blue/10 px-1.5 py-0.5 text-sco-blue">
                  {tc.tool_name}
                </span>
                <span className="break-all">{tc.display}</span>
                {tc.status === "error" && tc.error && (
                  <span className="text-red-500">— {tc.error}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* v0.8.1 hook wiki ingest: card "Vuoi salvare nel wiki?" sotto la bubble
           assistant quando il backend ha emesso SSE event wiki_ingest_proposal
           e l'utente non l'ha ancora scartata o confermata. */}
        {!isUser &&
          wikiProposal &&
          !wikiDismissed &&
          wikiProposal.slots.length > 0 && (
            <WikiIngestProposalCard proposal={wikiProposal} messageId={message.id} />
          )}

        {/* Widget AskUserQuestion strutturato (Conv. 48 — persistito in DB lato
           backend nel campo ask_user_question_json). Ha priorita su quello inline:
           se il backend ha popolato il payload strutturato, lo usiamo come
           fonte di verita autoritativa. */}
        {message.ask_user_question && (
          <div className="mt-3 overflow-hidden rounded-lg border border-sco-blue/30 bg-sco-blue/5">
            <div className="border-b border-sco-blue/20 bg-sco-blue/10 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-sco-blue">
              Domanda
            </div>
            <div className="p-3">
              <div className="mb-3 text-sm font-medium text-sco-text dark:text-sco-text-dark">
                {message.ask_user_question.prompt}
              </div>
              <div className="flex flex-col gap-1.5">
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
                        "rounded-md border px-3 py-2 text-left text-sm transition-all duration-150",
                        isAnswered
                          ? "cursor-not-allowed border-sco-border bg-sco-muted text-sco-muted-foreground"
                          : "border-sco-border bg-sco-bg hover:border-sco-blue hover:bg-sco-blue/10 hover:shadow-sm",
                        isSelected &&
                          "border-sco-amber bg-sco-amber/10 ring-1 ring-sco-amber/40",
                      )}
                    >
                      <span className="font-medium text-sco-text dark:text-sco-text-dark">
                        {opt.label}
                      </span>
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
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Badge compatto per tag inline `<TOOL_CALL>` emesso dall'agente.
 *
 * Mostra un'icona wrench + nome tool + JSON args collapsable via <details>.
 * Variante mute della pill `tool_calls` strutturata in fondo al messaggio.
 */
function InlineToolCallBadge({ payload }: { payload: InlineToolCallPayload }) {
  const toolName = payload.tool_name ?? "tool";
  const hasArgs = payload.args && Object.keys(payload.args).length > 0;
  return (
    <details className="group rounded-md border border-sco-border bg-sco-bg/50 text-xs">
      <summary className="flex cursor-pointer items-center gap-2 px-2.5 py-1.5 font-mono text-sco-muted-foreground hover:bg-sco-bg">
        <Wrench size={12} className="text-sco-blue" />
        <span className="font-semibold text-sco-blue">Tool:</span>
        <span className="text-sco-text dark:text-sco-text-dark">{toolName}</span>
      </summary>
      {hasArgs && (
        <pre className="mt-1 max-h-40 overflow-auto border-t border-sco-border px-2.5 py-1.5 text-[11px] leading-snug text-sco-muted-foreground">
          {JSON.stringify(payload.args, null, 2)}
        </pre>
      )}
    </details>
  );
}

/**
 * Badge compatto per tag inline `<TOOL_RESULT>` emesso dall'agente.
 *
 * Mostra check verde se ok, x rossa se errore, + payload collapsable.
 */
function InlineToolResultBadge({ payload }: { payload: InlineToolResultPayload }) {
  const toolName = payload.tool_name ?? "tool";
  const isError = payload.is_error === true;
  return (
    <details className="group rounded-md border border-sco-border bg-sco-bg/50 text-xs">
      <summary className="flex cursor-pointer items-center gap-2 px-2.5 py-1.5 font-mono text-sco-muted-foreground hover:bg-sco-bg">
        {isError ? (
          <XCircle size={12} className="text-red-500" />
        ) : (
          <CheckCircle2 size={12} className="text-green-600" />
        )}
        <span className={cn("font-semibold", isError ? "text-red-500" : "text-green-700")}>
          Risultato:
        </span>
        <span className="text-sco-text dark:text-sco-text-dark">{toolName}</span>
      </summary>
      <pre className="mt-1 max-h-40 overflow-auto border-t border-sco-border px-2.5 py-1.5 text-[11px] leading-snug text-sco-muted-foreground">
        {typeof payload.result === "string"
          ? payload.result
          : JSON.stringify(payload.result, null, 2)}
      </pre>
    </details>
  );
}
