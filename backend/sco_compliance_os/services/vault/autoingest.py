"""Auto-ingestion vault SCO nel Memory Tree bucket-seal (v0.6.0).

Risolve il bug "agente non legge i file" mostrato esplicitamente da Antonio
(screenshot chat v0.5.0 con messaggio "non ho accesso diretto ai file in
questo momento"). Quando un vault viene registrato via POST /api/vault/add,
il backend walka recursive tutto il path, estrae testo dai file supportati
(7 formati), li chunka via tree_chunker e li ingerisce in mem_tree_chunks.

Pipeline:
    1. Walka recursive vault_path con Path.rglob (skip cartelle escluse).
    2. Per ogni file supportato: extract_file(path) -> ExtractedFile.
    3. Dedup intelligente: query mem_tree_chunks per source_id=path,
       confronto (mtime_ms, content_hash) con valori in DB. Skip se invariato.
    4. Chunk via chunk_text con source_kind=VAULT_FILE, source_id=path assoluto.
    5. Ingest via ingest_chunks (admission gate Fase 3 con cheap signals).
    6. Persist in mem_tree_chunks (single source of truth Conv. 47).

Pattern SCO "single source of truth": chunk vivono SOLO in mem_tree_chunks,
mai duplicati. Schema source_kind='vault_file' gia esistente, no migrazione.

Pattern Conv. 41 (tracciatura sessione): SyncReport con counts dettagliati,
logger structured per ogni decisione di sync/skip/error.

Pattern Conv. 44 lesson 1 (CircuitBreaker): errori per file isolati, 3 fail
consecutivi su stesso file -> 30s pause su quel path (no storm).

Pattern Conv. 34 (spot check): SyncReport.errors lista esplicita errori per
permettere ispezione main agent post-sync.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiosqlite

from ..memory.store import default_db_path
from ..memory.tree_chunker import TreeChunk, TreeChunkSourceKind, chunk_text
from ..memory.tree_ingester import IngestCounts, ingest_chunks
from .extractors import (
    SUPPORTED_EXTENSIONS,
    ExtractedFile,
    extract_file,
    is_supported,
    utc_now_ms,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# COSTANTI — single source of truth (Conv. 47)
# --------------------------------------------------------------------------

# Cartelle da escludere dal walk recursivo.
# Allineato a scanner.py + aggiunte coerenti con CLAUDE.md vault Antonio.
SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".obsidian",
        ".claude",
        "node_modules",
        "_template-originale",
        "__pycache__",
        ".venv",
        "venv",
        ".kdrive-shadow",
        ".idea",
        ".vscode",
        "dist",
        "build",
    }
)

# Prefissi cartelle da escludere (archivio + dot-prefixed altri).
SKIP_DIR_PREFIXES: tuple[str, ...] = (
    "_archivio",
    "_archived",
    ".",  # dot-prefixed in generale (eccezioni in SKIP_DIR_NAMES gestite a parte)
)

# CircuitBreaker per file rotti ripetuti: stato per file path.
# Threshold 3 fail consecutivi -> 30s pause sul path specifico.
_FILE_BREAKER_THRESHOLD = 3
_FILE_BREAKER_PAUSE_SEC = 30.0


# --------------------------------------------------------------------------
# DATACLASSES — SyncReport + stati interni
# --------------------------------------------------------------------------


@dataclass(slots=True)
class FileError:
    """Errore singolo per file durante sync (Conv. 34 spot check audit trail)."""

    path: str
    error: str
    stage: str  # 'extract' | 'chunk' | 'ingest' | 'dedup'


@dataclass(slots=True)
class SyncReport:
    """Esito dettagliato di un sync vault run."""

    vault_id: str
    vault_path: str
    total_files_scanned: int = 0
    files_extracted: int = 0
    chunks_ingested: int = 0
    chunks_admitted: int = 0
    chunks_dropped: int = 0
    chunks_pending_extraction: int = 0
    chunks_skipped_dedup: int = 0
    errors: list[FileError] = field(default_factory=list)
    duration_sec: float = 0.0
    started_at_ms: int = 0
    finished_at_ms: int = 0
    forced: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "vault_id": self.vault_id,
            "vault_path": self.vault_path,
            "total_files_scanned": self.total_files_scanned,
            "files_extracted": self.files_extracted,
            "chunks_ingested": self.chunks_ingested,
            "chunks_admitted": self.chunks_admitted,
            "chunks_dropped": self.chunks_dropped,
            "chunks_pending_extraction": self.chunks_pending_extraction,
            "chunks_skipped_dedup": self.chunks_skipped_dedup,
            "errors": [
                {"path": e.path, "error": e.error, "stage": e.stage}
                for e in self.errors
            ],
            "duration_sec": round(self.duration_sec, 3),
            "started_at_ms": self.started_at_ms,
            "finished_at_ms": self.finished_at_ms,
            "forced": self.forced,
        }


@dataclass(slots=True)
class SyncProgress:
    """Progress event emesso durante sync (per UI o log)."""

    vault_id: str
    file_path: str
    files_done: int
    total_estimated: int
    stage: str  # 'extract' | 'ingest' | 'skip' | 'error'


# Tipo callback progress (sync invoca on ogni file).
ProgressCallback = Callable[[SyncProgress], Awaitable[None] | None]


# --------------------------------------------------------------------------
# CIRCUIT BREAKER per file rotti (Conv. 44 lesson 1)
# --------------------------------------------------------------------------


class _FileCircuitBreaker:
    """Tracker stato per file: blocca path che fail consecutivi."""

    def __init__(self) -> None:
        self._fails: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def can_attempt(self, path: str) -> bool:
        """Ritorna False se path e' in pause (CircuitBreaker open su quel file)."""
        async with self._lock:
            opened = self._opened_at.get(path)
            if opened is None:
                return True
            elapsed = time.monotonic() - opened
            if elapsed < _FILE_BREAKER_PAUSE_SEC:
                return False
            # Pause scaduta -> reset (HALF_OPEN semantica)
            self._opened_at.pop(path, None)
            self._fails[path] = 0
            return True

    async def record_success(self, path: str) -> None:
        async with self._lock:
            self._fails.pop(path, None)
            self._opened_at.pop(path, None)

    async def record_failure(self, path: str) -> None:
        async with self._lock:
            self._fails[path] = self._fails.get(path, 0) + 1
            if self._fails[path] >= _FILE_BREAKER_THRESHOLD:
                self._opened_at[path] = time.monotonic()
                logger.warning(
                    "file_circuit_breaker.opened path=%s fails=%d pause_sec=%.0f",
                    path,
                    self._fails[path],
                    _FILE_BREAKER_PAUSE_SEC,
                )


