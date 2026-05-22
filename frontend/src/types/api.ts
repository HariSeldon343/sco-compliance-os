// SCO Compliance OS — TypeScript types contratto backend /api
// Pattern Conv. 48: stato widget vive in DB lato backend, frontend lo riceve via GET.

/** Identificatore opaco assegnato dal backend (UUID v4) */
export type Id = string;

/** Ruolo del messaggio nella conversazione */
export type MessageRole = "user" | "assistant" | "system" | "tool";

/** Tool call inline (riferimento operazione che l'agente ha eseguito) */
export interface ToolCallItem {
  id: Id;
  tool_name: string;
  // Riassunto leggibile: "ha letto file.md", "ha eseguito grep su src/"
  display: string;
  status: "running" | "ok" | "error";
  error?: string | null;
}

/** Widget "domanda all'utente" cliccabile (Conv. 48 — payload persistito in DB) */
export interface AskUserQuestionWidget {
  prompt: string;
  options: Array<{
    id: string;
    label: string;
    description?: string;
  }>;
  // Stato del widget: aperto (clickabile), risposto (chiuso), scaduto
  state: "open" | "answered" | "expired";
  answer_id?: string | null;
}

/** Messaggio in conversazione */
export interface MessageItem {
  id: Id;
  conversation_id: Id;
  role: MessageRole;
  content: string;
  // Inline tool calls (read, grep, write, ...)
  tool_calls?: ToolCallItem[] | null;
  // Widget AskUserQuestion persistito (Conv. 48)
  ask_user_question?: AskUserQuestionWidget | null;
  created_at: string; // ISO 8601
}

/** Conversazione (intestazione + metadata) */
export interface ConversationItem {
  id: Id;
  title: string;
  vault_id: Id | null;
  created_at: string;
  updated_at: string;
  // Numero messaggi (denormalizzato per UI sidebar)
  message_count: number;
}

/** Vault registrato (cartella Obsidian collegata) */
export interface VaultItem {
  id: Id;
  name: string;
  path: string; // path assoluto filesystem
  is_active: boolean;
  // Stato sync (ultimo controllo)
  last_sync?: string | null;
  file_count?: number | null;
}

/** Integrazione esterna (Gmail, Calendar, Drive, Slack, GitHub) */
export interface IntegrationItem {
  id: Id;
  provider: "gmail" | "google-calendar" | "google-drive" | "slack" | "github";
  display_name: string;
  status: "connected" | "disconnected" | "error";
  account_email?: string | null;
  last_used?: string | null;
}

/** Risposta standard endpoint /api/chat/stream (chunk SSE) */
export interface ChatStreamChunk {
  type:
    | "message_start"
    | "content_delta"
    | "tool_call"
    | "ask_user_question"
    | "message_end"
    | "error";
  message_id?: Id;
  delta?: string;
  tool_call?: ToolCallItem;
  ask_user_question?: AskUserQuestionWidget;
  error?: { code: string; message: string };
}
