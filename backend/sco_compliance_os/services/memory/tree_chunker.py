"""Memory Tree bucket-seal — Fase 1: Canonicalize + Chunker.

Pipeline 4 fasi del Memory Tree bucket-seal architecture (clean-room
reimplementation ispirata a OpenHuman MEMORY_ARCHITECTURE_LLD, NO code copy):

    1. Canonicalize     — source heterogeneo -> Markdown canonico normalizzato
    2. Chunker          -> stable deterministic IDs, ~3k token max per chunk
    3. Scoring + gate   -> cheap signals admit/drop, borderline -> LLM extractor
    4. Tree summariz.   -> tree_source / tree_topic / tree_global con sealing

Questo modulo implementa Fase 1 + 2 (canonicalize + chunker).
Fase 3 in `tree_scoring.py`. Fase 4 sealing/summarization carry-over Sessione 7+.

Pattern Karpathy "schema is the product":
    - Stable IDs deterministici: hash(content + source_kind + source_id + seq)
    - Idempotent re-ingest: stesso input -> stessi IDs -> upsert no-op
    - No hallucination: chunk vuoto -> lista vuota, mai chunk fantoccio

Pattern Karpathy "single source of truth":
    - Token count vive nel Chunk, mai cached altrove
    - Status enum vive nel DB, mai cached in memory

Pattern Conv. 41 (tracciatura): logger structured per ogni decision di split.
Pattern Conv. 47 (single source of truth costanti): TREE_MAX_TOKENS default
configurabile via parametro funzione, mai duplicato hard-coded altrove.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Fallback heuristic: 1 token ~= 4 caratteri (stima conservativa Anthropic/OpenAI)
_HEURISTIC_CHARS_PER_TOKEN = 4

# Default max tokens per chunk (allineato a OpenHuman LLD ~3k token).
_DEFAULT_MAX_TOKENS = 3000

# Soglia minima per chunk valido (sotto questo -> noise filtering Fase 3).
_MIN_VIABLE_TOKENS = 10


class TreeChunkSourceKind(str, Enum):
    """Vocabolario chiuso source_kind del Memory Tree bucket-seal.

    Valori mutualmente esclusivi. Aggiunte richiedono OK utente esplicito
    (Conv. di stabilita vocabolario tipizzato Ondata 2 vault Karpathy).
    """

    CHAT = "chat"
    EMAIL = "email"
    DOCUMENT = "document"
    VAULT_FILE = "vault_file"
    NOTE = "note"


class TreeChunkStatus(str, Enum):
    """Stato del chunk nel pipeline bucket-seal 4 fasi.

    Macchina a stati (transizioni ammesse):
        pending_extraction -> admitted | dropped | buffered
        buffered -> sealed | dropped
        admitted -> buffered | sealed (post promozione tree_source L1)
        sealed -> (terminal, post sealing finale tree_global L2)
        dropped -> (terminal, mai re-ingerito senza re-ingest esplicito)
    """

    PENDING_EXTRACTION = "pending_extraction"  # borderline -> attende LLM signal
    ADMITTED = "admitted"  # cheap-total >= DEFINITE_KEEP, autoclear admit
    BUFFERED = "buffered"  # in attesa di promozione L0 -> L1 sealing
    SEALED = "sealed"  # promosso a tree level, terminal
    DROPPED = "dropped"  # cheap-total <= DEFINITE_DROP, terminal


@dataclass(slots=True)
class TreeChunk:
    """Unita atomica del Memory Tree bucket-seal.

    Schema allineato a `mem_tree_chunks` SQLite table (vedi `tree_store.py`).

    Attributes:
        id: stable deterministic hash(content + source_kind + source_id + seq).
            Idempotent: stesso input -> stesso ID -> upsert no-op.
        source_kind: vocabolario chiuso TreeChunkSourceKind.
        source_id: identificatore opaco del sorgente (msg_id, file_md5, vault_path).
        owner: identificatore utente (default 'local' per single-user app).
        timestamp_ms: timestamp evento (POSIX ms, UTC). Per chat = msg send time.
        time_range_start_ms: inizio finestra temporale rappresentata dal chunk.
        time_range_end_ms: fine finestra temporale (per chat = ultimo msg di sessione).
        tags: lista tag arbitrari (es. ['nis2', 'cybersicurezza', 'ACN']).
        content: testo markdown canonicalizzato del chunk.
        token_count: token stimati (tiktoken se disponibile, fallback euristico).
        seq_in_source: posizione sequenziale nel sorgente (0-based).
        created_at_ms: timestamp di creazione del chunk record (POSIX ms, UTC).
        status: stato pipeline bucket-seal (vedi TreeChunkStatus).
    """

    id: str
    source_kind: str
    source_id: str
    owner: str
    timestamp_ms: int
    time_range_start_ms: int
    time_range_end_ms: int
    tags: list[str]
    content: str
    token_count: int
    seq_in_source: int
    created_at_ms: int
    status: str = TreeChunkStatus.PENDING_EXTRACTION.value

    def to_dict(self) -> dict[str, object]:
        """Serializzazione per response API + log structured."""
        return {
            "id": self.id,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "owner": self.owner,
            "timestamp_ms": self.timestamp_ms,
            "time_range_start_ms": self.time_range_start_ms,
            "time_range_end_ms": self.time_range_end_ms,
            "tags": list(self.tags),
            "content": self.content,
            "token_count": self.token_count,
            "seq_in_source": self.seq_in_source,
            "created_at_ms": self.created_at_ms,
            "status": self.status,
        }


# --------------------------------------------------------------------------
# CANONICALIZATION — Fase 1
# --------------------------------------------------------------------------

# Whitespace squeeze: collassa run di whitespace ma preserva linebreak.
_RE_INLINE_WS = re.compile(r"[ \t]+")
# Triplice (o piu) newline -> doppio newline.
_RE_TRIPLE_NEWLINE = re.compile(r"\n{3,}")
# Zero-width char di Unicode (BOM, ZWJ, ZWNJ).
_RE_ZERO_WIDTH = re.compile(r"[​‌‍﻿]")


def canonicalize_markdown(text: str) -> str:
    """Normalizza testo a Markdown canonico (Fase 1 pipeline bucket-seal).

    Operazioni:
        - Strip zero-width Unicode chars (BOM, ZWJ, ZWNJ).
        - Normalizza line endings CRLF/CR -> LF.
        - Collassa run di spazi/tab inline.
        - Collassa run di 3+ newlines -> 2 newlines (separazione paragrafi).
        - Trim outer whitespace.

    Args:
        text: input raw (str). None o empty -> stringa vuota.

    Returns:
        Markdown canonicalizzato. Output deterministico per stesso input.
    """
    if not text:
        return ""
    out = text.replace("\r\n", "\n").replace("\r", "\n")
    out = _RE_ZERO_WIDTH.sub("", out)
    # Normalizza inline whitespace ma PRESERVA newlines.
    lines = out.split("\n")
    lines = [_RE_INLINE_WS.sub(" ", line).rstrip() for line in lines]
    out = "\n".join(lines)
    out = _RE_TRIPLE_NEWLINE.sub("\n\n", out)
    return out.strip()


# --------------------------------------------------------------------------
# TOKEN COUNTING — utility shared
# --------------------------------------------------------------------------


def count_tokens(text: str) -> int:
    """Conta token con tiktoken se disponibile, altrimenti fallback euristico.

    Fallback: ~4 chars/token (stima conservativa cross-tokenizer).
    """
    if not text:
        return 0
    try:
        import tiktoken  # type: ignore

        encoder = tiktoken.get_encoding("cl100k_base")
        return len(encoder.encode(text))
    except (ImportError, ModuleNotFoundError):
        return max(1, len(text) // _HEURISTIC_CHARS_PER_TOKEN)


# --------------------------------------------------------------------------
# STABLE ID — deterministic hash
# --------------------------------------------------------------------------


def compute_chunk_id(
    *,
    content: str,
    source_kind: str,
    source_id: str,
    seq_in_source: int,
) -> str:
    """Computa stable deterministic ID per un chunk.

    Pattern: SHA-256(source_kind + '|' + source_id + '|' + seq + '|' + content).
    Idempotent: stesso input -> stesso output. Re-ingest produce upsert no-op.

    Returns:
        Hex digest 16 chars (64 bit, sufficiente per ~4M chunk senza collision).
    """
    payload = f"{source_kind}|{source_id}|{seq_in_source}|{content}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


# --------------------------------------------------------------------------
# CHUNKER — Fase 2
# --------------------------------------------------------------------------

# Paragrafo break: doppio newline (markdown canonico).
_RE_PARAGRAPH = re.compile(r"\n\s*\n")
# Frase break euristica IT/EN: . ! ? seguiti da spazio + capital o EOL.
_RE_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-ſ])")


def _split_paragraph_into_sentences(paragraph: str) -> list[str]:
    """Split paragrafo lungo in frasi via euristica IT/EN punctuation."""
    if not paragraph.strip():
        return []
    parts = _RE_SENTENCE.split(paragraph)
    return [p.strip() for p in parts if p.strip()]


def _pack_sentences_into_chunks(
    sentences: list[str],
    max_tokens: int,
) -> list[str]:
    """Pack lista di frasi in chunks rispettando max_tokens.

    Greedy: aggiunge frasi al buffer corrente finche entra; appena overflow,
    flush e apri buffer nuovo. Frase singola > max_tokens -> hard-split a parole.
    """
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_tokens = 0
    for sent in sentences:
        sent_tokens = count_tokens(sent)
        if sent_tokens > max_tokens:
            # Hard split: frase enorme, split a parole.
            if buffer:
                chunks.append(" ".join(buffer))
                buffer = []
                buffer_tokens = 0
            words = sent.split()
            word_buf: list[str] = []
            word_tokens = 0
            for w in words:
                wt = count_tokens(w + " ")
                if word_tokens + wt > max_tokens and word_buf:
                    chunks.append(" ".join(word_buf))
                    word_buf = [w]
                    word_tokens = wt
                else:
                    word_buf.append(w)
                    word_tokens += wt
            if word_buf:
                chunks.append(" ".join(word_buf))
            continue
        if buffer_tokens + sent_tokens > max_tokens and buffer:
            chunks.append(" ".join(buffer))
            buffer = [sent]
            buffer_tokens = sent_tokens
        else:
            buffer.append(sent)
            buffer_tokens += sent_tokens
    if buffer:
        chunks.append(" ".join(buffer))
    return chunks


def chunk_text(
    text: str,
    *,
    source_kind: str,
    source_id: str,
    owner: str = "local",
    timestamp_ms: int | None = None,
    time_range_start_ms: int | None = None,
    time_range_end_ms: int | None = None,
    tags: list[str] | None = None,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> list[TreeChunk]:
    """Spezza testo in TreeChunk semantici rispettando max_tokens.

    Strategia di split (Fase 2 bucket-seal):
        1. canonicalize_markdown(text).
        2. Split per paragrafi (doppio newline).
        3. Se paragrafo > max_tokens -> sub-split per frasi.
        4. Pack frasi in chunks greedy fino a max_tokens.
        5. Genera stable ID deterministico per ogni chunk.

    Args:
        text: input raw (canonicalization automatica).
        source_kind: vocabolario chiuso (vedi TreeChunkSourceKind).
        source_id: identificatore opaco sorgente.
        owner: default 'local' per single-user app.
        timestamp_ms: timestamp evento (POSIX ms UTC). Default = now.
        time_range_start_ms: default = timestamp_ms.
        time_range_end_ms: default = timestamp_ms.
        tags: tag arbitrari (es. ['nis2', 'ACN']). Default lista vuota.
        max_tokens: budget massimo per chunk (default 3000).

    Returns:
        Lista di TreeChunk con stable IDs. Vuota se input vuoto / non viable.
        Status iniziale = PENDING_EXTRACTION (Fase 3 decidera).
    """
    canonical = canonicalize_markdown(text)
    if not canonical:
        logger.debug("chunk_text: empty after canonicalization", extra={
            "source_kind": source_kind,
            "source_id": source_id,
        })
        return []

    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    ts_ms = timestamp_ms if timestamp_ms is not None else now_ms
    range_start = time_range_start_ms if time_range_start_ms is not None else ts_ms
    range_end = time_range_end_ms if time_range_end_ms is not None else ts_ms
    chunk_tags = list(tags) if tags else []

    # Validazione source_kind (Conv. 12 enforcement: solo vocabolario chiuso).
    valid_kinds = {k.value for k in TreeChunkSourceKind}
    if source_kind not in valid_kinds:
        logger.warning(
            "chunk_text: source_kind fuori vocabolario chiuso",
            extra={"source_kind": source_kind, "valid": sorted(valid_kinds)},
        )

    # Split per paragrafi
    paragraphs = [p.strip() for p in _RE_PARAGRAPH.split(canonical) if p.strip()]
    if not paragraphs:
        return []

    # Per ogni paragrafo: se entra in max_tokens -> chunk diretto, else sub-split.
    raw_chunk_texts: list[str] = []
    for para in paragraphs:
        para_tokens = count_tokens(para)
        if para_tokens <= max_tokens:
            raw_chunk_texts.append(para)
        else:
            sentences = _split_paragraph_into_sentences(para)
            packed = _pack_sentences_into_chunks(sentences, max_tokens)
            raw_chunk_texts.extend(packed)

    # Filter chunks sotto _MIN_VIABLE_TOKENS (noise).
    chunks: list[TreeChunk] = []
    for seq, body in enumerate(raw_chunk_texts):
        tok = count_tokens(body)
        if tok < _MIN_VIABLE_TOKENS:
            logger.debug(
                "chunk_text: skipping non-viable chunk",
                extra={"source_id": source_id, "seq": seq, "tokens": tok},
            )
            continue
        cid = compute_chunk_id(
            content=body,
            source_kind=source_kind,
            source_id=source_id,
            seq_in_source=seq,
        )
        chunks.append(
            TreeChunk(
                id=cid,
                source_kind=source_kind,
                source_id=source_id,
                owner=owner,
                timestamp_ms=ts_ms,
                time_range_start_ms=range_start,
                time_range_end_ms=range_end,
                tags=chunk_tags,
                content=body,
                token_count=tok,
                seq_in_source=seq,
                created_at_ms=now_ms,
                status=TreeChunkStatus.PENDING_EXTRACTION.value,
            )
        )

    logger.info(
        "chunk_text: produced chunks",
        extra={
            "source_kind": source_kind,
            "source_id": source_id,
            "input_tokens": count_tokens(canonical),
            "chunk_count": len(chunks),
            "max_tokens": max_tokens,
        },
    )
    return chunks


__all__ = [
    "TreeChunk",
    "TreeChunkSourceKind",
    "TreeChunkStatus",
    "canonicalize_markdown",
    "chunk_text",
    "compute_chunk_id",
    "count_tokens",
]
