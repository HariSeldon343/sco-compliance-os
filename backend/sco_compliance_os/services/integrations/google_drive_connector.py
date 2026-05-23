"""
google_drive_connector.py — Connector OAuth per Google Drive.

Provider: Google (OAuth 2.0)
Scopes:
    - ``https://www.googleapis.com/auth/drive.readonly`` (lettura completa)
    - ``https://www.googleapis.com/auth/drive.file`` (file creati dall'app)

Docs ufficiali (Pattern Conv. 35 RESEARCH-BEFORE-ACT):
    - Google Drive API files.list:
      https://developers.google.com/drive/api/v3/reference/files/list
    - Scopes reference:
      https://developers.google.com/identity/protocols/oauth2/scopes#drive

Wave 1 status: STUB.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from .base import BaseConnector, MemoryChunk, OAuthError, OAuthTokens
from .registry import connector

logger = logging.getLogger(__name__)


@connector
class GoogleDriveConnector(BaseConnector):
    """Connector Google Drive read + file-scoped via OAuth 2.0."""

    slug = "google_drive"
    name = "Google Drive"
    category = "storage"
    oauth_provider = "google"
    scopes_required = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
    ]
    auth_url_template = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    revoke_url = "https://oauth2.googleapis.com/revoke"
    supports_pkce = True

    async def start_oauth_flow(self, state: str) -> str:
        """Genera authorize URL Google con scopes Drive."""
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
        """STUB. TODO Wave 2."""
        logger.warning("google_drive handle_callback STUB — wave 2 pending")
        now = datetime.now(UTC)
        return OAuthTokens(
            access_token="STUB_ACCESS_TOKEN_GDRIVE",
            refresh_token="STUB_REFRESH_TOKEN_GDRIVE",
            expires_at=now + timedelta(hours=1),
            scopes_granted=self.scopes_required,
            raw_response={"stub": True},
        )

    async def refresh_token_if_needed(self, tokens: OAuthTokens) -> OAuthTokens:
        """STUB refresh."""
        if not tokens.is_expired():
            return tokens
        if tokens.refresh_token is None:
            raise OAuthError(
                code="missing_refresh_token",
                message="Refresh token assente.",
                provider=self.oauth_provider,
            )
        logger.warning("google_drive refresh STUB — wave 2 pending")
        now = datetime.now(UTC)
        return OAuthTokens(
            access_token="STUB_ACCESS_TOKEN_GDRIVE_REFRESHED",
            refresh_token=tokens.refresh_token,
            expires_at=now + timedelta(hours=1),
            scopes_granted=tokens.scopes_granted,
        )

    async def fetch_data(
        self, tokens: OAuthTokens, since: datetime | None = None
    ) -> list[MemoryChunk]:
        """Fetch file recenti come MemoryChunk.

        TODO Wave 2:
            1. GET /drive/v3/files?orderBy=modifiedTime%20desc&pageSize=50
            2. Filter by modifiedTime > since (se since non None).
            3. Parsing: file.id, file.name, file.mimeType, file.modifiedTime,
               file.owners[].emailAddress, file.webViewLink.
            4. Per file docx/pdf/xlsx: opzionale download + extraction testo
               (rispetta privacy: solo se utente abilita esplicitamente).
        """
        logger.warning("google_drive fetch_data STUB — wave 2 pending")
        now = datetime.now(UTC)
        return [
            MemoryChunk(
                external_id="gdrive_file_stub_001",
                source_connector=self.slug,
                kind="file",
                title="[STUB] Manuale SGSI v2.3.docx",
                body="Stub file metadata for Wave 1 scaffolding demo.",
                occurred_at=now - timedelta(hours=12),
                metadata={
                    "mime_type": (
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    ),
                    "size_bytes": 245_678,
                    "owner": "user@example.com",
                    "web_view_link": "https://drive.google.com/file/d/stub",
                },
                tags=["stub", "wave-1-demo", "docx"],
            ),
        ]

    async def disconnect(self, tokens: OAuthTokens) -> None:
        """STUB revoke."""
        logger.warning("google_drive disconnect STUB — wave 2 pending")
        return None
