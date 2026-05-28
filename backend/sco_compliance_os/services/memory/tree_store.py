"""Memory Tree bucket-seal — Store SQLite + CircuitBreaker.

Persistent storage layer per il pipeline bucket-seal 4 fasi (vedi
`tree_chunker.py`, `tree_scoring.py`, `tree_ingester.py`).

Schema: tabella `mem_tree_chunks` (clean-room reimplementation ispirata a
OpenHuman MEMORY_ARCHITECTURE_LLD, NO code copy).

Storage: usa stesso DB di `store.py` esistente (~/.sco-compliance-os/memory_tree.db)
per single-source-of-truth filesystem (Conv. 47 enforcement).

Migration idempotente via `init_tree_schema()` — pattern allineato a
`store.py` esistente e a `sco-agent-local` store init.

Indici (5 totali):
    - PRIMARY KEY (id)
    - INDEX (source_kind, source_id)
    - INDEX (owner, timestamp_ms)
    - INDEX (status)
    - INDEX (status, created_at_ms)  -- per query "pending da X giorni"

CircuitBreaker pattern (clean-room implementation):
    - 3 fail consecutivi -> 30s pause (prevenire WAL cold-start storm / disk full).
    - Conv. 44 lesson 1 enforcement: protegge da background process zombie.
    - Reset on success.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from pathlib import Path
from types import TracebackType
from typing import Any

import aiosqlite
from aiosqlite import Row

from .store import default_db_path
from .tree_chunker import TreeChunk

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# SCHEMA — tabella mem_tree_chunks (Fase 1-3 storage)
# --------------------------------------------------------------------------

_TREE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS mem_tree_chunks (
    id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL CHECK (source_kind IN
        ('chat','email','document','vault_file','note')),
    source_id TEXT NOT NULL DEFAULT '',
    owner TEXT NOT NULL DEFAULT 'local',
    timestamp_ms INTEGER NOT NULL DEFAULT 0,
    time_range_start_ms INTEGER NOT NULL DEFAULT 0,
    time_range_end_ms INTEGER NOT NULL DEFAULT 0,
    tags_json TEXT NOT NULL DEFAULT '[]',
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    seq_in_source INTEGER NOT NULL DEFAULT 0,
    created_at_ms INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending_extraction' CHECK (status IN
        ('pending_extraction','admitted','buffered','sealed','dropped')),
    cheap_total REAL NULL,
    llm_score REAL NULL,
    admission_reasoning TEXT NULL,
    parent_summary_id TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_tree_source
    ON mem_tree_chunks(source_kind, source_id);
CREATE INDEX IF NOT EXISTS idx_tree_owner_timestamp
    ON mem_tree_chunks(owner, timestamp_ms DESC);
CREATE INDEX IF NOT EXISTS idx_tree_status
    ON mem_tree_chunks(status);
CREATE INDEX IF NOT EXISTS idx_tree_status_created
    ON mem_tree_chunks(status, created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_tree_created_at
    ON mem_tree_chunks(created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_tree_parent_summary
    ON mem_tree_chunks(parent_summary_id);

-- LLM score cache idempotente: hash(content) -> score (no ri-extraction)
CREATE TABLE IF NOT EXISTS mem_llm_score_cache (
    chunk_id_hash TEXT PRIMARY KEY,
    score REAL NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    scored_at_ms INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_llm_score_cache_scored_at
    ON mem_llm_score_cache(scored_at_ms DESC);

-- Memory Tree summaries — Fase 4 sealing L0->L1->L2->L3
-- tree_kind: source | topic | global (3 alberi concentrici)
-- tree_id: source_id (per source) | topic_name (per topic) | 'global' (per global)
-- level: 0 raw (chunk) | 1 L1 sealed | 2 L2 sealed | 3 L3 sealed
-- status: pending (in buffer) | sealed (promosso) | archived (sealed L2+ then archived)
CREATE TABLE IF NOT EXISTS mem_tree_summaries (
    id TEXT PRIMARY KEY,
    tree_kind TEXT NOT NULL CHECK (tree_kind IN ('source','topic','global')),
    tree_id TEXT NOT NULL DEFAULT '',
    level INTEGER NOT NULL DEFAULT 1 CHECK (level BETWEEN 1 AND 3),
    content_summary TEXT NOT NULL,
    parent_summary_id TEXT NULL,
    children_chunk_ids_json TEXT NOT NULL DEFAULT '[]',
    children_summary_ids_json TEXT NOT NULL DEFAULT '[]',
    token_count INTEGER NOT NULL DEFAULT 0,
    source_kind_hint TEXT NULL,
    owner TEXT NOT NULL DEFAULT 'local',
    created_at_ms INTEGER NOT NULL DEFAULT 0,
    sealed_at_ms INTEGER NULL,
    status TEXT NOT NULL DEFAULT 'sealed' CHECK (status IN
        ('pending','sealed','archived'))
);

CREATE INDEX IF NOT EXISTS idx_tree_summaries_kind_id
    ON mem_tree_summaries(tree_kind, tree_id);
CREATE INDEX IF NOT EXISTS idx_tree_summaries_level
    ON mem_tree_summaries(level);
CREATE INDEX IF NOT EXISTS idx_tree_summaries_kind_id_level
    ON mem_tree_summaries(tree_kind, tree_id, level);
CREATE INDEX IF NOT EXISTS idx_tree_summaries_status
    ON mem_tree_summaries(status);
CREATE INDEX IF NOT EXISTS idx_tree_summaries_sealed_at
    ON mem_tree_summaries(sealed_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_tree_summaries_created_at
    ON mem_tree_summaries(created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_tree_summaries_parent
    ON mem_tree_summaries(parent_summary_id);
CREATE INDEX IF NOT EXISTS idx_tree_summaries_owner
    ON mem_tree_summaries(owner);
"""

