-- Migration 0002 — OpenHuman features (Wave 1 v0.2.0).
-- Pattern: idempotente IF NOT EXISTS, sicuro da rieseguire ad ogni startup.
-- Target DB: ~/.sco-compliance-os/memory_tree.db (stesso di memory_chunks).
--
-- Tabelle nuove (4 in Wave 1 partial — subagent W1-MEMORY):
--   summaries     — hierarchical summary tree L0/L1/L2
--   scores        — fast/deep score + hotness decay per chunk
--   entity_index  — entity → chunk_id mapping (carry-over wave 2, scaffold)
--   jobs          — async job queue per deep_score batch + tree promotion (carry-over)
--
-- Tabelle carry-over wave 3-4 (NON in scope subagent W1-MEMORY):
--   triggers_log, oauth_tokens, compression_rules (wave 3-4 enforcement)
--
-- Conv. 44 lesson 3 PyInstaller hidden imports: questo file viene letto da
-- runner Python e applicato via aiosqlite executescript(). Idempotenza
-- garantita da IF NOT EXISTS su tutte le DDL.

-- ============================================================================
-- TABLE summaries: hierarchical summary tree L0/L1/L2
-- ============================================================================
CREATE TABLE IF NOT EXISTS summaries (
    id              TEXT PRIMARY KEY,
    level           INTEGER NOT NULL CHECK (level IN (0, 1, 2)),
    source          TEXT NOT NULL DEFAULT '',
    topic           TEXT NULL,
    day             TEXT NULL,                          -- ISO YYYY-MM-DD
    content         TEXT NOT NULL DEFAULT '',
    parent_id       TEXT NULL REFERENCES summaries(id) ON DELETE SET NULL,
    chunk_ids       TEXT NOT NULL DEFAULT '[]',         -- JSON array
    token_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_summaries_source_day
    ON summaries(source, day);
CREATE INDEX IF NOT EXISTS idx_summaries_topic
    ON summaries(topic);
CREATE INDEX IF NOT EXISTS idx_summaries_parent
    ON summaries(parent_id);
CREATE INDEX IF NOT EXISTS idx_summaries_level
    ON summaries(level);

-- ============================================================================
-- TABLE scores: fast/deep score + hotness decay per chunk
-- ============================================================================
CREATE TABLE IF NOT EXISTS scores (
    id              TEXT PRIMARY KEY,
    chunk_id        TEXT NOT NULL UNIQUE,
    fast_score      REAL NOT NULL DEFAULT 0.0,
    deep_score      REAL NULL,
    hotness         REAL NOT NULL DEFAULT 0.0,
    last_accessed   TEXT NULL,
    access_count    INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scores_chunk_id
    ON scores(chunk_id);
CREATE INDEX IF NOT EXISTS idx_scores_hotness_desc
    ON scores(hotness DESC);

-- ============================================================================
-- TABLE entity_index: entity → chunk_id mapping
-- ============================================================================
-- Wave 1 scaffold; populate in deep_score batch async (entity extraction LLM).
-- Carry-over wave 2 per query "tutte le menzioni di NIS2".
CREATE TABLE IF NOT EXISTS entity_index (
    id              TEXT PRIMARY KEY,
    entity_name     TEXT NOT NULL,
    entity_type     TEXT NOT NULL,                      -- 'norm', 'standard', 'authority', 'client', ...
    chunk_id        TEXT NULL,
    summary_id      TEXT NULL,
    confidence      REAL NOT NULL DEFAULT 0.0,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entity_index_name
    ON entity_index(entity_name);
CREATE INDEX IF NOT EXISTS idx_entity_index_type
    ON entity_index(entity_type);
CREATE INDEX IF NOT EXISTS idx_entity_index_chunk
    ON entity_index(chunk_id);

-- ============================================================================
-- TABLE jobs: async job queue per deep_score batch + tree promotion
-- ============================================================================
-- Wave 1 scaffold; usato da scorer.deep_score_async + cascade.promote_to_l1.
CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,
    job_type        TEXT NOT NULL,                      -- 'deep_score', 'promote_l1', 'aggregate_l2'
    payload         TEXT NOT NULL DEFAULT '{}',         -- JSON dict
    status          TEXT NOT NULL DEFAULT 'pending',    -- 'pending', 'running', 'done', 'failed'
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_error      TEXT NULL,
    scheduled_at    TEXT NOT NULL,
    started_at      TEXT NULL,
    completed_at    TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_scheduled
    ON jobs(status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_jobs_type
    ON jobs(job_type);
