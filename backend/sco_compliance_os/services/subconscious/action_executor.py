"""Esecutore azioni sicure del Subconscious (cantiere Subconscio v0.15.0).

Antonio ha scelto: il Subconscio puo' eseguire DA SOLO solo azioni locali sicure
(riassunti, indicizzazione). Mai toccare file clienti, mail, calendari o il vault
Obsidian dell'utente senza approvazione.

Boundary enforcement (non negoziabile):
- Solo le decisioni ACT con ``kind`` nella whitelist CHIUSA ``SAFE_ACTION_KINDS``
  vengono eseguite in automatico.
- ESCALATE resta SEMPRE una proposta: mai eseguita automaticamente (richiede
  approvazione utente nel pannello).
- SKIP non esegue nulla.
- L'esecuzione automatica avviene solo se il Subconscio e' abilitato
  (``settings.subconscious_enabled``); altrimenti l'azione resta una proposta.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sco_compliance_os.config import get_settings
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.subconscious.decision_engine import Decision, DecisionOutcome

logger = get_logger(__name__)

# Whitelist CHIUSA delle azioni che il Subconscio puo' eseguire in autonomia.
# Qualsiasi kind non presente qui resta una proposta (mai eseguito in auto).
SAFE_ACTION_KINDS: frozenset[str] = frozenset({"summarize", "index"})

# Tipo del callable esecutore iniettabile nel tick loop.
ActionExecutor = Callable[[DecisionOutcome], Awaitable["ExecutionResult"]]


@dataclass(slots=True)
class ExecutionResult:
    """Esito dell'esecuzione (o del rifiuto) di un'azione proposta dal tick."""

    executed: bool
    kind: str | None
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"executed": self.executed, "kind": self.kind, "detail": self.detail}


async def execute_safe_action(outcome: DecisionOutcome, *, enabled: bool) -> ExecutionResult:
    """Esegue l'azione proposta SOLO se sicura, ACT e con Subconscio abilitato.

    Args:
        outcome: esito del decision engine.
        enabled: True se il Subconscio e' abilitato (esecuzione automatica ammessa).

    Returns:
        ExecutionResult: executed=True solo se l'azione e' stata realmente eseguita.
    """
    if not enabled:
        return ExecutionResult(executed=False, kind=None, detail="subconscious_disabled")
    if outcome.decision != Decision.ACT:
        # SKIP non fa nulla; ESCALATE resta proposta (mai auto-eseguita).
        return ExecutionResult(executed=False, kind=None, detail="not_act")

    action = outcome.proposed_action if isinstance(outcome.proposed_action, dict) else None
    kind = str(action.get("kind")) if action and action.get("kind") else None
    if not kind or kind not in SAFE_ACTION_KINDS:
        logger.info("subconscious.action.refused", kind=kind, reason="not_whitelisted")
        return ExecutionResult(executed=False, kind=kind, detail="not_whitelisted")

    try:
        detail = await _dispatch(kind)
    except Exception as exc:  # difensivo: un'azione non deve mai crashare il tick
        logger.warning("subconscious.action.exec_failed", kind=kind, error=str(exc))
        return ExecutionResult(executed=False, kind=kind, detail=f"error: {type(exc).__name__}")

    logger.info("subconscious.action.executed", kind=kind, detail=detail)
    return ExecutionResult(executed=True, kind=kind, detail=detail)


async def _dispatch(kind: str) -> str:
    """Dispatch verso l'azione sicura concreta. Solo operazioni locali sicure."""
    if kind == "summarize":
        # Consolidamento memoria: idempotente, gia' usato dallo seal scheduler.
        from sco_compliance_os.services.memory.tree_summaries import cascade_seal_all

        counts = await cascade_seal_all(owner="local", force=False)
        total = sum(sum(level_counts.values()) for level_counts in counts.values()) if counts else 0
        return f"consolidamento memoria: {total} summary generate/aggiornate"

    if kind == "index":
        # Refresh indice: sola lettura, conta i chunk presenti.
        from sco_compliance_os.services.memory.store import count_chunks

        n = await count_chunks()
        return f"reindex check: {n} chunk in memoria"

    return "noop"


def make_default_executor() -> ActionExecutor:
    """Crea l'esecutore di default che gating l'esecuzione su subconscious_enabled.

    Iniettato nel SubconsciousTickLoop da main.py. Legge il flag a ogni chiamata
    cosi' rispetta il toggle runtime (enable/disable via API).
    """

    async def _executor(outcome: DecisionOutcome) -> ExecutionResult:
        return await execute_safe_action(outcome, enabled=get_settings().subconscious_enabled)

    return _executor


__all__ = [
    "SAFE_ACTION_KINDS",
    "ActionExecutor",
    "ExecutionResult",
    "execute_safe_action",
    "make_default_executor",
]
