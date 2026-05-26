// SCO Compliance OS — area chat principale: WelcomeScreen animato + bubbles polished + widget AskUserQuestion
//
// v0.13.0 PSI: hero empty-state spostato in screens/WelcomeScreen.tsx come componente
// dedicato animato (Framer Motion char-by-char reveal + stagger card grid + tagline parole).
// MessageBubble ora ha entrance animation con motion.div + AnimatePresence.
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { motion, AnimatePresence } from "framer-motion";
import { Wrench, CheckCircle2, XCircle } from "lucide-react";

import { useChatStore } from "@/store/chat-store";
import type { MessageItem } from "@/types/api";
import { cn } from "@/lib/cn";
import { ThinkingIndicator } from "@/components/ThinkingIndicator";
import { AudioPlayer } from "@/components/voice/AudioPlayer";
import { AskQuestionCard } from "@/components/AskQuestionCard";
import { WikiIngestProposalCard } from "@/components/WikiIngestProposalCard";
import { WelcomeScreen } from "@/screens/WelcomeScreen";
import {
  parseInlineWidgets,
  type ContentSegment,
  type InlineToolCallPayload,
  type InlineToolResultPayload,
} from "@/lib/parseInlineWidgets";

// Soglia (px) entro cui l'utente e' considerato "ancora al bottom" della chat.
// Sotto questa distanza dal fondo, lo stick-to-bottom resta attivo; oltre,
// si disattiva per rispettare l'intent di scroll dell'utente.
const STICK_BOTTOM_THRESHOLD_PX = 100;

