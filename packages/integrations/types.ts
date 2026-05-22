/**
 * @sco/integrations — Shared TypeScript types
 *
 * Tipi condivisi fra frontend (Tauri WebView React) e backend (FastAPI sidecar).
 * Lato backend gli stessi tipi sono replicati in Pydantic models (`schemas.py`).
 *
 * SECURITY: i campi `access_token` e `refresh_token` NON devono MAI essere
 * serializzati verso il frontend. Vivono solo lato backend nel keyring OS.
 * Il frontend riceve solo `ConnectorStatus` + metadata pubblici.
 */

// ─────────────────────────────────────────────────────────────────────
// Connector metadata (pubblico, esposto al frontend)
// ─────────────────────────────────────────────────────────────────────

export type ConnectorCategory =
  | "email"
  | "calendar"
  | "storage"
  | "code"
  | "project_management"
  | "crm"
  | "communication"
  | "social"
  | "commerce"
  | "productivity";

export type OAuthProvider =
  | "google"
  | "slack"
  | "github"
  | "microsoft"
  | "dropbox"
  | "linkedin"
  | "atlassian"
  | "notion"
  | "hubspot"
  | "stripe";

export interface ConnectorMetadata {
  /** Slug univoco kebab-case (es. "gmail", "google_calendar", "github") */
  slug: string;
  /** Nome human-readable (es. "Gmail", "Google Calendar", "GitHub") */
  name: string;
  /** Categoria per raggruppamento UI */
  category: ConnectorCategory;
  /** URL icona (statica nel bundle o CDN) */
  icon_url: string;
  /** Descrizione breve (1-2 frasi) */
  description: string;
  /** Provider OAuth sottostante */
  oauth_provider: OAuthProvider;
  /** Scopes OAuth richiesti (es. ["gmail.readonly"]) */
  scopes_required: string[];
  /** Feature flags supportate dal connector */
  features: ConnectorFeature[];
}

export type ConnectorFeature =
  | "read_only"
  | "write"
  | "real_time"
  | "historical_fetch"
  | "search"
  | "attachments"
  | "webhooks";

// ─────────────────────────────────────────────────────────────────────
// Status (esposto al frontend per UI)
// ─────────────────────────────────────────────────────────────────────

export type ConnectorStatus =
  | "connected"
  | "disconnected"
  | "error"
  | "refreshing"
  | "pending_oauth";

export interface ConnectorStatusInfo {
  slug: string;
  status: ConnectorStatus;
  last_fetch_at: string | null; // ISO 8601
  last_error: string | null;
  scopes_granted: string[];
  expires_at: string | null;
}

// ─────────────────────────────────────────────────────────────────────
// OAuth session (BACKEND ONLY — mai esposto al frontend)
// ─────────────────────────────────────────────────────────────────────

/**
 * SECURITY CRITICAL: questa interfaccia rappresenta dati che vivono SOLO
 * nel backend, mai serializzati verso il frontend. La sua presenza qui è
 * solo per type-checking interno backend (es. mock test). Il filtering
 * verso il frontend è responsabilità di `schemas.py` Pydantic.
 */
export interface OAuthSession {
  provider: OAuthProvider;
  user_id: string;
  access_token: string; // NEVER serialized to frontend
  refresh_token: string; // NEVER serialized to frontend
  expires_at: string; // ISO 8601
  scopes_granted: string[];
  token_type: "Bearer" | "MAC";
}

// ─────────────────────────────────────────────────────────────────────
// Eventi telemetria connector
// ─────────────────────────────────────────────────────────────────────

export type ConnectorEventType =
  | "fetch_started"
  | "fetch_completed"
  | "fetch_error"
  | "token_refresh"
  | "token_refresh_failed"
  | "disconnect"
  | "oauth_started"
  | "oauth_completed";

export interface ConnectorEvent {
  type: ConnectorEventType;
  connector_slug: string;
  timestamp: string; // ISO 8601
  metadata: Record<string, unknown>;
}

// ─────────────────────────────────────────────────────────────────────
// Memory Tree ingestion (Conv. 43 Smart File Injection + Karpathy three-layer)
// ─────────────────────────────────────────────────────────────────────

export type MemoryChunkKind =
  | "email"
  | "calendar_event"
  | "file"
  | "message"
  | "pull_request"
  | "issue"
  | "commit"
  | "task"
  | "note";

export interface MemoryChunk {
  /** Identificatore univoco stabile generato dal connector (es. gmail_msg_id) */
  external_id: string;
  /** Slug del connector che ha prodotto il chunk */
  source_connector: string;
  /** Tipo logico del chunk */
  kind: MemoryChunkKind;
  /** Titolo / subject / nome file */
  title: string;
  /** Body / contenuto / preview testuale */
  body: string;
  /** Timestamp evento originale (es. data invio email) ISO 8601 */
  occurred_at: string;
  /** Timestamp ingest nel Memory Tree ISO 8601 */
  ingested_at: string;
  /** Metadata addizionali (mittente email, autore commit, etc.) */
  metadata: Record<string, unknown>;
  /** Tags per indicizzazione (vedi pattern Karpathy + Conv. 43) */
  tags: string[];
}
