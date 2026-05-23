"""Modello SQLAlchemy `Score` per Memory Tree scoring + hotness decay.

Pattern OpenHuman (clean-room reimplementation from docs):
    - fast_score = euristiche regex sync (entity match, freshness, lunghezza)
    - deep_score = LLM batch async (Haiku 4.5 scoring relevance + entity extraction)
    - hotness = decay temporale con access count boost

Tre componenti separati per disaccoppiare: il fast_score è sempre calcolato
sync alla ingestion (no LLM call), il deep_score è async batch via job queue
(costo controllato), la hotness vive nel ranking runtime per retrieval.

Pattern Karpathy "single source of truth": ogni chunk ha al massimo una row
Score (chunk_id UNIQUE), updated_at riflette ultimo refresh.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .summary import Base


def _utc_now_iso() -> str:
    """Timestamp UTC ISO 8601."""
    return datetime.now(UTC).isoformat()


def _new_uuid() -> str:
    """UUID v4 string per PK."""
    return str(uuid.uuid4())


class Score(Base):
    """Score per chunk del Memory Tree (fast + deep + hotness).

    Attributes:
        id: UUID v4 string PK.
        chunk_id: FK verso memory_chunks.id (UNIQUE — un solo Score per chunk).
        fast_score: float 0.0-1.0 calcolato sync via regex/heuristics.
        deep_score: float 0.0-1.0 da LLM batch Haiku, NULL se non ancora processato.
        hotness: float 0.0-1.0 con decay esponenziale (0.95/day no-access).
        last_accessed: timestamp UTC ISO ultimo access.
        access_count: contatore access (boost hotness +0.1 cap 1.0).
        updated_at: timestamp UTC ISO ultimo refresh row.

    Indici:
        (chunk_id) UNIQUE
        (hotness DESC) per top-N retrieval rapido
    """

    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_new_uuid,
        doc="UUID v4 string PK.",
    )

    chunk_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        doc="FK verso memory_chunks.id (logical FK, no constraint per perf bulk).",
    )

    fast_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Score sincrono regex/heuristics 0.0-1.0.",
    )

    deep_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Score LLM async Haiku 0.0-1.0, NULL se non ancora processato.",
    )

    hotness: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Hotness ranking con decay 0.95/day, boost +0.1/access cap 1.0.",
    )

    last_accessed: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        doc="Timestamp UTC ISO ultimo access del chunk.",
    )

    access_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Contatore access cumulativo.",
    )

    updated_at: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=_utc_now_iso,
        onupdate=_utc_now_iso,
        doc="Timestamp UTC ISO ultimo refresh row.",
    )

    __table_args__ = (
        UniqueConstraint("chunk_id", name="uq_scores_chunk_id"),
        Index("idx_scores_chunk_id", "chunk_id"),
        Index("idx_scores_hotness_desc", "hotness"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Serializza in dict JSON-safe (API response)."""
        return {
            "id": self.id,
            "chunk_id": self.chunk_id,
            "fast_score": self.fast_score,
            "deep_score": self.deep_score,
            "hotness": self.hotness,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "updated_at": self.updated_at,
        }

    def __repr__(self) -> str:
        return (
            f"Score(chunk_id={self.chunk_id[:8]}..., "
            f"fast={self.fast_score:.3f}, deep={self.deep_score}, "
            f"hot={self.hotness:.3f}, accesses={self.access_count})"
        )
