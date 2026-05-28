// SCO Compliance OS — chat store Zustand 5 con persistenza conversations + messages
import { create } from "zustand";
import { persist } from "zustand/middleware";

import type {
  ChatMode,
  ConversationItem,
  MessageItem,
  AskUserQuestionWidget,
  WikiIngestProposal,
  ChatAttachment,
} from "@/types/api";
import { apiClient } from "@/api/client";

export type { ChatMode } from "@/types/api";

// Permission mode UX dell'agente: lo store mantiene la scelta corrente e
// impedisce la persistenza della modalit? "yolo" oltre la sessione attiva.
// Il backend v0.14.0 salva agent_mode per conversation e propaga permission_mode
// verso l'LLM.
interface ChatModeState {
  mode: ChatMode;
  setMode: (mode: ChatMode) => void;
  yoloAcknowledged: boolean;
  setYoloAcknowledged: (acknowledged: boolean) => void;
}

export const useChatModeStore = create<ChatModeState>()(
  persist(
    (set) => ({
      // Default coerente con regola permanente GOAL-PERSISTENCE 20/05:
      // "auto" = procede in autonomia fino al completamento della condizione.
      mode: "auto",
      yoloAcknowledged: false,
      setMode: (mode) =>
        set((state) => ({
          mode,
          yoloAcknowledged: mode === "yolo" ? state.yoloAcknowledged : false,
        })),
      setYoloAcknowledged: (acknowledged) => set({ yoloAcknowledged: acknowledged }),
    }),
    {
      name: "sco-chat-mode",
      partialize: (s) => ({ mode: s.mode === "yolo" ? "auto" : s.mode }),
      onRehydrateStorage: () => (state) => {
        if (state?.mode === "yolo") {
          state.mode = "auto";
        }
      },
    },
  ),
);

/**
 * Stato risposta a un widget AskUserQuestion inline (tag testuale dentro il
 * content del messaggio assistant — v1.0.2 fix). Chiave: `${messageId}__${segmentIndex}`.
 *
 * Pattern Conv. 48: idealmente questo stato dovrebbe vivere lato backend e
 * tornare con il messaggio. Finche l'endpoint non e' cablato, manteniamo lo
 * stato qui per non perdere la selezione al re-render.
 */
export interface InlineAskAnswer {
  value: string;
  submitted_at: string; // ISO 8601
  submitting?: boolean;
  error?: string | null;
}

interface ChatState {
  // Mappa conversation_id -> ConversationItem
  conversations: Record<string, ConversationItem>;
  // Mappa conversation_id -> array messaggi ordinati
  messagesByConv: Record<string, MessageItem[]>;
  activeConversationId: string | null;
  // Stato runtime
  isStreaming: boolean;
  error: string | null;
  // v1.0.2 fix sidebar visibility: tracking auto-fetch + ID conversation già viste
  // per intercettare "nuova conversation comparsa" (es. vault.registered → os-setup
  // auto-crea "Configurazione iniziale del vault X") e auto-select + toast.
  lastFetchAt: number | null;
  knownConversationIds: Set<string>;
  // v0.8.1 fix auto-navigation: ID dell'ultima conversation auto-naviata in modo
  // automatico (post-vault.registered). Serve a non ri-naviare se l'utente ha
  // gia` cambiato chat manualmente (rispetta scelta utente). Se null, prossimo
  // "Configurazione iniziale" viene auto-selezionato.
  lastAutoNavigated: string | null;
  // Mappa "messageId__segmentIndex" -> InlineAskAnswer (Conv. 48 carry-over,
  // stato widget inline ask question vive qui finche backend non cabla endpoint).
  inlineAskAnswers: Record<string, InlineAskAnswer>;
  // v0.8.1 hook wiki ingest: mappa message_id -> WikiIngestProposal ricevuta
  // via SSE event wiki_ingest_proposal alla fine dello stream chat. Il widget
  // WikiIngestProposalCard renderizza la proposta sotto la bubble assistant.
  // Pattern Conv. 47: proposal_id deterministico, scrittura idempotente.
  // Mappa message_id -> "dismissed" se l'utente ha scartato la card senza
  // confermare alcuna ingestion (no re-render alla riapertura conversation).
  wikiIngestProposals: Record<string, WikiIngestProposal>;
  wikiIngestDismissed: Record<string, true>;

