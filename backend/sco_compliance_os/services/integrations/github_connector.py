"""
github_connector.py — Connector OAuth per GitHub.

Provider: GitHub (OAuth Apps — NON GitHub Apps; valutazione GitHub Apps
per Wave 2+)
Scopes:
    - ``repo`` — accesso completo a repository pubblici e privati
    - ``user`` — accesso al profilo utente

Docs ufficiali (Pattern Conv. 35 RESEARCH-BEFORE-ACT):
    - GitHub OAuth Apps authorization flow:
      https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
    - GitHub REST API search/issues:
      https://docs.github.com/en/rest/search/search#search-issues-and-pull-requests
    - GitHub scopes:
      https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps

Note: GitHub OAuth Apps supportano PKCE dal 2024.

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
class GitHubConnector(BaseConnector):
    """Connector GitHub via OAuth Apps."""

    slug = "github"
    name = "GitHub"
    category = "code"
    oauth_provider = "github"
    scopes_required = ["repo", "user"]
    # docs: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#1-request-a-users-github-identity
    auth_url_template = "https://github.com/login/oauth/authorize"
    token_url = "https://github.com/login/oauth/access_token"
    # GitHub OAuth Apps: no explicit revoke endpoint via OAuth;
    # revoke avviene via DELETE /applications/{client_id}/grant
    # docs: https://docs.github.com/en/rest/apps/oauth-applications#delete-an-app-authorization
    revoke_url = "https://api.github.com/applications/{client_id}/grant"
    supports_pkce = True

    async def start_oauth_flow(self, state: str) -> str:
        """Genera authorize URL GitHub."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes_required),
            "state": state,
            "allow_signup": "false",
        }
        return f"{self.auth_url_template}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str) -> OAuthTokens:
        """STUB. TODO Wave 2 POST a token_url con Accept: application/json.

        GitHub default risponde con ``application/x-www-form-urlencoded``;
        bisogna forzare ``Accept: application/json`` per JSON response.
        """
        logger.warning("github handle_callback STUB — wave 2 pending")
        now = datetime.now(UTC)
        # GitHub OAuth tokens NON scadono di default (a meno di expirations
        # abilitate). Codifichiamo expires_at lontano nel futuro.
        return OAuthTokens(
            access_token="gho_STUB_GITHUB_TOKEN",
            refresh_token=None,  # solo se "Expiring user authorization tokens" enabled
            expires_at=now + timedelta(days=365),
            scopes_granted=self.scopes_required,
            raw_response={"stub": True},
        )

    async def refresh_token_if_needed(self, tokens: OAuthTokens) -> OAuthTokens:
        """STUB. GitHub default no expiration; opt-in supportato.

        docs: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/refreshing-user-access-tokens
        """
        if not tokens.is_expired():
            return tokens
        if tokens.refresh_token is None:
            raise OAuthError(
                code="github_no_expiration_or_revoked",
                message=(
                    "Token GitHub non rinnovabile. Verifica config 'Expiring "
                    "user tokens' su GitHub App o richiedi nuova autorizzazione."
                ),
                provider=self.oauth_provider,
            )
        logger.warning("github refresh STUB — wave 2 pending")
        now = datetime.now(UTC)
        return OAuthTokens(
            access_token="gho_STUB_REFRESHED",
            refresh_token=tokens.refresh_token,
            expires_at=now + timedelta(hours=8),
            scopes_granted=tokens.scopes_granted,
        )

    async def fetch_data(
        self, tokens: OAuthTokens, since: datetime | None = None
    ) -> list[MemoryChunk]:
        """Fetch PR e issue recenti dell'utente come MemoryChunk.

        TODO Wave 2:
            1. GET /search/issues?q=author:@me+updated:>{since}+type:pr
            2. GET /search/issues?q=author:@me+updated:>{since}+type:issue
            3. Parsing: item.title, item.body, item.html_url, item.repository_url,
               item.state, item.created_at, item.updated_at.
            4. Header rate limit handling: X-RateLimit-Remaining; backoff on 403.
        """
        logger.warning("github fetch_data STUB — wave 2 pending")
        now = datetime.now(UTC)
        return [
            MemoryChunk(
                external_id="gh_pr_stub_001",
                source_connector=self.slug,
                kind="pull_request",
                title="[STUB] feat(integrations): wave 1 scaffolding",
                body="Stub PR body for Wave 1 scaffolding demo.",
                occurred_at=now - timedelta(hours=1),
                metadata={
                    "repo": "sco-compliance-os/sco-compliance-os",
                    "pr_number": 42,
                    "state": "open",
                    "url": "https://github.com/stub/pr/42",
                },
                tags=["stub", "wave-1-demo", "github", "pr"],
            ),
            MemoryChunk(
                external_id="gh_issue_stub_001",
                source_connector=self.slug,
                kind="issue",
                title="[STUB] Bug: token refresh fails on edge case",
                body="Stub issue body.",
                occurred_at=now - timedelta(hours=6),
                metadata={
                    "repo": "sco-compliance-os/sco-compliance-os",
                    "issue_number": 101,
                    "state": "open",
                    "labels": ["bug", "wave-2"],
                },
                tags=["stub", "wave-1-demo", "github", "issue"],
            ),
        ]

    async def disconnect(self, tokens: OAuthTokens) -> None:
        """STUB. TODO Wave 2: DELETE su /applications/{client_id}/grant.

        Richiede Basic Auth con client_id + client_secret (NON il token utente).
        """
        logger.warning("github disconnect STUB — wave 2 pending")
        return None
