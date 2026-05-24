"""Servizi chat-side per SCO Compliance OS.

Hook post-message che analizzano il contenuto dell'agente (allegati, link a
fonti, risultati web search) e propongono ingestion strutturata nel wiki
(sources / entities / concepts / synthesis / glossari / memory_tree).

Riusa il parser tipizzato esistente sco_compliance_os.services.vault.parser
(Conv. 47 enforcement: single source of truth dello schema frontmatter).
"""

from sco_compliance_os.services.chat.wiki_proposal import (
    INSTITUTIONAL_DOMAINS,
    WikiDestination,
    WikiIngestProposal,
    WikiIngestSlot,
    analyze_message_for_wiki_ingest,
    build_proposal_id,
    classify_attachment_to_destination,
    classify_url_to_destination,
    detect_acronyms,
    detect_normative_refs,
    extract_urls_from_text,
    generate_slug_suggestion,
    propose_frontmatter_draft,
)

__all__ = [
    "INSTITUTIONAL_DOMAINS",
    "WikiDestination",
    "WikiIngestProposal",
    "WikiIngestSlot",
    "analyze_message_for_wiki_ingest",
    "build_proposal_id",
    "classify_attachment_to_destination",
    "classify_url_to_destination",
    "detect_acronyms",
    "detect_normative_refs",
    "extract_urls_from_text",
    "generate_slug_suggestion",
    "propose_frontmatter_draft",
]
