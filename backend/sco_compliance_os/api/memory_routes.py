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
