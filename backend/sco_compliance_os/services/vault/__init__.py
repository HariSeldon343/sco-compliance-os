"""Vault Karpathy — compliance ontology curata per ogni cliente del consulente.

Pattern: file markdown locali in vault_root/ con frontmatter YAML tipizzato
(Ondate 2-3-4 del vault Antonio Amodeo) + relationships fra entity + edge
cliente↔entity con vocabolario chiuso.

Componenti:
    - parser: legge file vault .md con frontmatter + estrae dimensioni tipizzate
    - scanner: walk ricorsivo vault_root, index in SQLite vault_index.db
    - query: query layer cross-cliente (chi applica X, chi fornisce Y, ecc.)
    - sync: orchestratore scan + index refresh (vault_index.db legacy)
    - extractors: estrattori tipizzati 7 formati (.md/.pdf/.docx/.xlsx/.txt/.json/.yaml)
    - autoingest: pipeline auto-ingest vault -> mem_tree_chunks (v0.6.0)
    - watcher: file watcher live (watchdog) per re-ingest delta on modify/delete

Storage:
    - vault_index.db (legacy): file markdown autoritativo + index per query Karpathy.
    - mem_tree_chunks (v0.6.0): chunk testo da TUTTI i 7 formati per memoria
      contestuale agente AI. Pipeline bucket-seal admission gate (Fase 3).

Complementare al Memory Tree (services/memory/) per ontology compliance curata.
"""

from __future__ import annotations

__all__ = [
    "autoingest",
    "extractors",
    "parser",
    "query",
    "scanner",
    "sync",
    "watcher",
]
