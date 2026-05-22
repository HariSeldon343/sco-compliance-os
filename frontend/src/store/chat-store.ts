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
        const { activeConversationId, createConversation } = get();
        const convId = activeConversationId ?? createConversation();
        const now = new Date().toISOString();

        // Append messaggio utente
        const userMsg: MessageItem = {
          id: `msg-${Date.now()}-u`,
          conversation_id: convId,
          role: "user",
          content: text,
          created_at: now,
        };
        set((s) => ({
          messagesByConv: {
            ...s.messagesByConv,
            [convId]: [...(s.messagesByConv[convId] ?? []), userMsg],
          },
          isStreaming: true,
          error: null,
        }));

        try {
          // Stream backend (stub: chiamata fittizia con delay)
          // TODO: collegare a /api/chat/stream SSE reale lato backend.
          await apiClient.sendChatMessage({
            conversation_id: convId,
            content: text,
            onChunk: (chunk) => {
              // Hook futuro: aggiorna messaggio assistant in streaming
              void chunk;
            },
          });

          const assistantMsg: MessageItem = {
            id: `msg-${Date.now()}-a`,
            conversation_id: convId,
            role: "assistant",
            content:
              "Backend non collegato — questo è un messaggio di prova della UI. Il messaggio reale arriverà dal backend FastAPI quando l'endpoint /api/chat/stream sarà attivo.",
            created_at: new Date().toISOString(),
          };
          set((s) => ({
            messagesByConv: {
              ...s.messagesByConv,
              [convId]: [...(s.messagesByConv[convId] ?? []), assistantMsg],
            },
            isStreaming: false,
          }));
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Errore sconosciuto";
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
