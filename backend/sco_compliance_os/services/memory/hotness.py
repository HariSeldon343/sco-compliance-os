"""Hotness decay temporale per chunk del Memory Tree.

Pattern OpenHuman (clean-room reimplementation from docs):
    - Hotness decay esponenziale: hotness *= 0.95 per giorno senza access.
    - Access boost: +0.1 cap 1.0 per ogni access.
    - Composite ranking: useful per retrieval "memory hot list".

Razionale: la hotness è ortogonale a fast_score / deep_score.
    - fast_score / deep_score = qualità statica del chunk (norm density, relevance).
    - hotness = quanto è "vivo" il chunk nel ranking dinamico (decay + access).

Storage: vivono entrambi nella tabella `scores` (FK chunk_id), aggiornati da
componenti diversi in momenti diversi.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite
import structlog

from .store import default_db_path

logger = structlog.get_logger(__name__)


# Decay esponenziale: 0.95^days_no_access
_DECAY_PER_DAY = 0.95

# Access boost: +0.1 per access, cap 1.0
_ACCESS_BOOST = 0.1
_HOTNESS_CAP = 1.0


@dataclass(slots=True)
class HotnessSnapshot:
    """Snapshot di hotness per un chunk.

    Attributes:
        chunk_id: ID del chunk.
        hotness: hotness corrente 0.0-1.0.
        last_accessed: ISO timestamp ultimo access (NULL se mai accesso).
        access_count: contatore access cumulativo.
        days_since_access: giorni dall'ultimo access (None se mai).
    """

    chunk_id: str
    hotness: float
    last_accessed: str | None
    access_count: int
    days_since_access: float | None = None


def _utc_now_iso() -> str:
    """Timestamp UTC ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def _days_between(iso_then: str, iso_now: str | None = None) -> float:
    """Calcola giorni tra due timestamp ISO."""
    try:
        then = datetime.fromisoformat(iso_then)
        if then.tzinfo is None:
            then = then.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.0
    if iso_now:
        try:
            now = datetime.fromisoformat(iso_now)
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            now = datetime.now(timezone.utc)
    else:
        now = datetime.now(timezone.utc)
    return (now - then).total_seconds() / 86400.0


def _apply_decay(current_hotness: float, days_no_access: float) -> float:
    """Applica decay esponenziale: hotness *= 0.95^days_no_access.

    Args:
        current_hotness: hotness corrente.
        days_no_access: giorni senza access.

    Returns:
        hotness decaduta.
    """
    if days_no_access <= 0:
        return current_hotness
    return current_hotness * math.pow(_DECAY_PER_DAY, days_no_access)


async def compute_hotness(
    chunk_id: str,
    db_path: Optional[Path] = None,
) -> float:
    """Calcola hotness corrente per un chunk applicando decay temporale.

    Legge la row scores per chunk_id, applica decay sul tempo trascorso dal
    last_accessed, ritorna il valore corrente.

    Args:
        chunk_id: ID del chunk.
        db_path: path al DB (default: ~/.sco-compliance-os/memory_tree.db).

    Returns:
        float 0.0-1.0 hotness corrente. 0.0 se chunk non trovato.
    """
    path = db_path or default_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT hotness, last_accessed, access_count FROM scores WHERE chunk_id = ?",
            (chunk_id,),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return 0.0
            base_hotness = float(row["hotness"])
            last_accessed = row["last_accessed"]
            if not last_accessed:
                return base_hotness
            days_no_access = _days_between(last_accessed)
            return _apply_decay(base_hotness, days_no_access)


