"""
gmail_connector.py — Connector OAuth per Gmail (read-only).

Provider: Google (OAuth 2.0)
Scopes: ``https://www.googleapis.com/auth/gmail.readonly``

Docs ufficiali (Pattern Conv. 35 RESEARCH-BEFORE-ACT):
    - Google OAuth 2.0 web server flow:
      https://developers.google.com/identity/protocols/oauth2/web-server
    - Gmail API users.messages.list:
      https://developers.google.com/gmail/api/reference/rest/v1/users.messages/list
    - Gmail API users.messages.get:
      https://developers.google.com/gmail/api/reference/rest/v1/users.messages/get
    - Token revoke:
      https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke

Wave 1 status: STUB. ``fetch_data()`` ritorna MemoryChunk mock di esempio.
Implementazione reale (HTTP client + paginazione + parsing MIME) è TODO
Wave 2.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from .base import BaseConnector, MemoryChunk, OAuthError, OAuthTokens
from .registry import connector

logger = logging.getLogger(__name__)


@connector
class GmailConnector(BaseConnector):
    """Connector Gmail read-only via Google OAuth 2.0."""

    slug = "gmail"
    name = "Gmail"
    category = "email"
    oauth_provider = "google"
    scopes_required = ["https://www.googleapis.com/auth/gmail.readonly"]
    # docs: https://developers.google.com/identity/protocols/oauth2/web-server#creatingclient
    auth_url_template = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    revoke_url = "https://oauth2.googleapis.com/revoke"
    supports_pkce = True

    async def start_oauth_flow(self, state: str) -> str:
        """Genera URL di authorize Google con scopes Gmail readonly.

        Note: Google richiede ``access_type=offline`` + ``prompt=consent``
        per ottenere un refresh_token sul primo grant.
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes_required),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }
        return f"{self.auth_url_template}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str) -> OAuthTokens:
        """Scambia code per token via Google token endpoint.

        TODO Wave 2: chiamata HTTP reale via ``httpx.AsyncClient``.
        Per ora STUB che simula token reali con expires_at = now + 1h.
        """
        # TODO: httpx.AsyncClient.post(self.token_url, data={...})
        logger.warning("gmail handle_callback STUB — wave 2 implementation pending")
        now = datetime.now(UTC)
        return OAuthTokens(
            access_token="STUB_ACCESS_TOKEN_GMAIL",
            refresh_token="STUB_REFRESH_TOKEN_GMAIL",
            expires_at=now + timedelta(hours=1),
            scopes_granted=self.scopes_required,
            token_type="Bearer",
            raw_response={"stub": True, "code_received": code[:8] + "..."},
        )

    async def refresh_token_if_needed(self, tokens: OAuthTokens) -> OAuthTokens:
        """Refresh tramite Google refresh_token grant.

        docs: https://developers.google.com/identity/protocols/oauth2/web-server#offline
        """
        if not tokens.is_expired():
            return tokens
        if tokens.refresh_token is None:
            raise OAuthError(
                code="missing_refresh_token",
                message="Refresh token assente; richiesta nuova autorizzazione.",
                provider=self.oauth_provider,
            )
        # TODO Wave 2: chiamata reale a token_url con grant_type=refresh_token
        logger.warning("gmail refresh_token STUB — wave 2 implementation pending")
        now = datetime.now(UTC)
        return OAuthTokens(
            access_token="STUB_ACCESS_TOKEN_GMAIL_REFRESHED",
            refresh_token=tokens.refresh_token,
            expires_at=now + timedelta(hours=1),
            scopes_granted=tokens.scopes_granted,
            token_type="Bearer",
            raw_response={"stub": True, "refreshed": True},
        )

    async def fetch_data(
        self, tokens: OAuthTokens, since: datetime | None = None
    ) -> list[MemoryChunk]:
        """Fetch ultime N email come MemoryChunk.

        TODO Wave 2:
            1. GET https://gmail.googleapis.com/gmail/v1/users/me/messages?q=after:{since}
            2. Paginazione via pageToken.
            3. Per ogni msg_id: GET .../messages/{id} con format=metadata o full.
            4. Parsing payload MIME (headers Subject/From/Date + snippet/body).
        """
        logger.warning("gmail fetch_data STUB — wave 2 implementation pending")
        now = datetime.now(UTC)
        # MOCK: 2 chunk di esempio per dimostrare la shape
        return [
            MemoryChunk(
                external_id="gmail_msg_stub_001",
                source_connector=self.slug,
                kind="email",
                title="[STUB] Welcome to SCO Compliance OS",
                body="Stub email body for Wave 1 scaffolding demo.",
                occurred_at=now - timedelta(hours=2),
                metadata={
                    "from": "noreply@example.com",
                    "to": "user@example.com",
                    "thread_id": "stub_thread_001",
                },
                tags=["stub", "wave-1-demo"],
            ),
            MemoryChunk(
                external_id="gmail_msg_stub_002",
                source_connector=self.slug,
                kind="email",
                title="[STUB] Audit report attached",
                body="Stub email with attachment reference.",
                occurred_at=now - timedelta(hours=5),
                metadata={
                    "from": "audit@example.com",
                    "has_attachments": True,
                },
                tags=["stub", "wave-1-demo"],
            ),
        ]

    async def disconnect(self, tokens: OAuthTokens) -> None:
        """Revoke tramite Google revoke endpoint.

        docs: https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke
        Endpoint: POST https://oauth2.googleapis.com/revoke?token={token}
        """
        # TODO Wave 2: httpx POST a revoke_url con token=tokens.access_token
        logger.warning("gmail disconnect STUB — wave 2 implementation pending")
        return None
