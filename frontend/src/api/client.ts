// SCO Compliance OS — API client verso backend FastAPI localhost:7800
// Conv. 48 enforcement: il backend è single source of truth per stato widget;
// il frontend deduce sempre lo stato dal fetch, mai dalla memoria React optimistic.

import type {
  ConversationItem,
  HotnessItem,
  IntegrationItem,
  MessageItem,
  TreeChunkItem,
  TreeLevel,
  TreeStatsResponse,
  TreeSummaryItem,
  TreeSummaryItemV2,
  VaultItem,
  WikiCategory,
  WikiFileDetail,
  WikiGraphResponse,
  WikiIngestConfirmRequest,
  WikiIngestConfirmResponse,
  WikiIngestProposal,
  WikiListResponse,
  WikiStatsResponse,
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
  // Conv. 47 fix v0.4.0: endpoint backend è /api/chat/conversations (vedi chat_routes.py:164),
  // l'app puntava erroneamente a /api/conversations facendo fallire sidebar history.
  async listConversations(): Promise<ConversationItem[]> {
    return request<ConversationItem[]>("/api/chat/conversations");
  },
  async getConversationMessages(id: string): Promise<MessageItem[]> {
    return request<MessageItem[]>(`/api/chat/conversations/${id}/messages`);
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

  /**
   * Invia la scelta dell'utente in risposta a un widget AskUserQuestion
   * emesso inline dal backend (tag `<ASK_USER_QUESTION>` nel content del
   * messaggio assistant, vedi `lib/parseInlineWidgets.ts`).
   *
   * Endpoint: `POST /api/chat/answer-ask-user-question`. Body:
   * `{conversation_id, message_id, option_value}`. Risposta attesa:
   * 2xx → vuoto o `{status: "ok"}`.
   *
   * IMPORTANTE (bug v1.0.2): l'endpoint backend NON e' ancora cablato al
   * 2026-05-24. La chiamata HTTP fallira' con 404. Il caller deve gestire
   * il fallback inviando la risposta come messaggio utente normale via
   * `sendChatMessage`. Vedi `useChatStore.answerInlineAskQuestion`.
   *
   * Una volta cablato lato backend, questo metodo diventera' il path
   * primario senza modifiche alla firma.
   */
  async answerAskUserQuestion(params: {
    conversation_id: string;
    message_id: string;
    option_value: string;
  }): Promise<void> {
    const res = await fetch(`${BACKEND_URL}/api/chat/answer-ask-user-question`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new ApiError(
        res.status,
        "answer_ask_user_question_error",
        `HTTP ${res.status} ${body || "answer endpoint failed"}`,
      );
    }
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
  // Conv. 47 fix v0.4.0: endpoint backend è /api/vault/list (singolare, vedi vault_routes.py:104),
  // l'app puntava erroneamente a /api/vaults plurale facendo fallire VaultScreen.
  async listVaults(): Promise<VaultItem[]> {
    return request<VaultItem[]>("/api/vault/list");
  },

  // ---- Integrations ----
  async listIntegrations(): Promise<IntegrationItem[]> {
    return request<IntegrationItem[]>("/api/integrations");
  },

  // ---- Memory Tree (Wave 2 OpenHuman replica) ----
  // Backend single source of truth: tabella `summaries` (migration 0002).
  // Endpoint distinto da `/tree` legacy per evitare breaking changes contratto.
  async listTreeSummaries(params: {
    source?: string;
    level?: TreeLevel;
    topic?: string;
    day?: string; // ISO YYYY-MM-DD
    limit?: number;
  } = {}): Promise<TreeSummaryItem[]> {
    const search = new URLSearchParams();
    if (params.source) search.set("source", params.source);
    if (params.level !== undefined) search.set("level", String(params.level));
    if (params.topic) search.set("topic", params.topic);
    if (params.day) search.set("day", params.day);
    if (params.limit !== undefined) search.set("limit", String(params.limit));
    const qs = search.toString();
    const path = qs
      ? `/api/memory/tree-summaries?${qs}`
      : "/api/memory/tree-summaries";
    return request<TreeSummaryItem[]>(path);
  },

  // Top-N chunks per hotness con decay 0.95/day applicato lato backend.
  async getTopHotness(params: { n?: number } = {}): Promise<HotnessItem[]> {
    const n = params.n ?? 20;
    return request<HotnessItem[]>(`/api/memory/hotness/top?n=${n}`);
  },

  // ---- Voice (STT + TTS, on-device) ----
  // Privacy hard requirement: nessun dato lascia il dispositivo.
  // Pattern Conv. 47 single source of truth: tooling + modelli vivono lato
  // backend (~/.sco-compliance-os/voice-*). Frontend interroga via /status.

  /** STT: trascrive audio bytes (WebM Opus / WAV / MP3 / M4A) in testo. */
  async transcribeAudio(params: {
    audio: Blob;
    language?: string;
    filename?: string;
  }): Promise<{ text: string; duration_ms: number; model: string; language: string }> {
    const { audio, language = "it", filename = "recording.webm" } = params;
    const form = new FormData();
    form.append("audio", audio, filename);
    form.append("language", language);

    const res = await fetch(`${BACKEND_URL}/api/voice/transcribe`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      let code = "transcribe_error";
      let message = `HTTP ${res.status}`;
      try {
        const parsed = JSON.parse(body);
        code = parsed.code ?? code;
        message = parsed.detail ?? parsed.message ?? message;
      } catch {
        message = body || message;
      }
      throw new ApiError(res.status, code, message);
    }
    return res.json() as Promise<{
      text: string;
      duration_ms: number;
      model: string;
      language: string;
    }>;
  },

  /** TTS: sintetizza testo in WAV blob. */
  async synthesizeText(params: {
    text: string;
    voice?: string;
  }): Promise<Blob> {
    const { text, voice = "it_IT-paola-medium" } = params;
    const res = await fetch(`${BACKEND_URL}/api/voice/synthesize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice }),
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new ApiError(res.status, "synthesize_error", body || `HTTP ${res.status}`);
    }
    return res.blob();
  },

  /** Lista voci TTS disponibili (con flag installed). */
  async listVoices(): Promise<{
    voices: Array<{
      id: string;
      language: string;
      size_mb: string;
      installed: string;
    }>;
  }> {
    return request("/api/voice/voices");
  },

  /** Diagnostica tooling voice (binari + modelli). */
  async voiceStatus(): Promise<{
    stt: { ffmpeg: boolean; whisper_cli: boolean; model_base: boolean; model_base_en: boolean };
    tts: { piper_bin: boolean; voice_it_paola: boolean; voice_en_libritts: boolean };
  }> {
    return request("/api/voice/status");
  },

  // ---- Wiki SCO (ALPHA v0.4.0) — endpoint nuovi v0.6.0+ ----
  // 5 categorie: sources / entities / concepts / synthesis / glossari.
  // Risoluzione vault attivo lato backend (registry sco-first).
  // Pattern Conv. 47: shape stabile, mai duplicare schema frontmatter.

  /** Conteggi per categoria nel vault attivo. */
  async getWikiStats(params: { vault_path?: string } = {}): Promise<WikiStatsResponse> {
    const search = new URLSearchParams();
    if (params.vault_path) search.set("vault_path", params.vault_path);
    const qs = search.toString();
    return request<WikiStatsResponse>(qs ? `/api/wiki/stats?${qs}` : "/api/wiki/stats");
  },

  /** Lista schede wiki/sources/ del vault attivo. */
  async listWikiSources(
    params: {
      vault_path?: string;
      ambito_canonico?: string;
      status?: string;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<WikiListResponse> {
    return request<WikiListResponse>(buildWikiQuery("/api/wiki/sources", params));
  },

  /** Lista entity wiki/entities/ con filtri tipizzati Ondate 2-3. */
  async listWikiEntities(
    params: {
      vault_path?: string;
      entity_type?: string;
      ambito_canonico?: string;
      status?: string;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<WikiListResponse> {
    return request<WikiListResponse>(buildWikiQuery("/api/wiki/entities", params));
  },

  /** Lista concepts wiki/concepts/ del vault attivo. */
  async listWikiConcepts(
    params: {
      vault_path?: string;
      ambito_canonico?: string;
      status?: string;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<WikiListResponse> {
    return request<WikiListResponse>(buildWikiQuery("/api/wiki/concepts", params));
  },

  /** Lista synthesis wiki/synthesis/ del vault attivo. */
  async listWikiSynthesis(
    params: {
      vault_path?: string;
      ambito_canonico?: string;
      status?: string;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<WikiListResponse> {
    return request<WikiListResponse>(buildWikiQuery("/api/wiki/synthesis", params));
  },

  /** Lista glossari wiki/glossari/ del vault attivo. */
  async listWikiGlossari(
    params: {
      vault_path?: string;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<WikiListResponse> {
    return request<WikiListResponse>(buildWikiQuery("/api/wiki/glossari", params));
  },

  /** Singolo file wiki con frontmatter + body completo. */
  async getWikiFile(
    category: WikiCategory,
    slug: string,
    params: { vault_path?: string } = {},
  ): Promise<WikiFileDetail> {
    const search = new URLSearchParams();
    if (params.vault_path) search.set("vault_path", params.vault_path);
    const qs = search.toString();
    const base = `/api/wiki/${encodeURIComponent(category)}/${encodeURIComponent(slug)}`;
    return request<WikiFileDetail>(qs ? `${base}?${qs}` : base);
  },

  /** Grafo vault force-directed: nodi (entity + clienti) + edges (relationships + applica). */
  async getWikiGraph(
    params: {
      vault_path?: string;
      include_clienti?: boolean;
      include_orphans?: boolean;
      entity_type?: string;
      ambito_canonico?: string;
    } = {},
  ): Promise<WikiGraphResponse> {
    const search = new URLSearchParams();
    if (params.vault_path) search.set("vault_path", params.vault_path);
    if (params.include_clienti !== undefined)
      search.set("include_clienti", String(params.include_clienti));
    if (params.include_orphans !== undefined)
      search.set("include_orphans", String(params.include_orphans));
    if (params.entity_type) search.set("entity_type", params.entity_type);
    if (params.ambito_canonico)
      search.set("ambito_canonico", params.ambito_canonico);
    const qs = search.toString();
    return request<WikiGraphResponse>(
      qs ? `/api/wiki/graph?${qs}` : "/api/wiki/graph",
    );
  },

  // ---- Memory Tree bucket-seal Fase 4 (DEV-MEMORY-TREE v0.6.0) ----
  // Endpoint nuovi distinti da `/tree-summaries` legacy Wave 1 (tabella `summaries`
  // mai migrata in v0.6.0+). Niente HTTP 500 "no such table".

  /** Lista chunks Memory Tree con filtri bucket-seal. */
  async getMemoryTreeChunks(
    params: {
      source_kind?: string;
      status?: string;
      source_id?: string;
      owner?: string;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<TreeChunkItem[]> {
    const search = new URLSearchParams();
    if (params.source_kind) search.set("source_kind", params.source_kind);
    if (params.status) search.set("status", params.status);
    if (params.source_id) search.set("source_id", params.source_id);
    if (params.owner) search.set("owner", params.owner);
    if (params.limit !== undefined) search.set("limit", String(params.limit));
    if (params.offset !== undefined) search.set("offset", String(params.offset));
    const qs = search.toString();
    return request<TreeChunkItem[]>(
      qs ? `/api/memory/tree/chunks?${qs}` : "/api/memory/tree/chunks",
    );
  },

  /** Lista summaries L1/L2/L3 Memory Tree (Fase 4 v0.6.0 nuovo schema). */
  async getMemoryTreeSummariesNew(
    params: {
      tree_kind?: string;
      tree_id?: string;
      level?: number;
      owner?: string;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<TreeSummaryItemV2[]> {
    const search = new URLSearchParams();
    if (params.tree_kind) search.set("tree_kind", params.tree_kind);
    if (params.tree_id) search.set("tree_id", params.tree_id);
    if (params.level !== undefined) search.set("level", String(params.level));
    if (params.owner) search.set("owner", params.owner);
    if (params.limit !== undefined) search.set("limit", String(params.limit));
    if (params.offset !== undefined) search.set("offset", String(params.offset));
    const qs = search.toString();
    return request<TreeSummaryItemV2[]>(
      qs ? `/api/memory/tree/summaries?${qs}` : "/api/memory/tree/summaries",
    );
  },

  /** Statistiche aggregate Memory Tree bucket-seal (count by status + source_kind). */
  async getMemoryTreeStats(): Promise<TreeStatsResponse> {
    return request<TreeStatsResponse>("/api/memory/tree/stats");
  },

  // ---- Wiki Ingest Proposal (v0.8.1 hook chat -> wiki) ----
  // POST /api/wiki/ingest/proposal: chiama analyze_message_for_wiki_ingest
  // lato backend. Idempotente (proposal_id deterministico).
  // POST /api/wiki/ingest/confirm: scrive il file nella destinazione scelta.

  /**
   * Analizza un messaggio assistant + i suoi allegati / URL / search results
   * e restituisce la proposta classificata per ingest wiki.
   *
   * Tipicamente NON serve invocarlo direttamente: l'evento SSE
   * `wiki_ingest_proposal` arriva automaticamente alla fine dello stream
   * chat e contiene gia la WikiIngestProposal. Questo endpoint resta
   * disponibile per re-fetch (cache miss, refresh manuale).
   */
  async analyzeWikiIngestProposal(payload: {
    conversation_id: string;
    message_id: string;
    message_content?: string;
    attachments?: Array<{
      path: string;
      mime_type?: string;
      title?: string;
      content_preview?: string;
    }>;
    search_results?: Array<{
      url: string;
      title: string;
      snippet?: string;
    }>;
  }): Promise<WikiIngestProposal> {
    const res = await fetch(`${BACKEND_URL}/api/wiki/ingest/proposal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new ApiError(
        res.status,
        "wiki_ingest_proposal_error",
        `HTTP ${res.status} ${body}`,
      );
    }
    return (await res.json()) as WikiIngestProposal;
  },

  /**
   * Conferma la proposta e crea il file wiki nella destinazione scelta.
   * L'utente puo' aver modificato destination / slug / frontmatter / body_md
   * rispetto al suggerimento iniziale (single source of truth Conv. 47).
   */
  async confirmWikiIngest(
    payload: WikiIngestConfirmRequest,
    params: { vault_path?: string } = {},
  ): Promise<WikiIngestConfirmResponse> {
    const search = new URLSearchParams();
    if (params.vault_path) search.set("vault_path", params.vault_path);
    const qs = search.toString();
    const url = qs
      ? `${BACKEND_URL}/api/wiki/ingest/confirm?${qs}`
      : `${BACKEND_URL}/api/wiki/ingest/confirm`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new ApiError(
        res.status,
        "wiki_ingest_confirm_error",
        `HTTP ${res.status} ${body}`,
      );
    }
    return (await res.json()) as WikiIngestConfirmResponse;
  },
};

/** Builder URL query con stripping campi undefined/null (helper interno wiki endpoints). */
function buildWikiQuery(
  base: string,
  params: Record<string, string | number | undefined>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `${base}?${qs}` : base;
}