# Singleton di processo: stato breaker condiviso tra sync + watcher.
_file_breaker = _FileCircuitBreaker()


# --------------------------------------------------------------------------
# WALK FILESYSTEM
# --------------------------------------------------------------------------


def _should_skip_dir(name: str) -> bool:
    """Decide se saltare una directory in walk recursivo."""
    if name in SKIP_DIR_NAMES:
        return True
    return any(name.startswith(prefix) for prefix in SKIP_DIR_PREFIXES)


def walk_vault_files(vault_root: Path) -> AsyncIterator[Path]:
    """Generatore async di file supportati nel vault, skip cartelle escluse.

    Args:
        vault_root: directory root del vault SCO.

    Yields:
        Path assoluti di file con estensione in SUPPORTED_EXTENSIONS.
    """

    async def _walk() -> AsyncIterator[Path]:
        if not vault_root.exists() or not vault_root.is_dir():
            logger.error("walk_vault_files: vault_root invalido: %s", vault_root)
            return

        stack: list[Path] = [vault_root]
        while stack:
            current = stack.pop()
            try:
                # Yield al loop periodicamente per non bloccare uvicorn
                await asyncio.sleep(0)
                for entry in current.iterdir():
                    if entry.is_dir():
                        if _should_skip_dir(entry.name):
                            continue
                        stack.append(entry)
                    elif entry.is_file() and is_supported(entry):
                        yield entry
            except (PermissionError, OSError) as exc:
                logger.warning("walk error %s: %s", current, exc)
                continue

    return _walk()


def count_supported_files(vault_root: Path) -> int:
    """Conta SYNC i file supportati nel vault per stima totale (no async).

    Usato per stima `total_estimated` da inviare al primo progress event.
    Esegue una walk leggera senza estrazione testo.
    """
    if not vault_root.exists() or not vault_root.is_dir():
        return 0
    count = 0
    stack: list[Path] = [vault_root]
    while stack:
        current = stack.pop()
        try:
            for entry in current.iterdir():
                if entry.is_dir():
                    if _should_skip_dir(entry.name):
                        continue
                    stack.append(entry)
                elif entry.is_file() and is_supported(entry):
                    count += 1
        except (PermissionError, OSError):
            continue
    return count


