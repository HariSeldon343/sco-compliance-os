"""Vault file extractors per auto-ingestion (v0.6.0 DEV-VAULT-AUTOINGEST).

Estrattori di testo + metadata per i 7 formati supportati nell'auto-ingest
del vault SCO:

    - .md            -> frontmatter YAML + body markdown
    - .pdf           -> testo per pagina (pypdf), metadata page_count
    - .docx          -> testo paragrafi + tabelle (python-docx)
    - .xlsx          -> testo celle per foglio (openpyxl), metadata sheet_count
    - .txt           -> testo grezzo
    - .json          -> serializzazione canonica leggibile (json.dumps indent=2)
    - .yaml / .yml   -> serializzazione canonica leggibile

Pattern SCO "schema is the product":
    - ExtractedFile dataclass tipizzato, output deterministico per stesso input.
    - content_hash SHA-256 sul body normalizzato per dedup robusta cross-mtime.
    - Tutti i parser blocking sono wrapped in run_in_executor (async-compatible).

Pattern Conv. 44 lesson 1 (CircuitBreaker per estrattori):
    - Errori per file isolati: 1 file rotto non blocca il sync di altri 999.
    - Eccezioni catturate + restituite come ExtractedFile con error popolato.

Pattern Conv. 47 (single source of truth):
    - Dispatch dictionary EXTRACTORS singola fonte di verita per estensioni.
    - Aggiungere nuovo formato = aggiungere una entry al dict + funzione.

Pattern Conv. 41 (tracciatura):
    - Logger structured per ogni estrazione (path, bytes, tokens stimati, errors).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Mime type lookup per estensione (deterministico, niente sniffing magic bytes).
_MIME_TYPES: dict[str, str] = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
}

# Estensioni supportate (immutabile, single source of truth).
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(_MIME_TYPES.keys())

# Frontmatter regex (riusa pattern di parser.py per coerenza).
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass(slots=True)
class ExtractedFile:
    """Risultato dell'estrazione di un file vault.

    Attributes:
        path: path assoluto del file estratto (str per JSON-serializable).
        mime_type: lookup deterministico da estensione.
        text_content: testo estratto, post-normalizzazione minima.
        metadata: dict tipo-specifico (frontmatter, page_count, sheet_count, ecc.).
        mtime_ms: timestamp ultima modifica filesystem (POSIX ms UTC).
        size_bytes: dimensione file in byte.
        content_hash: SHA-256 hex sul text_content (per dedup invarianza mtime).
        extension: estensione lowercased con dot (es. '.md').
        error: messaggio errore se estrazione fallita (None se OK).
    """

    path: str
    mime_type: str
    text_content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    mtime_ms: int = 0
    size_bytes: int = 0
    content_hash: str = ""
    extension: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True se estrazione completata senza errore."""
        return self.error is None


def _compute_content_hash(text: str) -> str:
    """SHA-256 hex sul testo estratto, troncato a 32 chars (128 bit)."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:32]


def _file_stat(path: Path) -> tuple[int, int]:
    """Ritorna (mtime_ms, size_bytes) del file, con fallback safe su errore."""
    try:
        st = path.stat()
        mtime_ms = int(st.st_mtime * 1000)
        size_bytes = int(st.st_size)
        return mtime_ms, size_bytes
    except OSError as exc:
        logger.warning("file_stat failed for %s: %s", path, exc)
        return 0, 0


def _build_empty_result(path: Path, error: str) -> ExtractedFile:
    """Costruisce ExtractedFile minimo per fallimento."""
    mtime_ms, size_bytes = _file_stat(path)
    ext = path.suffix.lower()
    return ExtractedFile(
        path=str(path),
        mime_type=_MIME_TYPES.get(ext, "application/octet-stream"),
        text_content="",
        metadata={},
        mtime_ms=mtime_ms,
        size_bytes=size_bytes,
        content_hash="",
        extension=ext,
        error=error,
    )


# --------------------------------------------------------------------------
# Estrattori sincroni (chiamati via run_in_executor da dispatch async)
# --------------------------------------------------------------------------


def _read_text_safe(path: Path) -> str:
    """Lettura testo con fallback latin-1 su UnicodeDecodeError."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="replace")


