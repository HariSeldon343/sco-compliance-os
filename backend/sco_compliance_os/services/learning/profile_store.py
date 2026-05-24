"""SQLite store async per profilo utente progressivo.

Pattern store: aiosqlite + init_schema() idempotente + connection context
manager (riusa pattern di services/memory/store.py per coerenza).

Schema:
    user_profile (
        id INTEGER PK AUTOINCREMENT,
        tenant_id TEXT NOT NULL DEFAULT 'local',
        slug TEXT NOT NULL,
        text TEXT NOT NULL,
        category TEXT NOT NULL CHECK IN ('identity','preference','aversion','fact','stack'),
        confidence REAL NOT NULL DEFAULT 0.7,
        first_extracted_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        seen_count INTEGER NOT NULL DEFAULT 1,
        pinned INTEGER NOT NULL DEFAULT 0,
        source_turn_id TEXT NULL,
        UNIQUE (tenant_id, slug)
    )
    Indici: (tenant_id, pinned DESC, seen_count DESC), (category), (last_seen_at DESC)

Pattern Conv. 47 SINGLE SOURCE OF TRUTH BACKEND: le preferenze vivono solo
nel DB SQLite, mai duplicate in cache process-local o env. Pattern Conv. 48
applicato a stato widget — qui esteso a stato profilo persistito post-turn.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from sco_compliance_os.services.learning.user_profile import (
    Preference,
    ProfileCategory,
)

logger = logging.getLogger(__name__)


_DEFAULT_DB_DIR = Path.home() / ".sco-compliance-os"
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "user_profile.db"


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL DEFAULT 'local',
    slug TEXT NOT NULL,
    text TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN
        ('identity','preference','aversion','fact','stack')),
    confidence REAL NOT NULL DEFAULT 0.7,
    first_extracted_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    seen_count INTEGER NOT NULL DEFAULT 1,
    pinned INTEGER NOT NULL DEFAULT 0,
    source_turn_id TEXT NULL,
    UNIQUE (tenant_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_user_profile_rank
    ON user_profile (tenant_id, pinned DESC, seen_count DESC, confidence DESC);
CREATE INDEX IF NOT EXISTS idx_user_profile_category
    ON user_profile (category);
CREATE INDEX IF NOT EXISTS idx_user_profile_last_seen
    ON user_profile (last_seen_at DESC);
"""


def default_db_path() -> Path:
    """Path canonico del DB profilo utente."""
    return _DEFAULT_DB_PATH


async def init_schema(db_path: Path | None = None) -> None:
    """Inizializza schema idempotente. Sicuro a ogni avvio app."""
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.executescript(_SCHEMA_SQL)
        await db.commit()
    logger.info("user_profile schema inizializzato: %s", path)


@asynccontextmanager
async def _connection(
    db_path: Path | None = None,
) -> AsyncIterator[aiosqlite.Connection]:
    """Context manager connessione aiosqlite con row factory dict-like."""
    path = db_path or default_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        yield db


def _row_to_pref(row: aiosqlite.Row) -> Preference:
    """Deserializza una row in Preference dataclass."""
    extracted_at_str = row["first_extracted_at"]
    try:
        extracted_at = datetime.fromisoformat(extracted_at_str)
    except (ValueError, TypeError):
        extracted_at = datetime.now(UTC)
    return Preference(
        text=row["text"],
        slug=row["slug"],
        category=ProfileCategory(row["category"]),
        confidence=float(row["confidence"]),
        extracted_at=extracted_at,
        source_turn_id=row["source_turn_id"],
    )


