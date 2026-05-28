"""Memory Tree bucket-seal — Fase 3: Scoring + Admission Gate.

Pipeline 4 fasi del Memory Tree bucket-seal architecture (clean-room
reimplementation ispirata a OpenHuman MEMORY_ARCHITECTURE_LLD, NO code copy).

Questo modulo implementa Fase 3: scoring deterministico via cheap signals
(regex + length + structural cues) + admission gate con tre-soglia logic.

Thresholds (allineati a OpenHuman LLD):
    DEFINITE_KEEP  = 0.85  -> cheap-total >= 0.85 admit no LLM call
    DEFINITE_DROP  = 0.15  -> cheap-total <= 0.15 drop  no LLM call
    DROP_BASELINE  = 0.30  -> threshold base sotto cui cheap signals scartano
    BORDERLINE     = (0.15, 0.85)  -> consulta LLM extractor

Razionale tre-soglia:
    - Hot path: 80%+ dei chunk classificabili senza LLM (cost-zero, sub-ms).
    - LLM call solo per il 5-15% borderline (cost-controlled).
    - Asimmetria conservativa: DEFINITE_KEEP > DEFINITE_DROP per evitare false drop.

Pattern SCO "schema is the product":
    - cheap_signals() ritorna dict[str, float] strutturato, mai magic numbers.
    - Pesi aggregazione documentati in CHEAP_WEIGHTS.
    - LLM extractor REAL: Claude Haiku 4.5 via Anthropic SDK + license proxy SaaS.

Pattern Conv. 34 (spot check post-multi-agent): LLM extractor reale dichiara
esplicitamente l'incertezza nel campo `reasoning`, fallback 0.5 borderline su
ogni errore.

Pattern Conv. 47 (single source of truth costanti): score LLM cached in
SQLite `mem_llm_score_cache` (chunk_id_hash PK). Stessa content -> stesso
hash -> cache hit -> zero cost ri-extraction.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass

from .tree_chunker import TreeChunk

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# LLM EXTRACTOR — config Claude Haiku 4.5
# --------------------------------------------------------------------------

# Model slug per scoring borderline (cost ~$0.80/MTok input, ~$4/MTok output).
LLM_SCORE_MODEL = "claude-haiku-4-5-20251001"

# Max output tokens: 10 sufficienti per singolo float (es. "0.73\n").
LLM_SCORE_MAX_OUTPUT = 10

# Prompt sistema corto: classificatore numerico 0.0-1.0.
LLM_SCORE_SYSTEM = (
    "Sei un classificatore deterministico. Dato un chunk di testo, ritorna "
    "un singolo numero da 0.0 a 1.0 che rappresenta l'importanza del chunk "
    "per memoria persistente di un consulente compliance italiana:\n"
    "  - 0.0-0.2: trivial (small talk, conferme, saluti, no info).\n"
    "  - 0.3-0.5: contesto utile (riferimenti generici, nomi, date).\n"
    "  - 0.6-0.8: insight rilevante (decisione operativa, fatto normativo).\n"
    "  - 0.9-1.0: high-value (norma puntuale + autorita + decisione).\n"
    "Output: solo il numero (es. '0.73'), niente altro testo, niente spiegazione."
)

# Fallback score su error / timeout: borderline cautelativo (admit-leaning).
LLM_FALLBACK_SCORE = 0.5

# Stima cost USD per chunk (Haiku 4.5 input $0.80/MTok + output $4/MTok).
# Per ~300 token input + 5 token output -> ~$0.0003 per chunk.
LLM_COST_PER_INPUT_TOK = 0.80 / 1_000_000.0
LLM_COST_PER_OUTPUT_TOK = 4.00 / 1_000_000.0


# --------------------------------------------------------------------------
# THRESHOLDS — admission gate
# --------------------------------------------------------------------------

DEFINITE_KEEP = 0.85
DEFINITE_DROP = 0.15
DROP_BASELINE = 0.30

# Pesi aggregazione cheap_signals -> cheap_total (somma = 1.0).
CHEAP_WEIGHTS = {
    "length": 0.20,
    "entity_density": 0.45,
    "structural": 0.20,
    "freshness": 0.15,
}


# --------------------------------------------------------------------------
# REGEX PATTERNS — entity density
# --------------------------------------------------------------------------

# Pattern email (RFC 5322 semplificato).
_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Pattern URL HTTP/HTTPS.
_RE_URL = re.compile(r"https?://[^\s<>\"']{4,}", re.IGNORECASE)

# Pattern date IT/EN comuni (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY).
_RE_DATE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")

# Pattern names propri italiani: 2+ parole capitalizzate consecutive.
_RE_PROPER_NAME = re.compile(r"\b[A-ZÀ-Þ][a-zà-ÿ]+(?:\s+[A-ZÀ-Þ][a-zà-ÿ]+)+\b")

# Pattern riferimenti normativi italiani (D.Lgs., L., Reg. UE, ISO, DPR, DM, DPCM).
_RE_NORMATIVE = re.compile(
    r"\b(?:"
    r"D\.?Lgs\.?\s+\d+/\d{4}"
    r"|L(?:egge)?\.?\s+\d+/\d{4}"
    r"|Reg(?:olamento)?\.?\s+UE\s+\d+/\d{4}"
    r"|ISO(?:/IEC)?\s+\d+(?::\d{4})?"
    r"|DPR\s+\d+/\d{4}"
    r"|DM\s+\d+(?:/\d+)?/\d{4}"
    r"|DPCM\s+\d+/\d{4}"
    r"|NIS\s*2"
    r"|GDPR"
    r"|AI\s*Act"
    r")\b",
    re.IGNORECASE,
)

# Pattern authority italiane (ACN, AGENAS, AgID, Garante, ENISA, CSIRT).
_RE_AUTHORITY = re.compile(
    r"\b(?:ACN|AGENAS|AgID|ENISA|CSIRT(?:-Italia)?|Garante)\b",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------
# STRUCTURAL CUES — markdown structure detection
# --------------------------------------------------------------------------

_RE_HEADING = re.compile(r"^#{1,6}\s+\S+", re.MULTILINE)
_RE_LIST_ITEM = re.compile(r"^[\s]*(?:[-*+]|\d+\.)\s+\S+", re.MULTILINE)
_RE_CODE_BLOCK = re.compile(r"```", re.MULTILINE)
_RE_BLOCKQUOTE = re.compile(r"^>\s+\S+", re.MULTILINE)
_RE_TABLE_ROW = re.compile(r"^\|[^\n]+\|", re.MULTILINE)


# --------------------------------------------------------------------------
# DATA CLASSES
# --------------------------------------------------------------------------


@dataclass(slots=True)
class CheapSignals:
    """Risultato dei cheap signals deterministici (Fase 3 hot path).

    Tutti i campi 0.0-1.0 normalizzati.
    """

    length: float
    entity_density: float
    structural: float
    freshness: float

    def to_dict(self) -> dict[str, float]:
        return {
            "length": self.length,
            "entity_density": self.entity_density,
            "structural": self.structural,
            "freshness": self.freshness,
        }


@dataclass(slots=True)
class AdmissionDecision:
    """Decisione del gate di ammissione (Fase 3).

    Attributes:
        verdict: 'admit' | 'drop' | 'borderline'.
        cheap_total: score aggregato cheap signals (0.0-1.0).
        signals: breakdown per debug/audit trail.
        llm_consulted: True se LLM extractor stub e' stato chiamato.
        llm_score: score LLM extractor (None se non chiamato).
        reasoning: motivazione testuale per audit trail (Conv. 41 tracciatura).
    """

    verdict: str
    cheap_total: float
    signals: CheapSignals
    llm_consulted: bool = False
    llm_score: float | None = None
    reasoning: str = ""


# --------------------------------------------------------------------------
# CHEAP SIGNALS — Fase 3 hot path
# --------------------------------------------------------------------------


def _length_signal(token_count: int) -> float:
    """Score lunghezza: penalizza chunk troppo corti, plateau su lunghezza adeguata.

    Curva: linear ramp 0->1 da 0 a 200 token, plateau 1.0 fino a 2500 token,
    leggera penalita oltre 2500 (chunk over-sized = possibile mancato split).
    """
    if token_count <= 0:
        return 0.0
    if token_count < 200:
        return token_count / 200.0
    if token_count <= 2500:
        return 1.0
    # Over-sized penalty: linear decay 1.0 -> 0.6 fra 2500 e 4000 token.
    excess = token_count - 2500
    return max(0.6, 1.0 - excess / 3750.0)


def _entity_density_signal(text: str, token_count: int) -> float:
    """Score densita di entita: pesata su normative + authority + propri + email + url + date.

    Normative + Authority hanno peso maggiore (segnale compliance-rich).
    Density normalizzata su token_count (entity / 100 token, cap 1.0).
    """
    if not text or token_count <= 0:
        return 0.0
    norm_count = len(_RE_NORMATIVE.findall(text))
    auth_count = len(_RE_AUTHORITY.findall(text))
    name_count = len(_RE_PROPER_NAME.findall(text))
    email_count = len(_RE_EMAIL.findall(text))
    url_count = len(_RE_URL.findall(text))
    date_count = len(_RE_DATE.findall(text))
    # Weighted sum: normative/authority 2x, altri 1x.
    weighted_total = (
        2.0 * norm_count
        + 2.0 * auth_count
        + 1.0 * name_count
        + 1.0 * email_count
        + 1.0 * url_count
        + 1.0 * date_count
    )
    # Normalizza per chunk size (entities per 100 token, cap 1.0).
    density_per_100 = weighted_total / max(token_count / 100.0, 1.0)
    return min(1.0, density_per_100 / 3.0)  # 3 entities/100 token -> 1.0


def _structural_signal(text: str) -> float:
    """Score struttura: presenza di heading, lista, code, blockquote, table.

    Bonus per ogni elemento strutturale presente (additivo, cap 1.0).
    """
    if not text:
        return 0.0
    score = 0.0
    if _RE_HEADING.search(text):
        score += 0.30
    if _RE_LIST_ITEM.search(text):
        score += 0.25
    if _RE_CODE_BLOCK.search(text):
        score += 0.15
    if _RE_BLOCKQUOTE.search(text):
        score += 0.15
    if _RE_TABLE_ROW.search(text):
        score += 0.20
    return min(1.0, score)


def _freshness_signal(timestamp_ms: int, now_ms: int) -> float:
    """Score freshness: exponential decay half-life 30 giorni dal timestamp_ms.

    Chunk recenti (oggi) -> 1.0, vecchi (90+ giorni) -> ~0.1, oltre 1 anno -> ~0.0.
    """
    if timestamp_ms <= 0 or now_ms <= 0:
        return 0.5  # neutral fallback
    age_ms = max(0, now_ms - timestamp_ms)
    age_days = age_ms / (1000.0 * 86400.0)
    if age_days < 0:
        return 1.0
    import math

    return math.exp(-math.log(2) * age_days / 30.0)


def cheap_signals(chunk: TreeChunk, *, now_ms: int | None = None) -> CheapSignals:
    """Computa cheap signals deterministici per un chunk (Fase 3 hot path).

    Args:
        chunk: TreeChunk da scorare.
        now_ms: timestamp corrente per freshness (default = chunk.created_at_ms).

    Returns:
        CheapSignals con 4 componenti 0.0-1.0.
    """
    ref_now = now_ms if now_ms is not None else chunk.created_at_ms
    return CheapSignals(
        length=_length_signal(chunk.token_count),
        entity_density=_entity_density_signal(chunk.content, chunk.token_count),
        structural=_structural_signal(chunk.content),
        freshness=_freshness_signal(chunk.timestamp_ms, ref_now),
    )


def cheap_total(signals: CheapSignals) -> float:
    """Aggrega cheap signals in score totale via pesi CHEAP_WEIGHTS.

    Returns:
        float 0.0-1.0 weighted average.
    """
    total = (
        CHEAP_WEIGHTS["length"] * signals.length
        + CHEAP_WEIGHTS["entity_density"] * signals.entity_density
        + CHEAP_WEIGHTS["structural"] * signals.structural
        + CHEAP_WEIGHTS["freshness"] * signals.freshness
    )
    return round(total, 4)


# --------------------------------------------------------------------------
# LLM EXTRACTOR — Fase 3 borderline (REAL Claude Haiku 4.5 v0.6.0)
# --------------------------------------------------------------------------


def _content_hash(content: str) -> str:
    """Stable hash content per cache idempotente."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _parse_llm_score(raw: str) -> float | None:
    """Parsing robusto del singolo float da output LLM.

    Returns:
        float 0.0-1.0 se parsing OK, None altrimenti (fallback caller).
    """
    if not raw:
        return None
    # Estrai primo float-like pattern (es. "0.73", "0.85\n", "Score: 0.7")
    match = re.search(r"\b(?:0|1)(?:\.\d+)?\b", raw.strip())
    if not match:
        return None
    try:
        val = float(match.group(0))
        if 0.0 <= val <= 1.0:
            return val
        # Clamp out-of-range a [0.0, 1.0]
        return max(0.0, min(1.0, val))
    except ValueError:
        return None


