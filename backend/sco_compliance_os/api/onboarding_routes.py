"""Router /api/onboarding — stato EULA / Privacy / Demo / Tutorial.

Pattern Conv. 47 SINGLE SOURCE OF TRUTH BACKEND per version costanti:
le current_eula_version / current_privacy_version / current_demo_version vivono
QUI nel backend, il frontend NON le hardcoda — le legge dal /status endpoint.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


# ----- Costanti version (SINGLE SOURCE OF TRUTH, Conv. 47 enforcement) -----

CURRENT_EULA_VERSION = "1.0"
CURRENT_PRIVACY_VERSION = "1.0"
CURRENT_DEMO_VERSION = "1.0"


# ----- Schemi Pydantic -----


class OnboardingStatus(BaseModel):
    """Stato corrente onboarding utente."""

    eula_accepted: bool = False
    eula_accepted_version: str | None = None
    eula_accepted_at: datetime | None = None

    privacy_accepted: bool = False
    privacy_accepted_version: str | None = None
    privacy_accepted_at: datetime | None = None

    demo_seen: bool = False
    demo_seen_version: str | None = None
    demo_seen_at: datetime | None = None

    tutorial_done: bool = False
    tutorial_done_at: datetime | None = None

    # Version correnti (Conv. 47 — frontend LE LEGGE da qui, non le hardcoda)
    current_eula_version: str = Field(default=CURRENT_EULA_VERSION)
    current_privacy_version: str = Field(default=CURRENT_PRIVACY_VERSION)
    current_demo_version: str = Field(default=CURRENT_DEMO_VERSION)


class AcceptRequest(BaseModel):
    """Richiesta accept generica (eula/privacy/demo)."""

    version: str = Field(..., description="Version del documento accettato.")


# ----- Helper persistenza -----


def _load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("onboarding.load_failed", error=str(exc))
        return {}


def _save_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_status_from_state(state: dict[str, Any]) -> OnboardingStatus:
    """Costruisce OnboardingStatus da JSON state file."""

    def _parse_dt(value: Any) -> datetime | None:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    return OnboardingStatus(
        eula_accepted=bool(state.get("eula_accepted", False)),
        eula_accepted_version=state.get("eula_accepted_version"),
        eula_accepted_at=_parse_dt(state.get("eula_accepted_at")),
        privacy_accepted=bool(state.get("privacy_accepted", False)),
        privacy_accepted_version=state.get("privacy_accepted_version"),
        privacy_accepted_at=_parse_dt(state.get("privacy_accepted_at")),
        demo_seen=bool(state.get("demo_seen", False)),
        demo_seen_version=state.get("demo_seen_version"),
        demo_seen_at=_parse_dt(state.get("demo_seen_at")),
        tutorial_done=bool(state.get("tutorial_done", False)),
        tutorial_done_at=_parse_dt(state.get("tutorial_done_at")),
    )


# ----- Endpoint -----


@router.get("/status", response_model=OnboardingStatus)
async def get_status(settings: Settings = Depends(get_settings)) -> OnboardingStatus:
    """Stato corrente onboarding + version correnti backend."""
    settings.ensure_data_dir()
    state = _load_state(settings.onboarding_state_path)
    return _build_status_from_state(state)


@router.post("/eula/accept", response_model=OnboardingStatus)
async def accept_eula(
    payload: AcceptRequest, settings: Settings = Depends(get_settings)
) -> OnboardingStatus:
    """Marca EULA come accettato con version."""
    state = _load_state(settings.onboarding_state_path)
    state["eula_accepted"] = True
    state["eula_accepted_version"] = payload.version
    state["eula_accepted_at"] = datetime.utcnow().isoformat()
    _save_state(settings.onboarding_state_path, state)
    logger.info("onboarding.eula.accepted", version=payload.version)
    return _build_status_from_state(state)


@router.post("/privacy/accept", response_model=OnboardingStatus)
async def accept_privacy(
    payload: AcceptRequest, settings: Settings = Depends(get_settings)
) -> OnboardingStatus:
    """Marca Privacy come accettata con version."""
    state = _load_state(settings.onboarding_state_path)
    state["privacy_accepted"] = True
    state["privacy_accepted_version"] = payload.version
    state["privacy_accepted_at"] = datetime.utcnow().isoformat()
    _save_state(settings.onboarding_state_path, state)
    logger.info("onboarding.privacy.accepted", version=payload.version)
    return _build_status_from_state(state)


@router.post("/demo/seen", response_model=OnboardingStatus)
async def mark_demo_seen(
    payload: AcceptRequest, settings: Settings = Depends(get_settings)
) -> OnboardingStatus:
    """Marca demo come vista con version."""
    state = _load_state(settings.onboarding_state_path)
    state["demo_seen"] = True
    state["demo_seen_version"] = payload.version
    state["demo_seen_at"] = datetime.utcnow().isoformat()
    _save_state(settings.onboarding_state_path, state)
    logger.info("onboarding.demo.seen", version=payload.version)
    return _build_status_from_state(state)


@router.post("/tutorial/done", response_model=OnboardingStatus)
async def mark_tutorial_done(
    settings: Settings = Depends(get_settings),
) -> OnboardingStatus:
    """Marca tutorial come completato."""
    state = _load_state(settings.onboarding_state_path)
    state["tutorial_done"] = True
    state["tutorial_done_at"] = datetime.utcnow().isoformat()
    _save_state(settings.onboarding_state_path, state)
    logger.info("onboarding.tutorial.done")
    return _build_status_from_state(state)
