"""SQLite store async per Memory Tree.

Storage path: ~/.sco-compliance-os/memory_tree.db (cross-platform Path.home()).
Driver: aiosqlite (no SQLAlchemy per leggerezza + zero overhead ORM).
Migration: idempotente via init_schema() — pattern store.py di sco-agent-local.

Schema:
    memory_chunks (
        id TEXT PK,
        source_type TEXT NOT NULL CHECK IN ('connector','user_upload','vault_ingest','manual'),
        source_id TEXT NOT NULL,
        source_path TEXT NOT NULL,
        parent_id TEXT NULL REFERENCES memory_chunks(id),
        heading_path TEXT NOT NULL,         -- JSON array
        content_md TEXT NOT NULL,
        token_count INTEGER NOT NULL,
        score_metadata TEXT NOT NULL,       -- JSON dict (provenance + manual boost)
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    Indici: (source_type, source_id), (created_at DESC), (parent_id)
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Iterable, Optional

import aiosqlite

from .chunker import Chunk

logger = logging.getLogger(__name__)

_DEFAULT_DB_DIR = Path.home() / ".sco-compliance-os"
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "memory_tree.db"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS memory_chunks (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL CHECK (source_type IN
        ('connector','user_upload','vault_ingest','manual')),
    source_id TEXT NOT NULL DEFAULT '',
    source_path TEXT NOT NULL DEFAULT '',
    parent_id TEXT NULL REFERENCES memory_chunks(id) ON DELETE SET NULL,
    heading_path TEXT NOT NULL DEFAULT '[]',
    content_md TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    score_metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_source
    ON memory_chunks(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_memory_created
    ON memory_chunks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_parent
    ON memory_chunks(parent_id);
"""


def default_db_path() -> Path:
    """Path canonico del DB Memory Tree (overridable via env in futuro)."""
    return _DEFAULT_DB_PATH


async def init_schema(db_path: Optional[Path] = None) -> None:
    """Inizializza schema idempotente. Sicuro da chiamare a ogni avvio app."""
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.executescript(_SCHEMA_SQL)
        await db.commit()
    logger.info("Memory Tree schema inizializzato: %s", path)


@asynccontextmanager
async def _connection(db_path: Optional[Path] = None) -> AsyncIterator[aiosqlite.Connection]:
    """Context manager per connessione aiosqlite con row factory dict-like."""
    path = db_path or default_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        yield db


def _chunk_to_row(c: Chunk) -> tuple:
    """Serializza un Chunk in tupla per INSERT."""
    now = datetime.now(timezone.utc).isoformat()
    return (
        c.id,
        c.source_type,
        c.source_id,
        c.source_path,
        c.parent_chunk_id,
        json.dumps(c.heading_path, ensure_ascii=False),
        c.content_md,
        c.token_count,
        json.dumps(c.provenance, ensure_ascii=False),
        c.created_at,
        now,
    )


def _row_to_chunk(row: aiosqlite.Row) -> Chunk:
    """Deserializza una row in Chunk."""
    return Chunk(
        id=row["id"],
        source_path=row["source_path"],
        parent_chunk_id=row["parent_id"],
        heading_path=json.loads(row["heading_path"]),
        content_md=row["content_md"],
        token_count=row["token_count"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        provenance=json.loads(row["score_metadata"]),
        created_at=row["created_at"],
    )


async def insert_chunk(chunk: Chunk, db_path: Optional[Path] = None) -> None:
    """Inserisce singolo chunk (idempotente su PK conflict, sostituisce)."""
    async with _connection(db_path) as db:
        await db.execute(
            """INSERT OR REPLACE INTO memory_chunks
            (id, source_type, source_id, source_path, parent_id, heading_path,
             content_md, token_count, score_metadata, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            _chunk_to_row(chunk),
        )
        await db.commit()


async def bulk_insert(chunks: Iterable[Chunk], db_path: Optional[Path] = None) -> int:
    """Bulk insert efficiente in singola transazione."""
    rows = [_chunk_to_row(c) for c in chunks]
    if not rows:
        return 0
    async with _connection(db_path) as db:
        await db.executemany(
            """INSERT OR REPLACE INTO memory_chunks
            (id, source_type, source_id, source_path, parent_id, heading_path,
             content_md, token_count, score_metadata, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        await db.commit()
    return len(rows)


async def get_chunk(chunk_id: str, db_path: Optional[Path] = None) -> Optional[Chunk]:
    """Recupera un singolo chunk per ID."""
    async with _connection(db_path) as db:
        async with db.execute(
            "SELECT * FROM memory_chunks WHERE id = ?", (chunk_id,)
        ) as cur:
            row = await cur.fetchone()
            return _row_to_chunk(row) if row else None


async def query_by_source(
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[Path] = None,
) -> list[Chunk]:
    """Query per source_type e/o source_id."""
    sql = "SELECT * FROM memory_chunks WHERE 1=1"
    params: list = []
    if source_type:
        sql += " AND source_type = ?"
        params.append(source_type)
    if source_id:
        sql += " AND source_id = ?"
        params.append(source_id)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    async with _connection(db_path) as db:
        async with db.execute(sql, params) as cur:
            return [_row_to_chunk(r) async for r in cur]


async def query_recent(limit: int = 100, db_path: Optional[Path] = None) -> list[Chunk]:
    """Recupera N chunks più recenti (per scoring + retrieval iniziale)."""
    async with _connection(db_path) as db:
        async with db.execute(
            "SELECT * FROM memory_chunks ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            return [_row_to_chunk(r) async for r in cur]


async def delete_by_source(
    source_type: str,
    source_id: str,
    db_path: Optional[Path] = None,
) -> int:
    """Cancella tutti i chunks di un sorgente (re-ingest scenario)."""
    async with _connection(db_path) as db:
        cur = await db.execute(
            "DELETE FROM memory_chunks WHERE source_type = ? AND source_id = ?",
            (source_type, source_id),
        )
        await db.commit()
        return cur.rowcount or 0


async def count_chunks(db_path: Optional[Path] = None) -> int:
    """Conta totale chunks (cruscotto Conv. 41 tracciatura)."""
    async with _connection(db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM memory_chunks") as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0
