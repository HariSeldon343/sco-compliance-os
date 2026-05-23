"""
base.py — Classe astratta ``BaseConnector`` per il sistema di connettori OAuth.

Il pattern segue lo standard OAuth 2.0 Authorization Code Grant (RFC 6749),
con supporto opzionale a PKCE (RFC 7636) per provider che lo supportano
(Google, GitHub). Ogni connector concreto deve sottoclassare ``BaseConnector``
e implementare i metodi astratti.

Pattern Karpathy "schema is the product": le dataclass tipizzate
(`OAuthTokens`, `MemoryChunk`, `OAuthError`) sono il contratto stabile;
le implementazioni concrete dei connettori sono interscambiabili.

Riferimenti:
    - OAuth 2.0 RFC 6749: https://datatracker.ietf.org/doc/html/rfc6749
    - PKCE RFC 7636: https://datatracker.ietf.org/doc/html/rfc7636
"""

from __future__ import annotations

import abc
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar

# ─────────────────────────────────────────────────────────────────────
# Dataclass tipizzate (il contratto stabile del package)
# ─────────────────────────────────────────────────────────────────────


@dataclass
class OAuthTokens:
    """Token OAuth 2.0 ricevuti dal provider dopo lo scambio code → token.

    SECURITY: questa dataclass vive SOLO nel backend e SOLO transitoriamente
    in memoria. La persistenza è demandata a ``token_store.TokenStore`` che
    cifra i token nel keyring OS. Non serializzare verso il frontend.
    """

    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scopes_granted: list[str]
    token_type: str = "Bearer"
    raw_response: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, leeway_seconds: int = 60) -> bool:
        """Ritorna True se il token è scaduto (con leeway per network jitter)."""
        now = datetime.now(UTC)
        delta = (self.expires_at - now).total_seconds()
        return delta < leeway_seconds


@dataclass
class MemoryChunk:
    """Chunk di dati prodotto da ``fetch_data()`` e destinato al Memory Tree.

    Pattern Conv. 43 (Smart File Injection) + Karpathy three-layer: ogni
    chunk diventa una scheda markdown in ``wiki/sources/`` con frontmatter
    standard B (provenance metadata) e link bidirezionale verso entità.
    """

    external_id: str
    source_connector: str
    kind: str
    title: str
    body: str
    occurred_at: datetime
    ingested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class OAuthError(Exception):
    """Errore tipizzato per fallimenti OAuth (refresh, scambio, revoke).

    Distinto da ``Exception`` generica per permettere catch granulari
    nei layer superiori (API routes, scheduler).
    """

    code: str  # es. "invalid_grant", "expired_token", "network_error"
    message: str
    provider: str
    http_status: int | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.provider}/{self.code}] {self.message}"


# ─────────────────────────────────────────────────────────────────────
# Classe astratta BaseConnector
# ─────────────────────────────────────────────────────────────────────


class BaseConnector(abc.ABC):
    """Contratto comune per tutti i connettori OAuth.

    Ogni sottoclasse concreta deve dichiarare i seguenti class attribute:

    - ``slug``: identificatore univoco kebab-case (es. ``"gmail"``).
    - ``name``: nome human-readable (es. ``"Gmail"``).
    - ``category``: una di ``ConnectorCategory`` (vedi ``types.ts``).
    - ``oauth_provider``: provider OAuth sottostante.
    - ``scopes_required``: lista di scopes richiesti.
    - ``auth_url_template``: URL authorize endpoint del provider.
    - ``token_url``: URL token endpoint del provider.

    Deve poi implementare i metodi astratti:

    - ``start_oauth_flow()``: ritorna l'URL di authorize.
    - ``handle_callback()``: scambia code → token.
    - ``refresh_token_if_needed()``: refresh quando scaduto.
    - ``fetch_data()``: chiama API provider e produce MemoryChunk.
    - ``disconnect()``: revoke token presso il provider.
    """

    # Class attributes da override nei concrete connectors
    slug: ClassVar[str] = ""
    name: ClassVar[str] = ""
    category: ClassVar[str] = ""
    oauth_provider: ClassVar[str] = ""
    scopes_required: ClassVar[list[str]] = []
    auth_url_template: ClassVar[str] = ""
    token_url: ClassVar[str] = ""
    supports_pkce: ClassVar[bool] = False

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        """Inizializza il connector con credenziali OAuth applicative.

        Args:
            client_id: identificatore client OAuth registrato sul provider.
            client_secret: secret applicativo (mai esposto al frontend).
            redirect_uri: URI di callback registrata sul provider (es.
                ``http://localhost:7777/api/integrations/callback``).
        """
        if not self.slug:
            raise NotImplementedError(
                f"{type(self).__name__}: class attribute 'slug' non dichiarato."
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @staticmethod
    def generate_state() -> str:
        """Genera state parameter crittografico per anti-CSRF nel flow OAuth."""
        return secrets.token_urlsafe(32)

    @abc.abstractmethod
    async def start_oauth_flow(self, state: str) -> str:
        """Genera l'URL di authorize da aprire nel browser dell'utente.

        Args:
            state: parametro state anti-CSRF (generato da ``generate_state()``).

        Returns:
            URL completo di authorize endpoint con query string OAuth.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def handle_callback(self, code: str, state: str) -> OAuthTokens:
        """Scambia il code ricevuto in callback per access_token + refresh_token.

        Args:
            code: codice ricevuto dal provider sulla redirect_uri.
            state: state parameter da validare contro quello inviato.

        Returns:
            ``OAuthTokens`` con access_token, refresh_token, expires_at.

        Raises:
            OAuthError: se lo scambio fallisce (code invalido, network, etc.).
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def refresh_token_if_needed(self, tokens: OAuthTokens) -> OAuthTokens:
        """Refresh del token se scaduto, no-op altrimenti.

        Args:
            tokens: token correnti recuperati dal keyring.

        Returns:
            ``OAuthTokens`` aggiornati (stessi oggetti se non scaduti, nuovi se refresh).

        Raises:
            OAuthError: se il refresh fallisce (refresh_token invalido, revoked, etc.).
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_data(
        self,
        tokens: OAuthTokens,
        since: datetime | None = None,
    ) -> list[MemoryChunk]:
        """Chiama API provider e ritorna chunk di dati per il Memory Tree.

        Args:
            tokens: token OAuth validi (eventualmente già refreshati).
            since: timestamp incrementale (fetch solo dati dopo questo).

        Returns:
            Lista di ``MemoryChunk`` pronti per ingestion.

        Raises:
            OAuthError: se la chiamata API fallisce per ragioni OAuth.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def disconnect(self, tokens: OAuthTokens) -> None:
        """Revoke dei token presso il provider (token revocation endpoint).

        Args:
            tokens: token correnti da revocare.

        Raises:
            OAuthError: se la revoke fallisce (network, endpoint non supportato).
        """
        raise NotImplementedError
