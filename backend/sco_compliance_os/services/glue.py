"""Glue layer Memory Tree + Vault Karpathy.

Funzione unified_search: priorità a vault Karpathy quando query è semanticamente
compliance ("ISO 27001", "NIS 2", "cliente sanità"), altrimenti Memory Tree.

Pattern: heuristics regex-based per detection compliance-ness della query +
ranking combinato. Wave 1 niente embedding semantici; wave 2 integrare
sentence-transformers locali per pattern detection LLM-light.

Decisione strategica documentata in docs/adr/0004-memory-vault-hybrid.md:
- Memory Tree per dati freschi auto-popolati (email, calendar, drive, uploads)
- Vault Karpathy per ontology compliance curata cliente-per-cliente
- Glue rende la separazione semantica trasparente all'utente
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .memory.chunker import Chunk
from .memory.scorer import ScoredChunk, score_chunks
from .memory.store import query_recent
from .vault.parser import VaultDocument
from .vault.query import (
    EntityHit,
    clients_applying_entity,
    entities_by_ambito,
)

logger = logging.getLogger(__name__)


# Pattern regex per riconoscere query "compliance-flavored" (preferenza vault).
_COMPLIANCE_PATTERNS = [
    r"\bISO[/\s-]?(IEC[\s-]?)?\d{4,5}\b",  # ISO 27001, ISO/IEC 42001
    r"\bD\.\s?Lgs\.\s?\d+/\d{4}\b",  # D.Lgs. 138/2024
    r"\bReg(olamento)?\.?\s?UE\s?\d{4}/\d+\b",  # Reg. UE 2024/1689
    r"\bGDPR\b",
    r"\bNIS\s?2\b",
    r"\bAI\s?Act\b",
    r"\bHACCP\b",
    r"\bSGSI\b",
    r"\bSGQ\b",
    r"\bBCMS\b",
    r"\baccreditamento\b",
    r"\bfarmacovigilanza\b",
    r"\bsoggett[oi]\s+(essenziali?|important[ei])\b",
    r"\bfornitore\s+critico\b",
    r"\bcybersicurezza\b",
    r"\bcybersecurity\b",
    r"\bACN\b",
    r"\bCSIRT\b",
    r"\bAgID\b",
    r"\bAGENAS\b",
]

_COMPLIANCE_RE = re.compile("|".join(_COMPLIANCE_PATTERNS), re.IGNORECASE)

# Pattern per estrarre ambito_canonico hint dalla query.
_AMBITO_HINTS = {
    "cybersicurezza": ["cyber", "nis", "27001", "acn", "csirt", "sicurezza informaz"],
    "privacy-protezione-dati": ["gdpr", "privacy", "garante", "dpo", "dpia"],
    "governance-ai": ["ai act", "iso 42001", "intelligenza artificiale"],
    "accreditamento-sanitario": ["accreditamento", "sanit", "irccs", "ospedal"],
    "farmacovigilanza": ["farmacovig", "gdp", "mah", "distributor"],
    "sicurezza-lavoro": ["d.lgs. 81", "rspp", "rls", "dvr"],
    "prevenzione-incendi": ["antincend", "vvf", "cpi", "irai"],
    "qualita-sgq": ["9001", "sgq"],
    "sicurezza-alimentare": ["haccp", "alimentar", "852/2004"],
}


@dataclass(slots=True)
class SearchResults:
    """Risultato unificato di una ricerca cross-layer."""

    query: str
    is_compliance_query: bool
    vault_hits: list[VaultDocument] = field(default_factory=list)
    vault_entity_hits: list[EntityHit] = field(default_factory=list)
    memory_hits: list[ScoredChunk] = field(default_factory=list)
    combined_ranked: list[tuple[str, str, float]] = field(default_factory=list)
    # combined_ranked: lista (layer, identifier, score) ordinata DESC.


def is_compliance_query(query: str) -> bool:
    """Heuristics: la query è semanticamente compliance-flavored?"""
    return bool(_COMPLIANCE_RE.search(query))


def detect_ambito_hint(query: str) -> Optional[str]:
    """Detect ambito_canonico hint dalla query (lookup keyword)."""
    q_lower = query.lower()
    for ambito, keywords in _AMBITO_HINTS.items():
        if any(kw in q_lower for kw in keywords):
            return ambito
    return None


async def unified_search(
    query: str,
    *,
    vault_first: bool = True,
    memory_fallback: bool = True,
    memory_db_path: Optional[Path] = None,
    vault_db_path: Optional[Path] = None,
    memory_candidates: int = 200,
    top_k: int = 10,
) -> SearchResults:
    """Ricerca unificata Memory Tree + Vault Karpathy.

    Args:
        query: stringa query utente.
        vault_first: se True e la query è compliance-flavored, vault prioritario.
        memory_fallback: se True, integra anche Memory Tree nel ranking.
        memory_db_path: override path memory DB.
        vault_db_path: override path vault index DB.
        memory_candidates: numero di chunks recenti da scorare BM25.
        top_k: cap risultati per layer.

    Returns:
        SearchResults con vault_hits + memory_hits + combined_ranked.
    """
    is_compliance = is_compliance_query(query)
    ambito = detect_ambito_hint(query)
    results = SearchResults(query=query, is_compliance_query=is_compliance)

    # Layer 1: Vault Karpathy (priorità se compliance-flavored).
    if vault_first and is_compliance:
        # Strategy 1a: ambito hit → catalog entity per dominio.
        if ambito:
            results.vault_entity_hits = (
                await entities_by_ambito(ambito, db_path=vault_db_path)
            )[:top_k]

        # Strategy 1b: per ogni token "norma-like" nella query, prova reverse-edge.
        # Pattern: "D.Lgs. 138/2024" → slug "d-lgs-138-2024".
        slugs_from_query = _extract_norma_slugs(query)
        for slug in slugs_from_query:
            clients = await clients_applying_entity(slug, db_path=vault_db_path)
            if clients:
                # Crea VaultDocument placeholder per ogni cliente hit.
                for c in clients[:top_k]:
                    results.vault_hits.append(
                        VaultDocument(
                            path=c.path,
                            type="cliente",
                            title=c.title,
                            status="active",
                            raw_frontmatter={"matched_role": c.ruolo, "note": c.note},
                        )
                    )

    # Layer 2: Memory Tree (sempre se memory_fallback, primario se non compliance).
    if memory_fallback:
        candidates = await query_recent(
            limit=memory_candidates, db_path=memory_db_path
        )
        scored = score_chunks(candidates, query)
        results.memory_hits = scored[:top_k]

    # Combined ranking: vault hits guadagnano boost se is_compliance.
    combined: list[tuple[str, str, float]] = []
    vault_boost = 2.0 if is_compliance else 1.0
    for vhit in results.vault_hits:
        combined.append(("vault", vhit.path, vault_boost))
    for ehit in results.vault_entity_hits:
        combined.append(("vault_entity", ehit.path, vault_boost * 0.9))
    for mhit in results.memory_hits:
        combined.append(("memory", mhit.chunk.id, mhit.score))

    combined.sort(key=lambda x: x[2], reverse=True)
    results.combined_ranked = combined[:top_k]

    logger.info(
        "unified_search: query=%r compliance=%s ambito=%s vault=%d entity=%d memory=%d",
        query,
        is_compliance,
        ambito,
        len(results.vault_hits),
        len(results.vault_entity_hits),
        len(results.memory_hits),
    )
    return results


_NORMA_PATTERNS = [
    (re.compile(r"D\.\s?Lgs\.\s?(\d+)/(\d{4})", re.IGNORECASE), "d-lgs-{0}-{1}"),
    (re.compile(r"Reg\.?\s?UE\s?(\d{4})/(\d+)", re.IGNORECASE), "reg-ue-{0}-{1}"),
    (re.compile(r"ISO[/\s-]?IEC[\s-]?(\d+)[\s-:]?(\d{4})", re.IGNORECASE), "iso-iec-{0}-{1}"),
    (re.compile(r"ISO\s?(\d+)[\s-:]?(\d{4})", re.IGNORECASE), "iso-{0}-{1}"),
]


def _extract_norma_slugs(query: str) -> list[str]:
    """Estrae slug entity candidati dalla query (D.Lgs. 138/2024 → 'd-lgs-138-2024')."""
    slugs: list[str] = []
    for pattern, template in _NORMA_PATTERNS:
        for match in pattern.finditer(query):
            slugs.append(template.format(*match.groups()))
    return slugs