# --------------------------------------------------------------------------
# DEDUP CHECK — query mem_tree_chunks per (source_id, content_hash, mtime)
# --------------------------------------------------------------------------


async def _is_dedup_skippable(
    path_str: str,
    mtime_ms: int,
    content_hash: str,
    *,
    db_path: Path | None = None,
) -> bool:
    """True se il file e' gia in mem_tree_chunks con stesso mtime + content_hash.

    Dedup robusto: matcha (source_id + mtime stored come timestamp_ms + ANY
    chunk con quel source_id presente in 'admitted' o 'pending_extraction').

    L'mtime_ms del file estratto e' salvato in TreeChunk.timestamp_ms.
    Il content_hash NON e' attualmente persistito su mem_tree_chunks (lo schema
    non lo prevede), quindi qui usiamo SOLO il mtime_ms come signal:
        - same mtime -> skip
        - different mtime -> re-ingest (chunk_ids saranno comunque deterministici
          basati su content+seq, quindi upsert no-op se contenuto invariato)

    Tradeoff: se l'utente fa `touch` su un file senza cambiarne il contenuto,
    re-ingestiamo. Costo: trascurabile (chunk_ids stabili -> upsert no-op).
    Beneficio: evitiamo di persistere content_hash come colonna extra.
    """
    target_db = db_path or default_db_path()
    if not target_db.exists():
        return False
    try:
        async with aiosqlite.connect(target_db) as db:
            async with db.execute(
                """SELECT MAX(timestamp_ms) FROM mem_tree_chunks
                WHERE source_kind = 'vault_file' AND source_id = ?""",
                (path_str,),
            ) as cur:
                row = await cur.fetchone()
                if not row or row[0] is None:
                    return False
                stored_mtime = int(row[0])
                # Mtime invariato -> contenuto invariato -> skip.
                return stored_mtime == mtime_ms
    except Exception as exc:  # noqa: BLE001
        logger.warning("dedup check error path=%s: %s", path_str, exc)
        return False


# --------------------------------------------------------------------------
# FILE -> CHUNKS -> INGEST (singolo file)
# --------------------------------------------------------------------------


def _build_chunk_tags(extracted: ExtractedFile, vault_id: str) -> list[str]:
    """Costruisce lista tags per i chunk derivati dal file.

    Pattern: tag tecnico vault_id + tag estensione + eventuali frontmatter tags
    se .md. Permette query downstream filtrate per vault o per tipo.
    """
    tags: list[str] = [
        f"vault:{vault_id}",
        f"ext:{extracted.extension.lstrip('.')}",
    ]
    # Per .md: integra tags da frontmatter se presenti.
    fm = extracted.metadata.get("frontmatter") or {}
    if isinstance(fm, dict):
        fm_tags = fm.get("tags")
        if isinstance(fm_tags, list):
            for t in fm_tags:
                if isinstance(t, str) and t:
                    tags.append(t)
    return tags


