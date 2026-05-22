"""Scoring chunks per rilevanza in query — BM25 + recency + manual boost.

Wave 1 (corrente): no embedding, scoring puro BM25 sul testo + boost euristici.
Wave 2 (rinviato): integrazione embedding locali (Voyage AI o sentence-transformers
on-device) per scoring semantico. Decisione autonoma documentata in ADR 0004.

Razionale wave 1: la maggior parte delle query consulenziali italiane usano
terminologia tecnica esatta (sigle norme, articoli, nomi clienti) — BM25 è
notoriamente eccellente su query lessicali di alta precisione.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

from .chunker import Chunk


@dataclass(slots=True)
class ScoringOptions:
    """Parametri di scoring tunable.

    Attributes:
        bm25_k1: term frequency saturation (BM25 standard 1.5).
        bm25_b: length normalization (BM25 standard 0.75).
        recency_half_life_days: emivita recency boost (90 default).
        recency_weight: peso boost recency vs BM25 (0.2 = 20%).
        manual_boost_field: chiave provenance per boost manuale (es. 'pinned').
    """

    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    recency_half_life_days: float = 90.0
    recency_weight: float = 0.2
    manual_boost_field: str = "pinned"


@dataclass(slots=True)
class ScoredChunk:
    """Chunk con score di rilevanza per una specifica query."""

    chunk: Chunk
    score: float
    bm25_component: float
    recency_component: float
    manual_component: float


_TOKEN_RE = re.compile(r"\b\w+\b", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Tokenizzazione semplice case-insensitive."""
    return [tok.lower() for tok in _TOKEN_RE.findall(text)]


def _compute_idf(corpus_tokens: list[list[str]]) -> dict[str, float]:
    """Calcola IDF su corpus (formula BM25 standard con +1 smoothing)."""
    n_docs = len(corpus_tokens)
    if n_docs == 0:
        return {}
    df: dict[str, int] = {}
    for tokens in corpus_tokens:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1
    return {
        term: math.log((n_docs - count + 0.5) / (count + 0.5) + 1.0)
        for term, count in df.items()
    }


def _bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    idf: dict[str, float],
    avg_doc_len: float,
    k1: float,
    b: float,
) -> float:
    """Score BM25 di un documento per una query."""
    if not doc_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    tf: dict[str, int] = {}
    for tok in doc_tokens:
        tf[tok] = tf.get(tok, 0) + 1
    score = 0.0
    for q in query_tokens:
        if q not in idf:
            continue
        f = tf.get(q, 0)
        if f == 0:
            continue
        numerator = f * (k1 + 1)
        denominator = f + k1 * (1 - b + b * doc_len / max(avg_doc_len, 1.0))
        score += idf[q] * numerator / denominator
    return score


def _recency_score(created_at_iso: str, half_life_days: float) -> float:
    """Score di recency con decay esponenziale (0..1)."""
    try:
        created = datetime.fromisoformat(created_at_iso)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.0
    now = datetime.now(timezone.utc)
    age_days = (now - created).total_seconds() / 86400.0
    if age_days < 0:
        return 1.0
    return math.exp(-math.log(2) * age_days / max(half_life_days, 1.0))


def score_chunks(
    chunks: Iterable[Chunk],
    query: str,
    options: Optional[ScoringOptions] = None,
) -> list[ScoredChunk]:
    """Ranking chunks per rilevanza alla query.

    Args:
        chunks: iterabile di Chunk candidati (già pre-filtrati a livello store).
        query: stringa query utente.
        options: parametri di scoring (default ScoringOptions()).

    Returns:
        Lista ScoredChunk ordinata DESC per score; lista vuota se input vuoto.
    """
    opts = options or ScoringOptions()
    chunks_list = list(chunks)
    if not chunks_list or not query.strip():
        return []

    query_tokens = _tokenize(query)
    corpus_tokens = [_tokenize(c.content_md) for c in chunks_list]
    idf = _compute_idf(corpus_tokens)
    avg_doc_len = sum(len(t) for t in corpus_tokens) / max(len(corpus_tokens), 1)

    scored: list[ScoredChunk] = []
    for chunk, doc_tokens in zip(chunks_list, corpus_tokens):
        bm25 = _bm25_score(
            query_tokens, doc_tokens, idf, avg_doc_len, opts.bm25_k1, opts.bm25_b
        )
        recency = _recency_score(chunk.created_at, opts.recency_half_life_days)
        manual = float(chunk.provenance.get(opts.manual_boost_field, 0.0))
        # Composite score: BM25 dominante, recency + manual additivi.
        score = bm25 * (1.0 - opts.recency_weight) + recency * opts.recency_weight + manual
        scored.append(
            ScoredChunk(
                chunk=chunk,
                score=score,
                bm25_component=bm25,
                recency_component=recency,
                manual_component=manual,
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored
