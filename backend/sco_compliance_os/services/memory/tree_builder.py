"""Tree Builder per Memory Tree gerarchico OpenHuman replica.

Pattern OpenHuman (clean-room reimplementation from docs):
    - 3 alberi paralleli: per-source, per-topic, per-day.
    - Pipeline L0 → L1 → L2 con threshold token budget 6000 + age 7d.
    - Async via job queue (no sync LLM in hot path).
    - Compressione target 4:1 ogni livello.

Pattern Karpathy:
    - Schema is the product: ogni Summary L1/L2 carries chunk_ids in JSON.
    - Single source of truth: il tree è ricostruito on-demand via query
      (no caching duplicato dello stato).
    - Shallow + lossy summarization: i leaves L0 restano accessibili.

API pubblica:
    TreeBuilder.build_source_tree(source) — costruisce tree per uno specifico sorgente.
    TreeBuilder.build_topic_tree(topic) — costruisce tree per uno specifico topic.
    TreeBuilder.build_global_tree(day) — costruisce snapshot globale per data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite
import structlog

from .chunker import Chunk
from .store import default_db_path, query_by_source, query_recent
from .summarizer import LLMClient, StubLLMClient

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class TreeNode:
    """Nodo del tree gerarchico (L0 leaf o L1/L2 summary).

    Attributes:
        id: ID nodo (chunk_id per L0, summary_id per L1/L2).
        level: 0 = leaf chunk, 1 = summary, 2 = aggregated.
        source: identifier sorgente.
        topic: topic opzionale.
        day: data ISO opzionale.
        content_preview: primi 300 caratteri del content.
        token_count: stima token.
        children_ids: ID figli (chunk_ids per L1, summary_ids per L2).
        parent_id: ID parent (NULL per root).
        created_at: timestamp ISO.
    """

    id: str
    level: int
    source: str
    topic: str | None
    day: str | None
    content_preview: str
    token_count: int
    children_ids: list[str] = field(default_factory=list)
    parent_id: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level,
            "source": self.source,
            "topic": self.topic,
            "day": self.day,
            "content_preview": self.content_preview,
            "token_count": self.token_count,
            "children_ids": self.children_ids,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class TreeBuildResult:
    """Risultato di una build_*_tree call.

    Attributes:
        nodes: lista di TreeNode (mix L0/L1/L2).
        roots: ID dei nodi root (top level).
        l0_count: numero di leaves L0.
        l1_count: numero di summary L1.
        l2_count: numero di summary L2.
        compression_ratio: input_tokens / output_tokens.
    """

    nodes: list[TreeNode]
    roots: list[str]
    l0_count: int = 0
    l1_count: int = 0
    l2_count: int = 0
    compression_ratio: float = 1.0


def _utc_now_iso() -> str:
    """Timestamp UTC ISO 8601."""
    return datetime.now(UTC).isoformat()


def _chunk_to_node(chunk: Chunk) -> TreeNode:
    """Converte Chunk in TreeNode L0."""
    preview = chunk.content_md[:300].strip().replace("\n", " ")
    return TreeNode(
        id=chunk.id,
        level=0,
        source=f"{chunk.source_type}::{chunk.source_id}" if chunk.source_id else chunk.source_path,
        topic=None,
        day=chunk.created_at[:10] if chunk.created_at else None,
        content_preview=preview,
        token_count=chunk.token_count,
        children_ids=[],
        parent_id=chunk.parent_chunk_id,
        created_at=chunk.created_at,
    )


def _summary_row_to_node(row: aiosqlite.Row) -> TreeNode:
    """Converte SQLite row di summaries in TreeNode."""
    chunk_ids_raw = row["chunk_ids"]
    try:
        children_ids = json.loads(chunk_ids_raw) if chunk_ids_raw else []
    except (json.JSONDecodeError, TypeError):
        children_ids = []
    content = row["content"] or ""
    preview = content[:300].strip().replace("\n", " ")
    return TreeNode(
        id=row["id"],
        level=int(row["level"]),
        source=row["source"] or "",
        topic=row["topic"],
        day=row["day"],
        content_preview=preview,
        token_count=int(row["token_count"]),
        children_ids=children_ids,
        parent_id=row["parent_id"],
        created_at=row["created_at"] or "",
    )


class TreeBuilder:
    """Costruttore tree gerarchico Memory Tree.

    Pattern: factory class con tre metodi pubblici (source/topic/global).
    Stato: nessuno (stateless). Tutto deriva da query DB.

    Args:
        llm_client: client LLM per summarization (default StubLLMClient).
        db_path: path al DB (default ~/.sco-compliance-os/memory_tree.db).
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        db_path: Path | None = None,
    ) -> None:
        self.llm_client = llm_client or StubLLMClient()
        self.db_path = db_path or default_db_path()
        logger.info("tree_builder.init", db_path=str(self.db_path))

    async def build_source_tree(
        self,
        source: str,
        *,
        include_l0: bool = True,
    ) -> TreeBuildResult:
        """Costruisce tree gerarchico per uno specifico sorgente.

        Pipeline:
            1. Carica tutti i chunks L0 con source_id = source (o source_path = source).
            2. Carica Summary L1/L2 esistenti per source.
            3. Compone TreeNode list + identifica roots.

        Args:
            source: identifier sorgente (può essere source_id, source_path, o "source_type::source_id").
            include_l0: se True include leaves L0; se False solo L1/L2.

        Returns:
            TreeBuildResult con nodes + statistiche.
        """
        logger.info("tree_builder.build_source_tree.start", source=source)
        nodes: list[TreeNode] = []
        l0_count = l1_count = l2_count = 0
        total_input_tokens = 0
        total_output_tokens = 0

        # L0 chunks — tentiamo match source_id; fallback source_path
        if include_l0:
            # Cerca per source_id
            chunks: list[Chunk] = await query_by_source(
                source_id=source,
                limit=1000,
                db_path=self.db_path,
            )
            if not chunks:
                # Fallback: cerca per source_type::source_id pattern
                if "::" in source:
                    stype, sid = source.split("::", 1)
                    chunks = await query_by_source(
                        source_type=stype,
                        source_id=sid,
                        limit=1000,
                        db_path=self.db_path,
                    )

            for c in chunks:
                node = _chunk_to_node(c)
                nodes.append(node)
                l0_count += 1
                total_input_tokens += c.token_count

        # L1 + L2 summaries per source
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM summaries
                WHERE source = ?
                ORDER BY level ASC, created_at DESC""",
                (source,),
            ) as cur:
                async for row in cur:
                    node = _summary_row_to_node(row)
                    nodes.append(node)
                    if node.level == 1:
                        l1_count += 1
                    elif node.level == 2:
                        l2_count += 1
                    total_output_tokens += node.token_count

        # Roots: nodi senza parent_id
        roots = [n.id for n in nodes if not n.parent_id]

        compression_ratio = (
            total_input_tokens / max(total_output_tokens, 1) if total_output_tokens > 0 else 1.0
        )

        result = TreeBuildResult(
            nodes=nodes,
            roots=roots,
            l0_count=l0_count,
            l1_count=l1_count,
            l2_count=l2_count,
            compression_ratio=round(compression_ratio, 2),
        )
        logger.info(
            "tree_builder.build_source_tree.complete",
            source=source,
            l0=l0_count,
            l1=l1_count,
            l2=l2_count,
            roots=len(roots),
        )
        return result

    async def build_topic_tree(
        self,
        topic: str,
        *,
        include_l0: bool = False,
    ) -> TreeBuildResult:
        """Costruisce tree gerarchico per uno specifico topic.

        Args:
            topic: nome topic (es. 'cybersicurezza', 'NIS2', 'privacy-protezione-dati').
            include_l0: include leaves L0 dei chunks legati al topic.

        Returns:
            TreeBuildResult.
        """
        logger.info("tree_builder.build_topic_tree.start", topic=topic)
        nodes: list[TreeNode] = []
        l0_count = l1_count = l2_count = 0
        total_input_tokens = 0
        total_output_tokens = 0

        # Topic non vive su chunks (vive su summaries), ma se include_l0 cerchiamo
        # chunks correlati via entity_index (carry-over wave 2: per ora skip se include_l0).
        if include_l0:
            logger.debug(
                "tree_builder.build_topic_tree.l0_skip",
                note="L0 per topic richiede entity_index, carry-over wave 2",
            )

        # L1 + L2 summaries per topic
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM summaries
                WHERE topic = ?
                ORDER BY level ASC, created_at DESC""",
                (topic,),
            ) as cur:
                async for row in cur:
                    node = _summary_row_to_node(row)
                    nodes.append(node)
                    if node.level == 1:
                        l1_count += 1
                    elif node.level == 2:
                        l2_count += 1
                    total_output_tokens += node.token_count

        roots = [n.id for n in nodes if not n.parent_id]
        compression_ratio = (
            total_input_tokens / max(total_output_tokens, 1) if total_output_tokens > 0 else 1.0
        )

        result = TreeBuildResult(
            nodes=nodes,
            roots=roots,
            l0_count=l0_count,
            l1_count=l1_count,
            l2_count=l2_count,
            compression_ratio=round(compression_ratio, 2),
        )
        logger.info(
            "tree_builder.build_topic_tree.complete",
            topic=topic,
            l1=l1_count,
            l2=l2_count,
            roots=len(roots),
        )
        return result

    async def build_global_tree(
        self,
        day: str | None = None,
        *,
        recent_chunks_limit: int = 100,
    ) -> TreeBuildResult:
        """Costruisce snapshot globale del Memory Tree per data o overall.

        Args:
            day: data ISO YYYY-MM-DD opzionale. Se None, snapshot dei recent_chunks_limit più recenti.
            recent_chunks_limit: limite chunks L0 da includere se day=None.

        Returns:
            TreeBuildResult.
        """
        logger.info("tree_builder.build_global_tree.start", day=day)
        nodes: list[TreeNode] = []
        l0_count = l1_count = l2_count = 0
        total_input_tokens = 0
        total_output_tokens = 0

        # L0 recent chunks o filtered by day
        if day:
            # Carica chunks creati nella giornata day
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """SELECT * FROM memory_chunks
                    WHERE substr(created_at, 1, 10) = ?
                    ORDER BY created_at DESC""",
                    (day,),
                ) as cur:
                    async for row in cur:
                        # Ricostruisce Chunk dalla row
                        c = Chunk(
                            id=row["id"],
                            source_path=row["source_path"],
                            parent_chunk_id=row["parent_id"],
                            heading_path=json.loads(row["heading_path"]),
                            content_md=row["content_md"],
                            token_count=int(row["token_count"]),
                            source_type=row["source_type"],
                            source_id=row["source_id"],
                            provenance=json.loads(row["score_metadata"]),
                            created_at=row["created_at"],
                        )
                        nodes.append(_chunk_to_node(c))
                        l0_count += 1
                        total_input_tokens += c.token_count
        else:
            # Recent N chunks
            chunks = await query_recent(limit=recent_chunks_limit, db_path=self.db_path)
            for c in chunks:
                nodes.append(_chunk_to_node(c))
                l0_count += 1
                total_input_tokens += c.token_count

        # L1 + L2 summaries per day (se specificato) o tutti gli L2 (snapshot globale)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if day:
                query = """SELECT * FROM summaries
                WHERE day = ?
                ORDER BY level ASC, created_at DESC"""
                params: tuple[Any, ...] = (day,)
            else:
                # Snapshot globale: prendi tutti gli L2 + L1 più recenti
                query = """SELECT * FROM summaries
                ORDER BY level DESC, created_at DESC
                LIMIT 50"""
                params = ()
            async with db.execute(query, params) as cur:
                async for row in cur:
                    node = _summary_row_to_node(row)
                    nodes.append(node)
                    if node.level == 1:
                        l1_count += 1
                    elif node.level == 2:
                        l2_count += 1
                    total_output_tokens += node.token_count

        roots = [n.id for n in nodes if not n.parent_id]
        compression_ratio = (
            total_input_tokens / max(total_output_tokens, 1) if total_output_tokens > 0 else 1.0
        )

        result = TreeBuildResult(
            nodes=nodes,
            roots=roots,
            l0_count=l0_count,
            l1_count=l1_count,
            l2_count=l2_count,
            compression_ratio=round(compression_ratio, 2),
        )
        logger.info(
            "tree_builder.build_global_tree.complete",
            day=day,
            l0=l0_count,
            l1=l1_count,
            l2=l2_count,
            roots=len(roots),
        )
        return result

    async def list_summaries_by_filter(
        self,
        *,
        source: str | None = None,
        level: int | None = None,
        topic: str | None = None,
        day: str | None = None,
        limit: int = 50,
    ) -> list[TreeNode]:
        """Lista summaries con filtri arbitrari (per endpoint GET /api/memory/tree).

        Args:
            source: filtra per source identifier.
            level: filtra per level (1 o 2).
            topic: filtra per topic.
            day: filtra per data ISO YYYY-MM-DD.
            limit: max risultati.

        Returns:
            Lista di TreeNode.
        """
        sql = "SELECT * FROM summaries WHERE 1=1"
        params: list[Any] = []
        if source:
            sql += " AND source = ?"
            params.append(source)
        if level is not None:
            sql += " AND level = ?"
            params.append(level)
        if topic:
            sql += " AND topic = ?"
            params.append(topic)
        if day:
            sql += " AND day = ?"
            params.append(day)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        nodes: list[TreeNode] = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cur:
                async for row in cur:
                    nodes.append(_summary_row_to_node(row))

        logger.info(
            "tree_builder.list_summaries.complete",
            source=source,
            filter_level=level,  # renamed to avoid structlog reserved "level" key
            topic=topic,
            day=day,
            count=len(nodes),
        )
        return nodes
