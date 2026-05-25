"""Router /api/wiki — lettura wiki SCO vault attivo.

Endpoints:
    GET /api/wiki/stats
    GET /api/wiki/sources       (alias /api/wiki/list?category=sources)
    GET /api/wiki/entities
    GET /api/wiki/concepts
    GET /api/wiki/synthesis
    GET /api/wiki/glossari
    GET /api/wiki/{category}/{slug}

    POST /api/wiki/ingest/proposal   (v0.8.1 hook chat -> proposta ingest wiki)
    POST /api/wiki/ingest/confirm    (v0.8.1 confirm + creazione file)

Risoluzione vault attivo:
    1. Se query param vault_path è esplicito, usa quello (validazione containment).
    2. Altrimenti, legge vault registry (services/vault path JSON) e seleziona:
       - primo vault con is_sco_structure=true se presente,
       - altrimenti primo vault registrato,
       - altrimenti 404 con detail "Nessun vault attivo".

Conv. 41 enforcement: ogni richiesta logga vault_path risolto + categoria + filtri.
Conv. 47 enforcement: schema frontmatter NON duplicato (riusa services/vault/parser).
Conv. 48 enforcement: proposal id deterministico, single source of truth lato backend.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.chat.wiki_proposal import (
    WikiDestination,
    analyze_message_for_wiki_ingest,
)
from sco_compliance_os.services.wiki import (
    WIKI_CATEGORIES,
    WikiCategoryError,
    WikiNotFoundError,
    build_vault_graph,
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


# ----- Schemi Graph (vault force-directed) -----


class WikiGraphNode(BaseModel):
    """Nodo grafo: entity wiki, cliente business, scadenza, note generica, o placeholder.

    v0.12.1 Phase 2: aggiunte categorie 'note' (file .md generico con wikilink)
    e 'missing' (placeholder per target wikilink inesistente).
    """

    id: str
    label: str
    category: str  # entity | cliente | scadenza | note | missing
    entity_type: str
    entity_subtype: str
    ambito_canonico: str
    status: str  # active | draft | stub | deprecated | archived | missing
    path: str


class WikiGraphEdge(BaseModel):
    """Arco grafo: relationship entity-entity, applica_entity cliente-entity, o wikilink body.

    v0.12.1 Phase 2: aggiunta categoria 'wikilink' per menzioni wikilink nel
    body markdown di qualunque file (densità Obsidian Graph View).
    """

    source: str
    target: str
    type: str  # relationship_type | ruolo edge applica | 'menzione' (wikilink body)
    category: str  # relationship | applica | wikilink
    note: str


class WikiGraphStats(BaseModel):
    """Aggregati di copertura del grafo (per filtri UI).

    v0.12.1 Phase 2: aggiunti by_category (per categoria nodo) e
    by_edge_category (per categoria edge).
    """

    nodes_total: int
    edges_total: int
    by_entity_type: dict[str, int]
    by_ambito_canonico: dict[str, int]
    by_relationship_type: dict[str, int]
    by_category: dict[str, int] = Field(default_factory=dict)
    by_edge_category: dict[str, int] = Field(default_factory=dict)


class WikiGraphResponse(BaseModel):
    """Response per /api/wiki/graph."""

    nodes: list[WikiGraphNode]
    edges: list[WikiGraphEdge]
    stats: WikiGraphStats
    vault_path: str


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


# ----- Endpoint grafo (force-directed entity + clienti) -----


@router.get("/graph", response_model=WikiGraphResponse)
async def get_graph(
    vault_path: str | None = Query(
        default=None, description="Override vault root path (assoluto)"
    ),
    include_clienti: bool = Query(
        default=True,
        description="Includi nodi cliente da Business/*/clienti/*/_index.md",
    ),
    include_orphans: bool = Query(
        default=True,
        description="Crea placeholder per wikilink target inesistenti (status: missing)",
    ),
    include_body_wikilinks: bool = Query(
        default=True,
        description=(
            "v0.12.1 Phase 2: parsa wikilink [[...]] nel body markdown di tutti "
            "i file .md del vault (escluse cartelle .git/, node_modules/, "
            "_archivio*/, .obsidian/, .claude/). Esclude wikilink dentro code "
            "block. Default True per densità tipo Obsidian Graph View."
        ),
    ),
    include_notes: bool = Query(
        default=True,
        description=(
            "v0.12.1 Phase 2: emetti nodi categoria 'note' per file .md generici "
            "(non entity/cliente/scadenza) che hanno wikilink nel body. "
            "Richiede include_body_wikilinks=True. Default True."
        ),
    ),
    entity_type: str | None = Query(
        default=None,
        description=(
            "Filtra entity per entity_type (atto-normativo, standard-tecnico, "
            "linea-guida, autorita, metodologia, autore-prassi, "
            "soggetto-obbligato, scadenza)"
        ),
    ),
    ambito_canonico: str | None = Query(
        default=None,
        description="Filtra entity per ambito_canonico (17 valori, vedi CLAUDE.md INGEST)",
    ),
    settings: Settings = Depends(get_settings),
) -> WikiGraphResponse:
    """Costruisce grafo vault SCO per visualizzazione force-directed 2D.

    v0.12.0: nodi entity wiki + clienti business + scadenze, edges relationships
    (Dim. 4) + applica_entity (Dim. 5).

    v0.12.1 Phase 2: aggiunti wikilink body parsing per densità Obsidian. Walk
    completo vault per regex `[[...]]` con esclusione code block + frontmatter.
    Nodi 'note' emessi per file .md generici con wikilink, edges categoria
    'wikilink' con type='menzione'.

    Conv. 47 single source of truth: il grafo è derivato dai file vault, parsed
    dal parse_vault_file esistente. Nessun side effect, nessuna mutazione del
    vault.
    """
    vault_root = _resolve_active_vault(settings, vault_path)
    try:
        graph = build_vault_graph(
            vault_root,
            include_clienti=include_clienti,
            include_orphans=include_orphans,
            include_body_wikilinks=include_body_wikilinks,
            include_notes=include_notes,
            entity_type_filter=entity_type,
            ambito_canonico_filter=ambito_canonico,
        )
    except Exception as exc:
        logger.error(
            "wiki.graph.build_failed",
            vault=str(vault_root),
            error=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Errore costruzione grafo: {exc}",
        ) from exc

    logger.info(
        "wiki.graph",
        vault=str(vault_root),
        nodes=graph["stats"]["nodes_total"],
        edges=graph["stats"]["edges_total"],
        filters={
            "entity_type": entity_type,
            "ambito_canonico": ambito_canonico,
            "include_clienti": include_clienti,
            "include_orphans": include_orphans,
            "include_body_wikilinks": include_body_wikilinks,
            "include_notes": include_notes,
        },
    )
    return WikiGraphResponse(**graph)


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


# ============================================================================
# v0.8.1 INGEST PROPOSAL / CONFIRM — hook chat -> wiki
# ============================================================================
#
# Pattern Conv. 47: il backend è single source of truth della proposta.
# Frontend NON deve ricostruire la classificazione da capo: chiama
# /api/wiki/ingest/proposal con i dati del messaggio + allegati + search
# results e riceve indietro la struttura WikiIngestProposal pronta per il
# rendering nella WikiIngestProposalCard.
#
# Pattern Conv. 48: il proposal_id è deterministico (sha256 di
# conversation_id + message_id), così nello stesso messaggio la proposta è
# stabile a refresh e non si moltiplica.


# ----- Schemi Pydantic ingest -----


class AttachmentRef(BaseModel):
    """Attachment passato all'analyze (path + mime + content preview opzionali)."""

    path: str = Field(..., description="Path filesystem del file (per filename hints)")
    mime_type: str = Field(default="", description="MIME type opzionale")
    title: str | None = Field(default=None, description="Override titolo proposto")
    content_preview: str = Field(
        default="",
        description="Estratto testuale del file (per detection normative refs)",
    )


