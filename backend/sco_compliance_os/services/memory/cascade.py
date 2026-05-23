"""Cascade promotion logic L0 → L1 → L2 per Memory Tree.

Pattern OpenHuman (clean-room reimplementation from docs):
    - L0 chunks (raw) → L1 summary quando budget token siblings > 6000.
    - L1 summary aggregati settimanali → L2 monthly (compressione cumulative ~16:1).
    - Promotion async via job queue (no LLM sync in hot path).

Pattern Karpathy "shallow + lossy summarization":
    L1 condensa preservando entità + topic, scarta dettagli stilistici.
    L2 condensa L1 settimanali a snapshot mensile, preservando timeline + temi.

Threshold operative:
    - L0 → L1 trigger: sum(token_count siblings) > 6000 OR oldest chunk > 7 days.
    - L1 → L2 trigger: numero di L1 nello stesso source/topic > 7 (weekly aggregation).

Razionale: previene "memory bloat" mantenendo navigability + ricchezza accesso
on-demand ai dettagli L0 quando serve precisione.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Sequence

import aiosqlite
import structlog

from .chunker import Chunk
from .store import default_db_path
from .summarizer import LLMClient, StubLLMClient

logger = structlog.get_logger(__name__)


# Soglie cascade (configurable)
_L0_TO_L1_BUDGET_TOKENS = 6000
_L0_TO_L1_AGE_DAYS = 7
_L1_TO_L2_COUNT_THRESHOLD = 7
_SUMMARY_TARGET_TOKENS = 1500


def _utc_now_iso() -> str:
    """Timestamp UTC ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def should_seal_l0(buffer_chunks: Sequence[Chunk]) -> tuple[bool, str]:
    """Decide se i chunks L0 nel buffer devono essere "sigillati" e promossi a L1.

    Pattern threshold:
        - Token budget > 6000: troppo materiale, condensare.
        - Oldest chunk > 7 days: materiale vecchio, snapshot.

    Args:
        buffer_chunks: chunks L0 candidati siblings (stesso source/topic).

    Returns:
        Tupla (should_seal: bool, reason: str).
    """
    if not buffer_chunks:
        return False, "empty_buffer"

    total_tokens = sum(c.token_count for c in buffer_chunks)
    if total_tokens > _L0_TO_L1_BUDGET_TOKENS:
        return True, f"budget_exceeded: {total_tokens} > {_L0_TO_L1_BUDGET_TOKENS}"

    # Check oldest chunk age
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=_L0_TO_L1_AGE_DAYS)
    oldest_iso = min((c.created_at for c in buffer_chunks), default=None)
    if oldest_iso:
        try:
            oldest = datetime.fromisoformat(oldest_iso)
            if oldest.tzinfo is None:
                oldest = oldest.replace(tzinfo=timezone.utc)
            if oldest < threshold:
                return True, f"age_exceeded: oldest {oldest_iso} > {_L0_TO_L1_AGE_DAYS}d"
        except (ValueError, TypeError):
            pass

    return False, f"below_threshold: tokens={total_tokens}, oldest={oldest_iso}"