# Migration idempotente per aggiungere parent_summary_id su mem_tree_chunks
# (per installs esistenti pre-v0.6.0). SQLite ALTER TABLE ADD COLUMN e' safe
# se la colonna non esiste; cattura errore "duplicate column" come no-op.
_MIGRATION_PARENT_SUMMARY_SQL = """
ALTER TABLE mem_tree_chunks ADD COLUMN parent_summary_id TEXT NULL;
"""


# --------------------------------------------------------------------------
# CIRCUIT BREAKER — clean-room implementation
# --------------------------------------------------------------------------


class CircuitBreaker:
    """Circuit breaker per protezione DB ops (Conv. 44 lesson 1 enforcement).

    Pattern: 3 fail consecutivi -> 30s pause (prevenire WAL storm / I/O loop).
    Reset on success. Thread-safe via asyncio.Lock.

    Stato:
        CLOSED   -> ops normalmente; ogni fail incrementa counter.
        OPEN     -> ops bloccate; ritorna CircuitBreakerOpenError.
        HALF_OPEN -> dopo timeout, prossima op decide CLOSED o OPEN.
    """

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(
        self,
        *,
        fail_threshold: int = 3,
        pause_seconds: float = 30.0,
        name: str = "tree_store",
    ) -> None:
        self.fail_threshold = fail_threshold
        self.pause_seconds = pause_seconds
        self.name = name
        self._fail_count = 0
        self._state = self.STATE_CLOSED
        self._opened_at: float = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> CircuitBreaker:
        async with self._lock:
            now = time.monotonic()
            if self._state == self.STATE_OPEN:
                elapsed = now - self._opened_at
                if elapsed < self.pause_seconds:
                    raise CircuitBreakerOpenError(
                        f"CircuitBreaker[{self.name}] OPEN; "
                        f"retry in {self.pause_seconds - elapsed:.1f}s"
                    )
                # Timeout scaduto -> transizione HALF_OPEN.
                self._state = self.STATE_HALF_OPEN
                logger.info(
                    "circuit_breaker: transizione OPEN -> HALF_OPEN",
                    extra={"name": self.name},
                )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        async with self._lock:
            if exc_type is None:
                # Success -> reset.
                if self._state in (self.STATE_HALF_OPEN, self.STATE_CLOSED):
                    if self._fail_count > 0:
                        logger.info(
                            "circuit_breaker: success -> reset",
                            extra={"name": self.name, "prev_fails": self._fail_count},
                        )
                    self._fail_count = 0
                    self._state = self.STATE_CLOSED
            else:
                self._fail_count += 1
                logger.warning(
                    "circuit_breaker: fail counted",
                    extra={
                        "name": self.name,
                        "fail_count": self._fail_count,
                        "exc": str(exc_val)[:200],
                    },
                )
                if self._fail_count >= self.fail_threshold:
                    self._state = self.STATE_OPEN
                    self._opened_at = time.monotonic()
                    logger.error(
                        "circuit_breaker: OPEN tripped",
                        extra={
                            "name": self.name,
                            "fail_threshold": self.fail_threshold,
                            "pause_seconds": self.pause_seconds,
                        },
                    )

    @property
    def state(self) -> str:
        return self._state

    @property
    def fail_count(self) -> int:
        return self._fail_count


