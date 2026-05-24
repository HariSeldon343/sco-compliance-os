"""Memory Tree bucket-seal — Ingestion orchestrator (Fase 1 -> 2 -> 3).

Orchestra le 3 fasi di ingest del pipeline bucket-seal:

    Fase 1+2: canonicalize + chunk_text -> lista TreeChunk
    Fase 3:   admission_decision -> status admit/drop/borderline + scoring
    Persistenza: bulk_upsert_chunks con scoring_map

Fase 4 (sealing summarization tree_source/tree_topic/tree_global) e' carry-over
Sessione 7+. Per ora il pipeline si ferma al post-admission persistence.

Pattern Conv. 41 (tracciatura sessione): logger structured con esiti per
ogni chunk processed (verdict + cheap_total + reasoning).

Pattern SCO "schema is the product": output strutturato counts per status,
mai magic numbers nei log.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .tree_chunker import (
    TreeChunk,
    TreeChunkStatus,
    chunk_text,
)
from .tree_scoring import admission_decision
from .tree_store import bulk_upsert_chunks

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# DATACLASSES
# --------------------------------------------------------------------------


@dataclass(slots=True)
class IngestInput:
    """Input singolo per ingest pipeline.

    Attributes:
        source_kind: vocabolario chiuso TreeChunkSourceKind.
        source_id: identificatore opaco sorgente.
        content: testo raw da ingerire (canonicalization automatica).
        owner: default 'local'.
        timestamp_ms: timestamp evento (default = now).
        time_range_start_ms / end_ms: finestra temporale opzionale.
        tags: tag arbitrari.
    """

    source_kind: str
    source_id: str
    content: str
    owner: str = "local"
    timestamp_ms: int | None = None
    time_range_start_ms: int | None = None
    time_range_end_ms: int | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IngestCounts:
    """Risultato aggregato di un batch ingest.

    Attributes:
        admitted: chunk con cheap_total >= DEFINITE_KEEP -> status admitted.
        dropped: chunk con cheap_total <= DEFINITE_DROP -> status dropped.
        pending_extraction: chunk borderline -> status pending_extraction.
        total: totale chunk processed (admitted + dropped + pending_extraction).
        upserted: numero righe scritte in DB (puo' essere < total se errore).
    """

    admitted: int = 0
    dropped: int = 0
    pending_extraction: int = 0
    total: int = 0
    upserted: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "admitted": self.admitted,
            "dropped": self.dropped,
            "pending_extraction": self.pending_extraction,
            "total": self.total,
            "upserted": self.upserted,
        }


# --------------------------------------------------------------------------
# PIPELINE ORCHESTRATOR
# --------------------------------------------------------------------------


async def ingest_chunks(
    chunks: list[TreeChunk],
    *,
    consult_llm_on_borderline: bool = False,
    db_path: Path | None = None,
) -> IngestCounts:
    """Esegue admission gate (Fase 3) + persistenza su lista TreeChunk gia chunked.

    Args:
        chunks: lista TreeChunk in stato PENDING_EXTRACTION (output di chunk_text).
        consult_llm_on_borderline: se True consulta LLM extractor stub per borderline.
        db_path: override path DB SQLite.

    Returns:
        IngestCounts con breakdown verdetti + righe upserted.
    """
    if not chunks:
        logger.debug("ingest_chunks: lista vuota, no-op")
        return IngestCounts()

    counts = IngestCounts(total=len(chunks))
    scoring_map: dict[str, tuple[float | None, float | None, str | None]] = {}

    for ch in chunks:
        decision = await admission_decision(
            ch,
            consult_llm_on_borderline=consult_llm_on_borderline,
        )
        # Apply verdict to chunk status
        if decision.verdict == "admit":
            ch.status = TreeChunkStatus.ADMITTED.value
            counts.admitted += 1
        elif decision.verdict == "drop":
            ch.status = TreeChunkStatus.DROPPED.value
            counts.dropped += 1
        else:  # borderline
            ch.status = TreeChunkStatus.PENDING_EXTRACTION.value
            counts.pending_extraction += 1

        scoring_map[ch.id] = (
            decision.cheap_total,
            decision.llm_score,
            decision.reasoning,
        )

        logger.info(
            "tree_ingester.decision",
            extra={
                "chunk_id": ch.id,
                "source_kind": ch.source_kind,
                "source_id": ch.source_id,
                "verdict": decision.verdict,
                "cheap_total": decision.cheap_total,
                "llm_consulted": decision.llm_consulted,
                "tokens": ch.token_count,
            },
        )

    # Persistenza bulk
    upserted = await bulk_upsert_chunks(
        chunks,
        scoring_map=scoring_map,
        db_path=db_path,
    )
    counts.upserted = upserted

    logger.info(
        "tree_ingester.batch_complete",
        extra={
            "total": counts.total,
            "admitted": counts.admitted,
            "dropped": counts.dropped,
            "pending_extraction": counts.pending_extraction,
            "upserted": counts.upserted,
        },
    )
    return counts


async def ingest_inputs(
    inputs: list[IngestInput],
    *,
    consult_llm_on_borderline: bool = False,
    max_tokens: int = 3000,
    db_path: Path | None = None,
) -> IngestCounts:
    """Pipeline end-to-end: IngestInput -> chunk_text (Fase 1+2) -> ingest_chunks (Fase 3).

    Args:
        inputs: lista IngestInput grezzi.
        consult_llm_on_borderline: passa a admission_decision.
        max_tokens: budget chunk (passa a chunk_text).
        db_path: override path DB SQLite.

    Returns:
        IngestCounts aggregati su tutti gli input.
    """
    all_chunks: list[TreeChunk] = []
    for inp in inputs:
        produced = chunk_text(
            inp.content,
            source_kind=inp.source_kind,
            source_id=inp.source_id,
            owner=inp.owner,
            timestamp_ms=inp.timestamp_ms,
            time_range_start_ms=inp.time_range_start_ms,
            time_range_end_ms=inp.time_range_end_ms,
            tags=inp.tags,
            max_tokens=max_tokens,
        )
        all_chunks.extend(produced)

    if not all_chunks:
        logger.info(
            "tree_ingester.no_viable_chunks",
            extra={"input_count": len(inputs)},
        )
        return IngestCounts()

    return await ingest_chunks(
        all_chunks,
        consult_llm_on_borderline=consult_llm_on_borderline,
        db_path=db_path,
    )


__all__ = [
    "IngestCounts",
    "IngestInput",
    "ingest_chunks",
    "ingest_inputs",
]
