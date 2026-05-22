"""
slack_connector.py — Connector OAuth per Slack (OAuth v2).

Provider: Slack (OAuth v2 — distinto da OAuth v1 deprecato)
Scopes (bot scopes):
    - ``channels:read`` — leggere lista canali pubblici workspace
    - ``chat:write`` — postare messaggi come bot (opzionale per Wave 1)
    - ``users:read`` — leggere info utenti workspace
    - ``channels:history`` — leggere messaggi canali (richiesto per fetch_data)

Docs ufficiali (Pattern Conv. 35 RESEARCH-BEFORE-ACT):
    - Slack OAuth v2 installation flow:
      https://api.slack.com/authentication/oauth-v2
    - Slack API conversations.history:
      https://api.slack.com/methods/conversations.history
    - Slack scopes reference:
      https://api.slack.com/scopes

Note: Slack NON supporta PKCE.

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
class SlackConnector(BaseConnector):
    """Connector Slack via OAuth v2."""

    slug = "slack"
    name = "Slack"
    category = "communication"
    oauth_provider = "slack"
    # Wave 1: scopes minimi per discovery + lettura
    scopes_required = [
        "channels:read",
        "channels:history",
        "users:read",
        "chat:write",
    ]
    # docs: https://api.slack.com/authentication/oauth-v2#asking
    auth_url_template = "https://slack.com/oauth/v2/authorize"
    token_url = "https://slack.com/api/oauth.v2.access"
    revoke_url = "https://slack.com/api/auth.revoke"
    supports_pkce = False  # Slack OAuth v2 non supporta PKCE

    async def start_oauth_flow(self, state: str) -> str:
        """Genera authorize URL Slack v2.

        Note: Slack v2 distingue ``scope`` (bot scopes) e ``user_scope``
        (user scopes). Wave 1 usa solo bot scopes.
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": ",".join(self.scopes_required),  # CSV, NON spazi
            "state": state,
        }
        return f"{self.auth_url_template}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str) -> OAuthTokens:
        """STUB. TODO Wave 2 POST a oauth.v2.access.

        Slack response include ``access_token`` (xoxb-...) per bot e
        opzionalmente ``authed_user.access_token`` (xoxp-...) per user.
        """
        logger.warning("slack handle_callback STUB — wave 2 pending")
        now = datetime.now(timezone.utc)
        # Slack bot tokens (xoxb-) NON scadono di default (unless rotation enabled)
        # ma codifichiamo expires_at lontano nel futuro per compatibilità schema.
        return OAuthTokens(
            access_token="xoxb-STUB-SLACK-BOT-TOKEN",
            refresh_token=None,  # Slack v2 default no refresh (rotation opt-in)
            expires_at=now + timedelta(days=365),
            scopes_granted=self.scopes_required,
            raw_response={"stub": True, "team_id": "T_STUB_001"},
        )

    async def refresh_token_if_needed(self, tokens: OAuthTokens) -> OAuthTokens:
        """STUB. Slack v2 default non ha refresh; rotation opt-in.

        docs: https://api.slack.com/authentication/rotation
        """
        if not tokens.is_expired():
            return tokens
        # Se token rotation NON è abilitata sull'app Slack, refresh_token è None
        # e l'utente deve ri-autenticarsi.
        if tokens.refresh_token is None:
            raise OAuthError(
                code="slack_rotation_disabled",
                message=(
                    "Token Slack scaduto e rotation non abilitata. "
                    "Richiesta nuova autorizzazione."
                ),
                provider=self.oauth_provider,
            )
        logger.warning("slack refresh STUB — wave 2 pending")
        now = datetime.now(timezone.utc)
        return OAuthTokens(
            access_token="xoxb-STUB-REFRESHED",
            refresh_token=tokens.refresh_token,
            expires_at=now + timedelta(hours=12),
            scopes_granted=tokens.scopes_granted,
        )

    async def fetch_data(
        self, tokens: OAuthTokens, since: datetime | None = None
    ) -> list[MemoryChunk]:
        """Fetch messaggi recenti dai canali "watched" dell'utente.

        TODO Wave 2:
            1. GET /conversations.list (channels:read) — filter is_member=true
               o lista whitelist configurata dall'utente.
            2. Per ogni canale: GET /conversations.history?oldest={since_ts}
            3. Parsing: msg.text, msg.user, msg.ts, msg.thread_ts.
            4. Risoluzione user_id → nome via /users.info (cache locale).
        """
        logger.warning("slack fetch_data STUB — wave 2 pending")
        now = datetime.now(timezone.utc)
        return [
            MemoryChunk(
                external_id="slack_msg_stub_001",
                source_connector=self.slug,
                kind="message",
                title="[STUB] Channel #compliance — message",
                body="Stub Slack message body for Wave 1 demo.",
                occurred_at=now - timedelta(minutes=30),
                metadata={
                    "channel_id": "C_STUB_001",
                    "channel_name": "compliance",
                    "user_id": "U_STUB_001",
                    "user_name": "antonio",
                },
                tags=["stub", "wave-1-demo", "slack"],
            ),
        ]

    async def disconnect(self, tokens: OAuthTokens) -> None:
        """STUB. TODO Wave 2 POST a auth.revoke.

        docs: https://api.slack.com/methods/auth.revoke
        """
        logger.warning("slack disconnect STUB — wave 2 pending")
        return None
