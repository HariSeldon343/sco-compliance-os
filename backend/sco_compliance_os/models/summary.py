"""Modello SQLAlchemy `Summary` per Memory Tree gerarchico.

Pattern: 3 livelli L0/L1/L2 + parent self-FK + indici composti.

Livelli:
    L0 = chunks raw (vivono in `memory_chunks` table esistente)
    L1 = summary per source/topic/day (compressione 4:1 target)
    L2 = aggregated weekly/monthly (compressione 16:1 cumulative)

Pattern Karpathy single-source-of-truth: ogni Summary L1/L2 conosce i chunk_ids
o summary_ids figli via colonna JSON. La direzione opposta è ricostruita via
query sul campo `parent_id` (no duplicazione del dato).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative SQLAlchemy v2 condivisa dai modelli OpenHuman replica."""


def _utc_now_iso() -> str:
    """Timestamp UTC ISO 8601 (string) — coerente con memory_chunks.created_at."""
    return datetime.now(UTC).isoformat()


def _new_uuid() -> str:
    """UUID v4 string per PK."""
    return str(uuid.uuid4())


class Summary(Base):
    """Summary gerarchico del Memory Tree (L0/L1/L2).

    Attributes:
        id: UUID v4 string PK.
        level: 0 = chunk leaf reference, 1 = summary per source/topic/day, 2 = aggregated.
        source: identifier sorgente (vault path, connector_id, source_type::source_id).
        topic: topic/dominio opzionale (es. 'NIS2', 'GDPR', 'ISO27001'). NULL per global.
        day: data ISO YYYY-MM-DD opzionale. NULL per topic/source level senza scope giornaliero.
        content: markdown del summary (placeholder L1, compresso L2).
        parent_id: FK self verso Summary di livello superiore (NULL per L2 roots).
        chunk_ids: JSON array di chunk_ids (L1) o summary_ids figli (L2).
        token_count: stima token nel content.
        created_at + updated_at: timestamps UTC ISO.

    Indici:
        (source, day) per query per-source-per-day fast lookup
        (topic) per topic-tree retrieval
        (parent_id) per ricostruzione gerarchia
    """

    __tablename__ = "summaries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_new_uuid,
        doc="UUID v4 string PK.",
    )

    level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="0 = chunk reference, 1 = summary, 2 = aggregated.",
    )

    source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        doc="Sorgente identifier (vault path, connector::source_id).",
    )

    topic: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Topic/dominio opzionale (NIS2, GDPR, ISO27001, ecc.).",
    )

    day: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        doc="Data ISO YYYY-MM-DD opzionale per scope giornaliero.",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        doc="Markdown del summary content.",
    )

    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("summaries.id", ondelete="SET NULL"),
        nullable=True,
        doc="FK self verso Summary parent (NULL per root).",
    )

    chunk_ids: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        doc="JSON array di chunk_ids (L1) o summary_ids figli (L2).",
    )

    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Stima token nel content.",
    )

    created_at: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=_utc_now_iso,
        doc="Timestamp UTC ISO 8601 creazione.",
    )

    updated_at: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=_utc_now_iso,
        onupdate=_utc_now_iso,
        doc="Timestamp UTC ISO 8601 ultima modifica.",
    )

    # Self-referential parent relationship (optional, lazy)
    parent: Mapped[Summary | None] = relationship(
        "Summary",
        remote_side="Summary.id",
        backref="children",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("level IN (0, 1, 2)", name="ck_summaries_level"),
        Index("idx_summaries_source_day", "source", "day"),
        Index("idx_summaries_topic", "topic"),
        Index("idx_summaries_parent", "parent_id"),
        Index("idx_summaries_level", "level"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Serializza in dict JSON-safe (API response)."""
        return {
            "id": self.id,
            "level": self.level,
            "source": self.source,
            "topic": self.topic,
            "day": self.day,
            "content": self.content,
            "parent_id": self.parent_id,
            "chunk_ids": json.loads(self.chunk_ids) if self.chunk_ids else [],
            "token_count": self.token_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def parse_day(day_val: str | date | None) -> str | None:
        """Normalizza date in stringa ISO YYYY-MM-DD."""
        if day_val is None:
            return None
        if isinstance(day_val, date):
            return day_val.isoformat()
        # Già stringa: trust caller
        return day_val

    def __repr__(self) -> str:
        return (
            f"Summary(id={self.id[:8]}..., level={self.level}, "
            f"source={self.source!r}, topic={self.topic!r}, day={self.day!r})"
        )
