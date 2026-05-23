"""Scoring chunks OpenHuman replica — fast_score (sync regex) + deep_score (async LLM).

Pattern OpenHuman (clean-room reimplementation from public docs):
    - fast_score_sync(chunk) → euristiche regex + lunghezza + freshness, NO LLM call.
      Sempre disponibile alla ingestion. Output float 0.0-1.0.
    - deep_score_async(chunk_ids) → batch Claude Haiku 4.5 con prompt scoring.
      Async via job queue, cost-controlled. Output {chunk_id: (score, entity_list)}.

Razionale architetturale: separa scoring "hot path" (deve girare a ogni ingest
senza latenza LLM) da scoring "cold batch" (LLM con costo, può attendere).

NOTA path: questo file NON sovrascrive `scorer.py` esistente (che implementa
BM25 query-time ranking, scopo diverso). Il main agent ha facoltà di decidere
se unificare i due file in un solo modulo `scoring/` con sotto-moduli o
lasciare la dual-file separation per chiarezza semantica.

Pattern Karpathy "single source of truth": entity extraction è inline nel
deep_score (no doppio LLM call), output entity_list popola entity_index.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from .chunker import Chunk

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# FAST SCORE — regex/heuristics sync, NO LLM call
# ---------------------------------------------------------------------------

# Pattern normativi italiani: D.Lgs. NNN/YYYY, Reg. UE NNNN/YYYY, ISO/IEC NNNNN
_NORM_PATTERNS = [
    re.compile(r"\bD\.?Lgs\.?\s+\d+/\d{4}\b", re.IGNORECASE),
    re.compile(r"\bReg(?:olamento)?\.?\s+UE\s+\d+/\d{4}\b", re.IGNORECASE),
    re.compile(r"\bISO(?:/IEC)?\s+\d+(?::\d{4})?\b", re.IGNORECASE),
    re.compile(r"\bL(?:egge)?\.?\s+\d+/\d{4}\b", re.IGNORECASE),
    re.compile(r"\bDPR\s+\d+/\d{4}\b", re.IGNORECASE),
    re.compile(r"\bDM\s+\d+(?:/\d+)?/\d{4}\b", re.IGNORECASE),
    re.compile(r"\bNIS\s*2\b", re.IGNORECASE),
    re.compile(r"\bGDPR\b"),
    re.compile(r"\bAI\s*Act\b", re.IGNORECASE),
]

# Pattern entity authorities italiane (ACN, AGENAS, AgID, Garante, ENISA)
_AUTHORITY_PATTERNS = [
    re.compile(r"\bACN\b"),
    re.compile(r"\bAGENAS\b", re.IGNORECASE),
    re.compile(r"\bAgID\b", re.IGNORECASE),
    re.compile(r"\bGarante\s+(?:Privacy|della\s+Privacy)\b", re.IGNORECASE),
    re.compile(r"\bENISA\b"),
    re.compile(r"\bCSIRT(?:-Italia)?\b", re.IGNORECASE),
]


@dataclass(slots=True)
class FastScoreResult:
    """Risultato fast_score sync per un singolo chunk.

    Attributes:
        chunk_id: ID del chunk scorato.
        fast_score: score finale aggregato 0.0-1.0.
        norm_matches: numero di pattern normativi matchati.
        authority_matches: numero di pattern authority matchati.
        length_factor: fattore lunghezza (chunk troppo corti penalizzati).
        freshness_factor: fattore freshness (chunk recenti boostati).
    """

    chunk_id: str
    fast_score: float
    norm_matches: int = 0
    authority_matches: int = 0
    length_factor: float = 0.0
    freshness_factor: float = 0.0


def _freshness_score(created_at_iso: str, half_life_days: float = 30.0) -> float:
    """Score freshness con decay esponenziale (half-life 30 giorni default).

    Args:
        created_at_iso: timestamp ISO 8601 di creazione chunk.
        half_life_days: half-life del decay (default 30 giorni).

    Returns:
        float 0.0-1.0 (chunk recente = 1.0, chunk vecchio → 0).
    """
    try:
        created = datetime.fromisoformat(created_at_iso)
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return 0.0
    now = datetime.now(UTC)
    age_days = (now - created).total_seconds() / 86400.0
    if age_days < 0:
        return 1.0
    # exp(-ln(2) * age / half_life) — half_life days → 0.5
    import math

    return math.exp(-math.log(2) * age_days / max(half_life_days, 1.0))


def _length_factor(token_count: int, ideal_min: int = 100, ideal_max: int = 2000) -> float:
    """Fattore lunghezza: penalizza chunks <100 token o >2000 token.

    Args:
        token_count: numero di token nel chunk.
        ideal_min: soglia minima ideale (default 100).
        ideal_max: soglia massima ideale (default 2000).

    Returns:
        float 0.0-1.0.
    """
    if token_count < ideal_min:
        # Penalizza chunks troppo corti (probabile rumore).
        return token_count / ideal_min
    if token_count > ideal_max:
        # Penalizza chunks troppo lunghi (probabile non chunked bene).
        excess = token_count - ideal_max
        return max(0.3, 1.0 - excess / (ideal_max * 2.0))
    return 1.0


def fast_score_sync(chunk: Chunk) -> FastScoreResult:
    """Calcola fast_score sincrono via regex + euristiche per un chunk.

    NO LLM call. Sempre disponibile alla ingestion (hot path).

    Componenti score:
        - norm_density: numero di pattern normativi / 10 (cap 1.0)
        - authority_density: numero di pattern authority / 5 (cap 1.0)
        - length_factor: 0.0-1.0 in base a token_count
        - freshness_factor: 0.0-1.0 decay esponenziale half-life 30d

    Aggregazione: media pesata (40% norm + 20% authority + 20% length + 20% freshness).

    Args:
        chunk: Chunk da scorare.

    Returns:
        FastScoreResult con score finale + componenti.
    """
    text = chunk.content_md or ""

    norm_count = sum(len(p.findall(text)) for p in _NORM_PATTERNS)
    auth_count = sum(len(p.findall(text)) for p in _AUTHORITY_PATTERNS)

    norm_density = min(1.0, norm_count / 10.0)
    auth_density = min(1.0, auth_count / 5.0)
    length_f = _length_factor(chunk.token_count)
    freshness_f = _freshness_score(chunk.created_at)

    final_score = 0.40 * norm_density + 0.20 * auth_density + 0.20 * length_f + 0.20 * freshness_f

    return FastScoreResult(
        chunk_id=chunk.id,
        fast_score=round(final_score, 4),
        norm_matches=norm_count,
        authority_matches=auth_count,
        length_factor=round(length_f, 4),
        freshness_factor=round(freshness_f, 4),
    )


def fast_score_batch(chunks: Iterable[Chunk]) -> list[FastScoreResult]:
    """Versione batch sincrona di fast_score_sync.

    Args:
        chunks: iterabile di Chunk.

    Returns:
        Lista di FastScoreResult ordinata DESC per fast_score.
    """
    results = [fast_score_sync(c) for c in chunks]
    results.sort(key=lambda r: r.fast_score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# DEEP SCORE — async LLM batch Claude Haiku 4.5
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DeepScoreResult:
    """Risultato deep_score async per un singolo chunk.

    Attributes:
        chunk_id: ID del chunk scorato.
        deep_score: score relevance 0.0-1.0 da LLM.
        entities: lista entity estratte (es. ['NIS2', 'ACN', 'D.Lgs. 138/2024']).
        topic: topic prevalente identificato (es. 'cybersicurezza').
        reasoning: breve motivazione (debug/audit trail).
    """

    chunk_id: str
    deep_score: float
    entities: list[str] = field(default_factory=list)
    topic: str | None = None
    reasoning: str = ""


_DEEP_SCORE_PROMPT_TEMPLATE = """Sei un classificatore di rilevanza di chunks markdown per un knowledge base di consulenza compliance italiana (NIS2, ISO 27001, GDPR, AI Act, accreditamento sanitario).

