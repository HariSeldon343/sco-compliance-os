"""Router /api/autofetch — orchestratore auto-fetch loop connettori 20 min.

Endpoint (simmetrici al subconscious_routes Wave 1):

- ``GET  /api/autofetch/status``    -> JSON snapshot stato loop + connectors RR.
- ``POST /api/autofetch/tick``      -> manual trigger sync (attende completion).
- ``POST /api/autofetch/enable``    -> avvia loop (idempotente).
- ``POST /api/autofetch/disable``   -> ferma loop (idempotente, cooperativo).
- ``GET  /api/autofetch/activity``  -> ultime N entry da autofetch_activity.jsonl.

Pattern privacy v0.3.0: auto-fetch OFF di default (blueprint Sezione 7
mitigazione "OAuth token leak via logs"). L'utente deve abilitare via
``settings.auto_fetch_enabled = True`` (in env / config) E chiamare
``POST /api/autofetch/enable``. Il flag enabled e' uno switch logico
durante il runtime, ortogonale al setting persistente.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.integrations.auto_fetch_loop import (
    AutoFetchLoop,
    get_active_loop,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/autofetch", tags=["autofetch"])


# ----- Schemi Pydantic ---------------------------------------------------------------


class ConnectorRRState(BaseModel):
    """Stato per-connector nel round-robin."""

    name: str
    last_fetch_ts: str | None = None
    consecutive_failures: int = 0
    cooldown_until: str | None = None
    fetched_total: int = 0
    last_outcome: str | None = None


class AutoFetchStatus(BaseModel):
    """Snapshot stato corrente del loop auto-fetch."""

    enabled: bool = Field(..., description="Flag setting persistente (config).")
    running: bool
    interval_seconds: int
    interval_seconds_effective: int
    is_throttle_busy: bool
    last_tick_started_at: str | None
    last_tick_completed_at: str | None
    last_tick_connector: str | None
    last_tick_fetched_count: int
    last_tick_errors: list[str]
    total_ticks: int
    rr_cursor: int
    connectors: list[str]
    connectors_round_robin_state: dict[str, ConnectorRRState]
    user_id: str | None = None
    failure_threshold: int
    cooldown_seconds: int


class TickResponse(BaseModel):
    """Esito di un manual tick auto-fetch."""

    connector_name: str
    fetched_count: int
    errors: list[str] = Field(default_factory=list)
    used_oauth: bool
    duration_seconds: float
    cancelled: bool


class ToggleResponse(BaseModel):
    """Esito enable/disable."""

    running: bool
    message: str


class ActivityEntry(BaseModel):
    """Entry del activity log JSONL auto-fetch."""

    ts: str
    connector_name: str
    fetched_count: int
    errors: list[str] = Field(default_factory=list)
    used_oauth: bool
    duration_seconds: float
    manual: bool
    cancelled: bool


class ActivityResponse(BaseModel):
    """Response /activity."""

    entries: list[ActivityEntry] = Field(default_factory=list)
    count: int = 0


# ----- Helpers -----------------------------------------------------------------------


def _require_loop() -> AutoFetchLoop:
    """Ritorna il loop attivo o 503 se non inizializzato dal lifespan."""
    loop = get_active_loop()
    if loop is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "AutoFetch loop not initialized. Set auto_fetch_enabled=true "
                "in config and restart the backend, or wait for first lifespan."
            ),
        )
    return loop


def _coerce_status_payload(snap: dict[str, Any]) -> dict[str, Any]:
    """Coerce raw dict snapshot in payload Pydantic-friendly per AutoFetchStatus.

    Il loop ritorna ``connectors_round_robin_state`` come ``dict[str, dict]``
    annidato; Pydantic vuole ``dict[str, ConnectorRRState]``. Il coerce qui
    e' tollerante a key mancanti (failsafe: connector con dict vuoto vs full).
    """
    raw_rr = snap.get("connectors_round_robin_state", {})
    if not isinstance(raw_rr, dict):
        raw_rr = {}
    return {**snap, "connectors_round_robin_state": raw_rr}


# ----- Endpoint ----------------------------------------------------------------------


@router.get("/status", response_model=AutoFetchStatus)
async def get_status() -> AutoFetchStatus:
    """Snapshot stato corrente del loop auto-fetch."""
    from sco_compliance_os.config import get_settings

    settings = get_settings()
    loop = get_active_loop()
    if loop is None:
        # Stato pre-init: ritorna defaults coerenti (loop ancora non costruito).
        return AutoFetchStatus(
            enabled=settings.auto_fetch_enabled,
            running=False,
            interval_seconds=settings.auto_fetch_interval_seconds,
            interval_seconds_effective=settings.auto_fetch_interval_seconds,
            is_throttle_busy=False,
            last_tick_started_at=None,
            last_tick_completed_at=None,
            last_tick_connector=None,
            last_tick_fetched_count=0,
            last_tick_errors=[],
            total_ticks=0,
            rr_cursor=0,
            connectors=[],
            connectors_round_robin_state={},
            user_id=None,
            failure_threshold=3,
            cooldown_seconds=3600,
        )
    snap = _coerce_status_payload(loop.get_status())
    return AutoFetchStatus(enabled=settings.auto_fetch_enabled, **snap)


@router.post("/tick", response_model=TickResponse)
async def manual_tick() -> TickResponse:
    """Esegue un tick manuale sincrono (attende completion).

    Ritorna l'outcome del connector pickato in round-robin.
    """
    loop = _require_loop()
    outcome = await loop.run_tick_now()
    return TickResponse(
        connector_name=outcome.connector_name,
        fetched_count=outcome.fetched_count,
        errors=list(outcome.errors),
        used_oauth=outcome.used_oauth,
        duration_seconds=outcome.duration_seconds,
        cancelled=outcome.cancelled,
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
    """Ultime N entry del activity log JSONL auto-fetch."""
    loop = get_active_loop()
    if loop is None:
        return ActivityResponse(entries=[], count=0)
    raw = loop.read_activity_log(n=n)
    parsed: list[ActivityEntry] = []
    for r in raw:
        try:
            parsed.append(ActivityEntry(**r))
        except Exception as e:
            logger.warning("autofetch.activity.parse_error", error=str(e))
            continue
    return ActivityResponse(entries=parsed, count=len(parsed))


__all__ = ["router"]
