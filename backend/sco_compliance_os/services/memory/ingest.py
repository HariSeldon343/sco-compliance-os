"""Pipeline ingest end-to-end per Memory Tree.

Funzioni principali:
    - ingest_text: chunker + store, da string in memoria.
    - ingest_file: legge .md/.txt/.pdf/.docx + chunker + store con provenance.

Pattern Conv. 43 SMART FILE INJECTION: ogni file ingerito porta con sé
provenance metadata completi nella tabella memory_chunks.score_metadata:
    - parser (libreria usata: 'markdown'|'pypdf'|'python-docx'|'plain-text')
    - hash_md5 (computed runtime)
    - dimensione_byte
    - pagine (PDF only)
    - mime_type (heuristic + extension)
    - data_import_vault (UTC ISO)

Pattern Karpathy "schema is the product, no hallucination": nessun parser
inventa contenuto. Se il file non è leggibile o vuoto, ritorna lista vuota
e registra warning. Mai produrre chunk fantoccio.
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .chunker import Chunk, chunk_markdown
from .store import bulk_insert

logger = logging.getLogger(__name__)


def _compute_md5(path: Path) -> str:
    """Hash MD5 del file (provenance metadata Conv. 43)."""
    md5 = hashlib.md5()  # noqa: S324 — uso per dedup, non security
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def _read_pdf(path: Path) -> tuple[str, int]:
    """Estrae testo da PDF, ritorna (testo, n_pagine).

    Usa pypdf come parser default. Se non installato, ritorna stringa vuota
    + warning esplicito (mai inventare contenuto).
    """
    try:
        from pypdf import PdfReader  # type: ignore
    except (ImportError, ModuleNotFoundError):
        logger.warning("pypdf non disponibile, skipping PDF %s", path)
        return "", 0

    try:
        reader = PdfReader(str(path))
        pages = [p.extract_text() or "" for p in reader.pages]
        return "\n\n".join(pages), len(pages)
    except Exception as exc:  # noqa: BLE001
        logger.error("Errore parsing PDF %s: %s", path, exc)
        return "", 0


def _read_docx(path: Path) -> str:
    """Estrae testo da .docx via python-docx.

    Pattern Conv. 42 enforcement: NON eseguiamo write su docx in ingest,
    solo read del body markdown-ish (paragrafi). Tabelle escluse per ora
    (Wave 2: parser tabelle dedicato).
    """
    try:
        from docx import Document  # type: ignore
    except (ImportError, ModuleNotFoundError):
        logger.warning("python-docx non disponibile, skipping DOCX %s", path)
        return ""

    try:
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as exc:  # noqa: BLE001
        logger.error("Errore parsing DOCX %s: %s", path, exc)
        return ""


def _read_text(path: Path) -> str:
    """Lettura testuale (.md, .txt) con UTF-8 + fallback latin-1."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("UTF-8 decode failed per %s, fallback latin-1", path)
        return path.read_text(encoding="latin-1", errors="replace")


async def ingest_text(
    text: str,
    *,
    source_type: str = "manual",
    source_id: str = "",
    source_path: str = "",
    provenance: Optional[dict] = None,
    db_path: Optional[Path] = None,
) -> list[Chunk]:
    """Ingest di stringa in memoria → chunker → store.

    Returns:
        Lista Chunk inseriti in DB.
    """
    if not text or not text.strip():
        return []
    chunks = chunk_markdown(
        text,
        source_path=source_path,
        source_type=source_type,
        source_id=source_id,
        provenance=provenance or {},
    )
    if chunks:
        await bulk_insert(chunks, db_path=db_path)
    logger.info(
        "ingest_text: source_type=%s source_id=%s chunks=%d",
        source_type,
        source_id,
        len(chunks),
    )
    return chunks


async def ingest_file(
    path: Path,
    *,
    source_type: str = "user_upload",
    db_path: Optional[Path] = None,
    extra_provenance: Optional[dict] = None,
) -> list[Chunk]:
    """Ingest di file da filesystem con provenance metadata completi (Conv. 43).

    Supporta: .md, .txt, .pdf, .docx. Altri formati → warning + skip.

    Returns:
        Lista Chunk inseriti in DB.
    """
    if not path.exists() or not path.is_file():
        logger.warning("ingest_file: file non esiste %s", path)
        return []

    md5 = _compute_md5(path)
    size_bytes = path.stat().st_size
    suffix = path.suffix.lower()
    mime, _ = mimetypes.guess_type(str(path))
    pages: Optional[int] = None
    parser: str

    if suffix in {".md", ".markdown"}:
        text = _read_text(path)
        parser = "markdown"
    elif suffix == ".txt":
        text = _read_text(path)
        parser = "plain-text"
    elif suffix == ".pdf":
        text, pages = _read_pdf(path)
        parser = "pypdf"
    elif suffix == ".docx":
        text = _read_docx(path)
        parser = "python-docx"
    else:
        logger.warning("ingest_file: estensione non supportata %s", suffix)
        return []

    if not text or not text.strip():
        logger.warning("ingest_file: contenuto vuoto per %s", path)
        return []

    provenance = {
        "parser": parser,
        "hash_md5": md5,
        "dimensione_byte": size_bytes,
        "mime_type": mime or "application/octet-stream",
        "data_import_vault": datetime.now(timezone.utc).isoformat(),
        "filename_original": path.name,
    }
    if pages is not None:
        provenance["pagine"] = pages
    if extra_provenance:
        provenance.update(extra_provenance)

    return await ingest_text(
        text,
        source_type=source_type,
        source_id=md5,
        source_path=str(path),
        provenance=provenance,
        db_path=db_path,
    )