class CircuitBreakerOpenError(RuntimeError):
    """Raised quando CircuitBreaker e' OPEN e l'op viene rifiutata."""


# Singleton di processo per il tree_store (Conv. 47 single source of truth).
_tree_breaker = CircuitBreaker(name="tree_store")


# --------------------------------------------------------------------------
# INIT SCHEMA — idempotente
# --------------------------------------------------------------------------


async def init_tree_schema(db_path: Path | None = None) -> None:
    """Inizializza schema mem_tree_chunks + mem_llm_score_cache + mem_tree_summaries.

    Safe da chiamare a ogni avvio app. Usa stesso DB di store.py legacy
    per single-source-of-truth filesystem (Conv. 47 enforcement).

    Migration idempotente parent_summary_id su mem_tree_chunks per upgrade
    da v0.5.0 a v0.6.0 senza data loss (Conv. 48 enforcement: estendere
    schema invece di workaround applicativi).
    """
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.executescript(_TREE_SCHEMA_SQL)
        # Migration idempotente: parent_summary_id added in v0.6.0
        # Pattern allineato a sco-agent-local store.py init_schema
        try:
            await db.execute(_MIGRATION_PARENT_SUMMARY_SQL)
        except Exception as exc:
            msg = str(exc).lower()
            if "duplicate column" not in msg and "already exists" not in msg:
                # Errore reale: log warning ma non blocca init (idempotency-first)
                logger.warning(
                    "init_tree_schema.migration_parent_summary_unexpected",
                    extra={"error": str(exc)[:200]},
                )
        await db.commit()
    logger.info(
        "mem_tree_chunks + mem_llm_score_cache + mem_tree_summaries schema inizializzato",
        extra={"db_path": str(path)},
    )


# --------------------------------------------------------------------------
# LLM SCORE CACHE — idempotente (chunk_id_hash PK)
# --------------------------------------------------------------------------


async def get_llm_score_cached(
    content_hash: str,
    db_path: Path | None = None,
) -> float | None:
    """Cache lookup score LLM per content hash.

    Returns:
        float score se cache hit, None se miss.
    """
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                async with db.execute(
                    "SELECT score FROM mem_llm_score_cache WHERE chunk_id_hash = ?",
                    (content_hash,),
                ) as cur:
                    row = await cur.fetchone()
                    if row is None:
                        return None
                    return float(row["score"])
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("get_llm_score_cached: errore: %s", exc)
        return None


async def set_llm_score_cached(
    content_hash: str,
    score: float,
    model: str,
    db_path: Path | None = None,
) -> bool:
    """Store score LLM in cache idempotente (INSERT OR REPLACE)."""
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                ts_ms = int(time.time() * 1000)
                await db.execute(
                    """INSERT OR REPLACE INTO mem_llm_score_cache
                    (chunk_id_hash, score, model, scored_at_ms)
                    VALUES (?, ?, ?, ?)""",
                    (content_hash, score, model, ts_ms),
                )
                await db.commit()
            return True
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("set_llm_score_cached: errore: %s", exc)
        return False


# --------------------------------------------------------------------------
# CONNECTION HELPER — dict-like rows
# --------------------------------------------------------------------------


@asynccontextmanager
async def _connection(db_path: Path | None = None) -> AsyncIterator[aiosqlite.Connection]:
    path = db_path or default_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        yield db


def _chunk_to_row(c: TreeChunk) -> tuple[Any, ...]:
    """Serializza TreeChunk in tupla per INSERT OR REPLACE."""
    return (
        c.id,
        c.source_kind,
        c.source_id,
        c.owner,
        c.timestamp_ms,
        c.time_range_start_ms,
        c.time_range_end_ms,
        json.dumps(c.tags, ensure_ascii=False),
        c.content,
        c.token_count,
        c.seq_in_source,
        c.created_at_ms,
        c.status,
    )


