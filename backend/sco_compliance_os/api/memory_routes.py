"""Router /api/memory — memory tree + ingest + search.

TODO Sessione successiva: cablare engine memory tree (Karpathy LLM Wiki pattern
+ filesystem markdown + JSON index). Per ora stub con response tipizzate.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/memory", tags=["memory"])


# ----- Schemi Pydantic -----


class MemoryNode(BaseModel):
    """Nodo del memory tree (filesystem markdown + JSON metadata)."""

    id: str
    title: str
    path: str
    kind: str = Field(..., description="entity | concept | source | synthesis | glossary")
    snippet: str | None = None
    children: list[str] = Field(default_factory=list, description="ID figli (lazy).")


class MemoryTreeResponse(BaseModel):
    """Response per GET /tree."""

    root_ids: list[str]
    nodes: dict[str, MemoryNode] = Field(default_factory=dict)
    total_count: int = 0


class MemoryIngestRequest(BaseModel):
    """Richiesta ingest file/url nel memory tree."""

    source: str = Field(..., description="File path locale o URL HTTPS.")
    category: str | None = Field(
        default=None,
        description="Categoria di destinazione (normativa, audit, web-clip, ecc.).",
    )


class MemoryIngestResponse(BaseModel):
    """Response ingest."""

    accepted: bool
    source_card_path: str | None = None
    detected_kind: str | None = None
    message: str


class MemorySearchHit(BaseModel):
    """Match singolo nella ricerca."""

    node_id: str
    title: str
    path: str
    score: float = Field(..., ge=0.0, le=1.0)
    snippet: str | None = None


class MemorySearchResponse(BaseModel):
    """Response /search."""

    query: str
    hits: list[MemorySearchHit] = Field(default_factory=list)


# ----- Endpoint -----


@router.get("/tree", response_model=MemoryTreeResponse)
async def get_memory_tree(
    vault_id: str | None = Query(default=None, description="Filtra per vault id."),
    settings: Settings = Depends(get_settings),
) -> MemoryTreeResponse:
    """Ritorna struttura tree del memory chunks indicizzati.

    TODO: implementare scan di vault wiki/entities + wiki/concepts + wiki/sources.
    Per ora stub con tree vuoto + counter zero.
    """
    _ = settings  # silence unused
    logger.info("memory.tree.requested", vault_id=vault_id)
    return MemoryTreeResponse(root_ids=[], nodes={}, total_count=0)


@router.post("/ingest", response_model=MemoryIngestResponse, status_code=202)
async def ingest_to_memory(
    payload: MemoryIngestRequest,
) -> MemoryIngestResponse:
    """Indicizza file/url come scheda wiki/sources/ + aggiorna tree.

    TODO: integrare pipeline Conv. 43 SMART FILE INJECTION + schema standard B
    Ondata 4 per wiki/sources/<slug>.md (frontmatter ricco provenance metadata).
    """
    logger.info("memory.ingest.requested", source=payload.source, category=payload.category)
    return MemoryIngestResponse(
        accepted=True,
        source_card_path=None,
        detected_kind="unknown",
        message=f"STUB: ingest accettato per '{payload.source}', cablaggio pipeline pending.",
    )


@router.get("/search", response_model=MemorySearchResponse)
async def search_memory(
    q: str = Query(..., min_length=1, max_length=500, description="Query string."),
    top_k: int = Query(default=10, ge=1, le=50, description="Numero risultati."),
) -> MemorySearchResponse:
    """Similarity search top-K sul memory tree.

    TODO: implementare retrieval. Karpathy pattern: niente vector DB, scan
    filesystem markdown con keyword + ranking semplice fino a ~100 fonti.
    Per ora stub ritorna lista vuota.
    """
    logger.info("memory.search.requested", q=q, top_k=top_k)
    _ = top_k  # silence unused
    return MemorySearchResponse(query=q, hits=[])


@router.get("/stats")
async def get_memory_stats() -> dict[str, Any]:
    """Statistiche aggregate del memory tree (entità, concept, sources, synth)."""
    return {
        "entities_count": 0,
        "concepts_count": 0,
        "sources_count": 0,
        "synthesis_count": 0,
        "last_ingest_at": None,
        "stub": True,
    }


# ----- Wave 1 OpenHuman replica: tree + hotness endpoints -----


class TreeSummaryItem(BaseModel):
    """Item di response per GET /api/memory/tree (Wave 1 OpenHuman)."""

    id: str
    level: int
    source: str
    topic: str | None = None
    day: str | None = None
    content_preview: str = ""
    token_count: int = 0
    children_ids: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    created_at: str = ""


class HotnessItem(BaseModel):
    """Item di response per GET /api/memory/hotness/top."""

    chunk_id: str
    hotness: float
    last_accessed: str | None = None
    access_count: int = 0
    days_since_access: float | None = None


@router.get("/tree-summaries", response_model=list[TreeSummaryItem])
async def get_memory_tree_summaries(
    source: str | None = Query(default=None, description="Filtra per source identifier."),
    level: int | None = Query(default=None, ge=0, le=2, description="Filtra per level (0/1/2)."),
    topic: str | None = Query(default=None, description="Filtra per topic."),
    day: str | None = Query(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Filtra per data ISO YYYY-MM-DD.",
    ),
    limit: int = Query(default=50, ge=1, le=500, description="Max risultati."),
) -> list[TreeSummaryItem]:
    """Wave 1 OpenHuman: ritorna lista summaries L1/L2 con filtri arbitrari.

    Pattern: TreeBuilder.list_summaries_by_filter — single source of truth da
    tabella `summaries` (migration 0002).

    Endpoint distinto da `/tree` legacy per evitare breaking changes su contratto
    response (MemoryTreeResponse legacy vs list[TreeSummaryItem] Wave 1).
    """
    from sco_compliance_os.services.memory.tree_builder import TreeBuilder

    logger.info(
        "memory.tree_summaries.requested",
        source=source,
        level=level,
        topic=topic,
        day=day,
        limit=limit,
    )
    builder = TreeBuilder()
    nodes = await builder.list_summaries_by_filter(
        source=source,
        level=level,
        topic=topic,
        day=day,
        limit=limit,
    )
    return [
        TreeSummaryItem(
            id=n.id,
            level=n.level,
            source=n.source,
            topic=n.topic,
            day=n.day,
            content_preview=n.content_preview,
            token_count=n.token_count,
            children_ids=n.children_ids,
            parent_id=n.parent_id,
            created_at=n.created_at,
        )
        for n in nodes
    ]


@router.get("/hotness/top", response_model=list[HotnessItem])
async def get_top_hotness(
    n: int = Query(default=20, ge=1, le=200, description="Numero top chunks."),
) -> list[HotnessItem]:
    """Wave 1 OpenHuman: ritorna top-N chunks per hotness con decay applicato.

    Pattern: hotness.get_top_hot_chunks — decay 0.95/day sul tempo trascorso
    da last_accessed, re-rank in memoria post-decay.
    """
    from sco_compliance_os.services.memory.hotness import get_top_hot_chunks

    logger.info("memory.hotness.top.requested", n=n)
    snapshots = await get_top_hot_chunks(n=n)
    return [
        HotnessItem(
            chunk_id=s.chunk_id,
            hotness=s.hotness,
            last_accessed=s.last_accessed,
            access_count=s.access_count,
            days_since_access=s.days_since_access,
        )
        for s in snapshots
    ]
