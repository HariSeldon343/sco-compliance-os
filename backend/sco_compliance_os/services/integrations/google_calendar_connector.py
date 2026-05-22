"""
google_calendar_connector.py — Connector OAuth per Google Calendar (read-only).

Provider: Google (OAuth 2.0)
Scopes: ``https://www.googleapis.com/auth/calendar.readonly``

Docs ufficiali (Pattern Conv. 35 RESEARCH-BEFORE-ACT):
    - Google Calendar API events.list:
      https://developers.google.com/calendar/api/v3/reference/events/list
    - Google OAuth 2.0 web server flow (stesso di Gmail):
      https://developers.google.com/identity/protocols/oauth2/web-server

Wave 1 status: STUB.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from .base import BaseConnector, MemoryChunk, OAuthError, OAuthTokens
from .registry import connector

logger = logging.getLogger(__name__)


@connector
class GoogleCalendarConnector(BaseConnector):
    """Connector Google Calendar read-only via OAuth 2.0."""

    slug = "google_calendar"
    name = "Google Calendar"
    category = "calendar"
    oauth_provider = "google"
    scopes_required = ["https://www.googleapis.com/auth/calendar.readonly"]
    auth_url_template = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    revoke_url = "https://oauth2.googleapis.com/revoke"
    supports_pkce = True

    async def start_oauth_flow(self, state: str) -> str:
        """Genera authorize URL Google con scope calendar.readonly."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes_required),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.auth_url_template}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str) -> OAuthTokens:
        """STUB scambio code→token. TODO Wave 2 httpx reale."""
        logger.warning(
            "google_calendar handle_callback STUB — wave 2 implementation pending"
        )
        now = datetime.now(timezone.utc)
        return OAuthTokens(
            access_token="STUB_ACCESS_TOKEN_GCAL",
            refresh_token="STUB_REFRESH_TOKEN_GCAL",
            expires_at=now + timedelta(hours=1),
            scopes_granted=self.scopes_required,
            raw_response={"stub": True, "code_received": code[:8] + "..."},
        )

    async def refresh_token_if_needed(self, tokens: OAuthTokens) -> OAuthTokens:
        """STUB refresh. TODO Wave 2."""
        if not tokens.is_expired():
            return tokens
        if tokens.refresh_token is None:
            raise OAuthError(
                code="missing_refresh_token",
                message="Refresh token assente.",
                provider=self.oauth_provider,
            )
        logger.warning("google_calendar refresh STUB — wave 2 pending")
        now = datetime.now(timezone.utc)
        return OAuthTokens(
            access_token="STUB_ACCESS_TOKEN_GCAL_REFRESHED",
            refresh_token=tokens.refresh_token,
            expires_at=now + timedelta(hours=1),
            scopes_granted=tokens.scopes_granted,
        )

    async def fetch_data(
        self, tokens: OAuthTokens, since: datetime | None = None
    ) -> list[MemoryChunk]:
        """Fetch eventi prossimi 7 giorni come MemoryChunk.

        TODO Wave 2:
            1. GET /calendar/v3/calendars/primary/events
            2. Query params: timeMin (now), timeMax (now+7d), singleEvents=true,
               orderBy=startTime
            3. Parsing: event.summary, event.start.dateTime, event.location,
               event.description, event.attendees[].email.
        """
        logger.warning("google_calendar fetch_data STUB — wave 2 implementation pending")
        now = datetime.now(timezone.utc)
        return [
            MemoryChunk(
                external_id="gcal_event_stub_001",
                source_connector=self.slug,
                kind="calendar_event",
                title="[STUB] Audit kickoff meeting — Don Calabria",
                body="Stub event for Wave 1 scaffolding demo.",
                occurred_at=now + timedelta(days=2, hours=10),
                metadata={
                    "location": "Negrar (VR)",
                    "attendees": ["antonio@sco.it", "audit-lead@example.com"],
                    "duration_minutes": 90,
                },
                tags=["stub", "wave-1-demo", "audit"],
            ),
        ]

    async def disconnect(self, tokens: OAuthTokens) -> None:
        """STUB revoke. TODO Wave 2."""
        logger.warning("google_calendar disconnect STUB — wave 2 pending")
        return None