def _extract_md_sync(path: Path) -> ExtractedFile:
    """Estrae frontmatter YAML + body markdown da file .md."""
    mtime_ms, size_bytes = _file_stat(path)
    ext = path.suffix.lower()
    try:
        content = _read_text_safe(path)
    except OSError as exc:
        return _build_empty_result(path, f"read_error: {exc}")

    fm: dict[str, Any] = {}
    body = content
    match = _FRONTMATTER_RE.match(content)
    if match:
        body = match.group(2)
        try:
            import yaml  # type: ignore

            parsed = yaml.safe_load(match.group(1)) or {}
            if isinstance(parsed, dict):
                fm = parsed
        except Exception as yaml_err:  # noqa: BLE001
            # YAML invalido: prosegui con body senza frontmatter strutturato
            # (Conv. 41 tracciatura: errore loggato ma non blocca)
            logger.debug("md frontmatter parse failed for %s: %s", path, yaml_err)

    return ExtractedFile(
        path=str(path),
        mime_type=_MIME_TYPES[".md"],
        text_content=body.strip(),
        metadata={
            "frontmatter": fm,
            "has_frontmatter": bool(fm),
        },
        mtime_ms=mtime_ms,
        size_bytes=size_bytes,
        content_hash=_compute_content_hash(body),
        extension=ext,
    )


def _extract_pdf_sync(path: Path) -> ExtractedFile:
    """Estrae testo da PDF via pypdf (gia in deps)."""
    mtime_ms, size_bytes = _file_stat(path)
    ext = path.suffix.lower()
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as imp_err:
        return _build_empty_result(path, f"pypdf_unavailable: {imp_err}")

    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001
        return _build_empty_result(path, f"pdf_open_error: {exc}")

    pages_text: list[str] = []
    page_count = 0
    try:
        for page in reader.pages:
            page_count += 1
            try:
                txt = page.extract_text() or ""
            except Exception as page_err:  # noqa: BLE001
                logger.debug(
                    "pdf page extract failed (path=%s page=%d): %s",
                    path,
                    page_count,
                    page_err,
                )
                txt = ""
            if txt.strip():
                pages_text.append(txt.strip())
    except Exception as exc:  # noqa: BLE001
        return _build_empty_result(path, f"pdf_iterate_error: {exc}")

    body = "\n\n".join(pages_text)
    return ExtractedFile(
        path=str(path),
        mime_type=_MIME_TYPES[".pdf"],
        text_content=body,
        metadata={
            "page_count": page_count,
            "non_empty_pages": len(pages_text),
        },
        mtime_ms=mtime_ms,
        size_bytes=size_bytes,
        content_hash=_compute_content_hash(body),
        extension=ext,
    )


def _extract_docx_sync(path: Path) -> ExtractedFile:
    """Estrae paragrafi + celle tabelle da file .docx via python-docx."""
    mtime_ms, size_bytes = _file_stat(path)
    ext = path.suffix.lower()
    try:
        from docx import Document  # type: ignore
    except ImportError as imp_err:
        return _build_empty_result(path, f"python_docx_unavailable: {imp_err}")

    try:
        doc = Document(str(path))
    except Exception as exc:  # noqa: BLE001
        return _build_empty_result(path, f"docx_open_error: {exc}")

    parts: list[str] = []
    para_count = 0
    table_count = 0
    try:
        for para in doc.paragraphs:
            para_count += 1
            txt = (para.text or "").strip()
            if txt:
                parts.append(txt)
        for table in doc.tables:
            table_count += 1
            for row in table.rows:
                row_txt = " | ".join((cell.text or "").strip() for cell in row.cells)
                if row_txt.strip(" |"):
                    parts.append(row_txt)
    except Exception as exc:  # noqa: BLE001
        # Errore parziale: ritorna quello estratto + segna l'errore
        body_so_far = "\n".join(parts)
        return ExtractedFile(
            path=str(path),
            mime_type=_MIME_TYPES[".docx"],
            text_content=body_so_far,
            metadata={"paragraph_count": para_count, "table_count": table_count},
            mtime_ms=mtime_ms,
            size_bytes=size_bytes,
            content_hash=_compute_content_hash(body_so_far),
            extension=ext,
            error=f"docx_partial_extract: {exc}",
        )

    body = "\n".join(parts)
    return ExtractedFile(
        path=str(path),
        mime_type=_MIME_TYPES[".docx"],
        text_content=body,
        metadata={
            "paragraph_count": para_count,
            "table_count": table_count,
        },
        mtime_ms=mtime_ms,
        size_bytes=size_bytes,
        content_hash=_compute_content_hash(body),
        extension=ext,
    )


