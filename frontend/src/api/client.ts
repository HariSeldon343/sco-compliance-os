// SCO Compliance OS — API client verso backend FastAPI localhost:7800
// Conv. 48 enforcement: il backend è single source of truth per stato widget;
// il frontend deduce sempre lo stato dal fetch, mai dalla memoria React optimistic.

import type {
  ConversationItem,
  IntegrationItem,
  MessageItem,
  VaultItem,
} from "@/types/api";

// Backend URL: env Vite oppure default localhost (Tauri dev + bundle)
const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";

/** Errore HTTP arricchito */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Wrapper fetch con timeout + parsing JSON + error handling */
async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = 30_000,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${BACKEND_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
      },
    });

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      let code = "http_error";
      let message = `HTTP ${res.status}`;
      try {
        const parsed = JSON.parse(body);
        code = parsed.code ?? code;
        message = parsed.message ?? message;
      } catch {
        // body non JSON, lascia i default
      }
      throw new ApiError(res.status, code, message);
    }

    return (await res.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

export const apiClient = {
  // ---- Conversations ----
  async listConversations(): Promise<ConversationItem[]> {
    return request<ConversationItem[]>("/api/conversations");
  },
  async getConversationMessages(id: string): Promise<MessageItem[]> {
    return request<MessageItem[]>(`/api/conversations/${id}/messages`);
  },

  // ---- Conversations CRUD ----
  async createConversation(title?: string): Promise<ConversationItem> {
    const res = await fetch(`${BACKEND_URL}/api/chat/conversations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(title ? { title } : {}),
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new ApiError(res.status, "create_conv_error", `HTTP ${res.status} ${body}`);
    }
    return res.json() as Promise<ConversationItem>;
  },

  // ---- Chat stream (SSE) ----
  // Backend field name è "message" (non "content"). Eventi SSE backend hanno
  // formato {kind, data, seq} (NON {type, delta} come ChatStreamChunk legacy).
  async sendChatMessage(params: {
    conversation_id: string;
    message: string;
    model_slug?: string;
    onEvent?: (event: { kind: string; data: Record<string, unknown>; seq: number }) => void;
  }): Promise<void> {
    const { conversation_id, message, model_slug, onEvent } = params;
    const res = await fetch(`${BACKEND_URL}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ conversation_id, message, model_slug }),
    }).catch((err) => {
      throw new ApiError(0, "network", `Backend non raggiungibile: ${err}`);
    });

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new ApiError(res.status, "stream_error", `HTTP ${res.status} ${body}`);
    }

    if (!res.body) {
      throw new ApiError(0, "no_body", "Response senza body SSE");
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let nlIndex = buffer.indexOf("\n\n");
      while (nlIndex !== -1) {
        const ev = buffer.slice(0, nlIndex);
        buffer = buffer.slice(nlIndex + 2);
        const dataLine = ev.split("\n").find((l) => l.startsWith("data: "));
        if (dataLine && onEvent) {
          const payload = dataLine.slice(6);
          if (payload === "[DONE]") return;
          try {
            onEvent(JSON.parse(payload));
          } catch {
            // chunk malformato: ignora
          }
        }
        nlIndex = buffer.indexOf("\n\n");
      }
    }
  },

  // ---- Vaults ----
  async listVaults(): Promise<VaultItem[]> {
    return request<VaultItem[]>("/api/vaults");
  },

  // ---- Integrations ----
  async listIntegrations(): Promise<IntegrationItem[]> {
    return request<IntegrationItem[]>("/api/integrations");
  },
};