class SearchResultRef(BaseModel):
    """Single hit emesso da web_search tool."""

    url: str
    title: str
    snippet: str = ""


class WikiIngestProposalRequest(BaseModel):
    """Richiesta analisi proposta ingest wiki."""

    conversation_id: str
    message_id: str
    message_content: str = Field(
        default="",
        description="Content del messaggio assistant (per detection URL + normative refs)",
    )
    attachments: list[AttachmentRef] = Field(default_factory=list)
    search_results: list[SearchResultRef] = Field(default_factory=list)


class WikiIngestSlotOut(BaseModel):
    """Slot della proposta serializzato per response REST."""

    source_type: str
    title: str
    identifier: str
    summary: str
    suggested_destination: str
    suggested_slug: str
    suggested_frontmatter: dict[str, Any]
    confidence: float
    rationale: str


class WikiIngestProposalResponse(BaseModel):
    """Response /api/wiki/ingest/proposal."""

    proposal_id: str
    conversation_id: str
    message_id: str
    created_at: str
    slots: list[WikiIngestSlotOut]
    has_strong_candidate: bool


class WikiIngestConfirmRequest(BaseModel):
    """Richiesta conferma + creazione file wiki dal proposal."""

    proposal_id: str = Field(
        ..., description="Proposal ID precedentemente emesso da /ingest/proposal"
    )
    slot_index: int = Field(
        ..., ge=0, description="Indice slot nella proposta originale"
    )
    destination: str = Field(
        ...,
        description=(
            "Destinazione finale (sources|entities|concepts|synthesis|glossari|"
            "memory_tree). Puo' differire da suggested_destination se l'utente "
            "l'ha modificata nel widget."
        ),
    )
    slug: str = Field(..., min_length=1, max_length=120)
    frontmatter: dict[str, Any] = Field(
        default_factory=dict,
        description="Frontmatter finale che andra' nel file (sovrascrive draft)",
    )
    body_md: str = Field(default="", description="Body markdown del file")
    # Identificatore dello slot di origine (path file o url) per audit trail.
    source_identifier: str = Field(default="", description="Path o URL della fonte")
    source_type: str = Field(
        default="",
        description="attachment|url|search_result (per logging Conv. 41)",
    )