def _extract_xlsx_sync(path: Path) -> ExtractedFile:
    """Estrae celle non-vuote per foglio da file .xlsx via openpyxl."""
    mtime_ms, size_bytes = _file_stat(path)
    ext = path.suffix.lower()
    try:
        from openpyxl import load_workbook  # type: ignore
    except ImportError as imp_err:
        return _build_empty_result(path, f"openpyxl_unavailable: {imp_err}")

    try:
        # read_only=True + data_only=True: ignora formule, ritorna valori cached.
        wb = load_workbook(str(path), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        return _build_empty_result(path, f"xlsx_open_error: {exc}")

    parts: list[str] = []
    sheet_names: list[str] = []
    total_cells = 0
    try:
        for sheet_name in wb.sheetnames:
            sheet_names.append(sheet_name)
            parts.append(f"# Sheet: {sheet_name}")
            ws = wb[sheet_name]
            for row in ws.iter_rows(values_only=True):
                # Salta righe completamente vuote
                row_vals = [
                    str(v).strip() for v in row if v is not None and str(v).strip()
                ]
                if not row_vals:
                    continue
                total_cells += len(row_vals)
                parts.append(" | ".join(row_vals))
    except Exception as exc:  # noqa: BLE001
        body_so_far = "\n".join(parts)
        return ExtractedFile(
            path=str(path),
            mime_type=_MIME_TYPES[".xlsx"],
            text_content=body_so_far,
            metadata={
                "sheet_count": len(sheet_names),
                "sheet_names": sheet_names,
                "non_empty_cells": total_cells,
            },
            mtime_ms=mtime_ms,
            size_bytes=size_bytes,
            content_hash=_compute_content_hash(body_so_far),
            extension=ext,
            error=f"xlsx_partial_extract: {exc}",
        )
    finally:
        try:
            wb.close()
        except Exception:  # noqa: BLE001, S110
            pass

    body = "\n".join(parts)
    return ExtractedFile(
        path=str(path),
        mime_type=_MIME_TYPES[".xlsx"],
        text_content=body,
        metadata={
            "sheet_count": len(sheet_names),
            "sheet_names": sheet_names,
            "non_empty_cells": total_cells,
        },
        mtime_ms=mtime_ms,
        size_bytes=size_bytes,
        content_hash=_compute_content_hash(body),
        extension=ext,
    )


def _extract_txt_sync(path: Path) -> ExtractedFile:
    """Estrae testo grezzo da file .txt."""
    mtime_ms, size_bytes = _file_stat(path)
    ext = path.suffix.lower()
    try:
        body = _read_text_safe(path)
    except OSError as exc:
        return _build_empty_result(path, f"read_error: {exc}")

    return ExtractedFile(
        path=str(path),
        mime_type=_MIME_TYPES[".txt"],
        text_content=body.strip(),
        metadata={"line_count": body.count("\n") + 1},
        mtime_ms=mtime_ms,
        size_bytes=size_bytes,
        content_hash=_compute_content_hash(body),
        extension=ext,
    )


def _extract_json_sync(path: Path) -> ExtractedFile:
    """Estrae JSON come testo canonico indent=2 + valida sintassi."""
    mtime_ms, size_bytes = _file_stat(path)
    ext = path.suffix.lower()
    try:
        raw = _read_text_safe(path)
    except OSError as exc:
        return _build_empty_result(path, f"read_error: {exc}")

    parsed: Any
    valid_json = True
    try:
        parsed = json.loads(raw)
        body = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=False)
    except json.JSONDecodeError as exc:
        # JSON invalido: usa raw come fallback, segna metadata
        logger.debug("json parse failed for %s: %s", path, exc)
        body = raw.strip()
        valid_json = False

    return ExtractedFile(
        path=str(path),
        mime_type=_MIME_TYPES[".json"],
        text_content=body,
        metadata={
            "valid_json": valid_json,
        },
        mtime_ms=mtime_ms,
        size_bytes=size_bytes,
        content_hash=_compute_content_hash(body),
        extension=ext,
    )


