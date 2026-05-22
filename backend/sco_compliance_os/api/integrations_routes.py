"""Router /api/integrations — connettori OAuth e ingestione dati esterni.

5 connettori demo nello scaffold iniziale: Gmail, GoogleCalendar, GoogleDrive,
Slack, GitHub. Per ora endpoint stub. La pipeline OAuth + token storage andrà
implementata nelle sessioni successive.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sco_compliance_os.core.logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


IntegrationStatus = Literal["pending", "connected", "error", "disconnected"]


# ----- Schemi -----


class IntegrationInfo(BaseModel):
    """Metadati connettore."""

    slug: str
    name: str
    description: str
    status: IntegrationStatus = "pending"
    icon_slug: str | None = None
    last_sync_at: datetime | None = None


class IntegrationConnectResponse(BaseModel):
    """Response OAuth start."""

    slug: str
    oauth_url: str
    state_token: str
    message: str


class IntegrationDataResponse(BaseModel):
    """Response generic dati fetched dal connettore."""

    slug: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: str | None = None
    fetched_at: datetime


# ----- Catalogo connettori (statico demo) -----

_INTEGRATIONS_CATALOG: dict[str, IntegrationInfo] = {
    "gmail": IntegrationInfo(
        slug="gmail",
        name="Gmail",
        description="Lettura e scrittura email dall'account Google dell'utente.",
        icon_slug="gmail",
    ),
    "google-calendar": IntegrationInfo(
        slug="google-calendar",
        name="Google Calendar",
        description="Gestione eventi e disponibilità calendario.",
        icon_slug="google-calendar",
    ),
    "google-drive": IntegrationInfo(
        slug="google-drive",
        name="Google Drive",
        description="Lettura file e documenti dal Drive personale e condiviso.",
        icon_slug="google-drive",
    ),
    "slack": IntegrationInfo(
        slug="slack",
        name="Slack",
        description="Lettura canali, DM, e messaggistica nei workspace Slack.",
        icon_slug="slack",
    ),
    "github": IntegrationInfo(
        slug="github",
        name="GitHub",
        description="Issue, PR, repo per progetti di codice.",
        icon_slug="github",
    ),
}


# ----- Endpoint -----


@router.get("/available", response_model=list[IntegrationInfo])
async def list_integrations() -> list[IntegrationInfo]:
    """Lista connettori disponibili con loro status corrente."""
    # TODO: leggere stato connessione effettiva da token storage encrypted.
    return list(_INTEGRATIONS_CATALOG.values())


@router.post("/{slug}/connect", response_model=IntegrationConnectResponse)
async def connect_integration(slug: str) -> IntegrationConnectResponse:
    """Avvia flow OAuth per connettore.

    TODO Sessione successiva: implementare OAuth2 PKCE per Google/Slack/GitHub.
    Per ora stub ritorna placeholder URL.
    """
    if slug not in _INTEGRATIONS_CATALOG:
        raise HTTPException(status_code=404, detail=f"Connettore '{slug}' non trovato")
    info = _INTEGRATIONS_CATALOG[slug]
    logger.info("integration.connect.requested", slug=slug)
    return IntegrationConnectResponse(
        slug=slug,
        oauth_url=f"https://stub.example.com/oauth/{slug}/authorize",
        state_token="STUB_STATE_TOKEN",
        message=f"STUB OAuth start per {info.name}. Implementazione pending.",
    )


@router.delete("/{slug}", status_code=204)
async def disconnect_integration(slug: str) -> None:
    """Revoca connessione + cancella token storage encrypted."""
    if slug not in _INTEGRATIONS_CATALOG:
        raise HTTPException(status_code=404, detail=f"Connettore '{slug}' non trovato")
    logger.info("integration.disconnect.requested", slug=slug)
    # TODO: cancella token storage encrypted.


@router.get("/{slug}/data", response_model=IntegrationDataResponse)
async def fetch_integration_data(
    slug: str,
    since: datetime | None = None,
    cursor: str | None = None,
) -> IntegrationDataResponse:
    """Fetch dati incrementale dal connettore.

    TODO: implementare per-slug adapter (gmail.messages.list, drive.files.list, ecc.).
    Per ora stub ritorna lista vuota.
    """
    if slug not in _INTEGRATIONS_CATALOG:
        raise HTTPException(status_code=404, detail=f"Connettore '{slug}' non trovato")
    logger.info("integration.data.requested", slug=slug, since=since, cursor=cursor)
    return IntegrationDataResponse(
        slug=slug,
        items=[],
        next_cursor=None,
        fetched_at=datetime.utcnow(),
    )
