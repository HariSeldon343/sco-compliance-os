"""Router /api/wiki — lettura wiki SCO vault attivo.

Endpoints:
    GET /api/wiki/stats
    GET /api/wiki/sources       (alias /api/wiki/list?category=sources)
    GET /api/wiki/entities
    GET /api/wiki/concepts
    GET /api/wiki/synthesis
    GET /api/wiki/glossari
    GET /api/wiki/{category}/{slug}

Risoluzione vault attivo:
    1. Se query param vault_path è esplicito, usa quello (validazione containment).
    2. Altrimenti, legge vault registry (services/vault path JSON) e seleziona:
       - primo vault con is_sco_structure=true se presente,
       - altrimenti primo vault registrato,
       - altrimenti 404 con detail "Nessun vault attivo".

Conv. 41 enforcement: ogni richiesta logga vault_path risolto + categoria + filtri.
Conv. 47 enforcement: schema frontmatter NON duplicato (riusa services/vault/parser).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.wiki import (
    WIKI_CATEGORIES,
    WikiCategoryError,
    WikiNotFoundError,
    get_wiki_file,
    list_wiki_files,
    wiki_stats,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


# ----- Schemi response (Pydantic per OpenAPI docs) -----


class WikiSummaryItem(BaseModel):
    """Item summary nella lista wiki (no body completo)."""

    slug: str
    title: str
    status: str
    type: str
    entity_type: str | None
    entity_subtype: str | None
    ambito_canonico: str | None
    domini_applicabili: list[str]
    parent_entity: str
    tags: list[str]
    last_reviewed: str
    last_modified: str
    body_excerpt: str
    relationships_count: int
    applica_entity_count: int


class WikiListResponse(BaseModel):
    """Response per endpoint lista categoria wiki."""

    category: str
    total: int
    limit: int
    offset: int
    items: list[WikiSummaryItem]
    vault_path: str


class WikiStatsResponse(BaseModel):
    """Response per /api/wiki/stats."""

    vault_path: str
    wiki_dir_exists: bool
    counts: dict[str, int]
    total: int


# ----- Helper risoluzione vault attivo -----


def _load_registry(registry_path: Path) -> list[dict[str, Any]]:
    """Carica vault registry (riproduce logica vault_routes._load_registry)."""
    if not registry_path.exists():
        return []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("wiki_routes.registry_load_failed", error=str(exc))
        return []


def _resolve_active_vault(
    settings: Settings, vault_path_override: str | None
) -> Path:
    """Risolve path vault attivo.

    Pattern:
        1. Se vault_path_override esplicito, validalo (esiste + è dir) e usalo.
        2. Altrimenti scan registry: primo sco_structure, fallback primo registered.
        3. Nessun vault risolto -> HTTPException 404.

    Returns:
        Path: vault root attivo, già resolved + validato esistente.

    Raises:
        HTTPException 404: nessun vault attivo.
        HTTPException 400: vault_path_override non valido.
    """
    if vault_path_override:
        candidate = Path(vault_path_override).expanduser().resolve()
        if not candidate.exists() or not candidate.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"vault_path '{candidate}' non esiste o non è directory",
            )
        return candidate

    settings.ensure_data_dir()
    entries = _load_registry(settings.vault_registry_path)
    if not entries:
        raise HTTPException(
            status_code=404,
            detail=(
                "Nessun vault attivo. Registra un vault via "
                "POST /api/vault/add o passa ?vault_path=..."
            ),
        )

    # Preferenza sco_structure.
    sco_structured = [e for e in entries if e.get("is_sco_structure")]
    chosen = sco_structured[0] if sco_structured else entries[0]
    raw_path = str(chosen.get("path", ""))
    if not raw_path:
        raise HTTPException(
            status_code=500,
            detail="Vault registry corrotto (entry senza path)",
        )

    resolved = Path(raw_path).expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Vault attivo '{resolved}' non esiste più sul filesystem. "
                "Aggiorna il registry."
            ),
        )
    return resolved


def _list_category(
    category: str,
    settings: Settings,
    vault_path: str | None,
    entity_type: str | None,
    ambito_canonico: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> WikiListResponse:
    """Helper condiviso fra endpoint categoria-named."""
    vault_root = _resolve_active_vault(settings, vault_path)
    try:
        result = list_wiki_files(
            vault_root,
            category,
            entity_type=entity_type,
            ambito_canonico=ambito_canonico,
            status=status,
            limit=limit,
            offset=offset,
        )
    except WikiCategoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    logger.info(
        "wiki.list",
        category=category,
        vault=str(vault_root),
        total=result["total"],
        filters={
            "entity_type": entity_type,
            "ambito_canonico": ambito_canonico,
            "status": status,
        },
    )
    return WikiListResponse(**result, vault_path=str(vault_root))


# ----- Endpoint stats -----


@router.get("/stats", response_model=WikiStatsResponse)
async def get_stats(
    vault_path: str | None = Query(
        default=None, description="Override vault root path (assoluto)"
    ),
    settings: Settings = Depends(get_settings),
) -> WikiStatsResponse:
    """Conteggio file wiki per categoria nel vault attivo."""
    vault_root = _resolve_active_vault(settings, vault_path)
    stats = wiki_stats(vault_root)
    logger.info("wiki.stats", vault=str(vault_root), total=stats["total"])
    return WikiStatsResponse(**stats)


# ----- Endpoint lista per categoria (named) -----


@router.get("/sources", response_model=WikiListResponse)
async def list_sources(
    vault_path: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    ambito_canonico: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
) -> WikiListResponse:
    """Lista schede wiki/sources/ del vault attivo."""
    return _list_category(
        "sources",
        settings,
        vault_path,
        entity_type,
        ambito_canonico,
        status,
        limit,
        offset,
    )


@router.get("/entities", response_model=WikiListResponse)
async def list_entities(
    vault_path: str | None = Query(default=None),
    entity_type: str | None = Query(
        default=None,
        description=(
            "Filtra per entity_type (atto-normativo, standard-tecnico, "
            "linea-guida, autorita, metodologia, autore-prassi, "
            "soggetto-obbligato, scadenza)"
        ),
    ),
    ambito_canonico: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
) -> WikiListResponse:
    """Lista entity wiki/entities/ con filtri tipizzati Ondate 2-3."""
    return _list_category(
        "entities",
        settings,
        vault_path,
        entity_type,
        ambito_canonico,
        status,
        limit,
        offset,
    )


@router.get("/concepts", response_model=WikiListResponse)
async def list_concepts(
    vault_path: str | None = Query(default=None),
    ambito_canonico: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
) -> WikiListResponse:
    """Lista concepts wiki/concepts/ del vault attivo."""
    return _list_category(
        "concepts",
        settings,
        vault_path,
        None,
        ambito_canonico,
        status,
        limit,
        offset,
    )


@router.get("/synthesis", response_model=WikiListResponse)
async def list_synthesis(
    vault_path: str | None = Query(default=None),
    ambito_canonico: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
) -> WikiListResponse:
    """Lista synthesis wiki/synthesis/ del vault attivo."""
    return _list_category(
        "synthesis",
        settings,
        vault_path,
        None,
        ambito_canonico,
        status,
        limit,
        offset,
    )


@router.get("/glossari", response_model=WikiListResponse)
async def list_glossari(
    vault_path: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
) -> WikiListResponse:
    """Lista glossari wiki/glossari/ del vault attivo.

    Tipicamente la categoria contiene un solo _index.md (escluso) + eventuali
    glossari di dominio (es. csqa, sanitario, cyber, privacy, lavoro).
    """
    return _list_category(
        "glossari",
        settings,
        vault_path,
        None,
        None,
        None,
        limit,
        offset,
    )


# ----- Endpoint dettaglio singolo file -----


@router.get("/{category}/{slug}")
async def get_single(
    category: str,
    slug: str,
    vault_path: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Recupera singolo file wiki con frontmatter + body completo.

    category ∈ {sources, entities, concepts, synthesis, glossari}.
    Raises 422 se categoria fuori vocabolario, 404 se file non trovato.
    """
    if category not in WIKI_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Categoria '{category}' non valida. "
                f"Ammesse: {sorted(WIKI_CATEGORIES)}"
            ),
        )

    vault_root = _resolve_active_vault(settings, vault_path)
    try:
        doc = get_wiki_file(vault_root, category, slug)
    except WikiCategoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WikiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "wiki.get_single",
        category=category,
        slug=slug,
        vault=str(vault_root),
    )
    return {**doc, "vault_path": str(vault_root)}