def _extract_yaml_sync(path: Path) -> ExtractedFile:
    """Estrae YAML come testo canonico (preserva struttura)."""
    mtime_ms, size_bytes = _file_stat(path)
    ext = path.suffix.lower()
    try:
        raw = _read_text_safe(path)
    except OSError as exc:
        return _build_empty_result(path, f"read_error: {exc}")

    valid_yaml = True
    body = raw.strip()
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(raw)
        if parsed is not None:
            # Riserializza per canonicalizzare formattazione/indentazione
            body = yaml.safe_dump(
                parsed,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            ).strip()
    except Exception as exc:  # noqa: BLE001
        logger.debug("yaml parse failed for %s: %s", path, exc)
        valid_yaml = False

    return ExtractedFile(
        path=str(path),
        mime_type=_MIME_TYPES[ext],
        text_content=body,
        metadata={
            "valid_yaml": valid_yaml,
        },
        mtime_ms=mtime_ms,
        size_bytes=size_bytes,
        content_hash=_compute_content_hash(body),
        extension=ext,
    )


# --------------------------------------------------------------------------
# Dispatch table (Conv. 47 single source of truth)
# --------------------------------------------------------------------------


# Type alias per il dispatch (Path -> ExtractedFile sync).
ExtractorFn = Callable[[Path], ExtractedFile]

EXTRACTORS: dict[str, ExtractorFn] = {
    ".md": _extract_md_sync,
    ".markdown": _extract_md_sync,
    ".pdf": _extract_pdf_sync,
    ".docx": _extract_docx_sync,
    ".xlsx": _extract_xlsx_sync,
    ".txt": _extract_txt_sync,
    ".json": _extract_json_sync,
    ".yaml": _extract_yaml_sync,
    ".yml": _extract_yaml_sync,
}


# --------------------------------------------------------------------------
# API pubblica (async wrappers)
# --------------------------------------------------------------------------


def is_supported(path: Path) -> bool:
    """True se l'estensione del file e' supportata da un extractor."""
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


async def extract_file(path: Path) -> ExtractedFile:
    """Estrazione async di un file vault tramite dispatch su estensione.

    Wrappa estrattori sincroni (potenzialmente blocking I/O) in run_in_executor
    per non bloccare il sidecar uvicorn async loop.

    Args:
        path: path assoluto del file. Deve esistere e essere supportato.

    Returns:
        ExtractedFile con error popolato se l'estrazione fallisce.
        MAI solleva eccezione: gli errori vivono nel campo `error`.
    """
    if not path.exists():
        return _build_empty_result(path, "file_not_found")
    if not path.is_file():
        return _build_empty_result(path, "not_a_file")

    ext = path.suffix.lower()
    extractor = EXTRACTORS.get(ext)
    if extractor is None:
        return _build_empty_result(path, f"unsupported_extension: {ext}")

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, extractor, path)
    except Exception as exc:  # noqa: BLE001
        logger.error("extract_file unexpected error path=%s: %s", path, exc)
        return _build_empty_result(path, f"extract_unhandled: {exc}")

    if result.ok:
        logger.debug(
            "extracted ok path=%s ext=%s bytes=%d text_len=%d",
            path,
            ext,
            result.size_bytes,
            len(result.text_content),
        )
    else:
        logger.warning(
            "extract_file error path=%s ext=%s error=%s",
            path,
            ext,
            result.error,
        )
    return result


def utc_now_ms() -> int:
    """Timestamp POSIX ms UTC corrente (utility per metadata mtime fallback)."""
    return int(datetime.now(UTC).timestamp() * 1000)


__all__ = [
    "EXTRACTORS",
    "ExtractedFile",
    "ExtractorFn",
    "SUPPORTED_EXTENSIONS",
    "extract_file",
    "is_supported",
    "utc_now_ms",
]
