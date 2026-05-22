"""Orchestratore sync vault → index SQLite.

Espone:
    - sync_vault: full rescan + reindex. Da invocare a startup app e on-demand.
    - sync_single_file: re-index puntuale di un singolo .md (per watch mode).

Watch mode opzionale via `watchdog` lib (auto-sync su modifiche file). Se
watchdog non disponibile, watch_vault() solleva NotImplementedError esplicito
e l'utente esegue sync_vault() manualmente.

Pattern Conv. 41 PROTOCOLLO TRACCIATURA SESSIONE: ogni sync emette log
strutturato (vault_root, processed, indexed, durata_ms) usabile lato API
per dashboard.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .parser import parse_vault_file
from .scanner import index_document, init_schema, scan_vault

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SyncReport:
    """Esito dettagliato di un sync run."""

    vault_root: str
    db_path: str
    processed: int
    indexed: int
    duration_ms: int
    forced: bool


async def sync_vault(
    vault_root: Path,
    *,
    db_path: Optional[Path] = None,
    force: bool = False,
) -> SyncReport:
    """Sync completo vault → index SQLite.

    Args:
        vault_root: directory root del vault Karpathy del cliente.
        db_path: override path index DB (default ~/.sco-compliance-os/vault_index.db).
        force: se True, forza reindex completo anche di doc non modificati.
               Wave 1: il flag è documentato ma non implementa diff incrementale
               (sempre full rescan). Wave 2: diff via last_indexed + mtime.

    Returns:
        SyncReport con statistiche del run.
    """
    start = time.monotonic()
    await init_schema(db_path)
    processed, indexed = await scan_vault(vault_root, db_path=db_path)
    duration_ms = int((time.monotonic() - start) * 1000)

    report = SyncReport(
        vault_root=str(vault_root),
        db_path=str(db_path or "<default>"),
        processed=processed,
        indexed=indexed,
        duration_ms=duration_ms,
        forced=force,
    )
    logger.info(
        "sync_vault complete: %s processed=%d indexed=%d duration=%dms",
        vault_root,
        processed,
        indexed,
        duration_ms,
    )
    return report


async def sync_single_file(
    file_path: Path,
    db_path: Optional[Path] = None,
) -> bool:
    """Re-index puntuale di un singolo file .md.

    Usato dal watch mode quando rileva modifica filesystem. Ritorna True se
    il file è stato indicizzato, False se è stato saltato (tipo unknown).
    """
    if not file_path.exists() or file_path.suffix.lower() != ".md":
        logger.warning("sync_single_file: skip %s", file_path)
        return False

    doc = parse_vault_file(file_path)
    if doc.type == "unknown" and not doc.entity_type:
        return False

    await index_document(doc, db_path=db_path)
    logger.debug("sync_single_file: indicizzato %s", file_path)
    return True


async def watch_vault(
    vault_root: Path,
    db_path: Optional[Path] = None,
) -> None:
    """Watch mode opzionale via watchdog.

    Wave 1: stub che solleva NotImplementedError. Wave 2: integrazione completa
    con watchdog Observer + debouncing modifiche filesystem.

    Raises:
        NotImplementedError: sempre in wave 1 (use sync_vault manualmente).
    """
    raise NotImplementedError(
        "watch_vault è wave 2. In wave 1 invocare sync_vault() manualmente "
        "o su trigger esplicito (startup, comando user)."
    )
