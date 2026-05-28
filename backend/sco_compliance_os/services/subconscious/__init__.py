"""Subconscious tick loop service per SCO Compliance OS.

Pattern replica clean-room (no apertura source GPL OpenHuman) di:
- Tick loop asincrono ogni 5 minuti (default OFF v0.2.0, opt-in privacy)
- Decision engine SKIP|ACT|ESCALATE alimentato da Claude Haiku 4.5
- Throttle no-overlap (i tick NON si accumulano mai)
- Backoff esponenziale su failure consecutive (10/20/40 min cap 60)
- Activity log append-only su ~/.sco-compliance-os/subconscious-activity.jsonl

Componenti:
- :class:`SubconsciousTickLoop` (tick_loop.py): orchestratore
- :class:`DecisionEngine` (decision_engine.py): LLM-backed decision tree
- :class:`TickThrottle` (throttle.py): lock manager + cancellation
- :class:`SubconsciousContext`, :class:`Decision`, :class:`DecisionOutcome`
  (decision_engine.py): tipi dato

Riferimenti vault:
- Blueprint: Libreria/framework/openhuman-replica-blueprint-2026-05-23.md
- Convenzioni: CLAUDE.md Conv. 33-34 (multi-agent + spot check), Conv. 41
  (tracciatura sessione), Conv. 46 (smoke E2E prima del tag).
"""

from __future__ import annotations

from .context_provider import build_context
from .decision_engine import (
    Decision,
    DecisionEngine,
    DecisionOutcome,
    SubconsciousContext,
)
from .throttle import TickThrottle
from .tick_loop import SubconsciousTickLoop

__all__ = [
    "Decision",
    "DecisionEngine",
    "DecisionOutcome",
    "SubconsciousContext",
    "SubconsciousTickLoop",
    "TickThrottle",
    "build_context",
]
