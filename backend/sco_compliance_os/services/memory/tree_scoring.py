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

Pattern Karpathy "schema is the product":
    - cheap_signals() ritorna dict[str, float] strutturato, mai magic numbers.
    - Pesi aggregazione documentati in CHEAP_WEIGHTS.
    - LLM extractor stub: ritorna 0.5 neutral fino a wire Sessione 7+.

Pattern Conv. 34 (spot check post-multi-agent): LLM extractor stub dichiara
esplicitamente l'incertezza nel campo `reasoning`, mai pretende un score reale.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from .tree_chunker import TreeChunk

logger = logging.getLogger(__name__)


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
_RE_DATE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"
)

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
# LLM EXTRACTOR — Fase 3 borderline (STUB carry-over Sessione 7+)
# --------------------------------------------------------------------------


def llm_extract_importance(chunk: TreeChunk) -> float:
    """STUB LLM extractor per chunks borderline (carry-over Sessione 7+).

    Implementazione reale: chiamata Claude Haiku 4.5 batch con prompt scoring
    relevance + entity extraction. Cost-controlled via batching + caching.

    Ora: ritorna 0.5 neutral (deferisce decisione al cheap_total signal).

    Pattern Conv. 34 spot check post-multi-agent: dichiarazione esplicita
    di incertezza nel reasoning, mai pretende score reale.

    Args:
        chunk: TreeChunk borderline da consultare.

    Returns:
        float 0.0-1.0 score LLM (stub: 0.5 fisso).
    """
    logger.info(
        "llm_extract_importance: STUB call (carry-over Sessione 7+)",
        extra={"chunk_id": chunk.id, "stub_score": 0.5},
    )
    return 0.5


# --------------------------------------------------------------------------
# ADMISSION GATE — Fase 3 decision logic
# --------------------------------------------------------------------------


def admission_decision(
    chunk: TreeChunk,
    *,
    definite_keep: float = DEFINITE_KEEP,
    definite_drop: float = DEFINITE_DROP,
    consult_llm_on_borderline: bool = False,
    now_ms: int | None = None,
) -> AdmissionDecision:
    """Decide admit/drop/borderline per un chunk via cheap signals + LLM optional.

    Logic:
        1. Calcola cheap_signals + cheap_total.
        2. Se cheap_total >= definite_keep -> admit no LLM (hot path).
        3. Se cheap_total <= definite_drop -> drop no LLM (hot path).
        4. Else borderline: se consult_llm_on_borderline -> chiama llm_extract,
           se LLM stub neutral (0.5) -> resta borderline (status pending_extraction).

    Args:
        chunk: TreeChunk da decidere.
        definite_keep: soglia admit no-LLM (default 0.85).
        definite_drop: soglia drop no-LLM (default 0.15).
        consult_llm_on_borderline: se True consulta LLM extractor (default False
            per non incorrere in cost durante smoke test e dev locale).
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
        llm_score = llm_extract_importance(chunk)
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
    "AdmissionDecision",
    "CheapSignals",
    "CHEAP_WEIGHTS",
    "DEFINITE_DROP",
    "DEFINITE_KEEP",
    "DROP_BASELINE",
    "admission_decision",
    "cheap_signals",
    "cheap_total",
    "llm_extract_importance",
]
