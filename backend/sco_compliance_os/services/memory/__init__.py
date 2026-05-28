"""Memory Tree — knowledge layer locale per sco-compliance-os.

Pattern: token-aware chunking + scoring BM25 + hierarchical summary tree.
Storage: SQLite locale via aiosqlite in ~/.sco-compliance-os/memory_tree.db.

Componenti:
    - chunker: token-aware markdown chunker (tiktoken)
    - scorer: ranking BM25 + recency + manual boost
    - store: SQLite async CRUD + bulk insert + query
    - summarizer: gerarchico sibling summarizer (stub LLM)
    - ingest: pipeline end-to-end con provenance metadata (Conv. 43)

Auto-popolato da connettori OAuth (email, calendar, drive) + user uploads.
Complementare al Vault SCO (services/vault/) per dati freschi non curati.
"""

from __future__ import annotations

__all__ = [
    "cascade",
    "chunker",
    "hotness",
    "ingest",
    "openhuman_scorer",
    "scorer",
    "store",
    "summarizer",
    # Wave 2 OpenHuman replica additions (subagent W2-TOKENJUICE 23/05/2026)
    "tokenjuice",
    # Wave 1 OpenHuman replica additions (subagent W1-MEMORY 23/05/2026)
    "tree_builder",
    # Memory Tree bucket-seal 4 fasi clean-room (subagent DEV-MEMORY-TREE 24/05/2026)
    "tree_chunker",
    "tree_ingester",
    "tree_scoring",
    "tree_store",
]
