"""Modelli SQLAlchemy per Memory Tree gerarchico (OpenHuman replica Wave 1).

Pattern: declarative ORM v2 + async aiosqlite driver.
Storage: ~/.sco-compliance-os/memory_tree.db (stesso DB di chunker store esistente).

Tabelle nuove (migration 0002):
    - summaries: hierarchical summary tree L0/L1/L2 per-source/per-topic/per-day
    - scores: fast_score (regex sync) + deep_score (LLM async) + hotness decay
    - entity_index: entity → chunk_id mapping per cross-reference (carry-over wave 2)
    - jobs: async job queue per deep_score batch + tree promotion (carry-over)

Pattern Karpathy "schema is the product": il modello dichiarativo è la single
source of truth dello schema; la migration 0002 SQL replica il DDL per
idempotenza cross-environment (PyInstaller bundle, dev local, CI).
"""

from __future__ import annotations

from .score import Score
from .summary import Base, Summary

__all__ = [
    "Base",
    "Score",
    "Summary",
]