  // Actions
  setActiveConversation: (id: string | null) => void;
  setConversationMode: (conversationId: string, mode: ChatMode) => void;
  createConversation: (title?: string) => string;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (text: string, attachments?: ChatAttachment[]) => Promise<void>;
  answerAskUserQuestion: (messageId: string, optionId: string) => void;
  /**
   * Invia la scelta dell'utente per un widget AskUserQuestion inline
   * (tag testuale `<ASK_USER_QUESTION>` dentro content). Tenta prima il POST
   * verso `/api/chat/answer-ask-user-question` con body `{conversation_id,
   * message_id, option_value}`. Se l'endpoint risponde 404 (carry-over:
   * non ancora cablato lato backend al 2026-05-24), fa fallback inviando
   * la `label` dell'opzione come messaggio utente normale dentro la
   * conversation corrente via `sendMessage`, cosi che l'agente possa
   * riprendere lo skill.
   *
   * Aggiorna `inlineAskAnswers[messageId__segmentIndex]` con il value
   * selezionato per impedire ulteriori click sul widget post-risposta.
   */
  answerInlineAskQuestion: (params: {
    messageId: string;
    segmentIndex: number;
    value: string;
    label: string;
  }) => Promise<void>;
  /**
   * Trigger manutenzione fine sessione via skill os-ottimizzatore.
   * Esegue POST /api/skills/run con streaming SSE, persiste output assistant
   * nella conversation creata dal backend, auto-naviga alla conversation.
   *
   * Conv. 47 + 48: backend è single source of truth (skill runner +
   * conversation storage), frontend solo orchestra UX e legge il risultato.
   */
  endSession: (params?: { vaultPath?: string }) => Promise<{
    success: boolean;
    conversationId: string | null;
    eventsCount: number;
    errorMessage: string | null;
  }>;
  clearError: () => void;
  // v1.0.2 fix sidebar visibility: fetch conversations dal backend + merge + auto-select
  // nuove "Configurazione iniziale del vault X" + toast notifica utente.
  fetchConversations: (opts?: { silent?: boolean }) => Promise<ConversationItem[]>;
  // v0.8.1 hook wiki ingest: action per scartare la proposta (utente clicca
  // X sulla card) o confermare salvataggio (rimuove la card dopo write OK).
  dismissWikiIngestProposal: (messageId: string) => void;
  removeWikiIngestProposal: (messageId: string) => void;
}

