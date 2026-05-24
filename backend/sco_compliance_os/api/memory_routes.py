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

    Subagent DEV-MEMORY-TREE 24/05/2026: ora ritorna dati reali da mem_tree_chunks
    (bucket-seal Fase 1+2+3) come MemoryNode roots. Ciascun chunk admitted appare
    come nodo root tree. Filtraggio per status='admitted' per coerenza UX.

    Per dati dettagliati con filtri completi usare GET /tree/chunks.
    Per stats aggregati usare GET /tree/stats.
    """
    _ = settings  # silence unused
    _ = vault_id  # vault filter futura, ora cumulativo
    from sco_compliance_os.services.memory.tree_store import (
        count_by_status,
        list_chunks,
    )

    logger.info("memory.tree.requested", vault_id=vault_id)

    # Ritorna top-50 chunk admitted ordinati per timestamp DESC
    chunks = await list_chunks(status="admitted", limit=50)
    counts = await count_by_status()
    total = counts.get("total", 0)

    nodes: dict[str, MemoryNode] = {}
    root_ids: list[str] = []
    for c in chunks:
        node = MemoryNode(
            id=c.id,
            title=f"[{c.source_kind}] {c.source_id}",
            path=f"mem_tree_chunks/{c.id}",
            kind=c.source_kind,
            snippet=c.content[:200].strip().replace("\n", " "),
            children=[],
        )
        nodes[c.id] = node
        root_ids.append(c.id)

    return MemoryTreeResponse(
        root_ids=root_ids,
        nodes=nodes,
        total_count=total,
    )


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
    # v0.7.3: graceful empty su tabella inesistente (Wave 1 legacy table 'summaries'
    # mai migrata in v0.6.0+ dove la Fase 4 ha introdotto mem_tree_summaries).
    # Senza questo handler il WikiView frontend riceve HTTP 500 e mostra
    # "Backend non raggiungibile" anche se il backend e' online (Antonio segnalato
    # bug v0.7.2). Carry-over Sessione 8+: refactor WikiView per leggere da
    # mem_tree_summaries (Fase 4) + endpoint /api/wiki/* (ALPHA v0.4.0).
    try:
        builder = TreeBuilder()
        nodes = await builder.list_summaries_by_filter(
            source=source,
            level=level,
            topic=topic,
            day=day,
            limit=limit,
        )
    except Exception as exc:  # noqa: BLE001 - graceful degradation tabella mancante
        logger.warning(
            "memory.tree_summaries.graceful_empty",
            error=str(exc),
            reason="Wave 1 'summaries' table assente, restituisco lista vuota per compat WikiView",
        )
        return []
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
    # v0.7.3: graceful empty su tabella inesistente (Wave 1 legacy 'scores').
    # Stesso pattern di /tree-summaries: tabella scores mai migrata in v0.6.0+.
    try:
        snapshots = await get_top_hot_chunks(n=n)
    except Exception as exc:  # noqa: BLE001 - graceful degradation tabella mancante
        logger.warning(
            "memory.hotness.top.graceful_empty",
            error=str(exc),
            reason="Wave 1 'scores' table assente, lista vuota per WikiView compat",
        )
        return []
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


# ----- Memory Tree bucket-seal 4 fasi (subagent DEV-MEMORY-TREE 24/05/2026) -----


class TreeIngestInputItem(BaseModel):
    """Singolo input per POST /tree/ingest."""

    source_kind: str = Field(
        ...,
        description="Vocabolario chiuso: chat | email | document | vault_file | note.",
    )
    source_id: str = Field(..., min_length=1, description="Identificatore opaco sorgente.")
    content: str = Field(..., min_length=1, description="Testo raw da ingerire.")
    owner: str = Field(default="local", description="Identificatore utente (default 'local').")
    timestamp_ms: int | None = Field(
        default=None,
        description="Timestamp evento POSIX ms UTC (default now).",
    )
    tags: list[str] = Field(default_factory=list, description="Tag arbitrari.")


class TreeIngestRequest(BaseModel):
    """Request body per POST /tree/ingest."""

    texts: list[TreeIngestInputItem] = Field(..., min_length=1, max_length=100)
    consult_llm_on_borderline: bool = Field(
        default=False,
        description="Se True consulta LLM extractor stub per chunk borderline.",
    )
    max_tokens: int = Field(
        default=3000,
        ge=100,
        le=8000,
        description="Budget massimo per chunk (default 3000).",
    )


class TreeIngestResponse(BaseModel):
    """Response per POST /tree/ingest — IngestCounts."""

    admitted: int
    dropped: int
    pending_extraction: int
    total: int
    upserted: int


class TreeChunkItem(BaseModel):
    """Item rappresentativo di un TreeChunk per GET /tree/chunks."""

    id: str
    source_kind: str
    source_id: str
    owner: str
    timestamp_ms: int
    tags: list[str]
    content_preview: str
    token_count: int
    seq_in_source: int
    created_at_ms: int
    status: str


class TreeStatsResponse(BaseModel):
    """Response per GET /tree/stats — count_by_status + count_by_source_kind."""

    counts_by_status: dict[str, int]
    counts_by_source_kind: dict[str, int]
    total: int


@router.post("/tree/ingest", response_model=TreeIngestResponse, status_code=202)
async def post_tree_ingest(payload: TreeIngestRequest) -> TreeIngestResponse:
    """Ingestion bucket-seal: canonicalize + chunk + admission gate + persist.

    Pipeline 4 fasi (Fase 1+2+3 implementate, Fase 4 sealing carry-over Sessione 7+):
        1. Canonicalize testo -> markdown canonico (whitespace normalize).
        2. Chunk_text -> stable deterministic IDs, max_tokens default 3000.
        3. Admission gate -> cheap signals + decisione admit/drop/borderline.
        4. (carry-over) Sealing summarization tree_source / tree_topic / tree_global.

    Args:
        payload: lista IngestInput + flag LLM consult + max_tokens.

    Returns:
        IngestCounts con breakdown admitted/dropped/pending + upserted.
    """
    from sco_compliance_os.services.memory.tree_ingester import (
        IngestInput,
        ingest_inputs,
    )

    inputs = [
        IngestInput(
            source_kind=item.source_kind,
            source_id=item.source_id,
            content=item.content,
            owner=item.owner,
            timestamp_ms=item.timestamp_ms,
            tags=item.tags,
        )
        for item in payload.texts
    ]

    logger.info(
        "memory.tree.ingest.requested",
        input_count=len(inputs),
        consult_llm=payload.consult_llm_on_borderline,
        max_tokens=payload.max_tokens,
    )

    counts = await ingest_inputs(
        inputs,
        consult_llm_on_borderline=payload.consult_llm_on_borderline,
        max_tokens=payload.max_tokens,
    )

    return TreeIngestResponse(
        admitted=counts.admitted,
        dropped=counts.dropped,
        pending_extraction=counts.pending_extraction,
        total=counts.total,
        upserted=counts.upserted,
    )


@router.get("/tree/chunks", response_model=list[TreeChunkItem])
async def get_tree_chunks(
    source_kind: str | None = Query(
        default=None,
        description="Filtra per source_kind (chat | email | document | vault_file | note).",
    ),
    status: str | None = Query(
        default=None,
        description="Filtra per status (pending_extraction | admitted | buffered | sealed | dropped).",
    ),
    source_id: str | None = Query(default=None, description="Filtra per source_id."),
    owner: str | None = Query(default=None, description="Filtra per owner."),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[TreeChunkItem]:
    """Lista chunks del Memory Tree bucket-seal con filtri + paginazione.

    Ordine: created_at_ms DESC (chunk piu' recenti per primi).
    """
    from sco_compliance_os.services.memory.tree_store import list_chunks

    logger.info(
        "memory.tree.chunks.requested",
        source_kind=source_kind,
        status=status,
        source_id=source_id,
        owner=owner,
        limit=limit,
        offset=offset,
    )

    chunks = await list_chunks(
        status=status,
        source_kind=source_kind,
        source_id=source_id,
        owner=owner,
        limit=limit,
        offset=offset,
    )

    return [
        TreeChunkItem(
            id=c.id,
            source_kind=c.source_kind,
            source_id=c.source_id,
            owner=c.owner,
            timestamp_ms=c.timestamp_ms,
            tags=c.tags,
            content_preview=c.content[:300].strip().replace("\n", " "),
            token_count=c.token_count,
            seq_in_source=c.seq_in_source,
            created_at_ms=c.created_at_ms,
            status=c.status,
        )
        for c in chunks
    ]


@router.get("/tree/stats", response_model=TreeStatsResponse)
async def get_tree_stats() -> TreeStatsResponse:
    """Statistiche aggregate Memory Tree bucket-seal (count by status + source_kind).

    Cruscotto Conv. 41 tracciatura: utile per smoke + verifica pipeline.
    """
    from sco_compliance_os.services.memory.tree_store import (
        count_by_source_kind,
        count_by_status,
    )

    by_status = await count_by_status()
    by_kind = await count_by_source_kind()
    total = by_status.pop("total", 0) if "total" in by_status else 0

    logger.info(
        "memory.tree.stats.requested",
        total=total,
        statuses=len(by_status),
        source_kinds=len(by_kind),
    )

    return TreeStatsResponse(
        counts_by_status=by_status,
        counts_by_source_kind=by_kind,
        total=total,
    )


# ----- Memory Tree bucket-seal Fase 4: summaries L1/L2/L3 + BM25 query (v0.6.0) -----


class TreeSummaryItemV2(BaseModel):
    """Item summary L1/L2/L3 per GET /tree/summaries (v0.6.0)."""

    id: str
    tree_kind: str = Field(..., description="source | topic | global")
    tree_id: str
    level: int = Field(..., ge=1, le=3)
    content_summary: str
    content_preview: str = Field(default="", description="Preview 300 char.")
    parent_summary_id: str | None = None
    children_chunk_ids: list[str] = Field(default_factory=list)
    children_summary_ids: list[str] = Field(default_factory=list)
    token_count: int = 0
    source_kind_hint: str | None = None
    owner: str = "local"
    created_at_ms: int = 0
    sealed_at_ms: int | None = None
    status: str = "sealed"


class TreeSealRequest(BaseModel):
    """Request body per POST /tree/seal."""

    tree_kind: str = Field(
        ..., description="Vocabolario chiuso: source | topic | global."
    )
    tree_id: str = Field(
        ..., description="source_id (per source) o 'global'.", min_length=1
    )
    force: bool = Field(
        default=False,
        description="Se True, sigilla anche sotto-threshold per smoke test / on-demand.",
    )


class TreeSealResponse(BaseModel):
    """Response per POST /tree/seal."""

    tree_kind: str
    tree_id: str
    force: bool
    summaries_l1_created: int = 0
    summaries_l2_created: int = 0
    summaries_l3_created: int = 0


class TreeRelevantQuery(BaseModel):
    """Item summary relevant per GET /tree/summaries/relevant."""

    id: str
    tree_kind: str
    tree_id: str
    level: int
    content_preview: str = ""
    token_count: int = 0
    sealed_at_ms: int | None = None


@router.get("/tree/summaries", response_model=list[TreeSummaryItemV2])
async def get_tree_summaries_v2(
    tree_kind: str | None = Query(
        default=None,
        description="Filtra per tree_kind: source | topic | global.",
    ),
    tree_id: str | None = Query(
        default=None,
        description="Filtra per tree_id (source_id o 'global').",
    ),
    level: int | None = Query(
        default=None,
        ge=1,
        le=3,
        description="Filtra per level (1 / 2 / 3).",
    ),
    owner: str | None = Query(default="local", description="Filtra per owner."),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[TreeSummaryItemV2]:
    """Lista summaries L1/L2/L3 con filtri + paginazione (Fase 4 v0.6.0).

    Endpoint distinto da `/tree-summaries` legacy Wave 1 (su tabella
    `summaries` diversa) per evitare breaking change.

    Ordine: sealed_at_ms DESC, created_at_ms DESC.
    """
    from sco_compliance_os.services.memory.tree_summaries import list_summaries

    logger.info(
        "memory.tree.summaries_v2.requested",
        tree_kind=tree_kind,
        tree_id=tree_id,
        level=level,
        owner=owner,
        limit=limit,
        offset=offset,
    )
    summaries = await list_summaries(
        tree_kind=tree_kind,
        tree_id=tree_id,
        level=level,
        owner=owner,
        limit=limit,
        offset=offset,
    )
    return [
        TreeSummaryItemV2(
            id=s.id,
            tree_kind=s.tree_kind,
            tree_id=s.tree_id,
            level=s.level,
            content_summary=s.content_summary,
            content_preview=s.content_summary[:300].strip().replace("\n", " "),
            parent_summary_id=s.parent_summary_id,
            children_chunk_ids=s.children_chunk_ids,
            children_summary_ids=s.children_summary_ids,
            token_count=s.token_count,
            source_kind_hint=s.source_kind_hint,
            owner=s.owner,
            created_at_ms=s.created_at_ms,
            sealed_at_ms=s.sealed_at_ms,
            status=s.status,
        )
        for s in summaries
    ]


@router.post("/tree/seal", response_model=TreeSealResponse, status_code=202)
async def post_tree_seal(payload: TreeSealRequest) -> TreeSealResponse:
    """Trigger cascade_seal sync per tree_kind/tree_id (Fase 4 sealing v0.6.0).

    Pipeline:
        1. L0 (chunks admitted) -> seal L1 se total tokens >= threshold (32k).
        2. L1 pending -> cascade L2 se total tokens >= threshold (16k).
        3. L2 pending -> cascade L3 se total tokens >= threshold (8k).

    `force=True` bypassa threshold (utile per smoke test + on-demand sealing).
    """
    from sco_compliance_os.services.memory.tree_summaries import cascade_seal

    logger.info(
        "memory.tree.seal.requested",
        tree_kind=payload.tree_kind,
        tree_id=payload.tree_id,
        force=payload.force,
    )

    counts = await cascade_seal(
        tree_kind=payload.tree_kind,
        tree_id=payload.tree_id,
        force=payload.force,
    )

    return TreeSealResponse(
        tree_kind=payload.tree_kind,
        tree_id=payload.tree_id,
        force=payload.force,
        summaries_l1_created=counts.get(1, 0),
        summaries_l2_created=counts.get(2, 0),
        summaries_l3_created=counts.get(3, 0),
    )


@router.get("/tree/summaries/relevant", response_model=list[TreeRelevantQuery])
async def get_tree_summaries_relevant(
    query: str = Query(..., min_length=1, max_length=500, description="Query BM25."),
    tree_kind: str | None = Query(
        default=None,
        description="Opzionale filtro tree_kind: source | topic | global.",
    ),
    top_k: int = Query(default=5, ge=1, le=20),
) -> list[TreeRelevantQuery]:
    """BM25-like retrieval top-K summaries pertinenti alla query (Fase 4 v0.6.0).

    Pattern Karpathy "no vector DB fino a ~100 fonti": BM25 keyword search
    su content_summary, stateless (recompute ad ogni query).

    Usato dal chat system prompt per RAG-like prepend dei top-3 summaries.
    """
    from sco_compliance_os.services.memory.tree_summaries import (
        query_relevant_summaries,
    )

    logger.info(
        "memory.tree.summaries_relevant.requested",
        query_len=len(query),
        tree_kind=tree_kind,
        top_k=top_k,
    )
    summaries = await query_relevant_summaries(
        query, tree_kind=tree_kind, top_k=top_k
    )
    return [
        TreeRelevantQuery(
            id=s.id,
            tree_kind=s.tree_kind,
            tree_id=s.tree_id,
            level=s.level,
            content_preview=s.content_summary[:500].strip().replace("\n", " "),
            token_count=s.token_count,
            sealed_at_ms=s.sealed_at_ms,
        )
        for s in summaries
    ]
