// SCO Compliance OS — chat store Zustand 5 con persistenza conversations + messages
import { create } from "zustand";
import { persist } from "zustand/middleware";

import type {
  ConversationItem,
  MessageItem,
  AskUserQuestionWidget,
} from "@/types/api";
import { apiClient } from "@/api/client";

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

// Stub mock per la sidebar iniziale (5 voci) — verranno sostituite dal fetch reale
const STUB_CONVERSATIONS: ConversationItem[] = [
  {
    id: "stub-1",
    title: "Audit ISO 27001 — Don Calabria",
    vault_id: null,
    created_at: "2026-05-19T09:00:00Z",
    updated_at: "2026-05-21T14:30:00Z",
    message_count: 12,
  },
  {
    id: "stub-2",
    title: "Gap analysis NIS 2 — TecnoSys",
    vault_id: null,
    created_at: "2026-05-20T11:15:00Z",
    updated_at: "2026-05-21T10:00:00Z",
    message_count: 8,
  },
  {
    id: "stub-3",
    title: "Procedura sanitaria — Romolo Hospital",
    vault_id: null,
    created_at: "2026-05-20T16:42:00Z",
    updated_at: "2026-05-20T18:10:00Z",
    message_count: 5,
  },
  {
    id: "stub-4",
    title: "Risk assessment cloud — Akrea",
    vault_id: null,
    created_at: "2026-05-21T08:30:00Z",
    updated_at: "2026-05-21T09:45:00Z",
    message_count: 3,
  },
  {
    id: "stub-5",
    title: "Verbale CDA AKREA 19/02/2026",
    vault_id: null,
    created_at: "2026-05-18T14:00:00Z",
    updated_at: "2026-05-18T16:30:00Z",
    message_count: 15,
  },
];

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
      partialize: (s) => ({
        conversations: s.conversations,
        messagesByConv: s.messagesByConv,
        activeConversationId: s.activeConversationId,
      }),
    },
  ),
);
