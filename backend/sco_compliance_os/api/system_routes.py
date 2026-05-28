"""Router /api/system — stato dati locali + reset completo (Feature 1 v0.15.0).

Due endpoint:

- GET /api/system/data-status: rileva se ci sono dati utente persistiti in
  data_dir (~/.sco-compliance-os/) e ritorna conteggi sintetici. Usato dal
  frontend per decidere se mostrare il dialog "Mantieni / Riparti da zero" al
  primo avvio dopo install/aggiornamento.
- POST /api/system/reset-data: cancella tutto il contenuto di data_dir e lo
  ricrea vuoto (wipe). Operazione distruttiva, protetta da token di conferma
  "RESET" nel body. Idempotente.

Sicurezza: il reset chiude il singleton Store (dispose_store) prima di
cancellare compliance_os.db, altrimenti su Windows il file SQLite resta
lockato. Rimozione resiliente con retry su PermissionError.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.core.store import dispose_store

logger = get_logger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

# Nome file del log attività Auto-Fetch dentro data_dir (default config.py).
_AUTOFETCH_LOG_FILENAME = "autofetch_activity.jsonl"


class DataStatusResponse(BaseModel):
    """Stato sintetico dei dati utente locali."""

    has_data: bool
    conversations: int
    vaults: int
    db_size_bytes: int
    onboarding_done: bool


class ResetDataRequest(BaseModel):
    """Richiesta di reset distruttivo. confirm deve valere esattamente 'RESET'."""

    confirm: str = Field(..., max_length=32, description="Deve valere la stringa 'RESET'.")


class ResetDataResponse(BaseModel):
    """Esito del reset: ok + lista nomi file/cartelle cancellati."""

    ok: bool
    deleted: list[str]


async def _count_conversations(db_path: Path) -> int:
    """Conta le conversation nel DB senza toccare il singleton Store.

    Usa un engine usa-e-getta sul path esatto (read-only COUNT, sicuro anche se
    il singleton ha lo stesso file aperto). Se il DB non esiste o la tabella non
    c'e' ancora, ritorna 0 in modo difensivo.
    """
    if not db_path.exists():
        return 0
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM conversations"))
            row = result.scalar_one_or_none()
            return int(row or 0)
    except Exception as exc:  # DB nuovo/corrotto o tabella assente: difensivo
        logger.warning("system.count_conversations_failed", error=str(exc))
        return 0
    finally:
        await engine.dispose()


def _count_vaults(vault_registry_path: Path) -> int:
    """Conta i vault registrati leggendo vault_registry.json. Difensivo."""
    if not vault_registry_path.exists():
        return 0
    try:
        data = json.loads(vault_registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("system.count_vaults_failed", error=str(exc))
        return 0
    if isinstance(data, dict) and isinstance(data.get("vaults"), list):
        return len(data["vaults"])
    if isinstance(data, list):
        return len(data)
    return 0


def _onboarding_done(onboarding_state_path: Path) -> bool:
    """True se onboarding.json esiste ed e' marcato completato. Difensivo."""
    if not onboarding_state_path.exists():
        return False
    try:
        data = json.loads(onboarding_state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return bool(isinstance(data, dict) and data.get("completed"))


@router.get("/data-status", response_model=DataStatusResponse)
async def get_data_status(
    settings: Settings = Depends(get_settings),
) -> DataStatusResponse:
    """Ritorna lo stato dei dati locali (per la scelta wipe/mantieni)."""
    db_path = settings.memory_tree_db_path
    vault_registry_path = settings.vault_registry_path
    onboarding_path = settings.onboarding_state_path
    autofetch_path = settings.data_dir / _AUTOFETCH_LOG_FILENAME

    db_size = db_path.stat().st_size if db_path.exists() else 0
    conversations = await _count_conversations(db_path)
    vaults = _count_vaults(vault_registry_path)
    onboarding = _onboarding_done(onboarding_path)
    # has_data significa "dati che vale la pena chiedere se mantenere": NON la
    # semplice esistenza di un compliance_os.db vuoto (creato a ogni primo avvio),
    # ma conversazioni reali, vault registrati, onboarding completato o log
    # Auto-Fetch. Cosi' il dialog wipe/mantieni NON compare su un install pulito.
    has_data = conversations > 0 or vaults > 0 or onboarding or autofetch_path.exists()
    return DataStatusResponse(
        has_data=has_data,
        conversations=conversations,
        vaults=vaults,
        db_size_bytes=db_size,
        onboarding_done=onboarding,
    )


async def _resilient_remove(entry: Path, attempts: int = 5, delay: float = 0.1) -> None:
    """Cancella un file o una cartella con retry su PermissionError (lock Windows).

    Backoff lineare 0.1..0.5s (totale ~1.5s) per dare tempo al rilascio del lock
    SQLite. FileNotFoundError trattato come gia' cancellato (idempotenza).
    """
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink(missing_ok=True)
            return
        except PermissionError as exc:  # lock Windows (SQLite)
            last_exc = exc
            await asyncio.sleep(delay * (i + 1))
        except FileNotFoundError:
            return
    if last_exc is not None:
        raise last_exc


@router.post("/reset-data", response_model=ResetDataResponse)
async def reset_data(
    payload: ResetDataRequest,
    settings: Settings = Depends(get_settings),
) -> ResetDataResponse:
    """Cancella tutto il contenuto di data_dir e lo ricrea vuoto (wipe).

    Protetto da token: confirm deve valere esattamente 'RESET', altrimenti 400.
    """
    if payload.confirm != "RESET":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il campo confirm deve valere esattamente la stringa 'RESET'.",
        )

    # Rilascia il lock SQLite chiudendo il singleton Store (Windows).
    try:
        await dispose_store()
    except Exception as exc:  # best-effort, non bloccare il reset
        logger.warning("system.dispose_store_failed", error=str(exc))

    data_dir = settings.data_dir
    deleted: list[str] = []
    if data_dir.exists():
        for entry in list(data_dir.iterdir()):
            try:
                await _resilient_remove(entry)
                deleted.append(entry.name)
            except Exception as exc:
                logger.error("system.reset_delete_failed", entry=str(entry), error=str(exc))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Impossibile cancellare {entry.name}: {exc}",
                ) from exc

    settings.ensure_data_dir()
    logger.info("system.data_reset_completed", deleted_count=len(deleted))
    return ResetDataResponse(ok=True, deleted=deleted)