async def upsert_preference(
    pref: Preference,
    *,
    tenant_id: str = "local",
    db_path: Path | None = None,
) -> Preference:
    """Upsert idempotente di una preferenza.

    Su conflict (tenant_id + slug):
    - incrementa seen_count di 1
    - aggiorna last_seen_at a ora UTC
    - aggiorna confidence a MAX(esistente, nuova) — preserva learning
    - aggiorna text al piu recente (potrebbe essere una rifrasi piu chiara)
    - aggiorna source_turn_id al piu recente
    - pinned NON viene mai sovrascritto (lo gestisce l'utente esplicitamente)

    Args:
        pref: Preference da inserire o aggiornare.
        tenant_id: ID tenant (default 'local' per single-machine).
        db_path: override del path DB (testing).

    Returns:
        Preference effettivamente persistita (dopo upsert).
    """
    now = datetime.now(UTC).isoformat()
    async with _connection(db_path) as db:
        await db.execute(
            """
            INSERT INTO user_profile
                (tenant_id, slug, text, category, confidence,
                 first_extracted_at, last_seen_at, seen_count, pinned,
                 source_turn_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?)
            ON CONFLICT(tenant_id, slug) DO UPDATE SET
                seen_count = seen_count + 1,
                last_seen_at = excluded.last_seen_at,
                confidence = MAX(confidence, excluded.confidence),
                text = excluded.text,
                source_turn_id = excluded.source_turn_id
            """,
            (
                tenant_id,
                pref.slug,
                pref.text,
                pref.category.value,
                pref.confidence,
                pref.extracted_at.isoformat(),
                now,
                pref.source_turn_id,
            ),
        )
        await db.commit()
    logger.debug(
        "user_profile.upsert tenant=%s slug=%s category=%s",
        tenant_id,
        pref.slug,
        pref.category.value,
    )
    return pref


async def list_preferences(
    *,
    tenant_id: str = "local",
    category: ProfileCategory | None = None,
    limit: int = 50,
    db_path: Path | None = None,
) -> list[Preference]:
    """Lista preferenze ordinate per priorita di display.

    Ordering:
        1. pinned DESC (preferenze pinnate dall'utente in cima)
        2. seen_count DESC (cose viste piu volte = piu rilevanti)
        3. confidence DESC (tiebreak con peso pattern)
        4. last_seen_at DESC (tiebreak con recenza)

    Args:
        tenant_id: filtra per tenant (default 'local').
        category: se non None, filtra per categoria specifica.
        limit: numero massimo preferenze restituite.
        db_path: override del path DB (testing).

    Returns:
        Lista Preference ordinate per display priority.
    """
    sql = "SELECT * FROM user_profile WHERE tenant_id = ?"
    params: list = [tenant_id]
    if category is not None:
        sql += " AND category = ?"
        params.append(category.value)
    sql += (
        " ORDER BY pinned DESC, seen_count DESC, confidence DESC, last_seen_at DESC"
        " LIMIT ?"
    )
    params.append(limit)
    async with _connection(db_path) as db:
        async with db.execute(sql, params) as cur:
            return [_row_to_pref(r) async for r in cur]


async def delete_preference(
    slug: str,
    *,
    tenant_id: str = "local",
    db_path: Path | None = None,
) -> bool:
    """Cancella una preferenza per (tenant_id, slug).

    Returns:
        True se la preferenza esisteva ed e stata cancellata, False altrimenti.
    """
    async with _connection(db_path) as db:
        cur = await db.execute(
            "DELETE FROM user_profile WHERE tenant_id = ? AND slug = ?",
            (tenant_id, slug),
        )
        await db.commit()
        deleted = (cur.rowcount or 0) > 0
    if deleted:
        logger.info("user_profile.deleted tenant=%s slug=%s", tenant_id, slug)
    return deleted


async def pin_preference(
    slug: str,
    *,
    tenant_id: str = "local",
    db_path: Path | None = None,
) -> bool:
    """Marca una preferenza come pinned (sale in cima al system prompt).

    Returns:
        True se la preferenza esisteva ed e stata pinned, False altrimenti.
    """
    async with _connection(db_path) as db:
        cur = await db.execute(
            "UPDATE user_profile SET pinned = 1 WHERE tenant_id = ? AND slug = ?",
            (tenant_id, slug),
        )
        await db.commit()
        return (cur.rowcount or 0) > 0


async def unpin_preference(
    slug: str,
    *,
    tenant_id: str = "local",
    db_path: Path | None = None,
) -> bool:
    """Rimuove pin da una preferenza.

    Returns:
        True se la preferenza esisteva ed e stata unpinned, False altrimenti.
    """
    async with _connection(db_path) as db:
        cur = await db.execute(
            "UPDATE user_profile SET pinned = 0 WHERE tenant_id = ? AND slug = ?",
            (tenant_id, slug),
        )
        await db.commit()
        return (cur.rowcount or 0) > 0


async def count_preferences(
    *,
    tenant_id: str = "local",
    db_path: Path | None = None,
) -> int:
    """Conta totale preferenze per tenant (cruscotto Conv. 41 tracciatura)."""
    async with _connection(db_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_profile WHERE tenant_id = ?",
            (tenant_id,),
        ) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0