class WikiIngestConfirmResponse(BaseModel):
    """Esito conferma ingest: path file creato + flag overwrite."""

    written: bool
    file_path: str
    destination: str
    slug: str
    overwrite: bool


# ----- Helper: validazione destination + serializzazione frontmatter -----


_VALID_INGEST_DESTINATIONS: frozenset[str] = frozenset(WIKI_CATEGORIES) | {
    "memory_tree"
}


def _validate_destination(dest: str) -> WikiDestination:
    """Valida la destinazione contro vocabolario chiuso, raise 422 se invalida."""
    if dest not in _VALID_INGEST_DESTINATIONS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Destinazione '{dest}' non valida. "
                f"Ammesse: {sorted(_VALID_INGEST_DESTINATIONS)}"
            ),
        )
    return dest  # type: ignore[return-value]


def _serialize_frontmatter_yaml(fm: dict[str, Any]) -> str:
    """Serializza dict frontmatter come blocco YAML (style block, dash separators).

    Pattern Karpathy "schema is the product": preservare ordine chiavi non e'
    critico (PyYAML ricostruisce dict insertion-order in Python 3.7+).
    """
    if not fm:
        return ""
    try:
        body = yaml.safe_dump(
            fm,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ).strip()
    except yaml.YAMLError as exc:
        logger.warning("frontmatter serialize failed: %s", exc)
        body = "# frontmatter serialization error"
    return body


def _write_wiki_file(
    vault_root: Path,
    destination: WikiDestination,
    slug: str,
    frontmatter: dict[str, Any],
    body_md: str,
) -> tuple[Path, bool]:
    """Scrive file markdown nella categoria wiki indicata.

    destination='memory_tree' viene mappato a vault_root/raw/inbox/<slug>.md
    (fallback chunk generico, non e' una categoria wiki canonica). Pattern Conv.
    43 SMART FILE INJECTION: catch-all in raw/inbox/ quando non si riesce a
    classificare meglio.

    Returns:
        tupla (path_creato, overwrite_flag).

    Raises:
        ValueError: slug contiene caratteri non sicuri (path traversal).
    """
    # Validazione slug (re-usa stessa regex di get_wiki_file per coerenza).
    import re as _re

    if not _re.match(r"^[a-zA-Z0-9._\-]+$", slug):
        raise ValueError(
            f"Slug '{slug}' contiene caratteri non ammessi (solo a-z, 0-9, ., _, -)"
        )

    if destination == "memory_tree":
        target_dir = vault_root / "raw" / "inbox"
    else:
        target_dir = vault_root / "wiki" / destination

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{slug}.md"

    # Containment check: target_path deve restare dentro vault_root.
    try:
        resolved = target_path.resolve()
        vault_resolved = vault_root.resolve()
        resolved.relative_to(vault_resolved)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Slug/destinazione produce path fuori vault: {exc}",
        ) from exc

    overwrite = target_path.exists()
    fm_yaml = _serialize_frontmatter_yaml(frontmatter)
    if fm_yaml:
        full_content = f"---\n{fm_yaml}\n---\n\n{body_md.strip()}\n"
    else:
        full_content = body_md.strip() + "\n"
    target_path.write_text(full_content, encoding="utf-8")
    return target_path, overwrite


