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

import aiosqlite

from .store import default_db_path
from .tree_chunker import TreeChunk, TreeChunkStatus

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
    admission_reasoning TEXT NULL
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

    async def __aenter__(self) -> "CircuitBreaker":
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

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
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
    """Inizializza schema mem_tree_chunks idempotente.

    Safe da chiamare a ogni avvio app. Usa stesso DB di store.py legacy
    per single-source-of-truth filesystem (Conv. 47 enforcement).
    """
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.executescript(_TREE_SCHEMA_SQL)
        await db.commit()
    logger.info("mem_tree_chunks schema inizializzato", extra={"db_path": str(path)})


# --------------------------------------------------------------------------
# CONNECTION HELPER — dict-like rows
# --------------------------------------------------------------------------


@asynccontextmanager
async def _connection(db_path: Path | None = None) -> AsyncIterator[aiosqlite.Connection]:
    path = db_path or default_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        yield db


def _chunk_to_row(c: TreeChunk) -> tuple:
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
    params: list = []
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
                    row = await cur.fetchone()
                    out["total"] = int(row[0]) if row else 0
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


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "bulk_upsert_chunks",
    "count_by_source_kind",
    "count_by_status",
    "delete_chunk",
    "get_chunk",
    "init_tree_schema",
    "list_chunks",
    "upsert_chunk",
]
