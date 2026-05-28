"""Memory Tree bucket-seal — Fase 4: Sealing L0->L1->L2->L3.

Clean-room reimplementation ispirata a OpenHuman MEMORY_ARCHITECTURE_LLD
(NO code copy GPL).

Architettura 3 alberi concentrici + 3 livelli di sealing:

    tree_source       -> 1 albero per source (chat_thread, email_account, doc).
    tree_topic        -> cluster di chunk simili per topic.
    tree_global       -> radice utente (cumulativa).

Token thresholds sealing (allineati a OpenHuman LLD):

    L0 (raw chunks)   -> buffer fino a SEAL_L1_THRESHOLD_TOKENS (32k cumulativi)
                      -> seal in summary L1 (~2k token)
    L1 (sealed)       -> buffer fino a SEAL_L2_THRESHOLD_TOKENS (16k cumulativi)
                      -> seal in summary L2 (~1k token)
    L2 (sealed)       -> buffer fino a SEAL_L3_THRESHOLD_TOKENS (8k cumulativi)
                      -> seal in summary L3 (~500 token, "SCO radice")

Pattern SCO "schema is the product":
    - TreeSummary dataclass riflette mem_tree_summaries SQLite schema 1:1.
    - Stable IDs via hash(tree_kind + tree_id + level + children_ids).
    - No hallucination: lista vuota -> no summary creata.

Pattern Conv. 41 (tracciatura): logger structured ogni seal + count children
+ cost LLM summarization stimato.

Pattern Conv. 44 lesson 1 (CircuitBreaker): riusa _tree_breaker da tree_store
per protezione DB ops Fase 4.

Pattern Conv. 47 (single source of truth): TreeSummary persisted in
mem_tree_summaries SQLite, MAI cached in memoria applicativa.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import aiosqlite

from .tree_chunker import TreeChunk, count_tokens
from .tree_store import (
    CircuitBreakerOpenError,
    _connection,
    _tree_breaker,
    get_admitted_chunks_for_seal,
    list_distinct_sources,
    mark_chunks_sealed,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# THRESHOLDS — sealing cascading L0 -> L1 -> L2 -> L3
# --------------------------------------------------------------------------

# Soglie token cumulativi per innescare seal verso il livello successivo.
SEAL_L1_THRESHOLD_TOKENS = 32_000  # L0 buffer -> L1 summary
SEAL_L2_THRESHOLD_TOKENS = 16_000  # L1 buffer -> L2 summary
SEAL_L3_THRESHOLD_TOKENS = 8_000  # L2 buffer -> L3 summary

# Target tokens output per summary di livello N.
TARGET_TOKENS_L1 = 2_000
TARGET_TOKENS_L2 = 1_000
TARGET_TOKENS_L3 = 500

# Model slug summarizer (riusa stesso modello del scoring per cost efficiency).
SUMMARIZER_MODEL = "claude-haiku-4-5-20251001"

# Cost stima ($/MTok input + output) — Haiku 4.5.
SUMMARIZER_COST_PER_INPUT_TOK = 0.80 / 1_000_000.0
SUMMARIZER_COST_PER_OUTPUT_TOK = 4.00 / 1_000_000.0

# Cap input per call summarizer (sicurezza overflow context 200k).
SUMMARIZER_MAX_INPUT_CHARS = 100_000


# --------------------------------------------------------------------------
# ENUMS + DATACLASSES
# --------------------------------------------------------------------------


class TreeKind(StrEnum):
    """Vocabolario chiuso 3 alberi concentrici (clean-room ispirato OpenHuman)."""

    SOURCE = "source"  # 1 albero per source (chat thread, email account, document)
    TOPIC = "topic"  # cluster topic-based
    GLOBAL = "global"  # radice utente cumulativa


class SummaryStatus(StrEnum):
    """Stato lifecycle della TreeSummary."""

    PENDING = "pending"  # in buffer, attende threshold per seal next level
    SEALED = "sealed"  # promosso a livello stabile (default)
    ARCHIVED = "archived"  # successivamente archiviato (post-cascade-up)


@dataclass(slots=True)
class TreeSummary:
    """Unita di summary del Memory Tree bucket-seal (Fase 4).

    Schema allineato a `mem_tree_summaries` SQLite (vedi tree_store.py).

    Attributes:
        id: stable hash(tree_kind + tree_id + level + sorted(children_chunk_ids)).
        tree_kind: source | topic | global.
        tree_id: source_id (per source) | topic_name (per topic) | 'global'.
        level: 1 / 2 / 3 (mai 0 — quello e' raw chunk).
        content_summary: markdown 200-500 parole.
        parent_summary_id: id summary L+1 padre (NULL se non ancora cascata-su).
        children_chunk_ids: lista ID chunk admitted aggregati (solo per L1).
        children_summary_ids: lista ID summaries aggregati (per L2 e L3).
        token_count: stima tokens del content_summary.
        source_kind_hint: hint del source_kind originario (per L1, NULL per L2+).
        owner: identificatore utente (default 'local').
        created_at_ms: timestamp creazione record.
        sealed_at_ms: timestamp sealing (= created_at_ms se sealed alla creazione).
        status: pending | sealed | archived (default sealed).
    """

    id: str
    tree_kind: str
    tree_id: str
    level: int
    content_summary: str
    parent_summary_id: str | None
    children_chunk_ids: list[str]
    children_summary_ids: list[str]
    token_count: int
    source_kind_hint: str | None
    owner: str
    created_at_ms: int
    sealed_at_ms: int | None
    status: str = SummaryStatus.SEALED.value

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "tree_kind": self.tree_kind,
            "tree_id": self.tree_id,
            "level": self.level,
            "content_summary": self.content_summary,
            "parent_summary_id": self.parent_summary_id,
            "children_chunk_ids": list(self.children_chunk_ids),
            "children_summary_ids": list(self.children_summary_ids),
            "token_count": self.token_count,
            "source_kind_hint": self.source_kind_hint,
            "owner": self.owner,
            "created_at_ms": self.created_at_ms,
            "sealed_at_ms": self.sealed_at_ms,
            "status": self.status,
        }


# --------------------------------------------------------------------------
# STABLE ID — deterministic hash
# --------------------------------------------------------------------------


def compute_summary_id(
    *,
    tree_kind: str,
    tree_id: str,
    level: int,
    children_ids: list[str],
) -> str:
    """Computa stable deterministic ID per una summary.

    Pattern: SHA-256(tree_kind + '|' + tree_id + '|' + level + '|' + sorted_ids).
    Idempotent: stessi children -> stesso ID -> upsert no-op.
    """
    sorted_kids = sorted(children_ids)
    payload = f"{tree_kind}|{tree_id}|{level}|{','.join(sorted_kids)}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


# --------------------------------------------------------------------------
# CRUD — mem_tree_summaries
# --------------------------------------------------------------------------


def _summary_row_to_dataclass(row: aiosqlite.Row) -> TreeSummary:
    """Deserializza row in TreeSummary."""
    try:
        children_chunk_ids = (
            json.loads(row["children_chunk_ids_json"]) if row["children_chunk_ids_json"] else []
        )
    except (json.JSONDecodeError, TypeError):
        children_chunk_ids = []
    try:
        children_summary_ids = (
            json.loads(row["children_summary_ids_json"]) if row["children_summary_ids_json"] else []
        )
    except (json.JSONDecodeError, TypeError):
        children_summary_ids = []
    return TreeSummary(
        id=row["id"],
        tree_kind=row["tree_kind"],
        tree_id=row["tree_id"],
        level=int(row["level"]),
        content_summary=row["content_summary"],
        parent_summary_id=row["parent_summary_id"],
        children_chunk_ids=children_chunk_ids,
        children_summary_ids=children_summary_ids,
        token_count=int(row["token_count"]),
        source_kind_hint=row["source_kind_hint"],
        owner=row["owner"],
        created_at_ms=int(row["created_at_ms"]),
        sealed_at_ms=(int(row["sealed_at_ms"]) if row["sealed_at_ms"] is not None else None),
        status=row["status"],
    )


async def upsert_summary(
    summary: TreeSummary,
    db_path: Path | None = None,
) -> bool:
    """Upsert idempotente di una TreeSummary via PRIMARY KEY id."""
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO mem_tree_summaries
                    (id, tree_kind, tree_id, level, content_summary,
                     parent_summary_id, children_chunk_ids_json,
                     children_summary_ids_json, token_count, source_kind_hint,
                     owner, created_at_ms, sealed_at_ms, status)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        summary.id,
                        summary.tree_kind,
                        summary.tree_id,
                        summary.level,
                        summary.content_summary,
                        summary.parent_summary_id,
                        json.dumps(summary.children_chunk_ids, ensure_ascii=False),
                        json.dumps(summary.children_summary_ids, ensure_ascii=False),
                        summary.token_count,
                        summary.source_kind_hint,
                        summary.owner,
                        summary.created_at_ms,
                        summary.sealed_at_ms,
                        summary.status,
                    ),
                )
                await db.commit()
            return True
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("upsert_summary: errore: %s", exc)
        return False


async def list_summaries(
    *,
    tree_kind: str | None = None,
    tree_id: str | None = None,
    level: int | None = None,
    owner: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Path | None = None,
) -> list[TreeSummary]:
    """Lista summaries con filtri opzionali."""
    sql = "SELECT * FROM mem_tree_summaries WHERE 1=1"
    params: list[Any] = []
    if tree_kind:
        sql += " AND tree_kind = ?"
        params.append(tree_kind)
    if tree_id:
        sql += " AND tree_id = ?"
        params.append(tree_id)
    if level is not None:
        sql += " AND level = ?"
        params.append(level)
    if owner:
        sql += " AND owner = ?"
        params.append(owner)
    sql += " ORDER BY sealed_at_ms DESC, created_at_ms DESC LIMIT ? OFFSET ?"
    params.append(limit)
    params.append(offset)
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                async with db.execute(sql, params) as cur:
                    return [_summary_row_to_dataclass(r) async for r in cur]
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("list_summaries: errore: %s", exc)
        return []


async def get_pending_summaries_for_cascade(
    *,
    tree_kind: str,
    tree_id: str,
    level: int,
    owner: str = "local",
    db_path: Path | None = None,
) -> list[TreeSummary]:
    """Recupera summaries level=N NON ancora cascated-up (parent_summary_id IS NULL)."""
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                async with db.execute(
                    """SELECT * FROM mem_tree_summaries
                    WHERE tree_kind = ? AND tree_id = ? AND level = ?
                      AND parent_summary_id IS NULL AND owner = ?
                      AND status = 'sealed'
                    ORDER BY created_at_ms ASC""",
                    (tree_kind, tree_id, level, owner),
                ) as cur:
                    return [_summary_row_to_dataclass(r) async for r in cur]
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("get_pending_summaries_for_cascade: errore: %s", exc)
        return []


async def mark_summaries_cascaded(
    summary_ids: list[str],
    parent_summary_id: str,
    db_path: Path | None = None,
) -> int:
    """Marca lista summaries come cascated (parent_summary_id puntato a livello N+1)."""
    if not summary_ids:
        return 0
    placeholders = ",".join("?" * len(summary_ids))

    sql = (
        f"UPDATE mem_tree_summaries SET parent_summary_id = ? "  # noqa: S608
        f"WHERE id IN ({placeholders})"
    )
    try:
        async with _tree_breaker:
            async with _connection(db_path) as db:
                cur = await db.execute(sql, (parent_summary_id, *summary_ids))
                await db.commit()
                return cur.rowcount or 0
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("mark_summaries_cascaded: errore: %s", exc)
        return 0


# --------------------------------------------------------------------------
# LLM SUMMARIZER — Claude Haiku 4.5
# --------------------------------------------------------------------------


_SUMMARIZER_SYSTEM_PROMPT = (
    "Sei un riassuntore tecnico per memoria persistente di Antonio Amodeo, "
    "consulente compliance italiana (Lead Auditor ISO 27001 + NIS 2 + ISO 42001 "
    "+ qualita sanitaria + farmacovigilanza + appalti pubblici).\n\n"
    "Compito: sintetizza i seguenti N elementi in markdown 200-300 parole "
    "preservando obbligatoriamente:\n"
    "  - Nomi propri (persone, organizzazioni, clienti).\n"
    "  - Date specifiche (formato originale, es. 17/04/2025).\n"
    "  - Riferimenti normativi (D.Lgs. X/Y, Reg. UE X/Y, ISO/IEC X:Y, articoli, punti).\n"
    "  - Decisioni operative (cosa fatto, cosa deciso, da chi).\n"
    "  - Sigle aziendali (NIS 2, GDPR, AI Act, ACN, AgID, Garante, AGENAS, ENISA).\n\n"
    "Tono: italiano professionale, diretto, fact-based. "
    "Niente intro friendly ('Ecco il riassunto...'). "
    "Niente em-dash decorativi. Virgolette dritte. "
    "Inizia con un paragrafo di sintesi globale poi punti tecnici se utili.\n\n"
    "Output: solo il riassunto markdown, niente preamboli."
)


async def summarize_with_llm(
    items: list[str],
    *,
    target_tokens: int,
    tree_kind: str,
    tree_id: str,
    level: int,
) -> tuple[str, int, int, float]:
    """Chiama Claude Haiku per summarize una lista di chunk/summary.

    Args:
        items: lista testi raw (chunk content per L1, summary content per L2+).
        target_tokens: budget output stimato (300 / 150 / 75 parole per L1/L2/L3).
        tree_kind / tree_id / level: contesto per logger.

    Returns:
        (summary_text, input_tokens_used, output_tokens_used, cost_usd_est).

    Fallback robusti:
        - Missing credentials -> ritorna primo chunk truncated + cost 0.
        - LLM error -> ritorna fallback minimal + cost 0.
    """
    if not items:
        return ("", 0, 0, 0.0)

    # Combina items in singolo input markdown.
    joined = "\n\n---\n\n".join(items)
    if len(joined) > SUMMARIZER_MAX_INPUT_CHARS:
        joined = joined[:SUMMARIZER_MAX_INPUT_CHARS] + "\n\n[TRUNCATED]"

    # Input prompt: enumerazione N elementi con header.
    user_msg = (
        f"Aggrega e sintetizza i seguenti {len(items)} elementi "
        f"(livello {level}, tree {tree_kind}/{tree_id}) "
        f"in massimo {target_tokens} token (~{target_tokens // 4} parole):\n\n"
        f"{joined}"
    )

    try:
        from anthropic import AsyncAnthropic

        from sco_compliance_os.core.agent_sdk_runner import _resolve_credentials
    except ImportError as exc:
        logger.warning("summarize_with_llm.import_failed", extra={"error": str(exc)})
        return (_fallback_summary(items, target_tokens), 0, 0, 0.0)

    creds = _resolve_credentials()
    if creds is None:
        logger.warning("summarize_with_llm.no_credentials")
        return (_fallback_summary(items, target_tokens), 0, 0, 0.0)

    base_url, api_key = creds
    started_ms = int(time.time() * 1000)

    try:
        client = AsyncAnthropic(base_url=base_url, api_key=api_key)
        # Output cap: target_tokens + 20% safety.
        max_output = int(target_tokens * 1.2)
        response = await client.messages.create(
            model=SUMMARIZER_MODEL,
            max_tokens=max_output,
            system=_SUMMARIZER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        elapsed_ms = int(time.time() * 1000) - started_ms
        raw_text = ""
        if response.content:
            first_block = response.content[0]
            raw_text = getattr(first_block, "text", "") or ""

        input_tok = response.usage.input_tokens
        output_tok = response.usage.output_tokens
        est_cost_usd = (
            input_tok * SUMMARIZER_COST_PER_INPUT_TOK + output_tok * SUMMARIZER_COST_PER_OUTPUT_TOK
        )

        logger.info(
            "summarize_with_llm.success",
            extra={
                "tree_kind": tree_kind,
                "tree_id": tree_id,
                "level": level,
                "input_items_count": len(items),
                "input_tokens": input_tok,
                "output_tokens": output_tok,
                "est_cost_usd": round(est_cost_usd, 6),
                "elapsed_ms": elapsed_ms,
                "summary_chars": len(raw_text),
            },
        )
        return (raw_text.strip(), input_tok, output_tok, est_cost_usd)

    except Exception as exc:
        logger.error(
            "summarize_with_llm.error",
            extra={
                "tree_kind": tree_kind,
                "tree_id": tree_id,
                "level": level,
                "exc_type": type(exc).__name__,
                "error": str(exc)[:200],
            },
        )
        return (_fallback_summary(items, target_tokens), 0, 0, 0.0)


def _fallback_summary(items: list[str], target_tokens: int) -> str:
    """Fallback summary deterministico: concatena prime righe di ogni item.

    Usato quando LLM non disponibile (no credentials / error). Mantiene
    pipeline funzionante senza bloccare ingest.
    """
    if not items:
        return ""
    target_chars = target_tokens * 4  # ~4 char/token
    parts: list[str] = ["[FALLBACK SUMMARY — LLM non disponibile]\n"]
    accumulated = len(parts[0])
    for i, item in enumerate(items):
        first_line = (item.split("\n", 1)[0] or "").strip()[:200]
        line = f"- {first_line}"
        if accumulated + len(line) > target_chars:
            parts.append(f"- [+ altri {len(items) - i} elementi non riportati]")
            break
        parts.append(line)
        accumulated += len(line) + 1
    return "\n".join(parts)


# --------------------------------------------------------------------------
# CORE FUNCTIONS — compute_seal_candidates / seal_chunks / cascade_seal
# --------------------------------------------------------------------------


async def compute_seal_candidates(
    *,
    tree_kind: str,
    tree_id: str,
    threshold_tokens: int = SEAL_L1_THRESHOLD_TOKENS,
    owner: str = "local",
    db_path: Path | None = None,
) -> list[TreeChunk]:
    """Determina lista chunk admitted da sigillare per tree_kind/tree_id.

    Logic:
        1. Recupera chunks admitted non sealed (parent_summary_id NULL).
        2. Per tree_source: filter source_id == tree_id.
        3. Accumula token cumulativo; ritorna lista quando >= threshold_tokens
           (o tutta la lista se non raggiunge mai threshold ma >= 50% threshold).

    Args:
        tree_kind: 'source' o 'global'. ('topic' non supportato in v0.6.0).
        tree_id: source_id (per source) o 'global'.
        threshold_tokens: soglia tokens cumulativi per innescare seal.

    Returns:
        Lista TreeChunk pronti per seal (o vuota se sotto-threshold).
    """
    filter_source_id = tree_id if tree_kind == TreeKind.SOURCE.value else None
    candidates = await get_admitted_chunks_for_seal(
        source_id=filter_source_id, owner=owner, db_path=db_path
    )

    if not candidates:
        return []

    total_tokens = sum(c.token_count for c in candidates)
    if total_tokens < threshold_tokens:
        # Se siamo sotto threshold ma comunque a >= 50%, ritorniamo tutto
        # (per evitare di accumulare in eterno se l'utente non genera abbastanza).
        if total_tokens >= threshold_tokens // 2:
            return candidates
        return []

    # Token cumulativi >= threshold: ritorna tutti
    return candidates


async def seal_chunks(
    chunks: list[TreeChunk],
    *,
    tree_kind: str,
    tree_id: str,
    level: int = 1,
    owner: str = "local",
    db_path: Path | None = None,
) -> TreeSummary | None:
    """Sigilla una lista di chunk in una TreeSummary di livello L=N.

    Pipeline:
        1. Verifica input non vuoto.
        2. Computa stable summary ID.
        3. Chiama LLM summarizer (Haiku 4.5 + license proxy).
        4. Persiste summary in mem_tree_summaries.
        5. Marca chunks come SEALED + parent_summary_id puntato.

    Returns:
        TreeSummary creata, None se errore.
    """
    if not chunks:
        logger.debug("seal_chunks: lista vuota, skip")
        return None

    target_tokens = (
        TARGET_TOKENS_L1 if level == 1 else TARGET_TOKENS_L2 if level == 2 else TARGET_TOKENS_L3
    )

    children_chunk_ids = [c.id for c in chunks]
    summary_id = compute_summary_id(
        tree_kind=tree_kind,
        tree_id=tree_id,
        level=level,
        children_ids=children_chunk_ids,
    )

    # Build summary content via LLM
    items_text = [c.content for c in chunks]
    summary_text, input_tok, output_tok, cost_usd = await summarize_with_llm(
        items_text,
        target_tokens=target_tokens,
        tree_kind=tree_kind,
        tree_id=tree_id,
        level=level,
    )

    if not summary_text:
        logger.warning(
            "seal_chunks: empty summary text, skip seal",
            extra={
                "tree_kind": tree_kind,
                "tree_id": tree_id,
                "level": level,
                "chunks_count": len(chunks),
            },
        )
        return None

    now_ms = int(time.time() * 1000)
    source_kind_hint = chunks[0].source_kind if chunks else None
    summary_token_count = count_tokens(summary_text)

    summary = TreeSummary(
        id=summary_id,
        tree_kind=tree_kind,
        tree_id=tree_id,
        level=level,
        content_summary=summary_text,
        parent_summary_id=None,
        children_chunk_ids=children_chunk_ids,
        children_summary_ids=[],
        token_count=summary_token_count,
        source_kind_hint=source_kind_hint,
        owner=owner,
        created_at_ms=now_ms,
        sealed_at_ms=now_ms,
        status=SummaryStatus.SEALED.value,
    )

    ok = await upsert_summary(summary, db_path=db_path)
    if not ok:
        logger.error(
            "seal_chunks: upsert_summary failed, skip mark_chunks_sealed",
            extra={"summary_id": summary_id, "tree_kind": tree_kind, "tree_id": tree_id},
        )
        return None

    marked = await mark_chunks_sealed(children_chunk_ids, summary_id, db_path=db_path)

    logger.info(
        "seal_chunks.success",
        extra={
            "summary_id": summary_id,
            "tree_kind": tree_kind,
            "tree_id": tree_id,
            "level": level,
            "chunks_count": len(chunks),
            "chunks_marked": marked,
            "input_tokens": input_tok,
            "output_tokens": output_tok,
            "summary_tokens": summary_token_count,
            "cost_usd": round(cost_usd, 6),
        },
    )
    return summary


async def seal_summaries_to_next_level(
    summaries: list[TreeSummary],
    *,
    tree_kind: str,
    tree_id: str,
    next_level: int,
    owner: str = "local",
    db_path: Path | None = None,
) -> TreeSummary | None:
    """Sigilla lista summaries di livello L=N in singola summary L=N+1.

    Cascading L1 -> L2, L2 -> L3.

    Pipeline analoga a seal_chunks ma input sono content_summary di summaries
    già sigillate al livello precedente.

    Returns:
        TreeSummary di livello next_level, None se errore.
    """
    if not summaries:
        return None

    target_tokens = (
        TARGET_TOKENS_L2 if next_level == 2 else TARGET_TOKENS_L3 if next_level == 3 else 500
    )

    children_summary_ids = [s.id for s in summaries]
    summary_id = compute_summary_id(
        tree_kind=tree_kind,
        tree_id=tree_id,
        level=next_level,
        children_ids=children_summary_ids,
    )

    items_text = [s.content_summary for s in summaries]
    summary_text, input_tok, output_tok, cost_usd = await summarize_with_llm(
        items_text,
        target_tokens=target_tokens,
        tree_kind=tree_kind,
        tree_id=tree_id,
        level=next_level,
    )

    if not summary_text:
        logger.warning(
            "seal_summaries_to_next_level: empty summary text",
            extra={"tree_kind": tree_kind, "tree_id": tree_id, "next_level": next_level},
        )
        return None

    now_ms = int(time.time() * 1000)
    summary_token_count = count_tokens(summary_text)

    summary = TreeSummary(
        id=summary_id,
        tree_kind=tree_kind,
        tree_id=tree_id,
        level=next_level,
        content_summary=summary_text,
        parent_summary_id=None,
        children_chunk_ids=[],
        children_summary_ids=children_summary_ids,
        token_count=summary_token_count,
        source_kind_hint=None,
        owner=owner,
        created_at_ms=now_ms,
        sealed_at_ms=now_ms,
        status=SummaryStatus.SEALED.value,
    )

    ok = await upsert_summary(summary, db_path=db_path)
    if not ok:
        logger.error(
            "seal_summaries_to_next_level: upsert failed",
            extra={"summary_id": summary_id},
        )
        return None

    cascaded = await mark_summaries_cascaded(children_summary_ids, summary_id, db_path=db_path)

    logger.info(
        "seal_summaries_to_next_level.success",
        extra={
            "summary_id": summary_id,
            "tree_kind": tree_kind,
            "tree_id": tree_id,
            "next_level": next_level,
            "summaries_count": len(summaries),
            "summaries_cascaded": cascaded,
            "input_tokens": input_tok,
            "output_tokens": output_tok,
            "summary_tokens": summary_token_count,
            "cost_usd": round(cost_usd, 6),
        },
    )
    return summary


async def cascade_seal(
    *,
    tree_kind: str,
    tree_id: str,
    owner: str = "local",
    force: bool = False,
    db_path: Path | None = None,
) -> dict[int, int]:
    """Esegue cascading seal L0 -> L1 -> L2 -> L3 per tree_kind/tree_id.

    Logic:
        1. Compute seal candidates L0 -> se >= L1 threshold, seal_chunks -> L1.
        2. Get pending summaries L1 -> se >= L2 threshold cumulativa, cascade -> L2.
        3. Get pending summaries L2 -> se >= L3 threshold cumulativa, cascade -> L3.

    Args:
        tree_kind: 'source' o 'global'.
        tree_id: source_id o 'global'.
        force: se True, sigilla anche sotto-threshold (utile per /seal force).

    Returns:
        Dict {level: count_summaries_created}.
    """
    out: dict[int, int] = {1: 0, 2: 0, 3: 0}

    # L0 -> L1
    l1_threshold = 1 if force else SEAL_L1_THRESHOLD_TOKENS
    candidates_l0 = await compute_seal_candidates(
        tree_kind=tree_kind,
        tree_id=tree_id,
        threshold_tokens=l1_threshold,
        owner=owner,
        db_path=db_path,
    )
    if force and not candidates_l0:
        # Force mode: prendi anche se sotto threshold, sotto-50%
        candidates_l0 = await get_admitted_chunks_for_seal(
            source_id=tree_id if tree_kind == TreeKind.SOURCE.value else None,
            owner=owner,
            db_path=db_path,
        )

    if candidates_l0:
        summary_l1 = await seal_chunks(
            candidates_l0,
            tree_kind=tree_kind,
            tree_id=tree_id,
            level=1,
            owner=owner,
            db_path=db_path,
        )
        if summary_l1 is not None:
            out[1] += 1

    # L1 -> L2
    pending_l1 = await get_pending_summaries_for_cascade(
        tree_kind=tree_kind,
        tree_id=tree_id,
        level=1,
        owner=owner,
        db_path=db_path,
    )
    total_l1_tokens = sum(s.token_count for s in pending_l1)
    l2_threshold = 1 if force else SEAL_L2_THRESHOLD_TOKENS
    if pending_l1 and (total_l1_tokens >= l2_threshold or force):
        summary_l2 = await seal_summaries_to_next_level(
            pending_l1,
            tree_kind=tree_kind,
            tree_id=tree_id,
            next_level=2,
            owner=owner,
            db_path=db_path,
        )
        if summary_l2 is not None:
            out[2] += 1

    # L2 -> L3
    pending_l2 = await get_pending_summaries_for_cascade(
        tree_kind=tree_kind,
        tree_id=tree_id,
        level=2,
        owner=owner,
        db_path=db_path,
    )
    total_l2_tokens = sum(s.token_count for s in pending_l2)
    l3_threshold = 1 if force else SEAL_L3_THRESHOLD_TOKENS
    if pending_l2 and (total_l2_tokens >= l3_threshold or force):
        summary_l3 = await seal_summaries_to_next_level(
            pending_l2,
            tree_kind=tree_kind,
            tree_id=tree_id,
            next_level=3,
            owner=owner,
            db_path=db_path,
        )
        if summary_l3 is not None:
            out[3] += 1

    logger.info(
        "cascade_seal.complete",
        extra={
            "tree_kind": tree_kind,
            "tree_id": tree_id,
            "force": force,
            "summaries_l1": out[1],
            "summaries_l2": out[2],
            "summaries_l3": out[3],
        },
    )
    return out


async def cascade_seal_all(
    *,
    owner: str = "local",
    force: bool = False,
    db_path: Path | None = None,
) -> dict[str, dict[int, int]]:
    """Esegue cascade_seal per tutti i tree_source distinti + tree_global.

    Pattern background scheduler: chiamato ogni 5 min dal lifespan main.py.

    Returns:
        Dict {tree_key: {level: count}} dove tree_key = 'source:{source_id}' o 'global'.
    """
    out: dict[str, dict[int, int]] = {}

    # 1. Tree global (cumulativa)
    out["global"] = await cascade_seal(
        tree_kind=TreeKind.GLOBAL.value,
        tree_id="global",
        owner=owner,
        force=force,
        db_path=db_path,
    )

    # 2. Tree source per ciascun source_id distinto
    sources = await list_distinct_sources(owner=owner, db_path=db_path)
    for source_kind, source_id in sources:
        tree_key = f"source:{source_kind}:{source_id}"
        out[tree_key] = await cascade_seal(
            tree_kind=TreeKind.SOURCE.value,
            tree_id=source_id,
            owner=owner,
            force=force,
            db_path=db_path,
        )

    logger.info(
        "cascade_seal_all.complete",
        extra={
            "owner": owner,
            "force": force,
            "trees_processed": len(out),
            "total_summaries_l1": sum(v.get(1, 0) for v in out.values()),
            "total_summaries_l2": sum(v.get(2, 0) for v in out.values()),
            "total_summaries_l3": sum(v.get(3, 0) for v in out.values()),
        },
    )
    return out


# --------------------------------------------------------------------------
# BM25-LIKE QUERY — relevant summaries retrieval (no vector DB)
# --------------------------------------------------------------------------


_TOKEN_SPLIT_RE = re.compile(r"\w{2,}", re.UNICODE)


def _tokenize_for_bm25(text: str) -> list[str]:
    """Tokenizzazione semplice case-insensitive per BM25 lite."""
    if not text:
        return []
    return [t.lower() for t in _TOKEN_SPLIT_RE.findall(text)]


def _bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    *,
    avg_doc_len: float,
    k1: float = 1.5,
    b: float = 0.75,
    doc_freqs: dict[str, int] | None = None,
    total_docs: int = 1,
) -> float:
    """Compute BM25 score lite per (query, document).

    Args:
        query_tokens: lista token query (case-lower).
        doc_tokens: lista token documento (case-lower).
        avg_doc_len: average doc length nel corpus.
        k1: parametro BM25 (default 1.5).
        b: parametro BM25 length normalization (default 0.75).
        doc_freqs: dict {term: number of docs containing term}. Se None usa 1.
        total_docs: numero documenti nel corpus.

    Returns:
        float score (somma su query tokens).
    """
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    doc_counter = Counter(doc_tokens)

    score = 0.0
    for term in query_tokens:
        tf = doc_counter.get(term, 0)
        if tf == 0:
            continue
        df = doc_freqs.get(term, 1) if doc_freqs else 1
        # IDF formula classica BM25
        idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * doc_len / max(avg_doc_len, 1.0))
        score += idf * (numerator / denominator)
    return score


async def query_relevant_summaries(
    query: str,
    *,
    tree_kind: str | None = None,
    top_k: int = 5,
    owner: str = "local",
    db_path: Path | None = None,
) -> list[TreeSummary]:
    """BM25-like retrieval su content_summary di tutte le mem_tree_summaries.

    Pattern SCO "no vector DB fino a ~100 fonti": BM25 keyword search
    su contenuto markdown delle summaries, ranked top-K. Stateless (no index
    precompiled) — recompute scoring ad ogni query, accettabile per <10k summaries.

    Args:
        query: testo query utente (max 500 char raccomandato).
        tree_kind: filtra per 'source' | 'topic' | 'global' (None = tutti).
        top_k: max risultati ritornati.
        owner: filtra per owner (default 'local').

    Returns:
        Lista TreeSummary top-K rank desc per BM25 score. Vuota se no match.
    """
    if not query or not query.strip():
        return []

    # Recupera corpus summaries (tutti i livelli + tree_kind filter opzionale)
    all_summaries = await list_summaries(
        tree_kind=tree_kind,
        owner=owner,
        limit=2000,  # cap protezione
        db_path=db_path,
    )

    if not all_summaries:
        return []

    query_tokens = _tokenize_for_bm25(query)
    if not query_tokens:
        return []

    # Pre-compute doc tokens + corpus stats per BM25 IDF
    docs_tokens: list[list[str]] = [_tokenize_for_bm25(s.content_summary) for s in all_summaries]
    total_docs = len(docs_tokens)
    avg_doc_len = sum(len(d) for d in docs_tokens) / max(total_docs, 1)
    doc_freqs: dict[str, int] = {}
    for doc_tokens in docs_tokens:
        for term in set(doc_tokens):
            doc_freqs[term] = doc_freqs.get(term, 0) + 1

    # Score each summary
    scored: list[tuple[float, TreeSummary]] = []
    for summary, doc_tokens in zip(all_summaries, docs_tokens, strict=False):
        if not doc_tokens:
            continue
        score = _bm25_score(
            query_tokens,
            doc_tokens,
            avg_doc_len=avg_doc_len,
            doc_freqs=doc_freqs,
            total_docs=total_docs,
        )
        if score > 0.0:
            scored.append((score, summary))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:top_k]]

    logger.info(
        "query_relevant_summaries.complete",
        extra={
            "query_len": len(query),
            "tree_kind": tree_kind,
            "corpus_size": total_docs,
            "matched_count": len(scored),
            "top_k_returned": len(top),
        },
    )
    return top


__all__ = [
    "SEAL_L1_THRESHOLD_TOKENS",
    "SEAL_L2_THRESHOLD_TOKENS",
    "SEAL_L3_THRESHOLD_TOKENS",
    "SUMMARIZER_MODEL",
    "TARGET_TOKENS_L1",
    "TARGET_TOKENS_L2",
    "TARGET_TOKENS_L3",
    "SummaryStatus",
    "TreeKind",
    "TreeSummary",
    "cascade_seal",
    "cascade_seal_all",
    "compute_seal_candidates",
    "compute_summary_id",
    "get_pending_summaries_for_cascade",
    "list_summaries",
    "mark_summaries_cascaded",
    "query_relevant_summaries",
    "seal_chunks",
    "seal_summaries_to_next_level",
    "summarize_with_llm",
    "upsert_summary",
]