# ----- Endpoint: POST /api/wiki/ingest/proposal -----


@router.post(
    "/ingest/proposal",
    response_model=WikiIngestProposalResponse,
    summary="Analizza messaggio assistant e propone ingest wiki",
)
async def post_ingest_proposal(
    payload: WikiIngestProposalRequest,
) -> WikiIngestProposalResponse:
    """Hook post-message: classifica allegati + URL + search results nel messaggio.

    Pattern Conv. 41 tracciatura: ogni decisione e' loggata structured. Pattern
    Conv. 47 single source of truth: proposal_id deterministico (sha256 di
    conversation_id + message_id).

    Nessun side effect: l'analisi non crea file. Per creare il file servirà
    chiamare POST /api/wiki/ingest/confirm con il proposal_id + slot scelto.
    """
    # Converti Pydantic models -> dict per la funzione di servizio.
    attachments_dicts = [
        {
            "path": a.path,
            "mime_type": a.mime_type,
            "title": a.title,
            "content_preview": a.content_preview,
        }
        for a in payload.attachments
    ]
    search_dicts = [
        {"url": s.url, "title": s.title, "snippet": s.snippet}
        for s in payload.search_results
    ]
    proposal = analyze_message_for_wiki_ingest(
        conversation_id=payload.conversation_id,
        message_id=payload.message_id,
        message_content=payload.message_content,
        attachments=attachments_dicts,
        search_results=search_dicts,
    )
    logger.info(
        "wiki.ingest.proposal",
        proposal_id=proposal.proposal_id,
        conversation_id=payload.conversation_id,
        message_id=payload.message_id,
        slots=len(proposal.slots),
        has_strong=proposal.has_strong_candidate,
    )
    # Mapping a Pydantic response (dataclass -> dict -> Pydantic).
    return WikiIngestProposalResponse(
        proposal_id=proposal.proposal_id,
        conversation_id=proposal.conversation_id,
        message_id=proposal.message_id,
        created_at=proposal.created_at,
        slots=[WikiIngestSlotOut(**s.to_dict()) for s in proposal.slots],
        has_strong_candidate=proposal.has_strong_candidate,
    )


# ----- Endpoint: POST /api/wiki/ingest/confirm -----


@router.post(
    "/ingest/confirm",
    response_model=WikiIngestConfirmResponse,
    summary="Conferma proposta e crea file wiki",
)
async def post_ingest_confirm(
    payload: WikiIngestConfirmRequest,
    vault_path: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> WikiIngestConfirmResponse:
    """Crea fisicamente il file nella destinazione wiki scelta.

    L'utente puo' aver modificato destination / slug / frontmatter / body_md
    rispetto al suggerimento iniziale tramite il widget UI: noi accettiamo
    i valori finali senza ricontrollare la proposta originale (Conv. 47:
    single source of truth e' lo stato che l'utente conferma, non la cache
    della proposal).

    Idempotenza: se il file esiste già, sovrascrive (overwrite=True nel return).
    Audit trail: ogni write logga proposal_id + destination + slug + overwrite.
    """
    destination = _validate_destination(payload.destination)
    vault_root = _resolve_active_vault(settings, vault_path)
    try:
        target_path, overwrite = _write_wiki_file(
            vault_root=vault_root,
            destination=destination,
            slug=payload.slug,
            frontmatter=payload.frontmatter,
            body_md=payload.body_md,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        logger.error(
            "wiki.ingest.confirm.write_failed",
            proposal_id=payload.proposal_id,
            destination=destination,
            slug=payload.slug,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=f"Errore scrittura: {exc}") from exc

    logger.info(
        "wiki.ingest.confirm",
        proposal_id=payload.proposal_id,
        slot_index=payload.slot_index,
        destination=destination,
        slug=payload.slug,
        path=str(target_path),
        overwrite=overwrite,
        source_type=payload.source_type,
        source_identifier=payload.source_identifier,
        vault_path=str(vault_root),
    )
    return WikiIngestConfirmResponse(
        written=True,
        file_path=str(target_path),
        destination=destination,
        slug=payload.slug,
        overwrite=overwrite,
    )
