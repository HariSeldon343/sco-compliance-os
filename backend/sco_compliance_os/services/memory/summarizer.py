"""Summarizer gerarchico — Memory Tree Karpathy hierarchical summary.

Quando un gruppo di N chunks fratelli (stesso parent_chunk_id o stessa
heading_path radice) supera il token budget complessivo, viene generato un
chunk_summary parent che condensa la conoscenza, mantenendo i figli come
leaves accessibili in retrieval di precisione.

Wave 1: stub LLM client (TODO async claude.haiku per cost-effective).
Wave 2: integrazione completa con LLM provider + tracking cost.

Pattern Karpathy: la summarization è "shallow + lossy" intenzionalmente.
Lo scopo è un albero navigabile dove le query first-pass colpiscono summaries
e solo on-demand espandono ai leaves di dettaglio.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Protocol

from .chunker import Chunk

logger = logging.getLogger(__name__)

# Budget di default: se la somma dei figli supera 6000 token, si summarizza.
_DEFAULT_SIBLING_BUDGET = 6000

# Lunghezza target del summary: 1/4 del budget figli (compressione 4:1).
_SUMMARY_TARGET_TOKENS = 1500


class LLMClient(Protocol):
    """Interfaccia minimale LLM client per summarization.

    TODO wave 2: integrare con anthropic SDK (claude-haiku per cost) o locale.
    Stub corrente solleva NotImplementedError esplicito.
    """

    async def complete(self, prompt: str, max_tokens: int) -> str:
        """Genera completion async."""
        ...


class StubLLMClient:
    """Stub client per wave 1 — solleva esplicito per evitare hallucination.

    Wave 1 strategy: niente summary auto-generato, restituiamo concatenazione
    sintetica dei heading_path + primi 200 chars di ogni chunk figlio.
    Questo NON è un summary semantico ma un placeholder navigabile.
    """

    async def complete(self, prompt: str, max_tokens: int) -> str:  # noqa: ARG002
        # TODO wave 2: chiamata reale a claude-haiku-3.5 o equivalente locale.
        # Per wave 1, ritorniamo placeholder esplicito che non simula intelligenza.
        return "[SUMMARY STUB — wave 1 placeholder, integrate LLM in wave 2]"


@dataclass(slots=True)
class SummarizationResult:
    """Output del summarizer."""

    parent_chunk: Chunk
    child_count: int
    total_input_tokens: int
    summary_tokens: int


def _build_placeholder_summary(children: list[Chunk]) -> str:
    """Costruisce placeholder leggibile dai children (wave 1, no LLM)."""
    lines = ["# Memory Tree — Summary placeholder (wave 1)\n"]
    for idx, child in enumerate(children, start=1):
        breadcrumb = " > ".join(child.heading_path) or "(no heading)"
        excerpt = child.content_md.strip().replace("\n", " ")[:200]
        lines.append(f"## {idx}. {breadcrumb}\n\n{excerpt}...\n")
    return "\n".join(lines)


async def summarize_siblings(
    children: Iterable[Chunk],
    llm_client: LLMClient,
    *,
    sibling_budget: int = _DEFAULT_SIBLING_BUDGET,
    summary_target: int = _SUMMARY_TARGET_TOKENS,
) -> SummarizationResult | None:
    """Genera chunk parent che summarizza children quando supera budget.

    Args:
        children: iterabile di Chunk fratelli (stesso parent_chunk_id).
        llm_client: client LLM async (wave 1 può essere StubLLMClient).
        sibling_budget: soglia token oltre la quale si summarizza.
        summary_target: token target del summary generato.

    Returns:
        SummarizationResult con parent_chunk se summarization è scattata,
        altrimenti None (budget non superato).
    """
    children_list = list(children)
    if not children_list:
        return None

    total_tokens = sum(c.token_count for c in children_list)
    if total_tokens <= sibling_budget:
        logger.debug(
            "Summarization skipped: %d token < budget %d", total_tokens, sibling_budget
        )
        return None

    # Costruisce prompt per LLM (wave 2 lo userà davvero).
    prompt = (
        "Sintetizza i seguenti chunks markdown preservando concetti chiave, "
        "entità normative e riferimenti puntuali. Target: ~"
        f"{summary_target} token. Output in italiano.\n\n"
    )
    for child in children_list:
        prompt += f"### {' > '.join(child.heading_path)}\n{child.content_md}\n\n"

    try:
        summary_md = await llm_client.complete(prompt, max_tokens=summary_target)
    except NotImplementedError:
        # Wave 1 fallback: placeholder sintetico, non hallucinato.
        summary_md = _build_placeholder_summary(children_list)

    # Heading_path del parent eredita la radice comune dei children.
    common_root: list[str] = []
    if children_list and children_list[0].heading_path:
        common_root = [children_list[0].heading_path[0]]

    parent = Chunk(
        id=str(uuid.uuid4()),
        source_path=children_list[0].source_path,
        parent_chunk_id=None,
        heading_path=common_root,
        content_md=summary_md,
        token_count=len(summary_md) // 4,  # stima euristica
        source_type="vault_ingest",
        source_id=f"summary_{children_list[0].source_id}",
        provenance={
            "summary_of": [c.id for c in children_list],
            "summary_generated_at": datetime.now(timezone.utc).isoformat(),
            "summary_method": "stub" if isinstance(llm_client, StubLLMClient) else "llm",
        },
    )

    return SummarizationResult(
        parent_chunk=parent,
        child_count=len(children_list),
        total_input_tokens=total_tokens,
        summary_tokens=parent.token_count,
    )
