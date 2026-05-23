"""Router /api/subconscious — orchestratore tick loop subconscious 5 min.

Endpoint:
- GET  /api/subconscious/status    -> JSON snapshot stato loop
- POST /api/subconscious/tick      -> manual trigger sync (attende completion)
- POST /api/subconscious/enable    -> avvia loop (toggle runtime; richiede flag enabled)
- POST /api/subconscious/disable   -> ferma loop
- GET  /api/subconscious/activity  -> ultime N entry da activity.jsonl

Pattern privacy v0.2.0: Subconscious OFF di default. L'utente deve abilitare
via ``settings.subconscious_enabled = True`` (in env / config) E chiamare
``POST /api/subconscious/enable``. Il flag enabled e' uno switch logico
durante il runtime, ortogonale al setting persistente.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.subconscious.decision_engine import Decision
from sco_compliance_os.services.subconscious.tick_loop import (
    SubconsciousTickLoop,
    get_active_loop,
    set_active_loop,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/subconscious", tags=["subconscious"])


# ----- Schemi Pydantic ---------------------------------------------------------------


class SubconsciousStatus(BaseModel):
    """Snapshot stato corrente del subconscious loop."""

    enabled: bool = Field(..., description="Flag setting persistente (config).")
    running: bool
    interval_seconds: int
    interval_seconds_effective: int
    is_throttle_busy: bool
    last_tick_started_at: str | None
    last_tick_completed_at: str | None
    last_tick_decision: str | None
    last_tick_rationale: str | None
    last_tick_cancelled: bool
    last_tick_used_llm: bool
    consecutive_failures: int
    ticks_today: int
    ticks_today_date: str | None
    total_ticks: int


class TickResponse(BaseModel):
    """Esito di un manual tick."""

    decision: str
    rationale: str
    proposed_action: dict[str, Any] | None = None
    used_llm: bool


class ToggleResponse(BaseModel):
    """Esito enable/disable."""

    running: bool
    message: str


class ActivityEntry(BaseModel):
    """Entry del activity log JSONL."""

    ts: str
    decision: str
    rationale: str
    proposed_action: dict[str, Any] | None = None
    used_llm: bool
    manual: bool
    cancelled: bool


class ActivityResponse(BaseModel):
    """Response /activity."""

    entries: list[ActivityEntry] = Field(default_factory=list)
    count: int = 0


# ----- Helpers -----------------------------------------------------------------------


def _require_loop() -> SubconsciousTickLoop:
    """Ritorna il loop attivo o 503 se non inizializzato dal lifespan."""
    loop = get_active_loop()
    if loop is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Subconscious loop not initialized. Set subconscious_enabled=true "
                "in config and restart the backend."
            ),
        )
    return loop


# ----- Endpoint ----------------------------------------------------------------------


@router.get("/status", response_model=SubconsciousStatus)
async def get_status() -> SubconsciousStatus:
    """Snapshot stato corrente del loop."""
    from sco_compliance_os.config import get_settings

    settings = get_settings()
    loop = get_active_loop()
    if loop is None:
        # Stato pre-init: ritorna defaults coerenti
        return SubconsciousStatus(
            enabled=settings.subconscious_enabled,
            running=False,
            interval_seconds=settings.subconscious_interval_seconds,
            interval_seconds_effective=settings.subconscious_interval_seconds,
            is_throttle_busy=False,
            last_tick_started_at=None,
            last_tick_completed_at=None,
            last_tick_decision=None,
            last_tick_rationale=None,
            last_tick_cancelled=False,
            last_tick_used_llm=False,
            consecutive_failures=0,
            ticks_today=0,
            ticks_today_date=None,
            total_ticks=0,
        )
    snap = loop.get_status()
    return SubconsciousStatus(enabled=settings.subconscious_enabled, **snap)


@router.post("/tick", response_model=TickResponse)
async def manual_tick() -> TickResponse:
    """Esegue un tick manuale sincrono (attende completion). Ritorna Decision."""
    loop = _require_loop()
    try:
        outcome = await loop.run_tick_now()
    except RuntimeError as e:
        # Cap giornaliero raggiunto -> 429
        raise HTTPException(status_code=429, detail=str(e)) from e
    return TickResponse(
        decision=outcome.decision.value,
        rationale=outcome.rationale,
        proposed_action=outcome.proposed_action,
        used_llm=outcome.used_llm,
    )


@router.post("/enable", response_model=ToggleResponse)
async def enable_loop() -> ToggleResponse:
    """Avvia il loop in background. Idempotente."""
    loop = _require_loop()
    started = await loop.start()
    msg = "loop_started" if started else "already_running"
    return ToggleResponse(running=loop.is_running(), message=msg)


@router.post("/disable", response_model=ToggleResponse)
async def disable_loop() -> ToggleResponse:
    """Ferma il loop in modo cooperativo. Idempotente."""
    loop = _require_loop()
    stopped = await loop.stop()
    msg = "loop_stopped" if stopped else "was_not_running"
    return ToggleResponse(running=loop.is_running(), message=msg)


@router.get("/activity", response_model=ActivityResponse)
async def get_activity(
    n: int = Query(default=50, ge=1, le=500, description="Numero entry."),
) -> ActivityResponse:
    """Ultime N entry del activity log JSONL."""
    loop = get_active_loop()
    if loop is None:
        return ActivityResponse(entries=[], count=0)
    raw = loop.read_activity_log(n=n)
    parsed: list[ActivityEntry] = []
    for r in raw:
        try:
            parsed.append(ActivityEntry(**r))
        except Exception as e:  # noqa: BLE001 - schema mismatch tollerato
            logger.warning("subconscious.activity.parse_error", error=str(e))
            continue
    return ActivityResponse(entries=parsed, count=len(parsed))


__all__ = ["router", "set_active_loop"]
