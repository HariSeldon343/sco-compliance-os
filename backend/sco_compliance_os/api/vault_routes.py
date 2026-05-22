"""Router /api/vault — registrazione + ispezione vault Karpathy.

TODO: la classificazione "Karpathy compliant" richiede match della struttura
Second Brain (CLAUDE.md o AGENTS.md root + cartelle wiki/, raw/, log/ presenti).
Per ora ispezione lightweight + conteggio file .md.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/vault", tags=["vault"])


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
    registry_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


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
    """Aggiungi vault al registry."""
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
    # Dedup by path
    entries = [e for e in entries if e.get("path") != entry.path]
    entries.append(entry.model_dump())
    _save_registry(settings.vault_registry_path, entries)
    logger.info("vault.added", path=entry.path, is_karpathy=entry.is_karpathy)
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
    """Rimuovi vault dal registry (NON elimina i file su disco)."""
    settings.ensure_data_dir()
    entries = _load_registry(settings.vault_registry_path)
    new_entries = [e for e in entries if e.get("id") != vault_id]
    if len(new_entries) == len(entries):
        raise HTTPException(status_code=404, detail=f"Vault {vault_id} non trovato")
    _save_registry(settings.vault_registry_path, new_entries)
    logger.info("vault.removed", id=vault_id)