Per ciascuno dei seguenti chunks, restituisci JSON con:
- "id": id del chunk
- "score": float 0.0-1.0 di rilevanza per consulenza compliance (1.0 = altissimo valore consulenziale, 0.0 = rumore)
- "entities": array di entity normative/standard/authority menzionate (es. ["NIS2", "ACN"])
- "topic": topic prevalente in italiano lowercase (es. "cybersicurezza", "privacy-protezione-dati", "qualita-sgq")
- "reasoning": una frase breve in italiano di motivazione

Output JSON puro, array di oggetti, niente prefissi o commenti.

CHUNKS:

{chunks_text}
"""


async def deep_score_async(
    chunks: Sequence[Chunk],
    *,
    model: str = "claude-haiku-4-5-20251001",
    batch_size: int = 10,
    max_concurrent: int = 3,
) -> list[DeepScoreResult]:
    """Score profondo via LLM batch per una lista di chunks.

    Pattern: batch chunks in gruppi di `batch_size`, invio in parallelo
    con semaforo di `max_concurrent`. Output JSON parsato e validato.

    NOTA: questo è scaffold async. La chiamata Anthropic SDK reale richiede
    `anthropic_api_key` o `license_key` configurati. In assenza di token,
    ritorna risultati con deep_score=0.5 (neutral) + reasoning="LLM not configured".

    Args:
        chunks: sequenza di Chunk da scorare.
        model: model slug Anthropic (default Claude Haiku 4.5).
        batch_size: numero di chunks per batch LLM call.
        max_concurrent: numero massimo di batch in parallelo.

    Returns:
        Lista di DeepScoreResult (stesso ordine di input).
    """
    if not chunks:
        return []

    chunks_list = list(chunks)
    logger.info(
        "deep_score.start",
        chunk_count=len(chunks_list),
        batch_size=batch_size,
        model=model,
    )

    # Verifica disponibilità Anthropic client (lazy import per non rompere test offline).
    try:
        from sco_compliance_os.config import get_settings

        settings = get_settings()
        api_key = settings.anthropic_api_key.get_secret_value()
        license_key = settings.license_key.get_secret_value()
        has_credentials = bool(api_key or license_key)
    except Exception as e:
        logger.warning("deep_score.config_load_failed", error=str(e))
        has_credentials = False

    if not has_credentials:
        logger.warning(
            "deep_score.no_credentials",
            note="returning neutral 0.5 scores, configure anthropic_api_key or license_key",
        )
        return [
            DeepScoreResult(
                chunk_id=c.id,
                deep_score=0.5,
                entities=[],
                topic=None,
                reasoning="LLM not configured (neutral fallback)",
            )
            for c in chunks_list
        ]

    # Batching + concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)
    batches = [chunks_list[i : i + batch_size] for i in range(0, len(chunks_list), batch_size)]

    async def _score_batch(batch: list[Chunk]) -> list[DeepScoreResult]:
        async with semaphore:
            return await _llm_score_batch(batch, model=model)

    batch_results = await asyncio.gather(
        *(_score_batch(b) for b in batches),
        return_exceptions=True,
    )

    # Flatten + gestione errori
    final_results: list[DeepScoreResult] = []
    for idx, result in enumerate(batch_results):
        if isinstance(result, BaseException):
            logger.error(
                "deep_score.batch_failed",
                batch_idx=idx,
                error=str(result),
            )
            # Fallback neutral per il batch fallito
            for c in batches[idx]:
                final_results.append(
                    DeepScoreResult(
                        chunk_id=c.id,
                        deep_score=0.5,
                        entities=[],
                        reasoning=f"batch failed: {result}",
                    )
                )
        else:
            final_results.extend(result)

    logger.info(
        "deep_score.complete",
        chunk_count=len(chunks_list),
        result_count=len(final_results),
    )
    return final_results


async def _llm_score_batch(
    batch: list[Chunk],
    *,
    model: str,
) -> list[DeepScoreResult]:
    """Invoca LLM Claude su un singolo batch di chunks.

    Args:
        batch: lista di chunks per il batch.
        model: model slug.

    Returns:
        Lista di DeepScoreResult per il batch.
    """
    from sco_compliance_os.config import get_settings

    settings = get_settings()
    api_key = settings.anthropic_api_key.get_secret_value()
    license_key = settings.license_key.get_secret_value()

    # Build chunks_text per prompt
    chunks_text_parts: list[str] = []
    for c in batch:
        chunks_text_parts.append(f"--- id: {c.id} ---\n{c.content_md[:2000]}\n")
    chunks_text = "\n".join(chunks_text_parts)

    prompt = _DEEP_SCORE_PROMPT_TEMPLATE.format(chunks_text=chunks_text)

    # Choose client: license_key → SaaS proxy, else direct anthropic
    try:
        from anthropic import AsyncAnthropic

        # cast Any: AsyncAnthropic ha union types overload non amici di **dict[str, str]
        client_kwargs: dict[str, Any] = {}
        if license_key:
            client_kwargs["base_url"] = settings.sco_saas_base_url
            client_kwargs["api_key"] = license_key
        else:
            client_kwargs["api_key"] = api_key

        client = AsyncAnthropic(**client_kwargs)

        response = await client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response
        text_blocks = [block.text for block in response.content if hasattr(block, "text")]
        raw_text = "\n".join(text_blocks).strip()

        # Parse JSON output
        # Strip markdown code fence if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]
            raw_text = raw_text.strip()
        # Remove leading "json" tag if present
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()

        parsed = json.loads(raw_text)
        if not isinstance(parsed, list):
            raise ValueError(f"Expected list, got {type(parsed).__name__}")

        results: list[DeepScoreResult] = []
        chunk_ids_in_batch = {c.id for c in batch}
        for item in parsed:
            cid = item.get("id", "")
            if cid not in chunk_ids_in_batch:
                continue
            results.append(
                DeepScoreResult(
                    chunk_id=cid,
                    deep_score=float(item.get("score", 0.5)),
                    entities=list(item.get("entities", [])),
                    topic=item.get("topic"),
                    reasoning=str(item.get("reasoning", "")),
                )
            )

        # Fallback per chunks mancanti nella response
        scored_ids = {r.chunk_id for r in results}
        for c in batch:
            if c.id not in scored_ids:
                results.append(
                    DeepScoreResult(
                        chunk_id=c.id,
                        deep_score=0.5,
                        entities=[],
                        reasoning="missing from LLM response",
                    )
                )
        return results

    except Exception as e:
        logger.error("deep_score.llm_call_failed", error=str(e), model=model)
        # Fallback neutral
        return [
            DeepScoreResult(
                chunk_id=c.id,
                deep_score=0.5,
                entities=[],
                reasoning=f"LLM call failed: {e}",
            )
            for c in batch
        ]
