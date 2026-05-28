// SCO Compliance OS — TypeScript types contratto backend /api
// Pattern Conv. 48: stato widget vive in DB lato backend, frontend lo riceve via GET.

/** Identificatore opaco assegnato dal backend (UUID v4) */
export type Id = string;

/** Ruolo del messaggio nella conversazione */
export type MessageRole = "user" | "assistant" | "system" | "tool";

/** Modalità operative dell'agente per conversazione */
export type ChatMode = "plan" | "ask" | "auto" | "yolo";

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
  agent_mode: ChatMode;
}

/** Vault registrato (cartella SCO collegata) */
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

/** Skill registrata dal runtime (GET /api/skills/list) */
export interface SkillSummary {
  name: string;
  description: string;
  scope: "user" | "project" | "legacy";
  path: string;
  auto_trigger: string | null;
  language: string;
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

// ===== Wave 2 OpenHuman replica: Memory Tree summaries + Hotness =====
// Shape allineata 1:1 al Pydantic backend `TreeSummaryItem` / `HotnessItem`
// (vedi backend/sco_compliance_os/api/memory_routes.py righe 148-170).

/** Livello gerarchico nel Memory Tree (L0 = chunk raw, L1 = summary, L2 = meta-summary) */
export type TreeLevel = 0 | 1 | 2;

/** Nodo summary del Memory Tree (response GET /api/memory/tree-summaries) */
export interface TreeSummaryItem {
  id: string;
  level: number; // 0 | 1 | 2 — non vincolato a TreeLevel sul wire per tolleranza forward-compat
  source: string;
  topic: string | null;
  day: string | null; // ISO YYYY-MM-DD
  content_preview: string;
  token_count: number;
  children_ids: string[];
  parent_id: string | null;
  created_at: string; // ISO 8601
}

/** Snapshot hotness di un chunk (response GET /api/memory/hotness/top) */
export interface HotnessItem {
  chunk_id: string;
  hotness: number;
  last_accessed: string | null; // ISO 8601
  access_count: number;
  days_since_access: number | null;
}

// ===== Wiki SCO (ALPHA v0.4.0) — categorie sources/entities/concepts/synthesis/glossari =====
// Allineato 1:1 al Pydantic backend `WikiSummaryItem` / `WikiListResponse` / `WikiStatsResponse`
// (vedi backend/sco_compliance_os/api/wiki_routes.py righe 51-89).

/** 5 categorie wiki SCO del vault attivo */
export type WikiCategory =
  | "sources"
  | "entities"
  | "concepts"
  | "synthesis"
  | "glossari";

/** Vocabolario chiuso entity_type (vedi CLAUDE.md INGEST sezione tipizzata Ondata 2) */
export type WikiEntityType =
  | "atto-normativo"
  | "standard-tecnico"
  | "linea-guida"
  | "autorita"
  | "metodologia"
  | "autore-prassi"
  | "soggetto-obbligato"
  | "scadenza";

/** Vocabolario chiuso ambito_canonico (17 valori, vedi CLAUDE.md INGEST) */
export type WikiAmbitoCanonico =
  | "cybersicurezza"
  | "governance-ai"
  | "privacy-protezione-dati"
  | "accreditamento-sanitario"
  | "dispositivi-medici"
  | "radioprotezione"
  | "sicurezza-lavoro"
  | "farmacovigilanza"
  | "service-management-ict"
  | "appalti-pubblici"
  | "prevenzione-incendi"
  | "compliance-231"
  | "qualita-sgq"
  | "gestione-ambientale"
  | "sicurezza-alimentare"
  | "responsabilita-sociale"
  | "multi-dominio";

/** Stato pagina wiki (vedi CLAUDE.md INGEST "Stato delle pagine wiki") */
export type WikiStatus = "active" | "draft" | "stub" | "deprecated" | "archived";

/** Item summary in una lista wiki (no body completo) */
export interface WikiSummaryItem {
  slug: string;
  title: string;
  status: string;
  type: string;
  entity_type: string | null;
  entity_subtype: string | null;
  ambito_canonico: string | null;
  domini_applicabili: string[];
  parent_entity: string;
  tags: string[];
  last_reviewed: string;
  last_modified: string;
  body_excerpt: string;
  relationships_count: number;
  applica_entity_count: number;
}

/** Response per /api/wiki/{sources|entities|concepts|synthesis|glossari} */
export interface WikiListResponse {
  category: string;
  total: number;
  limit: number;
  offset: number;
  items: WikiSummaryItem[];
  vault_path: string;
}

/** Response per /api/wiki/stats — counts per categoria */
export interface WikiStatsResponse {
  vault_path: string;
  wiki_dir_exists: boolean;
  counts: Record<string, number>;
  total: number;
}

// ===== Wiki Graph (v0.12.0 force-directed 2D vault visualization) =====
// Allineato 1:1 al Pydantic backend `WikiGraphResponse` / `WikiGraphNode`
// / `WikiGraphEdge` / `WikiGraphStats` in wiki_routes.py.
//
// v0.12.1 Phase 2: aggiunte categorie 'note' + 'missing' per nodi, 'wikilink'
// per edges (body parsing wikilink) — densità tipo Obsidian Graph View.

/** Categoria di nodo nel grafo vault. */
export type WikiGraphNodeCategory =
  | "entity"
  | "cliente"
  | "scadenza"
  | "note"
  | "missing";

/** Categoria di edge nel grafo vault. */
export type WikiGraphEdgeCategory = "relationship" | "applica" | "wikilink";

/** Nodo grafo: entity wiki, cliente business, scadenza, nota generica, o placeholder. */
export interface WikiGraphNode {
  id: string;
  label: string;
  category: string; // WikiGraphNodeCategory (string per tolleranza forward-compat)
  entity_type: string;
  entity_subtype: string;
  ambito_canonico: string;
  status: string; // active | draft | stub | deprecated | archived | missing
  path: string;
}

/** Arco grafo: relationship entity-entity, applica_entity cliente-entity, o wikilink body. */
export interface WikiGraphEdge {
  source: string;
  target: string;
  type: string; // relationship_type | ruolo edge applica | 'menzione' (wikilink)
  category: string; // WikiGraphEdgeCategory (string per tolleranza forward-compat)
  note: string;
}

/** Aggregati di copertura del grafo per filtri UI. */
export interface WikiGraphStats {
  nodes_total: number;
  edges_total: number;
  by_entity_type: Record<string, number>;
  by_ambito_canonico: Record<string, number>;
  by_relationship_type: Record<string, number>;
  // v0.12.1 Phase 2: aggregati per categoria nodo/edge.
  by_category?: Record<string, number>;
  by_edge_category?: Record<string, number>;
}

/** Response per GET /api/wiki/graph */
export interface WikiGraphResponse {
  nodes: WikiGraphNode[];
  edges: WikiGraphEdge[];
  stats: WikiGraphStats;
  vault_path: string;
}

/** Dettaglio singolo file wiki con body completo + frontmatter (response GET /api/wiki/{category}/{slug}) */
export interface WikiFileDetail {
  slug: string;
  path: string;
  type: string;
  title: string;
  status: string;
  entity_type: string | null;
  entity_subtype: string | null;
  ambito_canonico: string | null;
  domini_applicabili: string[];
  parent_entity: string;
  tags: string[];
  last_reviewed: string;
  last_modified: string;
  frontmatter: Record<string, unknown>;
  body_md: string;
  relationships: Array<Record<string, unknown>>;
  applica_entity: Array<Record<string, unknown>>;
  pertinenza_in_verifica: Array<Record<string, unknown>>;
  fornitore_di: Array<Record<string, unknown>>;
  vault_path: string;
}

// ===== Memory Tree Fase 4 (DEV-MEMORY-TREE v0.6.0) — bucket-seal pipeline =====
// Endpoint distinti da Wave 1 legacy (`/tree-summaries` su tabella `summaries` deprecata)
// per evitare HTTP 500 quando le tabelle Wave 1 non sono migrate in v0.6.0+.

/** Item TreeChunk per GET /api/memory/tree/chunks (Fase 1+2+3 bucket-seal) */
export interface TreeChunkItem {
  id: string;
  source_kind: string; // chat | email | document | vault_file | note
  source_id: string;
  owner: string;
  timestamp_ms: number;
  tags: string[];
  content_preview: string;
  token_count: number;
  seq_in_source: number;
  created_at_ms: number;
  status: string; // pending_extraction | admitted | buffered | sealed | dropped
}

/** Item summary L1/L2/L3 per GET /api/memory/tree/summaries (Fase 4 v0.6.0) */
export interface TreeSummaryItemV2 {
  id: string;
  tree_kind: string; // source | topic | global
  tree_id: string;
  level: number; // 1 | 2 | 3
  content_summary: string;
  content_preview: string;
  parent_summary_id: string | null;
  children_chunk_ids: string[];
  children_summary_ids: string[];
  token_count: number;
  source_kind_hint: string | null;
  owner: string;
  created_at_ms: number;
  sealed_at_ms: number | null;
  status: string;
}

/** Response per GET /api/memory/tree/stats — count by status + source_kind */
export interface TreeStatsResponse {
  counts_by_status: Record<string, number>;
  counts_by_source_kind: Record<string, number>;
  total: number;
}

// ===== Wiki Ingest Proposal (v0.8.1 hook chat -> wiki) =====
// Allineato 1:1 al Pydantic backend `WikiIngestProposalResponse` / `WikiIngestSlotOut`
// (vedi backend/sco_compliance_os/api/wiki_routes.py sezione ingest).

/** Destinazione finale di un ingest wiki: 5 categorie canoniche + memory_tree fallback. */
export type WikiIngestDestination =
  | "sources"
  | "entities"
  | "concepts"
  | "synthesis"
  | "glossari"
  | "memory_tree";

/** Tipo di candidato detectato (allegato file, link nel content, search hit). */
export type WikiIngestSourceType = "attachment" | "url" | "search_result";

/** Singolo slot della proposta (un candidato classificato). */
export interface WikiIngestSlot {
  source_type: WikiIngestSourceType;
  title: string;
  identifier: string; // path | url | url+index
  summary: string;
  suggested_destination: WikiIngestDestination;
  suggested_slug: string;
  suggested_frontmatter: Record<string, unknown>;
  confidence: number; // 0.0 - 1.0
  rationale: string;
}

/** Proposta complessiva emessa via SSE event `wiki_ingest_proposal`. */
export interface WikiIngestProposal {
  proposal_id: string;
  conversation_id: string;
  message_id: string;
  created_at: string; // ISO 8601
  slots: WikiIngestSlot[];
  has_strong_candidate: boolean;
}

/** Body POST /api/wiki/ingest/confirm */
export interface WikiIngestConfirmRequest {
  proposal_id: string;
  slot_index: number;
  destination: WikiIngestDestination;
  slug: string;
  frontmatter: Record<string, unknown>;
  body_md: string;
  source_identifier?: string;
  source_type?: WikiIngestSourceType | "";
}

/** Response POST /api/wiki/ingest/confirm */
export interface WikiIngestConfirmResponse {
  written: boolean;
  file_path: string;
  destination: WikiIngestDestination;
  slug: string;
  overwrite: boolean;
}