async def _llm_score_cached_lookup(content_hash: str) -> float | None:
    """Cache lookup in mem_llm_score_cache per chunk hash.

    Returns:
        float score se cache hit, None se miss / error.
    """
    # Import locale per evitare circular import (tree_store importa scoring? no, ma safe)
    from .tree_store import get_llm_score_cached

    try:
        return await get_llm_score_cached(content_hash)
    except Exception as exc:
        logger.warning("llm_score_cache_lookup_failed", extra={"error": str(exc)})
        return None


async def _llm_score_cached_store(content_hash: str, score: float, model: str) -> None:
    """Store score in cache mem_llm_score_cache. Best-effort (no raise)."""
    from .tree_store import set_llm_score_cached

    try:
        await set_llm_score_cached(content_hash, score, model)
    except Exception as exc:
        logger.warning("llm_score_cache_store_failed", extra={"error": str(exc)})


async def llm_extract_importance(chunk: TreeChunk) -> float:
    """LLM extractor REALE per chunks borderline (Claude Haiku 4.5).

    Pipeline:
        1. Hash content -> lookup mem_llm_score_cache (idempotente).
        2. Se miss: chiamata Claude Haiku via anthropic.AsyncAnthropic +
           SaaS proxy SCO (license-gated, no API key cliente).
        3. Parse output -> score float 0.0-1.0.
        4. Store cache.
        5. Log cost (input + output tokens stimati).

    Fallback robusti:
        - Cache hit -> ritorna score cached (no LLM call).
        - LLM error / parse fail -> ritorna 0.5 (borderline admit-leaning).
        - Missing credentials -> ritorna 0.5 + logger warning (no exception).

    Args:
        chunk: TreeChunk borderline da consultare.

    Returns:
        float 0.0-1.0 score importanza chunk per memoria persistente.

    Pattern Conv. 34 spot check post-multi-agent: dichiarazione esplicita
    di incertezza nel campo `reasoning` upstream (admission_decision).

    Pattern Conv. 41 tracciatura: log strutturato cost USD + tokens per ogni call.
    """
    content_hash = _content_hash(chunk.content)

    # Lookup cache idempotente
    cached = await _llm_score_cached_lookup(content_hash)
    if cached is not None:
        logger.info(
            "llm_extract_importance.cache_hit",
            extra={
                "chunk_id": chunk.id,
                "content_hash": content_hash,
                "cached_score": cached,
            },
        )
        return cached

    # Cache miss: chiamata LLM reale
    # Import locale per evitare import top-level pesanti (anthropic SDK ~3 MB)
    try:
        from anthropic import AsyncAnthropic

        from sco_compliance_os.core.agent_sdk_runner import _resolve_credentials
    except ImportError as exc:
        logger.warning(
            "llm_extract_importance.import_failed",
            extra={"chunk_id": chunk.id, "error": str(exc)},
        )
        return LLM_FALLBACK_SCORE

    creds = _resolve_credentials()
    if creds is None:
        logger.warning(
            "llm_extract_importance.no_credentials",
            extra={"chunk_id": chunk.id, "fallback_score": LLM_FALLBACK_SCORE},
        )
        return LLM_FALLBACK_SCORE

    base_url, api_key = creds
    started_ms = int(time.time() * 1000)

    try:
        client = AsyncAnthropic(base_url=base_url, api_key=api_key)
        # User content: cap a ~2000 char per evitare overflow su chunk over-sized.
        content_capped = chunk.content[:2000]
        response = await client.messages.create(
            model=LLM_SCORE_MODEL,
            max_tokens=LLM_SCORE_MAX_OUTPUT,
            system=LLM_SCORE_SYSTEM,
            messages=[{"role": "user", "content": content_capped}],
        )

        elapsed_ms = int(time.time() * 1000) - started_ms

        # Estrai testo risposta (TextBlock list -> primo TextBlock.text)
        raw_text = ""
        if response.content:
            first_block = response.content[0]
            raw_text = getattr(first_block, "text", "") or ""

        score = _parse_llm_score(raw_text)
        if score is None:
            logger.warning(
                "llm_extract_importance.parse_failed",
                extra={
                    "chunk_id": chunk.id,
                    "raw_text": raw_text[:100],
                    "fallback_score": LLM_FALLBACK_SCORE,
                },
            )
            score = LLM_FALLBACK_SCORE

        # Cost tracking
        input_tok = response.usage.input_tokens
        output_tok = response.usage.output_tokens
        est_cost_usd = input_tok * LLM_COST_PER_INPUT_TOK + output_tok * LLM_COST_PER_OUTPUT_TOK
        logger.info(
            "llm_extract_importance.success",
            extra={
                "chunk_id": chunk.id,
                "content_hash": content_hash,
                "score": score,
                "model": LLM_SCORE_MODEL,
                "input_tokens": input_tok,
                "output_tokens": output_tok,
                "est_cost_usd": round(est_cost_usd, 6),
                "elapsed_ms": elapsed_ms,
            },
        )

        # Store cache (idempotente, best-effort)
        await _llm_score_cached_store(content_hash, score, LLM_SCORE_MODEL)

        return score

    except Exception as exc:
        logger.error(
            "llm_extract_importance.error",
            extra={
                "chunk_id": chunk.id,
                "exc_type": type(exc).__name__,
                "error": str(exc)[:200],
                "fallback_score": LLM_FALLBACK_SCORE,
            },
        )
        return LLM_FALLBACK_SCORE