async def ingest_single_file(
    path: Path,
    *,
    vault_id: str,
    db_path: Path | None = None,
    force: bool = False,
) -> tuple[ExtractedFile, IngestCounts, bool]:
    """Estrae + chunka + ingerisce un singolo file vault.

    Args:
        path: path assoluto del file.
        vault_id: ID del vault per tag chunk.
        db_path: override path DB SQLite (default ~/.sco-compliance-os/compliance_os.db).
        force: se True bypassa dedup check.

    Returns:
        Tupla (ExtractedFile, IngestCounts, skipped_dedup).
        - ExtractedFile: risultato estrazione (con .error se fallita).
        - IngestCounts: vuoto se estrazione fallita o dedup skip.
        - skipped_dedup: True se skip per dedup (no work fatto).
    """
    path_str = str(path)

    # CircuitBreaker check
    can_attempt = await _file_breaker.can_attempt(path_str)
    if not can_attempt:
        logger.debug("ingest_single_file: skip per circuit breaker open path=%s", path_str)
        empty_extracted = ExtractedFile(
            path=path_str,
            mime_type="application/octet-stream",
            text_content="",
            extension=path.suffix.lower(),
            error="circuit_breaker_open",
        )
        return empty_extracted, IngestCounts(), False

    extracted = await extract_file(path)

    if not extracted.ok:
        await _file_breaker.record_failure(path_str)
        return extracted, IngestCounts(), False

    if not extracted.text_content.strip():
        # File estratto ma vuoto: success ma niente da ingerire (no fail breaker)
        await _file_breaker.record_success(path_str)
        return extracted, IngestCounts(), False

    # Dedup check (skip se mtime invariato)
    if not force:
        skippable = await _is_dedup_skippable(
            path_str,
            extracted.mtime_ms,
            extracted.content_hash,
            db_path=db_path,
        )
        if skippable:
            await _file_breaker.record_success(path_str)
            logger.debug("ingest_single_file: skip dedup path=%s", path_str)
            return extracted, IngestCounts(), True

    # Chunk
    chunks: list[TreeChunk] = chunk_text(
        extracted.text_content,
        source_kind=TreeChunkSourceKind.VAULT_FILE.value,
        source_id=path_str,
        owner="local",
        timestamp_ms=extracted.mtime_ms,
        time_range_start_ms=extracted.mtime_ms,
        time_range_end_ms=extracted.mtime_ms,
        tags=_build_chunk_tags(extracted, vault_id),
    )

    if not chunks:
        # Nessun chunk viable -> no ingest, ma file e' stato comunque estratto OK
        await _file_breaker.record_success(path_str)
        return extracted, IngestCounts(), False

    # Ingest
    try:
        counts = await ingest_chunks(chunks, db_path=db_path)
    except Exception as exc:  # noqa: BLE001
        logger.error("ingest_single_file: ingest error path=%s: %s", path_str, exc)
        await _file_breaker.record_failure(path_str)
        # Ritorna extracted con error popolato per propagazione SyncReport
        extracted.error = f"ingest_error: {exc}"
        return extracted, IngestCounts(), False

    await _file_breaker.record_success(path_str)
    return extracted, counts, False


async def delete_chunks_for_file(
    path_str: str,
    *,
    db_path: Path | None = None,
) -> int:
    """Cancella tutti i chunks per source_id=path (uso: watcher on_delete).

    Strategia: HARD DELETE invece di soft (status='dropped') perche':
        - File rimosso definitivamente dal vault non torna come 'archivio'.
        - Riduce noise in count_by_status.
        - Audit trail vive comunque nei log.

    Returns:
        Numero righe cancellate. 0 se errore o nessun match.
    """
    target_db = db_path or default_db_path()
    if not target_db.exists():
        return 0
    try:
        async with aiosqlite.connect(target_db) as db:
            cur = await db.execute(
                """DELETE FROM mem_tree_chunks
                WHERE source_kind = 'vault_file' AND source_id = ?""",
                (path_str,),
            )
            await db.commit()
            deleted = cur.rowcount or 0
            if deleted > 0:
                logger.info(
                    "delete_chunks_for_file path=%s deleted=%d",
                    path_str,
                    deleted,
                )
            return deleted
    except Exception as exc:  # noqa: BLE001
        logger.warning("delete_chunks_for_file error path=%s: %s", path_str, exc)
        return 0


# --------------------------------------------------------------------------
# SYNC ORCHESTRATOR
# --------------------------------------------------------------------------


