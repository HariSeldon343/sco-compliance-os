"""Vault Karpathy — compliance ontology curata per ogni cliente del consulente.

Pattern: file markdown locali in vault_root/ con frontmatter YAML tipizzato
(Ondate 2-3-4 del vault Antonio Amodeo) + relationships fra entity + edge
cliente↔entity con vocabolario chiuso.

Componenti:
    - parser: legge file vault .md con frontmatter + estrae dimensioni tipizzate
    - scanner: walk ricorsivo vault_root, index in SQLite
    - query: query layer cross-cliente (chi applica X, chi fornisce Y, ecc.)
    - sync: orchestratore scan + index refresh

Storage: filesystem markdown autoritativo + index SQLite locale a
~/.sco-compliance-os/vault_index.db per query veloci.

Complementare al Memory Tree (services/memory/) per ontology compliance curata.
"""

from __future__ import annotations

__all__ = [
    "parser",
    "query",
    "scanner",
    "sync",
]