export function ChatArea() {
  const activeId = useChatStore((s) => s.activeConversationId);
  const messagesByConv = useChatStore((s) => s.messagesByConv);
  const isStreaming = useChatStore((s) => s.isStreaming);

  const messages = useMemo<MessageItem[]>(
    () => (activeId ? (messagesByConv[activeId] ?? []) : []),
    [activeId, messagesByConv],
  );

  // ===== Auto-scroll stick-to-bottom (v0.12.0) =====
  // Pattern Slack/Discord/Claude Code: scroll auto al fondo a ogni nuovo
  // messaggio O a ogni delta di streaming, MA solo se l'utente non ha
  // intenzionalmente scrollato verso l'alto per leggere messaggi precedenti.
  //
  // Tre ref/state in gioco:
  //   - scrollContainerRef: il <div className="h-full overflow-y-auto"> che
  //     ospita la lista messaggi e gestisce lo scroll.
  //   - bottomSentinelRef: un <div> vuoto in coda alla lista, target di
  //     scrollIntoView per portare il fondo in vista in modo smooth.
  //   - isStickyBottom: true finche l'utente sta guardando il fondo; passa a
  //     false appena si allontana di piu di STICK_BOTTOM_THRESHOLD_PX dal
  //     bottom; torna a true quando ritorna entro la soglia.
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const bottomSentinelRef = useRef<HTMLDivElement | null>(null);
  const [isStickyBottom, setIsStickyBottom] = useState(true);

  // Signature dei messaggi che cattura sia la lunghezza della lista
  // (nuovo messaggio aggiunto) sia la lunghezza del content dell'ultimo
  // messaggio (delta streaming inter-message). useEffect su questa stringa
  // re-triggera lo scroll a ogni token del backend.
  const messagesSignature = useMemo(() => {
    if (messages.length === 0) return "0";
    const last = messages[messages.length - 1];
    return `${messages.length}:${last.id}:${last.content.length}`;
  }, [messages]);

  // Handler scroll: stima la distanza dal bottom e aggiorna isStickyBottom.
  // Coperto: scroll mouse wheel, scroll touch, scroll tastiera, resize finestra
  // (resize cambia clientHeight e re-triggera questo handler in modo indiretto
  // via il resize listener piu sotto).
  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    const atBottom = distanceFromBottom <= STICK_BOTTOM_THRESHOLD_PX;
    setIsStickyBottom((prev) => (prev === atBottom ? prev : atBottom));
  }, []);

  // Scroll al bottom a ogni nuovo messaggio o delta streaming, ma solo se
  // l'utente non ha rotto lo stick scrollando in alto.
  useEffect(() => {
    if (!isStickyBottom) return;
    const sentinel = bottomSentinelRef.current;
    if (!sentinel) return;
    sentinel.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messagesSignature, isStickyBottom]);

  // Mount iniziale della view "lista messaggi" (es. apertura conversation
  // dalla sidebar con history caricata): scroll istantaneo al fondo SENZA
  // animazione, cosi l'utente vede subito l'ultimo messaggio. useLayoutEffect
  // perche deve avvenire prima del paint per evitare il flash a meta scroll.
  // Dipendenza activeId: si re-triggera a ogni cambio conversation.
  useLayoutEffect(() => {
    if (!activeId) return;
    const el = scrollContainerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    setIsStickyBottom(true);
  }, [activeId]);

  // Resize finestra: ricalcola lo stato sticky. Se la finestra si rimpicciolisce
  // mentre eravamo al fondo, vogliamo restare al fondo (lo scroll auto del
  // useEffect sopra non si triggera senza messagesSignature, quindi forziamo
  // qui un re-scroll quando ancora sticky).
  useEffect(() => {
    const onResize = () => {
      handleScroll();
      if (isStickyBottom) {
        bottomSentinelRef.current?.scrollIntoView({ behavior: "auto", block: "end" });
      }
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [handleScroll, isStickyBottom]);

  // ===== Welcome hero (state vuoto) =====
  // v0.13.0 PSI: delegato a WelcomeScreen component animato (Framer Motion).
  if (!activeId || messages.length === 0) {
    return <WelcomeScreen />;
  }

  // ===== Lista messaggi (state attivo) =====
  return (
    <div
      ref={scrollContainerRef}
      onScroll={handleScroll}
      className="h-full overflow-y-auto"
    >
      <div className="mx-auto flex w-full max-w-chat flex-col gap-5 px-6 py-8">
        {/* AnimatePresence con mode="popLayout" garantisce che ogni nuovo
            messaggio entri con motion.div initial→animate definito in
            MessageBubble. popLayout evita layout shift quando un messaggio
            cresce in lunghezza durante streaming. */}
        <AnimatePresence mode="popLayout" initial={false}>
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
        </AnimatePresence>
        {/* ThinkingIndicator con fade entrance/exit */}
        <AnimatePresence>
          {isStreaming && (
            <motion.div
              key="thinking"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="flex justify-start"
            >
              <ThinkingIndicator />
            </motion.div>
          )}
        </AnimatePresence>
        {/* Sentinel auto-scroll: target di scrollIntoView per stick-to-bottom.
            Resta sempre l'ultimo nodo DOM della lista cosi il fondo della
            chat e' garantito raggiungibile anche con ThinkingIndicator visibile. */}
        <div ref={bottomSentinelRef} aria-hidden="true" />
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
    <motion.div
      initial={{
        opacity: 0,
        y: 12,
        x: isUser ? 16 : -16,
      }}
      animate={{ opacity: 1, y: 0, x: 0 }}
      transition={{
        duration: 0.32,
        ease: [0.16, 1, 0.3, 1],
      }}
      className={cn("flex", isUser ? "justify-end" : "justify-start")}
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
            {/*
             * v0.13.4 Bug B fix (Antonio feedback 26/05): defensive rendering.
             * Diagnosi root cause subagent: backend emette content="" quando
             * Claude rifiuta task per VINCOLO ONBOARDING strict (v0.13.3
             * agent_sdk_runner:258-269) + zero text_delta + persistenza
             * silente. Pre-fix il bubble era visibile ma vuoto (rectangle
             * fantasma con border+padding senza children).
             *
             * Defensive check: se NESSUN segment ha contenuto renderable
             * (text whitespace-only + nessun ask/tool widget) + il messaggio
             * non ha widget ask_user_question Conv. 48 + nessun tool_call →
             * mostra placeholder visibile con suggerimento operativo.
             */}
            {(() => {
              const hasRenderableSegments = segments.some(
                (s) =>
                  (s.kind === "text" && s.text.trim().length > 0) ||
                  s.kind !== "text",
              );
              const hasStructuredWidget =
                message.ask_user_question != null ||
                (message.tool_calls != null && message.tool_calls.length > 0);
              if (!hasRenderableSegments && !hasStructuredWidget) {
                return (
                  <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2.5 text-sm italic text-amber-800 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-200">
                    L&apos;agente non ha generato una risposta. Possibile causa:
                    vincolo onboarding ancora attivo. Prova a scrivere{" "}
                    <code className="rounded bg-amber-100 px-1 text-xs dark:bg-amber-900/50">
                      salta onboarding
                    </code>{" "}
                    per procedere senza profilo, oppure completa le 10 domande
                    di profilazione.
                  </div>
                );
              }
              return null;
            })()}
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
    </motion.div>
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