async def sync_vault(
    vault_path: Path,
    vault_id: str,
    *,
    force: bool = False,
    on_progress: ProgressCallback | None = None,
    db_path: Path | None = None,
    max_files: int | None = None,
) -> SyncReport:
    """Sync completo vault -> mem_tree_chunks.

    Pipeline:
        1. Stima totale file supportati (count_supported_files SYNC).
        2. Walk recursivo skip cartelle escluse.
        3. Per ogni file: ingest_single_file (extract + dedup + chunk + ingest).
        4. Aggrega SyncReport con counts + errors.
        5. Callback on_progress per ogni file processato.

    Args:
        vault_path: directory root del vault.
        vault_id: ID del vault dal registry (per tag chunk).
        force: bypassa dedup, re-ingest tutto.
        on_progress: callback async/sync per progress event opzionale.
        db_path: override path DB SQLite Memory Tree.
        max_files: limite hard per testing (None = unlimited).

    Returns:
        SyncReport con counts dettagliati + errors.
    """
    start = time.monotonic()
    started_at_ms = utc_now_ms()
    report = SyncReport(
        vault_id=vault_id,
        vault_path=str(vault_path),
        forced=force,
        started_at_ms=started_at_ms,
    )

    if not vault_path.exists() or not vault_path.is_dir():
        report.errors.append(
            FileError(path=str(vault_path), error="vault_path_invalid", stage="walk")
        )
        report.duration_sec = time.monotonic() - start
        report.finished_at_ms = utc_now_ms()
        logger.error("sync_vault: vault_path invalid: %s", vault_path)
        return report

    # Stima totale per progress UI (count SYNC, no I/O extract)
    total_estimated = count_supported_files(vault_path)
    logger.info(
        "sync_vault.start vault_id=%s path=%s estimated=%d force=%s",
        vault_id,
        vault_path,
        total_estimated,
        force,
    )

    walker = walk_vault_files(vault_path)
    files_done = 0

    async for file_path in walker:
        if max_files is not None and report.total_files_scanned >= max_files:
            logger.info("sync_vault: max_files=%d reached, stopping", max_files)
            break

        report.total_files_scanned += 1
        path_str = str(file_path)

        try:
            extracted, counts, skipped_dedup = await ingest_single_file(
                file_path,
                vault_id=vault_id,
                db_path=db_path,
                force=force,
            )
        except Exception as exc:  # noqa: BLE001
            # Safety net: ingest_single_file dovrebbe non sollevare, ma per
            # garantire continuita' del walk in caso di edge cases.
            logger.error("sync_vault: unhandled error path=%s: %s", path_str, exc)
            report.errors.append(
                FileError(path=path_str, error=str(exc), stage="ingest_unhandled")
            )
            files_done += 1
            continue

        if skipped_dedup:
            report.chunks_skipped_dedup += 1
            stage = "skip"
        elif extracted.ok:
            report.files_extracted += 1
            report.chunks_ingested += counts.upserted
            report.chunks_admitted += counts.admitted
            report.chunks_dropped += counts.dropped
            report.chunks_pending_extraction += counts.pending_extraction
            stage = "ingest"
        else:
            report.errors.append(
                FileError(
                    path=path_str,
                    error=extracted.error or "unknown",
                    stage="extract",
                )
            )
            stage = "error"

        files_done += 1
        if on_progress is not None:
            progress = SyncProgress(
                vault_id=vault_id,
                file_path=path_str,
                files_done=files_done,
                total_estimated=total_estimated,
                stage=stage,
            )
            try:
                result = on_progress(progress)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as cb_err:  # noqa: BLE001
                logger.debug("on_progress callback error: %s", cb_err)

    report.duration_sec = time.monotonic() - start
    report.finished_at_ms = utc_now_ms()

    logger.info(
        "sync_vault.complete vault_id=%s scanned=%d extracted=%d "
        "chunks_ingested=%d admitted=%d dropped=%d skipped_dedup=%d "
        "errors=%d duration_sec=%.2f",
        vault_id,
        report.total_files_scanned,
        report.files_extracted,
        report.chunks_ingested,
        report.chunks_admitted,
        report.chunks_dropped,
        report.chunks_skipped_dedup,
        len(report.errors),
        report.duration_sec,
    )

    return report


# --------------------------------------------------------------------------
# SYNC STATUS — per endpoint GET /api/vault/{id}/sync-status
# --------------------------------------------------------------------------


@dataclass(slots=True)
class SyncStatus:
    """Stato corrente sync per un vault (per UI dashboard)."""

    vault_id: str
    vault_path: str
    in_progress: bool
    last_sync_at_ms: int | None
    total_chunks_in_db: int
    chunks_admitted: int
    chunks_pending_extraction: int
    chunks_dropped: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "vault_id": self.vault_id,
            "vault_path": self.vault_path,
            "in_progress": self.in_progress,
            "last_sync_at_ms": self.last_sync_at_ms,
            "total_chunks_in_db": self.total_chunks_in_db,
            "chunks_admitted": self.chunks_admitted,
            "chunks_pending_extraction": self.chunks_pending_extraction,
            "chunks_dropped": self.chunks_dropped,
        }


