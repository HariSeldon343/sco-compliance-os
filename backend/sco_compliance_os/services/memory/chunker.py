"""Token-aware markdown chunker per Memory Tree.

Strategia di chunking:
    1. Split per heading H1/H2 (preserva coerenza semantica).
    2. Se chunk > max_tokens, sub-split per paragrafo.
    3. Overlap di tail-head fra chunks consecutivi (continuità contesto).
    4. Mantiene breadcrumb dei heading parent (heading_path).

Tokenizer: usa `tiktoken` (compatibile con anthropic claude token count
approssimativamente, alternativa locale veloce). Se non disponibile, fallback
a stima euristica (4 chars/token, registrazione warning).

Pattern Karpathy: schema is the product. Il chunk è l'unità atomica del
Memory Tree, ogni chunk porta con sé provenance + heading_path per ricomposizione.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# Fallback heuristic: 1 token ≈ 4 caratteri (stima conservativa OpenAI/Anthropic).
_HEURISTIC_CHARS_PER_TOKEN = 4


@dataclass(slots=True)
class Chunk:
    """Unità atomica del Memory Tree.

    Attributes:
        id: UUID v4 generato alla creazione.
        source_path: path originale (file, URL, connector_id).
        parent_chunk_id: None per root chunks, ID parent per summary tree.
        heading_path: breadcrumb headings (es. ["# Doc", "## Sezione"]).
        content_md: testo markdown del chunk.
        token_count: token stimati nel content_md.
        source_type: 'connector' | 'user_upload' | 'vault_ingest' | 'manual'.
        source_id: identificatore opaco del sorgente (msg_id, file_md5, ecc.).
        provenance: metadata aggiuntivi (Conv. 43 SMART FILE INJECTION).
        created_at: timestamp UTC ISO.
    """

    id: str
    source_path: str
    parent_chunk_id: str | None
    heading_path: list[str]
    content_md: str
    token_count: int
    source_type: str = "manual"
    source_id: str = ""
    provenance: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _count_tokens(text: str) -> int:
    """Conta token con tiktoken se disponibile, altrimenti fallback euristico."""
    try:
        import tiktoken  # type: ignore

        encoder = tiktoken.get_encoding("cl100k_base")
        return len(encoder.encode(text))
    except (ImportError, ModuleNotFoundError):
        logger.debug("tiktoken non disponibile, uso fallback euristico 4 chars/token")
        return max(1, len(text) // _HEURISTIC_CHARS_PER_TOKEN)


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _split_by_headings(text: str) -> list[tuple[list[str], str]]:
    """Split testo per heading H1/H2/H3, ritorna lista (breadcrumb, body)."""
    # Trova posizioni heading H1/H2 (granularità sezione, non sub-section).
    splits: list[tuple[list[str], str]] = []
    current_breadcrumb: list[str] = []
    current_body: list[str] = []
    lines = text.splitlines()

    for line in lines:
        match = _HEADING_RE.match(line)
        if match and len(match.group(1)) <= 2:
            # Flush previous section.
            if current_body:
                splits.append((list(current_breadcrumb), "\n".join(current_body)))
                current_body = []
            level = len(match.group(1))
            heading_text = f"{match.group(1)} {match.group(2)}"
            # Reset breadcrumb a quel livello.
            current_breadcrumb = [*current_breadcrumb[: level - 1], heading_text]
            current_body.append(line)
        else:
            current_body.append(line)

    if current_body:
        splits.append((list(current_breadcrumb), "\n".join(current_body)))

    return splits or [([], text)]


def _split_by_paragraph(text: str, max_tokens: int) -> list[str]:
    """Sub-split per paragrafo quando una sezione supera max_tokens."""
    paragraphs = re.split(r"\n\s*\n", text)
    out: list[str] = []
    buffer: list[str] = []
    buffer_tokens = 0

    for para in paragraphs:
        para_tokens = _count_tokens(para)
        if buffer_tokens + para_tokens > max_tokens and buffer:
            out.append("\n\n".join(buffer))
            buffer = [para]
            buffer_tokens = para_tokens
        else:
            buffer.append(para)
            buffer_tokens += para_tokens

    if buffer:
        out.append("\n\n".join(buffer))

    return out


def chunk_markdown(
    text: str,
    *,
    source_path: str = "",
    source_type: str = "manual",
    source_id: str = "",
    provenance: dict | None = None,
    max_tokens: int = 3000,
    overlap: int = 200,
) -> list[Chunk]:
    """Spezza testo markdown in chunks coerenti ≤ max_tokens.

    Args:
        text: testo markdown sorgente.
        source_path: path originale per provenance.
        source_type: 'connector' | 'user_upload' | 'vault_ingest' | 'manual'.
        source_id: identificatore opaco (file MD5, message_id, ecc.).
        provenance: dict metadata Conv. 43 (parser, hash, dimensione, ecc.).
        max_tokens: budget massimo per chunk (default 3000).
        overlap: token di tail->head overlap fra chunk consecutivi.

    Returns:
        Lista di Chunk; lista vuota se input vuoto.
    """
    if not text or not text.strip():
        return []

    sections = _split_by_headings(text)
    chunks: list[Chunk] = []
    prev_tail = ""

    for breadcrumb, body in sections:
        body_with_overlap = (prev_tail + "\n\n" + body) if prev_tail else body
        body_tokens = _count_tokens(body_with_overlap)

        if body_tokens <= max_tokens:
            chunks.append(
                Chunk(
                    id=str(uuid.uuid4()),
                    source_path=source_path,
                    parent_chunk_id=None,
                    heading_path=breadcrumb,
                    content_md=body_with_overlap,
                    token_count=body_tokens,
                    source_type=source_type,
                    source_id=source_id,
                    provenance=provenance or {},
                )
            )
        else:
            for sub_body in _split_by_paragraph(body_with_overlap, max_tokens):
                sub_tokens = _count_tokens(sub_body)
                chunks.append(
                    Chunk(
                        id=str(uuid.uuid4()),
                        source_path=source_path,
                        parent_chunk_id=None,
                        heading_path=breadcrumb,
                        content_md=sub_body,
                        token_count=sub_tokens,
                        source_type=source_type,
                        source_id=source_id,
                        provenance=provenance or {},
                    )
                )

        # Calcola tail per overlap su prossima sezione.
        tail_chars = overlap * _HEURISTIC_CHARS_PER_TOKEN
        prev_tail = body[-tail_chars:] if len(body) > tail_chars else body

    return chunks
