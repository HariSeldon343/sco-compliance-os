"""Router /api/vault — registrazione + ispezione + auto-sync vault SCO.

v0.6.0 DEV-VAULT-AUTOINGEST: estensione con endpoint sync + sync-status +
auto-ingest fire-and-forget al register + integrazione VaultWatcher.

v1.0.0 DEV-OPTIMIZER-AUTO: estensione con endpoint complete-structure per
scaffolding incrementale di vault esistenti con struttura SCO INCOMPLETA.

v1.0.2 DEV-AUTO-SCAFFOLD: estensione con endpoint auto-organize per re-classify
file esistenti + popolamento entity seed/concepts/glossario in vault qualsiasi
(vuoto o pieno) SENZA chiedere conferma utente.

Endpoints:
    GET    /api/vault/list                          -> lista vault registrati
    POST   /api/vault/add                           -> aggiungi vault (fire-and-forget sync + watcher)
    POST   /api/vault/inspect                       -> ispeziona path senza registrare
    POST   /api/vault/scaffold                      -> scaffold completo da template (fresh vault)
    DELETE /api/vault/{id}                          -> rimuovi vault dal registry + stop watcher
    POST   /api/vault/{id}/sync                     -> trigger re-sync sincrono (timeout 5min)
    GET    /api/vault/{id}/sync-status              -> stato sync corrente + counts DB
    POST   /api/vault/{id}/complete-structure       -> crea cartelle/file SCO mancanti (incrementale, no overwrite)
    POST   /api/vault/{id}/auto-organize            -> auto-organize completa 5 fasi (mkdir + backup + re-classify + seed)
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
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
from sco_compliance_os.services.vault.scaffolder import (
    VALID_TEMPLATES,
    TemplateKind,
    auto_organize_vault,
    complete_missing_structure,
    inspect_missing_components,
    scaffold_vault,
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
    is_sco_structure: bool = False
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


class VaultScaffoldRequest(BaseModel):
    """Richiesta scaffold vault SCO (creazione + popolamento iniziale)."""

    path: str = Field(
        ...,
        description=(
            "Path assoluto della directory dove creare il vault. Se la directory "
            "non esiste viene creata. Se contiene gia un CLAUDE.md lo scaffold "
            "viene saltato (idempotenza)."
        ),
    )
    template: str = Field(
        default="vuoto",
        description=(
            "Template di partenza. Valori ammessi: vuoto, cyber, sanita, "
            "qualita, integrato."
        ),
    )
    vault_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nome leggibile del vault (usato in CLAUDE.md + README).",
    )


class VaultCompleteStructureRequest(BaseModel):
    """Richiesta completamento incrementale struttura SCO (vault esistente).

    DEV-OPTIMIZER-AUTO v1.0.0: usato dalla skill ``os-ottimizzatore`` (proposto
    in chat) o invocato direttamente dal frontend (button "Completa cartelle
    mancanti") per scaffolding incrementale di vault registrati con struttura
    SCO INCOMPLETA.
    """

    include_opt_in: bool = Field(
        default=False,
        description=(
            "Se True, crea anche cartelle/file opt-in (Contesto/, Business/, "
            "raw/, wiki/, CLAUDE.md). Se False (default), crea solo auto-create "
            "(Giornaliero/, Libreria/, Skill/, Progetti/, Team/, log/)."
        ),
    )


class VaultAutoOrganizeRequest(BaseModel):
    """Richiesta auto-organize vault SCO completa (5 fasi).

    DEV-AUTO-SCAFFOLD v1.0.2: endpoint per esecuzione manuale dell'auto-organize
    completa (gia eseguita automaticamente al register se vault non-SCO via
    auto_trigger). Riusato per re-run idempotente o per vault gia registrati
    pre-v1.0.2.

    Pipeline 5 fasi:
        1. Crea TUTTE le cartelle canoniche SCO + sotto-cartelle wiki/raw + log/
        2. Backup file in posizione di spostamento -> _archivio_pre_v1.0.2/
        3. Re-classify file .md esistenti (mapping non-SCO -> SCO o per frontmatter type:...)
        4. AGENTS.md + README.md + _index.md per cartelle nuove
        5. Popola entity seed (8 normative italiane comuni) + 5 concepts + glossario 35+ sigle

    Idempotente: chiamata ripetuta safe (skip su file/cartelle gia presenti).
    """

    auto_apply: bool = Field(
        default=True,
        description=(
            "Se True (default), applica realmente le modifiche al filesystem. "
            "Se False, ritorna lo stesso AutoOrganizeResult ma in dry-run "
            "(zero IO write). Utile per audit pre-conferma."
        ),
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

    is_sco_structure = has_claude_md and has_wiki_dir and has_raw_dir

    return {
        "is_sco_structure": is_sco_structure,
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
    request: Request,
    settings: Settings = Depends(get_settings),
) -> VaultEntry:
    """Aggiungi vault al registry + lancia auto-sync + watcher fire-and-forget.

    v0.6.0: dopo register, asyncio.create_task per sync_vault background +
    start VaultWatcher per modifiche live. Il client riceve 201 immediato
    senza aspettare il completamento del sync (consultabile via GET /sync-status).

    v0.6.1 Bug Antonio fix: emit ``vault.registered`` ANCHE su re-add path
    identico (rimosso skip silenzioso che bloccava il trigger della
    conversation system-generated "Configurazione iniziale del vault X").
    Il payload include ``is_new`` per dare al handler la facolta' di
    decidere se ri-eseguire le skill (default os-setup + os-ottimizzatore
    rieseguono sempre, idempotenti).
    """
    settings.ensure_data_dir()
    vault_path = Path(payload.path).expanduser().resolve()
    logger.info("vault.add.request", path=str(vault_path), name=payload.name)
    meta = _inspect_vault(vault_path)

    entry = VaultEntry(
        id=str(uuid.uuid4()),
        name=payload.name or vault_path.name,
        path=str(vault_path),
        **meta,
    )
    entries = _load_registry(settings.vault_registry_path)
    existing = [e for e in entries if e.get("path") == entry.path]
    already_registered = bool(existing)
    if already_registered:
        # Riusa l'ID esistente per non duplicare watcher / chunk tags
        entry.id = existing[0].get("id", entry.id)
    entries = [e for e in entries if e.get("path") != entry.path]
    entries.append(entry.model_dump())
    _save_registry(settings.vault_registry_path, entries)
    logger.info(
        "vault.add.success",
        path=entry.path,
        vault_id=entry.id,
        is_sco_structure=entry.is_sco_structure,
        registered=True,
        reason="re-add" if already_registered else "new",
    )

    # Auto-trigger skill loader runtime: emit evento ``vault.registered``
    # come task background fire-and-forget (TRACCIATO in app.state per
    # evitare GC prematura: Bug 3 root cause).
    # Pattern Conv. 47 single source of truth: emit SEMPRE (anche re-add),
    # handler decide se ri-eseguire skill via flag ``is_new``.
    background_tasks: set[asyncio.Task] = getattr(
        request.app.state, "background_tasks", set()
    )
    EventBus.instance().schedule_publish(
        EVENT_VAULT_REGISTERED,
        {
            "vault_id": entry.id,
            "vault_path": entry.path,
            "vault_name": entry.name,
            "is_sco_structure": entry.is_sco_structure,
            "is_new": not already_registered,
        },
        task_registry=background_tasks,
    )
    logger.info(
        "vault.add.event_published",
        event_type=EVENT_VAULT_REGISTERED,
        vault_id=entry.id,
        is_new=not already_registered,
    )

    # Fire-and-forget: sync + watcher start in background (tracciato).
    # Risolve bug v0.5.0 "agente non legge i file": il vault viene
    # ingerito in mem_tree_chunks automaticamente al register.
    sync_task = asyncio.create_task(
        _background_sync_and_watch(entry.id, vault_path),
        name=f"autoingest-{entry.id}",
    )
    background_tasks.add(sync_task)
    sync_task.add_done_callback(background_tasks.discard)

    return entry


@router.post("/inspect")
async def inspect_vault(payload: VaultInspectRequest) -> dict[str, Any]:
    """Ispeziona vault path senza registrarlo (preview struttura)."""
    vault_path = Path(payload.path).expanduser().resolve()
    meta = _inspect_vault(vault_path)
    meta["path"] = str(vault_path)
    return meta


@router.post("/scaffold", status_code=201)
async def scaffold_vault_endpoint(
    payload: VaultScaffoldRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Crea struttura vault SCO completa partendo da template + registra il vault.

    Pipeline:
        1. Validazione template (whitelist 5 valori) + vault_name non vuoto.
        2. Risoluzione path (creata se non esiste come directory).
        3. ``scaffold_vault()`` materializza struttura + entity seed.
        4. Registra il vault in registry JSON come fa ``add_vault()``.
        5. Emette evento ``vault.registered`` su EventBus (auto-trigger
           os-setup + os-ottimizzatore via skill auto_trigger).
        6. Lancia auto-sync + watcher fire-and-forget (idempotente con
           lo scaffold appena creato; ingestisce CLAUDE.md + README +
           entity seed in mem_tree_chunks).

    Idempotenza: se vault path contiene gia un CLAUDE.md, lo scaffold viene
    saltato (``scaffolded=false``, reason=``already_exists``) ma il vault
    viene comunque registrato. Il chiamante puo distinguere "scaffold nuovo"
    da "registrazione di esistente" dal campo ``scaffolded`` della response.

    Response:
        {
            "scaffolded": bool,
            "vault_id": str,
            "files_created": int,
            "directories_created": int,
            "entities_seeded": int,
            "template": str,
            "name": str,
            "path": str,
            "reason": "already_exists" (opzionale)
        }
    """
    settings.ensure_data_dir()

    # Validazione template lato API (oltre alla validazione interna allo scaffolder).
    if payload.template not in VALID_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Template '{payload.template}' non ammesso. "
                f"Valori: {', '.join(VALID_TEMPLATES)}"
            ),
        )

    vault_path = Path(payload.path).expanduser().resolve()
    logger.info(
        "vault.scaffold.request",
        path=str(vault_path),
        template=payload.template,
        vault_name=payload.vault_name,
    )

    # Se il path esiste deve essere una directory (mai un file).
    if vault_path.exists() and not vault_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path {vault_path} esiste ma non è una directory",
        )

    # Materializza struttura SCO sul filesystem.
    try:
        result = scaffold_vault(
            vault_path,
            template=payload.template,  # type: ignore[arg-type]
            vault_name=payload.vault_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        logger.error(
            "vault.scaffold.filesystem_error",
            path=str(vault_path),
            error=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Errore filesystem durante scaffold: {exc}",
        ) from exc

    # Post-scaffold: registra il vault come fa /api/vault/add (riusa la logica
    # ispezione meta + dedup by path + emit event + auto-sync fire-and-forget).
    meta = _inspect_vault(vault_path)
    entry = VaultEntry(
        id=str(uuid.uuid4()),
        name=payload.vault_name,
        path=str(vault_path),
        **meta,
    )
    entries = _load_registry(settings.vault_registry_path)
    existing = [e for e in entries if e.get("path") == entry.path]
    already_registered = bool(existing)
    if already_registered:
        entry.id = existing[0].get("id", entry.id)
    entries = [e for e in entries if e.get("path") != entry.path]
    entries.append(entry.model_dump())
    _save_registry(settings.vault_registry_path, entries)
    logger.info(
        "vault.scaffold.registered",
        vault_id=entry.id,
        path=entry.path,
        already_registered=already_registered,
        scaffolded=result.scaffolded,
        files_created=result.files_created,
        entities_seeded=result.entities_seeded,
    )

    # Emit evento auto-trigger skill (os-setup + os-ottimizzatore).
    # Conv. 47 single source of truth: nome campo univoco ``is_sco_structure``.
    background_tasks: set[asyncio.Task] = getattr(
        request.app.state, "background_tasks", set()
    )
    EventBus.instance().schedule_publish(
        EVENT_VAULT_REGISTERED,
        {
            "vault_id": entry.id,
            "vault_path": entry.path,
            "vault_name": entry.name,
            "is_sco_structure": entry.is_sco_structure,
            "is_new": not already_registered,
            "scaffolded": result.scaffolded,
            "template": payload.template,
        },
        task_registry=background_tasks,
    )

    # Auto-sync + watcher fire-and-forget (la struttura appena creata viene
    # ingerita in mem_tree_chunks per essere subito interrogabile dall'agente).
    sync_task = asyncio.create_task(
        _background_sync_and_watch(entry.id, vault_path),
        name=f"autoingest-scaffold-{entry.id}",
    )
    background_tasks.add(sync_task)
    sync_task.add_done_callback(background_tasks.discard)

    response: dict[str, Any] = {
        "scaffolded": result.scaffolded,
        "vault_id": entry.id,
        "files_created": result.files_created,
        "directories_created": result.directories_created,
        "entities_seeded": result.entities_seeded,
        "template": payload.template,
        "name": entry.name,
        "path": entry.path,
    }
    if result.reason is not None:
        response["reason"] = result.reason
    return response


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


@router.post("/{vault_id}/complete-structure", status_code=200)
async def complete_vault_structure(
    vault_id: str,
    payload: VaultCompleteStructureRequest | None = None,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Crea cartelle/file SCO mancanti per vault esistente (no overwrite).

    DEV-OPTIMIZER-AUTO v1.0.0: endpoint riusato dalla skill ``os-ottimizzatore``
    (quando vault.is_sco_structure=False) o da una azione esplicita del
    frontend per scaffolding incrementale.

    Differenza con ``POST /api/vault/scaffold``:
        - ``/scaffold``: vault NUOVO da template (vuoto/cyber/sanita/qualita/integrato).
            Salta se CLAUDE.md gia esistente.
        - ``/complete-structure``: vault ESISTENTE registrato, struttura SCO incompleta.
            NON salta su CLAUDE.md, crea solo le cartelle/file mancanti.

    Request body (opzionale):
        - include_opt_in: bool (default False). Se True, crea anche cartelle
          opt-in (Contesto/, Business/, raw/, wiki/, CLAUDE.md).

    Response:
        {
            "completed": bool,
            "files_created": list[str],
            "files_skipped": list[str],
            "missing_before": list[str],
            "errors": list[str]
        }
    """
    settings.ensure_data_dir()
    entry = _find_vault_in_registry(settings, vault_id)
    vault_path = Path(entry["path"])
    vault_name = entry.get("name", vault_path.name)
    include_opt_in = bool(payload.include_opt_in) if payload else False

    logger.info(
        "vault.complete_structure.request",
        vault_id=vault_id,
        path=str(vault_path),
        include_opt_in=include_opt_in,
    )

    # Snapshot pre-operazione per audit (Conv. 41 tracciatura).
    inspect_before = inspect_missing_components(vault_path)
    logger.info(
        "vault.complete_structure.inspect_before",
        vault_id=vault_id,
        is_sco_structure=inspect_before["is_sco_structure"],
        missing_folders=inspect_before["missing_folders"],
        missing_auto=inspect_before["missing_auto"],
        missing_opt_in=inspect_before["missing_opt_in"],
    )

    try:
        result = complete_missing_structure(
            vault_path,
            vault_name=vault_name,
            include_opt_in=include_opt_in,
        )
    except OSError as exc:
        logger.error(
            "vault.complete_structure.filesystem_error",
            vault_id=vault_id,
            path=str(vault_path),
            error=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Errore filesystem durante complete-structure: {exc}",
        ) from exc

    logger.info(
        "vault.complete_structure.completed",
        vault_id=vault_id,
        files_created_count=len(result.files_created),
        files_skipped_count=len(result.files_skipped),
        errors_count=len(result.errors),
    )

    # Aggiorna registry con nuovi flag struttura (la struttura SCO e' cambiata).
    # Riusa _inspect_vault per coerenza con i campi del VaultEntry schema
    # (has_wiki_dir, has_raw_dir, md_files_count) — single source of truth = filesystem
    # corrente, non snapshot in memoria.
    if result.completed:
        meta_after = _inspect_vault(vault_path)
        entries = _load_registry(settings.vault_registry_path)
        for e in entries:
            if e.get("id") == vault_id:
                e["is_sco_structure"] = meta_after["is_sco_structure"]
                e["has_claude_md"] = meta_after["has_claude_md"]
                e["has_wiki_dir"] = meta_after["has_wiki_dir"]
                e["has_raw_dir"] = meta_after["has_raw_dir"]
                e["has_agents_md"] = meta_after["has_agents_md"]
                e["md_files_count"] = meta_after["md_files_count"]
        _save_registry(settings.vault_registry_path, entries)
        logger.info(
            "vault.complete_structure.registry_updated",
            vault_id=vault_id,
            new_is_sco_structure=meta_after["is_sco_structure"],
            new_has_wiki_dir=meta_after["has_wiki_dir"],
            new_has_raw_dir=meta_after["has_raw_dir"],
        )

    return result.to_dict()


# ----- DEV-AUTO-SCAFFOLD v1.0.2 background task -----


async def _background_auto_organize(
    vault_id: str,
    vault_path: Path,
    vault_name: str,
    auto_apply: bool,
) -> dict[str, Any]:
    """Fire-and-forget task: auto-organize vault SCO completa.

    Pattern Conv. 41 tracciatura: log dettagliato.
    Pattern Conv. 44 lesson 1: errori catturati senza propagare al client.
    """
    try:
        logger.info(
            "background_auto_organize.start",
            vault_id=vault_id,
            path=str(vault_path),
            auto_apply=auto_apply,
        )
        result = auto_organize_vault(
            vault_path, vault_name=vault_name, auto_apply=auto_apply
        )
        logger.info(
            "background_auto_organize.complete",
            vault_id=vault_id,
            organized=result.organized,
            directories_created=len(result.directories_created),
            files_created=len(result.files_created),
            files_moved=len(result.files_moved),
            files_backed_up=len(result.files_backed_up),
            errors=len(result.errors),
        )
        return result.to_dict()
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "background_auto_organize.error",
            vault_id=vault_id,
            error=str(exc),
        )
        return {"organized": False, "errors": [str(exc)]}


@router.post("/{vault_id}/auto-organize", status_code=200)
async def auto_organize_vault_endpoint(
    vault_id: str,
    request: Request,
    payload: VaultAutoOrganizeRequest | None = None,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Auto-organize vault SCO completa (5 fasi pipeline, idempotente).

    DEV-AUTO-SCAFFOLD v1.0.2: endpoint REST per esecuzione manuale dell'auto-organize.
    Quando ``auto_apply=True`` (default), esegue le modifiche IN MODO SINCRONO
    sul vault (tipicamente pochi secondi per vault con <100 .md). Il client
    riceve l'esito completo. Per chiamata fire-and-forget asincrona (utile per
    vault molto grandi), passare ``background=true`` nel query param (non
    presente in MVP, carry-over v1.0.3).

    Per dry-run audit pre-conferma, passare ``auto_apply=False``: ritorna la
    stessa response simulata ma senza IO write.

    Pattern Conv. 41 tracciatura: log dettagliato di tutte le fasi nel response.
    Pattern Conv. 44 lesson 1 CircuitBreaker: errori per fase isolati, response
    contiene comunque counters parziali.
    Pattern Conv. 47 single source of truth: response coerente con
    AutoOrganizeResult.to_dict() del scaffolder.

    Response:
        {
            "organized": bool,
            "directories_created": list[str],
            "files_created": list[str],
            "files_moved": [{"src": str, "dest": str}, ...],
            "files_backed_up": list[str],
            "files_skipped": list[str],
            "errors": list[str],
            "vault_id": str,
            "vault_path": str
        }
    """
    settings.ensure_data_dir()
    entry = _find_vault_in_registry(settings, vault_id)
    vault_path = Path(entry["path"])
    vault_name = entry.get("name", vault_path.name)
    auto_apply = bool(payload.auto_apply) if payload else True

    logger.info(
        "vault.auto_organize.request",
        vault_id=vault_id,
        path=str(vault_path),
        auto_apply=auto_apply,
    )

    # Esecuzione sincrona (sub-pochi-secondi per vault tipici).
    try:
        result = auto_organize_vault(
            vault_path, vault_name=vault_name, auto_apply=auto_apply
        )
    except OSError as exc:
        logger.error(
            "vault.auto_organize.filesystem_error",
            vault_id=vault_id,
            path=str(vault_path),
            error=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Errore filesystem durante auto-organize: {exc}",
        ) from exc

    logger.info(
        "vault.auto_organize.completed",
        vault_id=vault_id,
        organized=result.organized,
        files_created_count=len(result.files_created),
        files_moved_count=len(result.files_moved),
        files_backed_up_count=len(result.files_backed_up),
        errors_count=len(result.errors),
    )

    # Aggiorna registry con flag struttura post-organize (la struttura SCO e'
    # cambiata se auto_apply=True, e' invariata se dry-run).
    if auto_apply and result.organized:
        meta_after = _inspect_vault(vault_path)
        entries = _load_registry(settings.vault_registry_path)
        for e in entries:
            if e.get("id") == vault_id:
                e["is_sco_structure"] = meta_after["is_sco_structure"]
                e["has_claude_md"] = meta_after["has_claude_md"]
                e["has_wiki_dir"] = meta_after["has_wiki_dir"]
                e["has_raw_dir"] = meta_after["has_raw_dir"]
                e["has_agents_md"] = meta_after["has_agents_md"]
                e["md_files_count"] = meta_after["md_files_count"]
        _save_registry(settings.vault_registry_path, entries)
        logger.info(
            "vault.auto_organize.registry_updated",
            vault_id=vault_id,
            new_is_sco_structure=meta_after["is_sco_structure"],
        )

    # Lancia re-sync fire-and-forget post-organize cosi' i nuovi file
    # (entity seed + concepts + glossario) entrano in mem_tree_chunks
    # per essere subito interrogabili dall'agente.
    if auto_apply and result.organized:
        background_tasks: set[asyncio.Task] = getattr(
            request.app.state, "background_tasks", set()
        )
        sync_task = asyncio.create_task(
            _background_sync_and_watch(vault_id, vault_path),
            name=f"resync-after-auto-organize-{vault_id}",
        )
        background_tasks.add(sync_task)
        sync_task.add_done_callback(background_tasks.discard)

    response = result.to_dict()
    response["vault_id"] = vault_id
    response["vault_path"] = str(vault_path)
    return response


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