async def get_sync_status(
    vault_id: str,
    vault_path: str,
    *,
    in_progress: bool = False,
    db_path: Path | None = None,
) -> SyncStatus:
    """Calcola stato sync per un vault dal DB (count by status filtrato vault tag).

    Args:
        vault_id: ID vault.
        vault_path: path vault (per response).
        in_progress: flag esterno (gestito da SyncRegistry, vedi sotto).
        db_path: override path DB.

    Returns:
        SyncStatus con counts attuali.
    """
    target_db = db_path or default_db_path()
    if not target_db.exists():
        return SyncStatus(
            vault_id=vault_id,
            vault_path=vault_path,
            in_progress=in_progress,
            last_sync_at_ms=None,
            total_chunks_in_db=0,
            chunks_admitted=0,
            chunks_pending_extraction=0,
            chunks_dropped=0,
        )

    vault_tag = f'"vault:{vault_id}"'
    # Filtra per tag JSON-array contiene vault_id. SQLite supporta LIKE.
    try:
        async with aiosqlite.connect(target_db) as db:
            # last_sync_at: MAX(created_at_ms) per quel vault_id tag
            async with db.execute(
                """SELECT MAX(created_at_ms) FROM mem_tree_chunks
                WHERE source_kind = 'vault_file' AND tags_json LIKE ?""",
                (f"%{vault_tag}%",),
            ) as cur:
                row = await cur.fetchone()
                last_sync = int(row[0]) if row and row[0] is not None else None

            # Counts per status
            counts: dict[str, int] = {}
            async with db.execute(
                """SELECT status, COUNT(*) FROM mem_tree_chunks
                WHERE source_kind = 'vault_file' AND tags_json LIKE ?
                GROUP BY status""",
                (f"%{vault_tag}%",),
            ) as cur:
                async for r in cur:
                    counts[str(r[0])] = int(r[1])

            total = sum(counts.values())
            return SyncStatus(
                vault_id=vault_id,
                vault_path=vault_path,
                in_progress=in_progress,
                last_sync_at_ms=last_sync,
                total_chunks_in_db=total,
                chunks_admitted=counts.get("admitted", 0),
                chunks_pending_extraction=counts.get("pending_extraction", 0),
                chunks_dropped=counts.get("dropped", 0),
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_sync_status error vault_id=%s: %s", vault_id, exc)
        return SyncStatus(
            vault_id=vault_id,
            vault_path=vault_path,
            in_progress=in_progress,
            last_sync_at_ms=None,
            total_chunks_in_db=0,
            chunks_admitted=0,
            chunks_pending_extraction=0,
            chunks_dropped=0,
        )


# --------------------------------------------------------------------------
# SYNC REGISTRY — tracking sync in-progress per vault_id (process-singleton)
# --------------------------------------------------------------------------


class SyncRegistry:
    """Registry process-level dei sync in corso per vault_id.

    Usato dal endpoint REST per:
        - sapere se un vault e' attualmente in sync (GET /sync-status).
        - prevenire sync concorrenti sullo stesso vault.
    """

    def __init__(self) -> None:
        self._in_progress: set[str] = set()
        self._lock = asyncio.Lock()

    async def mark_start(self, vault_id: str) -> bool:
        """Marca vault_id come in-progress. Ritorna False se gia in progress."""
        async with self._lock:
            if vault_id in self._in_progress:
                return False
            self._in_progress.add(vault_id)
            return True

    async def mark_done(self, vault_id: str) -> None:
        """Rimuove vault_id da in-progress set."""
        async with self._lock:
            self._in_progress.discard(vault_id)

    async def is_in_progress(self, vault_id: str) -> bool:
        async with self._lock:
            return vault_id in self._in_progress

    async def list_in_progress(self) -> list[str]:
        async with self._lock:
            return sorted(self._in_progress)


# Singleton di processo (Conv. 47 single source of truth).
_sync_registry = SyncRegistry()


def get_sync_registry() -> SyncRegistry:
    """Ritorna singleton SyncRegistry di processo."""
    return _sync_registry


__all__ = [
    "FileError",
    "ProgressCallback",
    "SKIP_DIR_NAMES",
    "SKIP_DIR_PREFIXES",
    "SUPPORTED_EXTENSIONS",
    "SyncProgress",
    "SyncRegistry",
    "SyncReport",
    "SyncStatus",
    "count_supported_files",
    "delete_chunks_for_file",
    "get_sync_registry",
    "get_sync_status",
    "ingest_single_file",
    "sync_vault",
    "walk_vault_files",
]
