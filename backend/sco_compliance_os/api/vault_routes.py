"""Router /api/vault — registrazione + ispezione + auto-sync vault Karpathy.

v0.6.0 DEV-VAULT-AUTOINGEST: estensione con endpoint sync + sync-status +
auto-ingest fire-and-forget al register + integrazione VaultWatcher.

Endpoints:
    GET    /api/vault/list                   -> lista vault registrati
    POST   /api/vault/add                    -> aggiungi vault (fire-and-forget sync + watcher)
    POST   /api/vault/inspect                -> ispeziona path senza registrare
    DELETE /api/vault/{id}                   -> rimuovi vault dal registry + stop watcher
    POST   /api/vault/{id}/sync              -> trigger re-sync sincrono (timeout 5min)
    GET    /api/vault/{id}/sync-status       -> stato sync corrente + counts DB
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.events import EventBus
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.skills.auto_trigger import EVENT_VAULT_REGISTERED
from sco_compliance_os.services.vault.autoingest import (
    SyncReport,
    delete_chunks_for_file,
    get_sync_registry,
    get_sync_status,
    ingest_single_file,
    sync_vault,
)
from sco_compliance_os.services.vault.watcher import (
    FileEvent,
    get_watcher_manager,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/vault", tags=["vault"])


# Timeout per sync sincrono on-demand (hard cap 5 minuti per evitare client hang).
_SYNC_TIMEOUT_SECONDS = 300.0


# ----- Schemi Pydantic -----


class VaultEntry(BaseModel):
    """Registro di un vault registrato."""

    id: str
    name: str
    path: str
    is_karpathy: bool = False
    md_files_count: int = 0
    has_claude_md: bool = False
    has_agents_md: bool = False
    has_wiki_dir: bool = False
    has_raw_dir: bool = False


class VaultAddRequest(BaseModel):
    """Richiesta aggiungi vault."""

    path: str = Field(..., description="Path assoluto del vault.")
    name: str | None = Field(default=None, max_length=200)


class VaultInspectRequest(BaseModel):
    """Richiesta ispeziona vault."""

    path: str = Field(..., description="Path assoluto da ispezionare.")


class VaultSyncRequest(BaseModel):
    """Richiesta sync vault on-demand."""

    force: bool = Field(
        default=False,
        description="Se True, bypassa dedup check e re-ingest tutto.",
    )


# ----- Helper persistenza registry -----


def _load_registry(registry_path: Path) -> list[dict[str, Any]]:
    """Carica vault registry da JSON (file user-scoped)."""
    if not registry_path.exists():
        return []
    try:
        return json.loads(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("vault_registry.load_failed", error=str(exc))
        return []


def _save_registry(registry_path: Path, entries: list[dict[str, Any]]) -> None:
    """Salva vault registry su JSON, atomico."""
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _inspect_vault(vault_path: Path) -> dict[str, Any]:
    """Ispeziona vault path. Ritorna metadata struttura."""
    if not vault_path.exists() or not vault_path.is_dir():
        raise HTTPException(
            status_code=400, detail=f"Path {vault_path} non esiste o non è directory"
        )

    has_claude_md = (vault_path / "CLAUDE.md").exists()
    has_agents_md = (vault_path / "AGENTS.md").exists()
    has_wiki_dir = (vault_path / "wiki").is_dir()
    has_raw_dir = (vault_path / "raw").is_dir()
    md_files_count = sum(1 for _ in vault_path.rglob("*.md"))

    is_karpathy = has_claude_md and has_wiki_dir and has_raw_dir

    return {
        "is_karpathy": is_karpathy,
        "md_files_count": md_files_count,
        "has_claude_md": has_claude_md,
        "has_agents_md": has_agents_md,
        "has_wiki_dir": has_wiki_dir,
        "has_raw_dir": has_raw_dir,
    }


def _find_vault_in_registry(
    settings: Settings, vault_id: str
) -> dict[str, Any]:
    """Trova vault per id nel registry. Solleva 404 se non trovato."""
    entries = _load_registry(settings.vault_registry_path)
    for entry in entries:
        if entry.get("id") == vault_id:
            return entry
    raise HTTPException(status_code=404, detail=f"Vault {vault_id} non trovato")


# ----- Background tasks -----


async def _background_sync_and_watch(
    vault_id: str,
    vault_path: Path,
) -> None:
    """Task fire-and-forget: sync vault + avvia watcher (chiamato post-add).

    Pattern Conv. 41 tracciatura: log dettagliato di ogni fase.
    Pattern Conv. 44 lesson 1: sync isolato, errori catturati senza
    propagare al request handler che ha gia restituito 201 al client.
    """
    registry = get_sync_registry()
    started = await registry.mark_start(vault_id)
    if not started:
        logger.info(
            "background_sync.skip_already_in_progress",
            vault_id=vault_id,
        )
    else:
        try:
            logger.info(
                "background_sync.start",
                vault_id=vault_id,
                path=str(vault_path),
            )
            report = await sync_vault(vault_path, vault_id, force=False)
            logger.info(
                "background_sync.complete",
                vault_id=vault_id,
                total_files_scanned=report.total_files_scanned,
                files_extracted=report.files_extracted,
                chunks_ingested=report.chunks_ingested,
                chunks_admitted=report.chunks_admitted,
                errors=len(report.errors),
                duration_sec=report.duration_sec,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "background_sync.error",
                vault_id=vault_id,
                error=str(exc),
            )
        finally:
            await registry.mark_done(vault_id)

    # Avvia watcher (idempotente). Watcher resta attivo anche se sync fallisce
    # (cosi' modifiche future vengono captate).
    try:
        manager = get_watcher_manager()
        watcher_started = await manager.start_watcher(vault_id, vault_path)
        logger.info(
            "background_watcher.start",
            vault_id=vault_id,
            watcher_started=watcher_started,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "background_watcher.start_failed",
            vault_id=vault_id,
            error=str(exc),
        )


# ----- Endpoint -----


@router.get("/list", response_model=list[VaultEntry])
async def list_vaults(
    settings: Settings = Depends(get_settings),
) -> list[VaultEntry]:
    """Lista vault registrati."""
    settings.ensure_data_dir()
    entries = _load_registry(settings.vault_registry_path)
    return [VaultEntry(**e) for e in entries]


@router.post("/add", response_model=VaultEntry, status_code=201)
async def add_vault(
    payload: VaultAddRequest,
    settings: Settings = Depends(get_settings),
) -> VaultEntry:
    """Aggiungi vault al registry + lancia auto-sync + watcher fire-and-forget.

    v0.6.0: dopo register, asyncio.create_task per sync_vault background +
    start VaultWatcher per modifiche live. Il client riceve 201 immediato
    senza aspettare il completamento del sync (consultabile via GET /sync-status).
    """
    settings.ensure_data_dir()
    vault_path = Path(payload.path).expanduser().resolve()
    meta = _inspect_vault(vault_path)

    entry = VaultEntry(
        id=str(uuid.uuid4()),
        name=payload.name or vault_path.name,
        path=str(vault_path),
        **meta,
    )
    entries = _load_registry(settings.vault_registry_path)
    # Dedup by path: se gia' presente, NON re-emettiamo evento auto-trigger
    # (per evitare loop os-setup ad ogni re-add dello stesso path).
    existing = [e for e in entries if e.get("path") == entry.path]
    already_registered = bool(existing)
    if already_registered:
        # Riusa l'ID esistente per non duplicare watcher / chunk tags
        entry.id = existing[0].get("id", entry.id)
    entries = [e for e in entries if e.get("path") != entry.path]
    entries.append(entry.model_dump())
    _save_registry(settings.vault_registry_path, entries)
    logger.info(
        "vault.added",
        path=entry.path,
        is_karpathy=entry.is_karpathy,
        already_registered=already_registered,
    )

    # Auto-trigger skill loader runtime: emit evento ``vault.registered``
    # come task background fire-and-forget. La response HTTP non attende che
    # le skill os-setup + os-ottimizzatore completino (possono richiedere
    # secondi / minuti via LLM call). Il frontend vede la nuova conversation
    # in sidebar Recents al successivo refresh /api/chat/conversations.
    if not already_registered:
        EventBus.instance().schedule_publish(
            EVENT_VAULT_REGISTERED,
            {
                "vault_id": entry.id,
                "vault_path": entry.path,
                "vault_name": entry.name,
                "is_karpathy": entry.is_karpathy,
            },
        )

    # Fire-and-forget: sync + watcher start in background (no await).
    # Risolve bug v0.5.0 "agente non legge i file": il vault viene
    # ingerito in mem_tree_chunks automaticamente al register.
    asyncio.create_task(
        _background_sync_and_watch(entry.id, vault_path),
        name=f"autoingest-{entry.id}",
    )

    return entry


@router.post("/inspect")
async def inspect_vault(payload: VaultInspectRequest) -> dict[str, Any]:
    """Ispeziona vault path senza registrarlo (preview struttura)."""
    vault_path = Path(payload.path).expanduser().resolve()
    meta = _inspect_vault(vault_path)
    meta["path"] = str(vault_path)
    return meta


@router.delete("/{vault_id}", status_code=204)
async def remove_vault(
    vault_id: str,
    settings: Settings = Depends(get_settings),
) -> None:
    """Rimuovi vault dal registry + stoppa watcher associato.

    NON elimina i file su disco né i chunks gia ingeriti in mem_tree_chunks
    (storia consultabile per audit). Per pulizia totale dei chunks, usare
    DELETE mem_tree_chunks WHERE tags_json LIKE '%vault:<id>%' manualmente.
    """
    settings.ensure_data_dir()
    entries = _load_registry(settings.vault_registry_path)
    new_entries = [e for e in entries if e.get("id") != vault_id]
    if len(new_entries) == len(entries):
        raise HTTPException(status_code=404, detail=f"Vault {vault_id} non trovato")
    _save_registry(settings.vault_registry_path, new_entries)

    # Stop watcher associato (idempotente)
    try:
        manager = get_watcher_manager()
        await manager.stop_watcher(vault_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("vault.remove.watcher_stop_failed", vault_id=vault_id, error=str(exc))

    logger.info("vault.removed", id=vault_id)


@router.post("/{vault_id}/sync")
async def sync_vault_endpoint(
    vault_id: str,
    payload: VaultSyncRequest | None = None,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Trigger re-sync sincrono per un vault registrato.

    Aspetta il completamento (timeout 5 min). Per sync background-only
    riutilizzare POST /api/vault/add (sync gia fire-and-forget).

    Conflict semantics: se un sync e' gia in progress per lo stesso vault_id,
    ritorna 409 con stato corrente invece di accodare un secondo sync.
    """
    settings.ensure_data_dir()
    entry = _find_vault_in_registry(settings, vault_id)
    vault_path = Path(entry["path"])
    force = bool(payload.force) if payload else False

    registry = get_sync_registry()
    if not await registry.mark_start(vault_id):
        raise HTTPException(
            status_code=409,
            detail=f"Sync gia in progress per vault {vault_id}",
        )

    try:
        report: SyncReport = await asyncio.wait_for(
            sync_vault(vault_path, vault_id, force=force),
            timeout=_SYNC_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=f"Sync timeout dopo {_SYNC_TIMEOUT_SECONDS}s",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("sync_vault.error", vault_id=vault_id, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Errore sync: {exc}") from exc
    finally:
        await registry.mark_done(vault_id)

    return report.to_dict()


@router.get("/{vault_id}/sync-status")
async def vault_sync_status(
    vault_id: str,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Ritorna stato sync corrente per il vault (in_progress + counts DB + watcher)."""
    settings.ensure_data_dir()
    entry = _find_vault_in_registry(settings, vault_id)
    vault_path = entry.get("path", "")

    registry = get_sync_registry()
    in_progress = await registry.is_in_progress(vault_id)

    status = await get_sync_status(
        vault_id=vault_id,
        vault_path=vault_path,
        in_progress=in_progress,
    )
    out = status.to_dict()

    # Aggiungi info watcher
    try:
        manager = get_watcher_manager()
        watchers = await manager.list_watchers()
        out["watcher_running"] = bool(watchers.get(vault_id, False))
    except Exception:  # noqa: BLE001
        out["watcher_running"] = False

    return out


# ----- Callback registrato dal lifespan per gestire eventi watcher -----


async def handle_file_event(event: FileEvent) -> None:
    """Handler eventi filesystem invocato da VaultWatcher post-debounce.

    Strategia:
        - created / modified -> ingest_single_file (delta re-ingest, dedup-aware).
        - deleted             -> delete_chunks_for_file (HARD DELETE).
        - moved               -> delete src + ingest dest.

    Wire in main.py lifespan:
        get_watcher_manager().set_event_callback(handle_file_event)
    """
    try:
        if event.event_type in ("created", "modified"):
            path = Path(event.src_path)
            if not path.exists() or not path.is_file():
                logger.debug(
                    "handle_file_event.skip_not_file",
                    path=event.src_path,
                )
                return
            extracted, counts, skipped = await ingest_single_file(
                path,
                vault_id=event.vault_id,
            )
            logger.info(
                "watcher.ingest_complete",
                vault_id=event.vault_id,
                event_type=event.event_type,
                path=event.src_path,
                skipped_dedup=skipped,
                ok=extracted.ok,
                upserted=counts.upserted,
                admitted=counts.admitted,
                dropped=counts.dropped,
            )

        elif event.event_type == "deleted":
            deleted = await delete_chunks_for_file(event.src_path)
            logger.info(
                "watcher.delete_complete",
                vault_id=event.vault_id,
                path=event.src_path,
                chunks_deleted=deleted,
            )

        elif event.event_type == "moved" and event.dest_path:
            # Delete chunks del src + ingest dest
            deleted = await delete_chunks_for_file(event.src_path)
            dest = Path(event.dest_path)
            if dest.exists() and dest.is_file():
                extracted, counts, _skipped = await ingest_single_file(
                    dest,
                    vault_id=event.vault_id,
                )
                logger.info(
                    "watcher.moved_complete",
                    vault_id=event.vault_id,
                    src=event.src_path,
                    dest=event.dest_path,
                    chunks_deleted=deleted,
                    upserted=counts.upserted,
                    ok=extracted.ok,
                )
            else:
                logger.info(
                    "watcher.moved_dest_missing",
                    vault_id=event.vault_id,
                    src=event.src_path,
                    dest=event.dest_path,
                    chunks_deleted=deleted,
                )

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "handle_file_event.error",
            vault_id=event.vault_id,
            event_type=event.event_type,
            path=event.src_path,
            error=str(exc),
        )