def _row_to_chunk(row: aiosqlite.Row) -> TreeChunk:
    """Deserializza row in TreeChunk."""
    try:
        tags = json.loads(row["tags_json"]) if row["tags_json"] else []
    except (json.JSONDecodeError, TypeError):
        tags = []
    return TreeChunk(
        id=row["id"],
        source_kind=row["source_kind"],
        source_id=row["source_id"],
        owner=row["owner"],
        timestamp_ms=int(row["timestamp_ms"]),
        time_range_start_ms=int(row["time_range_start_ms"]),
        time_range_end_ms=int(row["time_range_end_ms"]),
        tags=tags,
        content=row["content"],
        token_count=int(row["token_count"]),
        seq_in_source=int(row["seq_in_source"]),
        created_at_ms=int(row["created_at_ms"]),
        status=row["status"],
    )


# --------------------------------------------------------------------------
# CRUD OPERATIONS — protected by CircuitBreaker
# --------------------------------------------------------------------------


async def upsert_chunk(
    chunk: TreeChunk,
    *,
    cheap_total: float | None = None,
    llm_score: float | None = None,
    admission_reasoning: str | None = None,
    db_path: Path | None = None,
) -> bool:
    """Upsert idempotente di un TreeChunk via PRIMARY KEY id.

    Stable ID -> stesso input = upsert no-op semantico (REPLACE = stesso payload).

    Args:
        chunk: TreeChunk da persistere.
        cheap_total: score Fase 3 (opzionale, popolato post admission_decision).
        llm_score: score LLM extractor (opzionale, None se non consultato).
        admission_reasoning: motivazione testuale (audit trail Conv. 41).
        db_path: override path DB.

    Returns:
        True se inserito/aggiornato, False se errore (CircuitBreaker OPEN).
    """
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                row = _chunk_to_row(chunk)
                # Append scoring columns (manuali, non in _chunk_to_row).
                await db.execute(
                    """INSERT OR REPLACE INTO mem_tree_chunks
                    (id, source_kind, source_id, owner, timestamp_ms,
                     time_range_start_ms, time_range_end_ms, tags_json,
                     content, token_count, seq_in_source, created_at_ms,
                     status, cheap_total, llm_score, admission_reasoning)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (*row, cheap_total, llm_score, admission_reasoning),
                )
                await db.commit()
            return True
    except CircuitBreakerOpenError as cb_err:
        logger.warning("upsert_chunk: CircuitBreaker OPEN, op skipped: %s", cb_err)
        return False
    except Exception as exc:
        logger.error("upsert_chunk: errore inattesi: %s", exc, exc_info=False)
        return False


async def bulk_upsert_chunks(
    chunks: Iterable[TreeChunk],
    *,
    scoring_map: dict[str, tuple[float | None, float | None, str | None]] | None = None,
    db_path: Path | None = None,
) -> int:
    """Bulk upsert efficiente in singola transazione.

    Args:
        chunks: iterabile di TreeChunk.
        scoring_map: dict {chunk_id: (cheap_total, llm_score, reasoning)} opzionale.
            Se assente per un chunk -> NULL in colonne scoring.

    Returns:
        Numero righe processate. 0 se errore o lista vuota.
    """
    payload = []
    for c in chunks:
        scoring = scoring_map.get(c.id) if scoring_map else None
        cheap = scoring[0] if scoring else None
        llm = scoring[1] if scoring else None
        reasoning = scoring[2] if scoring else None
        row = _chunk_to_row(c)
        payload.append((*row, cheap, llm, reasoning))
    if not payload:
        return 0
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                await db.executemany(
                    """INSERT OR REPLACE INTO mem_tree_chunks
                    (id, source_kind, source_id, owner, timestamp_ms,
                     time_range_start_ms, time_range_end_ms, tags_json,
                     content, token_count, seq_in_source, created_at_ms,
                     status, cheap_total, llm_score, admission_reasoning)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    payload,
                )
                await db.commit()
            return len(payload)
    except CircuitBreakerOpenError as cb_err:
        logger.warning("bulk_upsert_chunks: CircuitBreaker OPEN: %s", cb_err)
        return 0
    except Exception as exc:
        logger.error("bulk_upsert_chunks: errore: %s", exc, exc_info=False)
        return 0


async def get_chunk(chunk_id: str, db_path: Path | None = None) -> TreeChunk | None:
    """Recupera singolo chunk per ID stabile."""
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                async with db.execute(
                    "SELECT * FROM mem_tree_chunks WHERE id = ?",
                    (chunk_id,),
                ) as cur:
                    row = await cur.fetchone()
                    return _row_to_chunk(row) if row else None
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("get_chunk: errore: %s", exc)
        return None