// Conv. 47 enforcement v0.7.2: conversations vivono ESCLUSIVAMENTE backend SQLite
// conversations.db. Lo stub hardcoded di 5 chat (Audit ISO 27001 + Gap NIS 2 +
// Procedura Romolo + Risk Akrea + Verbale AKREA) era pre-popolato nel JS bundle
// dal v0.0.1 demo iniziale e tornava SEMPRE post-cleanup AppData perche' caricato
// dal codice frontend, non dal disco. Antonio ha rilevato il drift dopo 4 release.
// Fix: init vuoto + fetch reale via apiClient.listConversations() al mount.
const STUB_CONVERSATIONS: ConversationItem[] = [];

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: Object.fromEntries(
        STUB_CONVERSATIONS.map((c) => [c.id, c]),
      ),
      messagesByConv: {},
      activeConversationId: null,
      isStreaming: false,
      error: null,
      lastFetchAt: null,
      knownConversationIds: new Set<string>(),
      lastAutoNavigated: null,
      inlineAskAnswers: {},
      wikiIngestProposals: {},
      wikiIngestDismissed: {},

      setActiveConversation: (id) => {
        set({ activeConversationId: id });
        // v1.0.2 fix sidebar visibility / widget render: fetch messaggi backend al
        // momento della selezione se non già in memoria. Conv. 48 single source of
        // truth: stato widget ask_user_question vive in DB messages, frontend lo
        // deduce SOLO dal fetch, non da optimistic UI memory.
        if (!id) return;
        const state = get();
        const modeStore = useChatModeStore.getState();
        const nextMode = state.conversations[id]?.agent_mode ?? "auto";
        if (nextMode === "yolo" && !modeStore.yoloAcknowledged) {
          if (modeStore.mode !== "auto") {
            modeStore.setMode("auto");
          }
        } else if (modeStore.mode !== nextMode) {
          modeStore.setMode(nextMode);
        }
        const isOptimisticConv = id.startsWith("stub-") || id.startsWith("conv-");
        const cached = state.messagesByConv[id] ?? [];
        const conv = state.conversations[id];
        const isConfigWelcome =
          conv?.title?.startsWith("Configurazione iniziale del vault") ?? false;
        const isOptimizerWelcome =
          conv?.title?.startsWith("Ottimizzazione iniziale del vault") ?? false;
        // Conv backend + (no cache OPPURE è "Configurazione/Ottimizzazione iniziale"
        // che potrebbe avere messaggi nuovi aggiunti dal skill loader
        // post-vault.registered / post-setup.completed)
        if (
          !isOptimisticConv &&
          (cached.length === 0 || isConfigWelcome || isOptimizerWelcome)
        ) {
          void apiClient
            .getConversationMessages(id)
            .then((msgs) => {
              set((s) => ({
                messagesByConv: { ...s.messagesByConv, [id]: msgs },
              }));
            })
            .catch((err) => {
              set({
                error: `Errore fetch messaggi: ${err instanceof Error ? err.message : err}`,
              });
            });
        }
      },

      setConversationMode: (conversationId, mode) => {
        const state = get();
        const current = state.conversations[conversationId];
        if (!current) {
          return;
        }

        if (current.agent_mode !== mode) {
          set({
            conversations: {
              ...state.conversations,
              [conversationId]: { ...current, agent_mode: mode },
            },
          });
        }

        const isStubId =
          conversationId.startsWith("conv-") || conversationId.startsWith("stub-");
        if (isStubId) {
          return;
        }

        void apiClient
          .setConversationMode(conversationId, mode)
          .then((updated) => {
            set((s) => {
              const existing = s.conversations[conversationId];
              if (!existing) {
                return {};
              }
              return {
                conversations: {
                  ...s.conversations,
                  [conversationId]: { ...existing, ...updated },
                },
              };
            });
          })
          .catch((err) => {
            set({
              error: `Errore aggiornamento modalita conversazione: ${
                err instanceof Error ? err.message : err
              }`,
            });
          });
      },

      createConversation: (title = "Nuova conversazione") => {
        const id = `conv-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        const now = new Date().toISOString();
        const conv: ConversationItem = {
          id,
          title,
          vault_id: null,
          created_at: now,
          updated_at: now,
          message_count: 0,
          agent_mode: "auto",
        };
        set((s) => ({
          conversations: { ...s.conversations, [id]: conv },
          messagesByConv: { ...s.messagesByConv, [id]: [] },
          activeConversationId: id,
        }));
        return id;
      },

      deleteConversation: async (id) => {
        const state = get();
        if (!state.conversations[id]) {
          return;
        }

        try {
          await apiClient.deleteConversation(id);
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          set({
            error: `Errore cancellazione conversazione: ${message}`,
          });
          throw err;
        }

        set((s) => {
          const { [id]: _removedConv, ...restConvs } = s.conversations;
          const { [id]: _removedMsgs, ...restMsgs } = s.messagesByConv;
          const nextKnown = new Set(s.knownConversationIds);
          nextKnown.delete(id);
          return {
            conversations: restConvs,
            messagesByConv: restMsgs,
            knownConversationIds: nextKnown,
            activeConversationId:
              s.activeConversationId === id ? null : s.activeConversationId,
            lastAutoNavigated: s.lastAutoNavigated === id ? null : s.lastAutoNavigated,
          };
        });
      },

      sendMessage: async (text, attachments = []) => {
        const state = get();
        let convId = state.activeConversationId;
        const now = new Date().toISOString();

        // v0.13.2 hotfix Bug bullet vuoto su 2ª chat NUOVA consecutiva:
        // `createConversation` (line ~191) crea stub locale con id
        // `conv-<timestamp>-<rand>`. La precedente check `startsWith("stub-")`
        // NON matchava mai perché il prefisso reale è "conv-" → stub veniva
        // trattato come backend conv → backend rispondeva 404 → bullet vuoto.
        // Backend conv id è UUID (vedi backend/.../store.py `_new_uuid`) che
        // mai inizia con "conv-" o "stub-". Quindi un id che inizia con "conv-"
        // o "stub-" è SEMPRE uno stub frontend non promosso.
        const existing = convId ? state.conversations[convId] : null;
        const isStubId = existing && (
          existing.id.startsWith("conv-") || existing.id.startsWith("stub-")
        );
        const isBackendConv = existing && !isStubId;

        if (!convId || !isBackendConv) {
          try {
            const newConv = await apiClient.createConversation();
            // v0.13.2 hotfix: rimuovi stub locale (se esisteva) per evitare
            // duplicati nella sidebar che mostrerebbero conv-<rand> orfana.
            const stubIdToRemove = convId && isStubId ? convId : null;
            convId = newConv.id;
            set((s) => {
              const conversations = { ...s.conversations };
              const messagesByConv = { ...s.messagesByConv };
              if (stubIdToRemove) {
                delete conversations[stubIdToRemove];
                delete messagesByConv[stubIdToRemove];
              }
              return {
                conversations: { ...conversations, [newConv.id]: newConv },
                messagesByConv: { ...messagesByConv, [newConv.id]: [] },
                activeConversationId: newConv.id,
              };
            });
          } catch (err) {
            set({
              error: `Errore creazione conversation: ${err instanceof Error ? err.message : err}`,
              isStreaming: false,
            });
            return;
          }
        }

        const conversationId: string = convId!;
        const chatMode = useChatModeStore.getState().mode;

        // Append messaggio utente locale
        const userMsg: MessageItem = {
          id: `msg-${Date.now()}-u`,
          conversation_id: conversationId,
          role: "user",
          content: text,
          created_at: now,
        };
        // Append empty assistant message che riempiremo via SSE
        const assistantMsgId = `msg-${Date.now()}-a`;
        const assistantMsg: MessageItem = {
          id: assistantMsgId,
          conversation_id: conversationId,
          role: "assistant",
          content: "",
          created_at: now,
        };
        set((s) => ({
          messagesByConv: {
            ...s.messagesByConv,
            [conversationId]: [...(s.messagesByConv[conversationId] ?? []), userMsg, assistantMsg],
          },
          isStreaming: true,
          error: null,
        }));

        try {
          await apiClient.sendChatMessage({
            conversation_id: conversationId,
            message: text,
            agent_mode: chatMode,
            attachments,
            onEvent: (event) => {
              if (event.kind === "text_delta") {
                const chunk = String(event.data?.text ?? "");
                if (chunk) {
                  // Append chunk al messaggio assistant in streaming
                  set((s) => ({
                    messagesByConv: {
                      ...s.messagesByConv,
                      [conversationId]: (s.messagesByConv[conversationId] ?? []).map((m) =>
                        m.id === assistantMsgId
                          ? { ...m, content: m.content + chunk }
                          : m,
                      ),
                    },
                  }));
                }
              } else if (event.kind === "error") {
                const errMsg = String((event.data as { message?: string })?.message ?? "errore stream");
                set({ error: errMsg });
              } else if (event.kind === "wiki_ingest_proposal") {
                // v0.8.1 hook: il backend ha analizzato il messaggio assistant
                // appena emesso (allegati / URL / search results) e ha trovato
                // candidati per ingest wiki. Salva la proposal nello store
                // indicizzata per message_id (quello del backend, non il client
                // ID ottimistico). La card si renderizza in ChatArea.
                const proposal = event.data as unknown as WikiIngestProposal;
                if (proposal?.message_id) {
                  set((s) => ({
                    wikiIngestProposals: {
                      ...s.wikiIngestProposals,
                      [proposal.message_id]: proposal,
                    },
                  }));
                }
              } else if (event.kind === "done") {
                set((s) => {
            const current = s.conversations[conversationId];
            if (!current || current.agent_mode === chatMode) {
              return {};
            }
            return {
              conversations: {
                ...s.conversations,
                [conversationId]: { ...current, agent_mode: chatMode },
              },
            };
          });
          set({ isStreaming: false });
              }
            },
          });
          set({ isStreaming: false });
        } catch (err) {
          const message = err instanceof Error ? err.message : "Errore sconosciuto";
          set({ isStreaming: false, error: message });
        }
      },

      answerAskUserQuestion: (messageId, optionId) => {
        set((s) => {
          const updated: typeof s.messagesByConv = {};
          for (const [convId, msgs] of Object.entries(s.messagesByConv)) {
            updated[convId] = msgs.map((m): MessageItem => {
              if (m.id !== messageId || !m.ask_user_question) return m;
              const widget: AskUserQuestionWidget = {
                ...m.ask_user_question,
                state: "answered",
                answer_id: optionId,
              };
              return { ...m, ask_user_question: widget };
            });
          }
          return { messagesByConv: updated };
        });
      },

      answerInlineAskQuestion: async ({ messageId, segmentIndex, value, label }) => {
        const key = `${messageId}__${segmentIndex}`;
        const state = get();

        // Guard: gia' risposto -> no-op (impedisce doppio click in race)
        if (state.inlineAskAnswers[key]?.value) return;

        const conversationId = state.activeConversationId;
        if (!conversationId) {
          set((s) => ({
            inlineAskAnswers: {
              ...s.inlineAskAnswers,
              [key]: {
                value,
                submitted_at: new Date().toISOString(),
                error: "Nessuna conversation attiva",
              },
            },
          }));
          return;
        }

        // Optimistic lock UI: marca submitting
        const submittedAt = new Date().toISOString();
        set((s) => ({
          inlineAskAnswers: {
            ...s.inlineAskAnswers,
            [key]: { value, submitted_at: submittedAt, submitting: true },
          },
        }));

        // 1) Primary: POST verso endpoint dedicato (quando backend lo cablera')
        try {
          await apiClient.answerAskUserQuestion({
            conversation_id: conversationId,
            message_id: messageId,
            option_value: value,
          });
          set((s) => ({
            inlineAskAnswers: {
              ...s.inlineAskAnswers,
              [key]: { value, submitted_at: submittedAt, submitting: false },
            },
          }));
          return;
        } catch (err) {
          // Stato 404 / endpoint non cablato -> fallback graceful via sendMessage
          // Pattern Conv. 35 RESEARCH-BEFORE-ACT: l'endpoint non esiste ancora
          // lato backend (verificato 2026-05-24), fallback obbligatorio per non
          // bloccare l'utente. Quando backend lo cablera', il path primario
          // sopra coprira' il caso e questo fallback non sara' raggiunto.
          const isMissingEndpoint =
            err instanceof Error &&
            /404|Not Found|answer_ask_user_question_error/i.test(err.message);

          if (!isMissingEndpoint) {
            // Errore generico -> registra ma NON fallback (non sappiamo cosa abbia
            // gia' fatto il backend, evitiamo doppio invio)
            set((s) => ({
              inlineAskAnswers: {
                ...s.inlineAskAnswers,
                [key]: {
                  value,
                  submitted_at: submittedAt,
                  submitting: false,
                  error: err instanceof Error ? err.message : String(err),
                },
              },
              error: `Errore invio risposta widget: ${err instanceof Error ? err.message : err}`,
            }));
            return;
          }
        }

        // 2) Fallback: invia la label come messaggio utente normale
        try {
          await get().sendMessage(label);
          set((s) => ({
            inlineAskAnswers: {
              ...s.inlineAskAnswers,
              [key]: { value, submitted_at: submittedAt, submitting: false },
            },
          }));
        } catch (err) {
          set((s) => ({
            inlineAskAnswers: {
              ...s.inlineAskAnswers,
              [key]: {
                value,
                submitted_at: submittedAt,
                submitting: false,
                error: err instanceof Error ? err.message : String(err),
              },
            },
            error: `Errore fallback sendMessage: ${err instanceof Error ? err.message : err}`,
          }));
        }
      },

      // Manutenzione fine sessione: trigger skill os-ottimizzatore via POST
      // /api/skills/run (streaming SSE). Conv. 47+48 enforcement.
      //
      // v0.13.4 Bug A fix (Antonio feedback 26/05): se l'utente sta gia' in una
      // conversation attiva, l'os-ottimizzatore deve scrivere NELLA STESSA chat
      // + emettere ASK_USER_QUESTION finale "Applica ottimizzazione?". Pre-fix:
      // creava sempre nuova chat "Skill os-ottimizzatore" + auto-navigate. Il
      // backend (skills_routes.py:142) accetta gia' payload.conversation_id
      // opzionale (riusa esistente vs crea nuova): basta passarlo qui.
      endSession: async (params) => {
        const vaultPath = params?.vaultPath;
        // v0.13.4 Conv. 48 SSOT: passa la conv attiva al backend per riuso.
        const currentConvId = get().activeConversationId;
        let conversationId: string | null = currentConvId;
        let eventsCount = 0;
        const buffer: string[] = [];
        let errorMessage: string | null = null;

        try {
          // Lazy import fetchWithRetry per robustezza race startup sidecar (v1.0.1 pattern).
          const { fetchWithRetry } = await import("@/api/retry");
          const backendUrl =
            import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";

          const res = await fetchWithRetry(`${backendUrl}/api/skills/run`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Accept: "text/event-stream",
            },
            body: JSON.stringify({
              name: "os-ottimizzatore",
              vault_path: vaultPath,
              // v0.13.4 Bug A: passa la conversation attiva al backend.
              // skills_routes.py riusa la conv esistente invece di crearne nuova.
              conversation_id: currentConvId,
              context: {
                trigger: "session_end",
                // v0.13.4 Bug A: interactive=true istruisce la skill os-ottimizzatore
                // a emettere ASK_USER_QUESTION widget finale "Applica? Si/No" invece
                // di chiusura testuale "rispondi 'si'".
                interactive: true,
              },
            }),
            maxRetries: 3,
            baseMs: 500,
          });

          if (!res.ok) {
            const body = await res.text().catch(() => "");
            throw new Error(`HTTP ${res.status} ${body}`);
          }

          // Backend ritorna X-Conversation-Id (vedi skills_routes.py:200).
          conversationId = res.headers.get("X-Conversation-Id");

          if (!res.body) {
            throw new Error("Response senza body SSE");
          }

          // Parse SSE eventi
          const reader = res.body.getReader();
          const decoder = new TextDecoder("utf-8");
          let parseBuffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            parseBuffer += decoder.decode(value, { stream: true });

            let nlIndex = parseBuffer.indexOf("\n\n");
            while (nlIndex !== -1) {
              const ev = parseBuffer.slice(0, nlIndex);
              parseBuffer = parseBuffer.slice(nlIndex + 2);
              const dataLine = ev.split("\n").find((l) => l.startsWith("data: "));
              if (dataLine) {
                const payload = dataLine.slice(6);
                if (payload === "[DONE]") break;
                try {
                  const parsed: { kind: string; data: Record<string, unknown> } =
                    JSON.parse(payload);
                  eventsCount += 1;
                  if (parsed.kind === "text_delta") {
                    const chunk = String(parsed.data?.text ?? "");
                    if (chunk) buffer.push(chunk);
                  } else if (parsed.kind === "error") {
                    errorMessage = String(
                      (parsed.data as { message?: string })?.message ??
                        "errore stream skill",
                    );
                  }
                } catch {
                  // chunk malformato: ignora
                }
              }
              nlIndex = parseBuffer.indexOf("\n\n");
            }
          }

          // v0.13.4 Bug A fix: refresh lista + (re-)selezione della conv
          // attiva. Se conversation_id e' stata riusata dal backend (Bug A
          // fix path), l'utente resta nella STESSA chat e vedra' la sintesi
          // os-ottimizzatore + AskQuestion widget aggiunti in append. Se il
          // backend ha creato una nuova conv (path legacy quando endSession
          // viene chiamata senza activeConversationId), allora si auto-naviga
          // alla nuova come prima.
          const fetchedList = await get().fetchConversations({ silent: true });
          if (conversationId) {
            const exists = fetchedList.some((c) => c.id === conversationId);
            if (exists && conversationId !== currentConvId) {
              // Path legacy: backend ha creato nuova conv (currentConvId era null).
              get().setActiveConversation(conversationId);
            } else if (exists && conversationId === currentConvId) {
              // Path v0.13.4 (Bug A fix): backend ha riusato la conv attiva.
              // Re-fetch dei messaggi per mostrare gli append (sintesi + widget).
              await get().setActiveConversation(conversationId);
            }
          }

          return {
            success: errorMessage === null,
            conversationId,
            eventsCount,
            errorMessage,
          };
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          return {
            success: false,
            conversationId,
            eventsCount,
            errorMessage: message,
          };
        }
      },

      clearError: () => set({ error: null }),

      // v0.8.1 hook wiki ingest: scarta la proposta (utente clicca "X" sulla card).
      // La card non si renderizza piu' per quel message_id finche la sessione e'
      // attiva (la flag persiste in localStorage via zustand persist).
      dismissWikiIngestProposal: (messageId) => {
        set((s) => {
          const { [messageId]: _removed, ...restProposals } = s.wikiIngestProposals;
          return {
            wikiIngestProposals: restProposals,
            wikiIngestDismissed: { ...s.wikiIngestDismissed, [messageId]: true },
          };
        });
      },

      // v0.8.1 hook wiki ingest: rimuovi la proposta DOPO una confirm OK.
      // Non marca come dismissed: se in futuro la stessa conversation triggera
      // un'altra proposta per lo stesso message, la mostriamo di nuovo.
      removeWikiIngestProposal: (messageId) => {
        set((s) => {
          const { [messageId]: _removed, ...restProposals } = s.wikiIngestProposals;
          return { wikiIngestProposals: restProposals };
        });
      },

      // v1.0.2 fix sidebar visibility + v0.8.1 fix auto-navigation: pull esplicito
      // + merge con state corrente. Pattern Conv. 47/48: backend single source of
      // truth. Auto-detect nuove "Configurazione iniziale del vault X" → toast +
      // auto-select aggressivo (rispettando solo `lastAutoNavigated` per non
      // ri-naviare se l'utente ha gia` cambiato chat dopo un'auto-nav precedente).
      //
      // v0.8.1 Goal A: il bug "non parte da sola, devo selezionare da Recenti"
      // era causato da check troppo restrittivo (`!state.activeConversationId`).
      // Quando vault.registered triggera, l'utente vede welcome screen ma puo'
      // gia` aver visitato qualche chat → activeConversationId non null. Nuova
      // logica: auto-select se la conv welcome e' diversa da quella gia` auto-
      // naviata (flag lastAutoNavigated) E utente NON sta streaming (no preempt).
      fetchConversations: async (opts) => {
        const silent = opts?.silent ?? true;
        try {
          const list = await apiClient.listConversations();
          const state = get();
          const known = state.knownConversationIds;

          // Detect nuove conversations comparse dal backend post-vault.registered
          // o post-setup.completed (v0.13.2 DEV-AUTO-OPTIMIZER).
          const newOnes = list.filter((c) => !known.has(c.id) && !state.conversations[c.id]);
          const configWelcome = newOnes.find((c) =>
            c.title.startsWith("Configurazione iniziale del vault"),
          );
          const optimizerWelcome = newOnes.find((c) =>
            c.title.startsWith("Ottimizzazione iniziale del vault"),
          );
          // Priorita: optimizer ha priorita su config welcome quando entrambe
          // compaiono nello stesso polling (caso post-setup completion).
          const welcomeCandidate = optimizerWelcome ?? configWelcome;

          // Merge: backend è autoritativo per shape/title/updated_at; preserva messagesByConv
          const newConvs: Record<string, ConversationItem> = { ...state.conversations };
          for (const conv of list) {
            newConvs[conv.id] = conv;
          }

          const nextKnown = new Set<string>(known);
          for (const conv of list) nextKnown.add(conv.id);

          // v0.8.1 fix Bug auto-nav: auto-select aggressivo per "Configurazione
          // iniziale" e "Ottimizzazione iniziale" (v0.13.2 DEV-AUTO-OPTIMIZER).
          // Condizioni di blocco esplicite:
          //   - NON e' welcomeCandidate (no candidate)
          //   - utente sta streaming (don't preempt)
          //   - conv welcome e' la STESSA gia` auto-naviata prima
          //     (lastAutoNavigated → rispetta scelta utente di andare altrove)
          const shouldAutoSelect =
            !!welcomeCandidate &&
            !state.isStreaming &&
            state.lastAutoNavigated !== welcomeCandidate.id;

          set({
            conversations: newConvs,
            knownConversationIds: nextKnown,
            lastFetchAt: Date.now(),
          });

          const activeId = get().activeConversationId;
          if (activeId) {
            const activeConv = newConvs[activeId];
            if (activeConv) {
              const modeStore = useChatModeStore.getState();
              const nextMode = activeConv.agent_mode ?? "auto";
              if (nextMode === "yolo" && !modeStore.yoloAcknowledged) {
                if (modeStore.mode !== "auto") {
                  modeStore.setMode("auto");
                }
              } else if (modeStore.mode !== nextMode) {
                modeStore.setMode(nextMode);
              }
            }
          }

          // Se auto-select scattato → chiama setActiveConversation (NON set diretto)
          // così triggera anche il fetch messaggi della conversation appena creata
          // (Conv. 48: backend single source of truth dei messaggi). Inoltre marca
          // lastAutoNavigated per non ri-naviare al prossimo polling (5s).
          if (shouldAutoSelect && welcomeCandidate) {
            get().setActiveConversation(welcomeCandidate.id);
            set({ lastAutoNavigated: welcomeCandidate.id });
          }

          // Toast notifica nuova conversation di configurazione/ottimizzazione
          // (lazy import sonner per evitare overhead bundle in chunk store).
          if (!silent && welcomeCandidate) {
            const { toast } = await import("sonner");
            const isOptimizer = welcomeCandidate === optimizerWelcome;
            const toastMsg = isOptimizer
              ? `Ottimizzazione del vault avviata: "${welcomeCandidate.title}"`
              : `Configurazione vault completata: nuova conversazione "${welcomeCandidate.title}"`;
            toast.success(toastMsg, {
              duration: 6000,
              action: shouldAutoSelect
                ? undefined
                : {
                    label: "Apri",
                    onClick: () => {
                      get().setActiveConversation(welcomeCandidate.id);
                      set({ lastAutoNavigated: welcomeCandidate.id });
                    },
                  },
            });
          }

          return list;
        } catch (err) {
          // Best-effort silent: il polling non deve generare toast errore ogni 5s.
          // Surface solo via state.error per debug.
          set({
            error: `Errore fetch conversations: ${err instanceof Error ? err.message : err}`,
          });
          return [];
        }
      },
    }),
    {
      name: "sco-chat",
      version: 2, // v0.7.2: migration purge stub-* conversations from localStorage
      migrate: (persistedState: unknown, version: number) => {
        if (version < 2) {
          // Rimuove le 5 conversations stub-* hardcoded pre-v0.7.2 dal localStorage
          // WebView2. Senza migrate restavano persisted post-upgrade in-place anche
          // se STUB_CONVERSATIONS adesso e' vuoto.
          const state = persistedState as {
            conversations?: Record<string, { id?: string }>;
            messagesByConv?: Record<string, unknown>;
            activeConversationId?: string | null;
          };
          if (state.conversations) {
            const filtered: Record<string, { id?: string }> = {};
            for (const [id, conv] of Object.entries(state.conversations)) {
              if (!id.startsWith("stub-")) {
                filtered[id] = conv;
              }
            }
            state.conversations = filtered;
          }
          if (
            state.activeConversationId &&
            state.activeConversationId.startsWith("stub-")
          ) {
            state.activeConversationId = null;
          }
        }
        return persistedState;
      },
      // NB v1.0.2: knownConversationIds (Set) NON va in localStorage (no JSON
      // serializzabile + comunque ricostruito dal primo fetchConversations al mount).
      // lastFetchAt non persiste per forzare refresh ogni cold start.
      // v0.8.1: lastAutoNavigated persiste per non ri-naviare al cold start su
      // conversation gia` viste in sessione precedente (rispetta scelta utente).
      partialize: (s) => ({
        conversations: s.conversations,
        messagesByConv: s.messagesByConv,
        activeConversationId: s.activeConversationId,
        // v1.0.2: persist inlineAskAnswers per non perdere selezione widget
        // al reload (carry-over finche backend non cabla endpoint dedicato e
        // restituisce stato widget come parte del payload messaggio).
        inlineAskAnswers: s.inlineAskAnswers,
        lastAutoNavigated: s.lastAutoNavigated,
        // v0.8.1 wiki ingest dismissed: persiste per non re-mostrare la card
        // sui messaggi che l'utente ha gia` scartato. Le proposals vere NON
        // vengono persistite (sono effimere, rigenerate al prossimo stream).
        wikiIngestDismissed: s.wikiIngestDismissed,
      }),
    },
  ),
);