async def promote_to_l1(
    buffer_chunks: Sequence[Chunk],
    *,
    source: str,
    topic: str | None = None,
    day: str | None = None,
    llm_client: LLMClient | None = None,
    db_path: Optional[Path] = None,
) -> dict[str, str | int | list[str]]:
    """Promuove buffer di chunks L0 a un Summary L1.

    Pipeline:
        1. Verifica should_seal_l0(buffer) — se False, no-op.
        2. Chiama summarizer LLM (Haiku) per condensare contenuti.
        3. Inserisce Summary L1 in tabella summaries con chunk_ids referenziati.
        4. Ritorna dict con summary_id + statistiche.

    Args:
        buffer_chunks: chunks L0 da sigillare.
        source: identifier sorgente per Summary.source.
        topic: topic opzionale.
        day: data ISO YYYY-MM-DD opzionale.
        llm_client: client LLM (default StubLLMClient se None).
        db_path: path al DB.

    Returns:
        dict con campi: summary_id, level, token_count, chunk_count, reason.
    """
    should_seal, reason = should_seal_l0(buffer_chunks)
    if not should_seal:
        logger.info("cascade.promote_l1.skip", reason=reason)
        return {
            "summary_id": "",
            "level": 1,
            "token_count": 0,
            "chunk_count": 0,
            "reason": reason,
        }

    chunks_list = list(buffer_chunks)
    chunk_ids = [c.id for c in chunks_list]
    total_input_tokens = sum(c.token_count for c in chunks_list)

    # Build LLM prompt + invoke
    client = llm_client or StubLLMClient()
    prompt = (
        "Sintetizza i seguenti chunks markdown preservando concetti chiave, "
        "entità normative (D.Lgs., Reg. UE, ISO, ACN, ENISA, ecc.) e riferimenti "
        f"puntuali. Target: ~{_SUMMARY_TARGET_TOKENS} token. Output in italiano.\n\n"
    )
    for c in chunks_list:
        breadcrumb = " > ".join(c.heading_path) or "(no heading)"
        prompt += f"### {breadcrumb}\n{c.content_md}\n\n"

    try:
        summary_md = await client.complete(prompt, max_tokens=_SUMMARY_TARGET_TOKENS)
    except (NotImplementedError, Exception) as e:
        logger.warning("cascade.promote_l1.llm_fallback", error=str(e))
        # Fallback placeholder
        summary_md = _build_placeholder_summary(chunks_list)

    # Insert Summary L1 in DB
    summary_id = str(uuid.uuid4())
    now_iso = _utc_now_iso()
    token_count = len(summary_md) // 4  # heuristic

    path = db_path or default_db_path()
    async with aiosqlite.connect(path) as db:
        await db.execute(
            """INSERT INTO summaries
            (id, level, source, topic, day, content, parent_id, chunk_ids,
             token_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)""",
            (
                summary_id,
                1,
                source,
                topic,
                day,
                summary_md,
                json.dumps(chunk_ids, ensure_ascii=False),
                token_count,
                now_iso,
                now_iso,
            ),
        )
        await db.commit()

    logger.info(
        "cascade.promote_l1.success",
        summary_id=summary_id,
        source=source,
        topic=topic,
        day=day,
        chunk_count=len(chunks_list),
        input_tokens=total_input_tokens,
        summary_tokens=token_count,
        reason=reason,
    )

    return {
        "summary_id": summary_id,
        "level": 1,
        "token_count": token_count,
        "chunk_count": len(chunks_list),
        "input_tokens": total_input_tokens,
        "reason": reason,
        "chunk_ids": chunk_ids,
    }


def _build_placeholder_summary(chunks: list[Chunk]) -> str:
    """Build placeholder summary fallback (no LLM)."""
    lines = [
        "# Memory Tree L1 — Summary placeholder",
        f"\n*Auto-generated da {len(chunks)} chunks L0.*\n",
    ]
    for idx, c in enumerate(chunks, start=1):
        breadcrumb = " > ".join(c.heading_path) or "(no heading)"
        excerpt = c.content_md.strip().replace("\n", " ")[:200]
        lines.append(f"## {idx}. {breadcrumb}\n\n{excerpt}...")
    return "\n\n".join(lines)