async def list_chunks(
    *,
    status: str | None = None,
    source_kind: str | None = None,
    source_id: str | None = None,
    owner: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Path | None = None,
) -> list[TreeChunk]:
    """Lista chunks con filtri opzionali + paginazione.

    Args:
        status: filtra per TreeChunkStatus.
        source_kind: filtra per vocabolario chiuso TreeChunkSourceKind.
        source_id: filtra per identificatore sorgente.
        owner: filtra per utente owner.
        limit: max risultati (default 100).
        offset: offset paginazione.
        db_path: override path DB.

    Returns:
        Lista TreeChunk ordinata per created_at_ms DESC.
    """
    sql = "SELECT * FROM mem_tree_chunks WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if source_kind:
        sql += " AND source_kind = ?"
        params.append(source_kind)
    if source_id:
        sql += " AND source_id = ?"
        params.append(source_id)
    if owner:
        sql += " AND owner = ?"
        params.append(owner)
    sql += " ORDER BY created_at_ms DESC LIMIT ? OFFSET ?"
    params.append(limit)
    params.append(offset)
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                async with db.execute(sql, params) as cur:
                    return [_row_to_chunk(r) async for r in cur]
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("list_chunks: errore: %s", exc)
        return []


async def delete_chunk(chunk_id: str, db_path: Path | None = None) -> bool:
    """Cancella singolo chunk per ID. Return True se cancellato, False altrimenti."""
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                cur = await db.execute(
                    "DELETE FROM mem_tree_chunks WHERE id = ?",
                    (chunk_id,),
                )
                await db.commit()
                return (cur.rowcount or 0) > 0
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("delete_chunk: errore: %s", exc)
        return False


async def delete_source(
    source_kind: str,
    source_id: str,
    db_path: Path | None = None,
) -> tuple[int, int]:
    """Cancella tutti i chunk + summaries per una sorgente specifica."""
    deleted_chunks = 0
    deleted_summaries = 0
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                cur_chunks = await db.execute(
                    "DELETE FROM mem_tree_chunks WHERE source_kind = ? AND source_id = ?",
                    (source_kind, source_id),
                )
                deleted_chunks = cur_chunks.rowcount or 0
                cur_summaries = await db.execute(
                    "DELETE FROM mem_tree_summaries WHERE tree_kind = 'source' AND tree_id = ?",
                    (source_id,),
                )
                deleted_summaries = cur_summaries.rowcount or 0
                await db.commit()
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("delete_source: errore: %s", exc)
        return 0, 0
    return deleted_chunks, deleted_summaries


async def count_by_status(db_path: Path | None = None) -> dict[str, int]:
    """Conta chunks raggruppati per status (cruscotto Conv. 41 tracciatura).

    Returns:
        Dict {status: count}. Status mai osservati -> non inclusi.
        Sempre include chiave 'total' con count cumulativo.
    """
    out: dict[str, int] = {}
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                async with db.execute(
                    """SELECT status, COUNT(*) as cnt
                    FROM mem_tree_chunks
                    GROUP BY status"""
                ) as cur:
                    async for row in cur:
                        out[row["status"]] = int(row["cnt"])
                async with db.execute("SELECT COUNT(*) FROM mem_tree_chunks") as cur:
                    row_opt = await cur.fetchone()
                    if row_opt is None:
                        raise RuntimeError("row attesa")
                    row_total: Row = row_opt
                    out["total"] = int(row_total[0])
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("count_by_status: errore: %s", exc)
        out["total"] = 0
    return out


async def count_by_source_kind(db_path: Path | None = None) -> dict[str, int]:
    """Conta chunks raggruppati per source_kind."""
    out: dict[str, int] = {}
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                async with db.execute(
                    """SELECT source_kind, COUNT(*) as cnt
                    FROM mem_tree_chunks
                    GROUP BY source_kind"""
                ) as cur:
                    async for row in cur:
                        out[row["source_kind"]] = int(row["cnt"])
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("count_by_source_kind: errore: %s", exc)
    return out


