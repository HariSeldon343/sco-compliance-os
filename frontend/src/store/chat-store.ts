// SCO Compliance OS — chat store Zustand 5 con persistenza conversations + messages
import { create } from "zustand";
import { persist } from "zustand/middleware";

import type {
  ConversationItem,
  MessageItem,
  AskUserQuestionWidget,
} from "@/types/api";
import { apiClient } from "@/api/client";

// Permission mode UX dell'agente. Backend non ha ancora cablaggio param dedicato
// (carry-over v0.2.0): per ora vive solo lato frontend come preferenza utente
// persistita. Quando backend esporrà `permission_mode` su POST /api/chat/stream,
// basterà inoltrarlo dallo store. Pattern Conv. 47 single source of truth.
export type ChatMode = "plan" | "ask" | "auto";

interface ChatModeState {
  mode: ChatMode;
  setMode: (mode: ChatMode) => void;
}

export const useChatModeStore = create<ChatModeState>()(
  persist(
    (set) => ({
      // Default coerente con regola permanente GOAL-PERSISTENCE 20/05:
      // "auto" = procede in autonomia fino al completamento della condizione.
      mode: "auto",
      setMode: (mode) => set({ mode }),
    }),
    {
      name: "sco-chat-mode",
      partialize: (s) => ({ mode: s.mode }),
    },
  ),
);

interface ChatState {
  // Mappa conversation_id -> ConversationItem
  conversations: Record<string, ConversationItem>;
  // Mappa conversation_id -> array messaggi ordinati
  messagesByConv: Record<string, MessageItem[]>;
  activeConversationId: string | null;
  // Stato runtime
  isStreaming: boolean;
  error: string | null;

  // Actions
  setActiveConversation: (id: string | null) => void;
  createConversation: (title?: string) => string;
  deleteConversation: (id: string) => void;
  sendMessage: (text: string, attachments?: string[]) => Promise<void>;
  answerAskUserQuestion: (messageId: string, optionId: string) => void;
  clearError: () => void;
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

      setActiveConversation: (id) => set({ activeConversationId: id }),

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
        };
        set((s) => ({
          conversations: { ...s.conversations, [id]: conv },
          messagesByConv: { ...s.messagesByConv, [id]: [] },
          activeConversationId: id,
        }));
        return id;
      },

      deleteConversation: (id) => {
        set((s) => {
          const { [id]: _removed, ...rest } = s.conversations;
          const { [id]: _removedMsgs, ...restMsgs } = s.messagesByConv;
          return {
            conversations: rest,
            messagesByConv: restMsgs,
            activeConversationId:
              s.activeConversationId === id ? null : s.activeConversationId,
          };
        });
      },

      sendMessage: async (text, _attachments) => {
        const state = get();
        let convId = state.activeConversationId;
        const now = new Date().toISOString();

        // Se non c'è conversation attiva OPPURE è una stub (non backend) → crea backend
        const existing = convId ? state.conversations[convId] : null;
        const isBackendConv = existing && !existing.id.startsWith("stub-");

        if (!convId || !isBackendConv) {
          try {
            const newConv = await apiClient.createConversation();
            convId = newConv.id;
            set((s) => ({
              conversations: { ...s.conversations, [newConv.id]: newConv },
              messagesByConv: { ...s.messagesByConv, [newConv.id]: [] },
              activeConversationId: newConv.id,
            }));
          } catch (err) {
            set({
              error: `Errore creazione conversation: ${err instanceof Error ? err.message : err}`,
              isStreaming: false,
            });
            return;
          }
        }

        const conversationId: string = convId!;

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
              } else if (event.kind === "done") {
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

      clearError: () => set({ error: null }),
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
      partialize: (s) => ({
        conversations: s.conversations,
        messagesByConv: s.messagesByConv,
        activeConversationId: s.activeConversationId,
      }),
    },
  ),
);