async def aggregate_l1_to_l2(
    summaries_l1: Sequence[dict[str, str | int | list[str]]],
    *,
    source: str,
    topic: str | None = None,
    llm_client: LLMClient | None = None,
    db_path: Optional[Path] = None,
) -> dict[str, str | int | list[str]]:
    """Aggrega N Summary L1 in un Summary L2 (weekly/monthly aggregation).

    Trigger threshold: >= 7 L1 summaries nello stesso source/topic.

    Pattern aggregazione:
        - Carica content di tutti i Summary L1.
        - Invoca LLM con prompt aggregato.
        - Inserisce Summary L2 con parent_id = NULL, chunk_ids = [L1_ids].

    Args:
        summaries_l1: lista di dict ritornati da promote_to_l1 (o ricaricati da DB).
        source: identifier sorgente.
        topic: topic opzionale.
        llm_client: client LLM.
        db_path: path al DB.

    Returns:
        dict con summary_id L2 + statistiche.
    """
    if len(summaries_l1) < _L1_TO_L2_COUNT_THRESHOLD:
        logger.info(
            "cascade.aggregate_l2.skip",
            count=len(summaries_l1),
            threshold=_L1_TO_L2_COUNT_THRESHOLD,
        )
        return {
            "summary_id": "",
            "level": 2,
            "token_count": 0,
            "child_count": 0,
            "reason": f"count_below_threshold: {len(summaries_l1)} < {_L1_TO_L2_COUNT_THRESHOLD}",
        }

    l1_ids: list[str] = []
    aggregate_content: list[str] = []
    total_input_tokens = 0

    path = db_path or default_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        for s in summaries_l1:
            sid = s.get("summary_id", "")
            if not isinstance(sid, str) or not sid:
                continue
            l1_ids.append(sid)
            # Carica content da DB
            async with db.execute(
                "SELECT content, token_count FROM summaries WHERE id = ?",
                (sid,),
            ) as cur:
                row = await cur.fetchone()
                if row:
                    aggregate_content.append(str(row["content"]))
                    total_input_tokens += int(row["token_count"])

    client = llm_client or StubLLMClient()
    prompt = (
        "Aggrega in un summary L2 i seguenti summary L1 settimanali, preservando "
        "temi cumulativi, entità ricorrenti, evoluzione temporale. "
        f"Target: ~{_SUMMARY_TARGET_TOKENS} token. Output in italiano.\n\n"
    )
    for idx, content in enumerate(aggregate_content, start=1):
        prompt += f"--- L1 #{idx} ---\n{content}\n\n"

    try:
        summary_md = await client.complete(prompt, max_tokens=_SUMMARY_TARGET_TOKENS)
    except (NotImplementedError, Exception) as e:
        logger.warning("cascade.aggregate_l2.llm_fallback", error=str(e))
        summary_md = (
            f"# Memory Tree L2 — Aggregate placeholder\n\n"
            f"Aggregazione di {len(l1_ids)} Summary L1 per source={source}, topic={topic}.\n"
            f"Total input tokens: {total_input_tokens}."
        )

    # Insert Summary L2
    summary_id = str(uuid.uuid4())
    now_iso = _utc_now_iso()
    token_count = len(summary_md) // 4

    async with aiosqlite.connect(path) as db:
        await db.execute(
            """INSERT INTO summaries
            (id, level, source, topic, day, content, parent_id, chunk_ids,
             token_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, NULL, ?, NULL, ?, ?, ?, ?)""",
            (
                summary_id,
                2,
                source,
                topic,
                summary_md,
                json.dumps(l1_ids, ensure_ascii=False),
                token_count,
                now_iso,
                now_iso,
            ),
        )
        # Aggiorna parent_id dei L1 figli
        await db.executemany(
            "UPDATE summaries SET parent_id = ?, updated_at = ? WHERE id = ?",
            [(summary_id, now_iso, l1_id) for l1_id in l1_ids],
        )
        await db.commit()

    logger.info(
        "cascade.aggregate_l2.success",
        summary_id=summary_id,
        source=source,
        topic=topic,
        child_count=len(l1_ids),
        input_tokens=total_input_tokens,
        summary_tokens=token_count,
    )

    return {
        "summary_id": summary_id,
        "level": 2,
        "token_count": token_count,
        "child_count": len(l1_ids),
        "input_tokens": total_input_tokens,
        "chunk_ids": l1_ids,
    }