async def activity_by_day(
    days: int = 240,
    db_path: Path | None = None,
) -> list[tuple[str, int]]:
    """Aggrega attivita` per giorno per Memory Heatmap GitHub-style (v0.13.2 PSI-2).

    Conta chunks ingeriti su ``mem_tree_chunks`` (tutte le source_kind incluse
    chat + email + document + vault_file + note) negli ultimi N giorni.
    Pattern: GROUP BY date(created_at_ms / 1000, 'unixepoch', 'localtime').

    Returns:
        Lista di tuple (date_iso_YYYY-MM-DD, count) ordinata per data ASC.
        Solo giorni con almeno 1 attivita`. Il frontend completa i giorni
        mancanti come "level 0" nella griglia 8-mese × 7-day.
    """
    out: list[tuple[str, int]] = []
    now_ms = int(time.time() * 1000)
    cutoff_ms = now_ms - days * 86_400_000
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                async with db.execute(
                    """SELECT
                        date(created_at_ms / 1000, 'unixepoch') AS day,
                        COUNT(*) AS cnt
                    FROM mem_tree_chunks
                    WHERE created_at_ms >= ?
                    GROUP BY day
                    ORDER BY day ASC""",
                    (cutoff_ms,),
                ) as cur:
                    async for row in cur:
                        out.append((str(row["day"]), int(row["cnt"])))
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("activity_by_day: errore (graceful empty): %s", exc)
    return out


async def mark_chunks_sealed(
    chunk_ids: list[str],
    parent_summary_id: str,
    db_path: Path | None = None,
) -> int:
    """Marca lista chunk come SEALED (Fase 4 promozione L0->L1).

    Aggiorna status -> 'sealed' + parent_summary_id -> id della summary L1
    appena creata. Idempotente: re-call con stesso parent_summary_id non
    cambia nulla.

    Args:
        chunk_ids: lista ID chunk da promuovere.
        parent_summary_id: ID della summary L1 padre.

    Returns:
        Numero righe aggiornate.
    """
    if not chunk_ids:
        return 0
    placeholders = ",".join("?" * len(chunk_ids))

    # i valori passano come parametri SQL separati. Nessun user input nell'SQL.
    sql = (
        f"UPDATE mem_tree_chunks "  # noqa: S608
        f"SET status = 'sealed', parent_summary_id = ? "
        f"WHERE id IN ({placeholders})"
    )
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                cur = await db.execute(sql, (parent_summary_id, *chunk_ids))
                await db.commit()
                return cur.rowcount or 0
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("mark_chunks_sealed: errore: %s", exc)
        return 0


async def get_admitted_chunks_for_seal(
    *,
    source_id: str | None = None,
    owner: str = "local",
    db_path: Path | None = None,
) -> list[TreeChunk]:
    """Recupera tutti i chunk admitted NON ancora sealed per un source/owner.

    Pattern Fase 4 sealing: query candidates pre-aggregazione per tree_source
    (filtro per source_id) o tree_global (no filter).

    Args:
        source_id: se non None filtra per source_id (tree_source mode).
        owner: filtra per owner (default 'local' single-user).

    Returns:
        Lista TreeChunk admitted ordinata per timestamp_ms ASC (cronologica).
    """
    sql = (
        "SELECT * FROM mem_tree_chunks "
        "WHERE status = 'admitted' AND owner = ? AND parent_summary_id IS NULL"
    )
    params: list[Any] = [owner]
    if source_id:
        sql += " AND source_id = ?"
        params.append(source_id)
    sql += " ORDER BY timestamp_ms ASC, seq_in_source ASC"
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                async with db.execute(sql, params) as cur:
                    return [_row_to_chunk(r) async for r in cur]
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("get_admitted_chunks_for_seal: errore: %s", exc)
        return []


async def list_distinct_sources(
    *,
    owner: str = "local",
    db_path: Path | None = None,
) -> list[tuple[str, str]]:
    """Lista distinti (source_kind, source_id) di chunk admitted per tree_source iteration.

    Returns:
        Lista tuple (source_kind, source_id) ordinata.
    """
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                async with db.execute(
                    """SELECT DISTINCT source_kind, source_id
                    FROM mem_tree_chunks
                    WHERE status = 'admitted' AND owner = ?
                      AND parent_summary_id IS NULL
                    ORDER BY source_kind, source_id""",
                    (owner,),
                ) as cur:
                    return [(r["source_kind"], r["source_id"]) async for r in cur]
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("list_distinct_sources: errore: %s", exc)
        return []


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "_connection",
    "_tree_breaker",
    "activity_by_day",
    "bulk_upsert_chunks",
    "count_by_source_kind",
    "count_by_status",
    "delete_chunk",
    "get_admitted_chunks_for_seal",
    "get_chunk",
    "get_llm_score_cached",
    "init_tree_schema",
    "list_chunks",
    "list_distinct_sources",
    "mark_chunks_sealed",
    "set_llm_score_cached",
    "upsert_chunk",
]