# --------------------------------------------------------------------------
# ADMISSION GATE — Fase 3 decision logic
# --------------------------------------------------------------------------


async def admission_decision(
    chunk: TreeChunk,
    *,
    definite_keep: float = DEFINITE_KEEP,
    definite_drop: float = DEFINITE_DROP,
    consult_llm_on_borderline: bool = False,
    now_ms: int | None = None,
) -> AdmissionDecision:
    """Decide admit/drop/borderline per un chunk via cheap signals + LLM optional.

    Async post-v0.6.0 (LLM extractor reale richiede await).

    Logic:
        1. Calcola cheap_signals + cheap_total.
        2. Se cheap_total >= definite_keep -> admit no LLM (hot path).
        3. Se cheap_total <= definite_drop -> drop no LLM (hot path).
        4. Else borderline: se consult_llm_on_borderline -> chiama llm_extract,
           merge cheap + llm via average, decide admit/drop/borderline finale.

    Args:
        chunk: TreeChunk da decidere.
        definite_keep: soglia admit no-LLM (default 0.85).
        definite_drop: soglia drop no-LLM (default 0.15).
        consult_llm_on_borderline: se True consulta LLM extractor reale Haiku
            (default False per non incorrere in cost durante smoke + dev).
        now_ms: timestamp corrente per freshness (default = chunk.created_at_ms).

    Returns:
        AdmissionDecision con verdict + breakdown signals.
    """
    signals = cheap_signals(chunk, now_ms=now_ms)
    total = cheap_total(signals)

    if total >= definite_keep:
        verdict = "admit"
        reasoning = f"cheap_total={total} >= definite_keep={definite_keep} (hot path admit)"
        return AdmissionDecision(
            verdict=verdict,
            cheap_total=total,
            signals=signals,
            llm_consulted=False,
            reasoning=reasoning,
        )

    if total <= definite_drop:
        verdict = "drop"
        reasoning = f"cheap_total={total} <= definite_drop={definite_drop} (hot path drop)"
        return AdmissionDecision(
            verdict=verdict,
            cheap_total=total,
            signals=signals,
            llm_consulted=False,
            reasoning=reasoning,
        )

    # Borderline
    if consult_llm_on_borderline:
        llm_score = await llm_extract_importance(chunk)
        # Decision merge: average cheap + llm.
        merged = round((total + llm_score) / 2.0, 4)
        if merged >= definite_keep:
            verdict = "admit"
            reasoning = (
                f"cheap_total={total} borderline; llm_score={llm_score}; "
                f"merged={merged} >= definite_keep -> admit"
            )
        elif merged <= definite_drop:
            verdict = "drop"
            reasoning = (
                f"cheap_total={total} borderline; llm_score={llm_score}; "
                f"merged={merged} <= definite_drop -> drop"
            )
        else:
            verdict = "borderline"
            reasoning = (
                f"cheap_total={total} borderline; llm_score={llm_score}; "
                f"merged={merged} resta borderline (pending_extraction)"
            )
        return AdmissionDecision(
            verdict=verdict,
            cheap_total=total,
            signals=signals,
            llm_consulted=True,
            llm_score=llm_score,
            reasoning=reasoning,
        )

    # Borderline senza LLM consult: deferisce status pending_extraction.
    verdict = "borderline"
    reasoning = (
        f"cheap_total={total} in borderline range "
        f"({definite_drop}, {definite_keep}); LLM consult disabilitato -> pending_extraction"
    )
    return AdmissionDecision(
        verdict=verdict,
        cheap_total=total,
        signals=signals,
        llm_consulted=False,
        reasoning=reasoning,
    )


__all__ = [
    "CHEAP_WEIGHTS",
    "DEFINITE_DROP",
    "DEFINITE_KEEP",
    "DROP_BASELINE",
    "AdmissionDecision",
    "CheapSignals",
    "admission_decision",
    "cheap_signals",
    "cheap_total",
    "llm_extract_importance",
]
