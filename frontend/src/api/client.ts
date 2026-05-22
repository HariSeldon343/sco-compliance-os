// SCO Compliance OS — API client verso backend FastAPI localhost:7800
// Conv. 48 enforcement: il backend è single source of truth per stato widget;
// il frontend deduce sempre lo stato dal fetch, mai dalla memoria React optimistic.

import type {
  ChatStreamChunk,
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

/** Parser SSE incremental — accumula chunk e invoca onChunk per ogni evento "data:" */
async function consumeSSE(
  response: Response,
  onChunk: (chunk: ChatStreamChunk) => void,
): Promise<void> {
  if (!response.body) {
    throw new ApiError(0, "no_body", "Response senza body SSE");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  // Pattern Conv. 48 + lezione sco-agent-local Bug 2 SSE consumer fix:
  // mai consumare il buffer per linee complete senza prima accumulare le partials.
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    let nlIndex = buffer.indexOf("\n\n");
    while (nlIndex !== -1) {
      const event = buffer.slice(0, nlIndex);
      buffer = buffer.slice(nlIndex + 2);
      const dataLine = event
        .split("\n")
        .find((line) => line.startsWith("data: "));
      if (dataLine) {
        const payload = dataLine.slice(6);
        if (payload === "[DONE]") return;
        try {
          onChunk(JSON.parse(payload) as ChatStreamChunk);
        } catch {
          // chunk malformato: ignora ma non interrompere lo stream
        }
      }
      nlIndex = buffer.indexOf("\n\n");
    }
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

  // ---- Chat stream (SSE) ----
  async sendChatMessage(params: {
    conversation_id: string;
    content: string;
    onChunk?: (chunk: ChatStreamChunk) => void;
  }): Promise<void> {
    const { conversation_id, content, onChunk } = params;
    const res = await fetch(`${BACKEND_URL}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ conversation_id, content }),
    }).catch((err) => {
      // Backend non raggiungibile (sviluppo iniziale): fail silenzioso non bloccante
      throw new ApiError(0, "network", `Backend non raggiungibile: ${err}`);
    });

    if (!res.ok) {
      throw new ApiError(res.status, "stream_error", `HTTP ${res.status}`);
    }

    if (onChunk) await consumeSSE(res, onChunk);
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