async def record_access(
    chunk_id: str,
    db_path: Optional[Path] = None,
) -> HotnessSnapshot:
    """Registra un access al chunk: aggiorna hotness, last_accessed, access_count.

    Pattern:
        1. Legge state corrente da scores (o crea row se non esiste).
        2. Applica decay sul tempo trascorso.
        3. Boost: +0.1 cap 1.0.
        4. Aggiorna last_accessed = now, access_count++.

    Args:
        chunk_id: ID del chunk.
        db_path: path al DB.

    Returns:
        HotnessSnapshot aggiornato.
    """
    path = db_path or default_db_path()
    now_iso = _utc_now_iso()

    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row

        # Carica row esistente o crea
        async with db.execute(
            "SELECT id, hotness, last_accessed, access_count FROM scores WHERE chunk_id = ?",
            (chunk_id,),
        ) as cur:
            row = await cur.fetchone()

        if row:
            current_hotness = float(row["hotness"])
            last_acc = row["last_accessed"]
            access_count = int(row["access_count"]) + 1

            # Decay sul tempo da last_accessed (se presente)
            if last_acc:
                days_no_access = _days_between(last_acc, now_iso)
                current_hotness = _apply_decay(current_hotness, days_no_access)

            # Boost access
            new_hotness = min(_HOTNESS_CAP, current_hotness + _ACCESS_BOOST)

            await db.execute(
                """UPDATE scores
                SET hotness = ?, last_accessed = ?, access_count = ?, updated_at = ?
                WHERE chunk_id = ?""",
                (new_hotness, now_iso, access_count, now_iso, chunk_id),
            )
            await db.commit()

            return HotnessSnapshot(
                chunk_id=chunk_id,
                hotness=new_hotness,
                last_accessed=now_iso,
                access_count=access_count,
                days_since_access=0.0,
            )
        else:
            # Crea nuova row score con hotness iniziale = boost
            import uuid as _uuid

            new_id = str(_uuid.uuid4())
            initial_hotness = _ACCESS_BOOST
            await db.execute(
                """INSERT INTO scores (id, chunk_id, fast_score, deep_score, hotness,
                last_accessed, access_count, updated_at)
                VALUES (?, ?, 0.0, NULL, ?, ?, 1, ?)""",
                (new_id, chunk_id, initial_hotness, now_iso, now_iso),
            )
            await db.commit()

            return HotnessSnapshot(
                chunk_id=chunk_id,
                hotness=initial_hotness,
                last_accessed=now_iso,
                access_count=1,
                days_since_access=0.0,
            )


async def get_top_hot_chunks(
    n: int = 20,
    db_path: Optional[Path] = None,
) -> list[HotnessSnapshot]:
    """Ritorna i top-N chunks per hotness corrente (decay applicato).

    Args:
        n: numero massimo di risultati.
        db_path: path al DB.

    Returns:
        Lista ordinata DESC per hotness con decay applicato.
    """
    path = db_path or default_db_path()
    snapshots: list[HotnessSnapshot] = []
    now_iso = _utc_now_iso()

    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        # Carica top 4*n da scores (poi applichiamo decay e re-rank)
        async with db.execute(
            """SELECT chunk_id, hotness, last_accessed, access_count
            FROM scores
            ORDER BY hotness DESC
            LIMIT ?""",
            (n * 4,),
        ) as cur:
            async for row in cur:
                chunk_id = row["chunk_id"]
                base_hotness = float(row["hotness"])
                last_acc = row["last_accessed"]
                access_count = int(row["access_count"])

                if last_acc:
                    days_no_access = _days_between(last_acc, now_iso)
                    current_hotness = _apply_decay(base_hotness, days_no_access)
                else:
                    days_no_access = None
                    current_hotness = base_hotness

                snapshots.append(
                    HotnessSnapshot(
                        chunk_id=chunk_id,
                        hotness=current_hotness,
                        last_accessed=last_acc,
                        access_count=access_count,
                        days_since_access=days_no_access,
                    )
                )

    # Re-rank dopo decay applicato
    snapshots.sort(key=lambda s: s.hotness, reverse=True)
    logger.info("hotness.top.computed", n=n, returned=len(snapshots[:n]))
    return snapshots[:n]


async def batch_decay_refresh(
    db_path: Optional[Path] = None,
) -> int:
    """Refresh batch: applica decay a tutte le rows scores e aggiorna hotness.

    Job da eseguire una volta al giorno (background) per consolidare la hotness
    nel DB invece di calcolarla on-the-fly ad ogni query.

    Args:
        db_path: path al DB.

    Returns:
        Numero di rows aggiornate.
    """
    path = db_path or default_db_path()
    now_iso = _utc_now_iso()
    updated_count = 0

    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, chunk_id, hotness, last_accessed FROM scores WHERE last_accessed IS NOT NULL"
        ) as cur:
            rows = await cur.fetchall()

        for row in rows:
            row_id = row["id"]
            base_hotness = float(row["hotness"])
            last_acc = row["last_accessed"]
            days_no_access = _days_between(last_acc, now_iso)
            if days_no_access < 1.0:
                continue  # No update needed if < 1 day
            new_hotness = _apply_decay(base_hotness, days_no_access)
            await db.execute(
                """UPDATE scores SET hotness = ?, updated_at = ? WHERE id = ?""",
                (new_hotness, now_iso, row_id),
            )
            updated_count += 1

        await db.commit()

    logger.info("hotness.batch_decay.complete", updated=updated_count)
    return updated_count
