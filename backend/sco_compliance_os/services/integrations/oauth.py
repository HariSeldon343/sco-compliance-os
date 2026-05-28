"""
oauth.py — Helper unificati OAuth 2.0 per provider Google (Gmail/GCal/GDrive).

Implementa il flow Authorization Code Grant (RFC 6749) end-to-end:

1. ``start_oauth_flow()`` → ritorna l'auth_url da aprire nel browser dell'utente
   per consentire scope OAuth specifici al provider.
2. ``complete_oauth_flow()`` → scambia il ``code`` ricevuto in callback per
   ``access_token`` + ``refresh_token`` via token endpoint Google.
3. ``refresh_token()`` → rinnova un access_token scaduto usando il refresh_token
   persistito nel keyring OS.
4. ``store_oauth_credentials()`` / ``get_oauth_credentials()`` → wrapper sopra
   ``token_store`` per persistere i token cifrati nel keyring OS, con chiave
   composta ``sco-compliance-os/{provider}/{tenant_id}``.

Pattern di sicurezza (Conv. 35 RESEARCH-BEFORE-ACT):
    - Token OAuth MAI salvati plaintext su disk o DB SQLite (sono nel keyring OS).
    - Client secret OAuth applicativo letto da ``~/.sco-compliance-os/oauth-config.json``
      che l'utente popola manualmente (non committed nel repo).
    - State parameter crittografico anti-CSRF generato ad ogni nuovo flow.
    - Endpoint Google referenziati dalla documentazione ufficiale, mai inventati.

Docs di riferimento:
    - https://developers.google.com/identity/protocols/oauth2/web-server
    - https://developers.google.com/identity/protocols/oauth2/scopes
    - https://datatracker.ietf.org/doc/html/rfc6749 (OAuth 2.0)

Pattern SCO "single source of truth":
    - Una sola pipeline di flow OAuth condivisa per i 3 provider Google.
    - I provider declinano solo gli scope + auth_url specifici.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from .base import OAuthError, OAuthTokens
from .token_store import (
    SERVICE_NAME_PREFIX,
)
from .token_store import (
    delete_tokens as _delete_tokens_kr,
)
from .token_store import (
    get_tokens as _get_tokens_kr,
)
from .token_store import (
    store_tokens as _store_tokens_kr,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Catalogo provider OAuth supportati
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProviderConfig:
    """Configurazione di un provider OAuth (endpoint + scope minimi).

    Pattern SCO "schema is the product": tutti i parametri di un provider
    sono qui, in modo che cambi futuri (es. revoca scope, rotazione endpoint)
    richiedano un solo punto di modifica.
    """

    slug: str
    name: str
    oauth_provider: str  # "google", "microsoft", ecc.
    auth_url: str
    token_url: str
    revoke_url: str
    userinfo_url: str
    scopes: list[str]
    extra_authorize_params: dict[str, str] = field(default_factory=dict)


# Endpoint Google OAuth — fonte: https://accounts.google.com/.well-known/openid-configuration
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
_GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# Scope minimi per provider (principle of least privilege).
# Aggiungiamo openid+email+profile per ricevere user.email nel callback,
# senza dover fare una request aggiuntiva a userinfo (ID token Google).
_OPENID_BASE_SCOPES = ["openid", "email", "profile"]

PROVIDERS: dict[str, ProviderConfig] = {
    "gmail": ProviderConfig(
        slug="gmail",
        name="Gmail",
        oauth_provider="google",
        auth_url=_GOOGLE_AUTH_URL,
        token_url=_GOOGLE_TOKEN_URL,
        revoke_url=_GOOGLE_REVOKE_URL,
        userinfo_url=_GOOGLE_USERINFO_URL,
        # Read-only: GET /messages, GET /messages/{id}. Per send_message servirà
        # https://www.googleapis.com/auth/gmail.send (incremental authorization).
        scopes=[
            *_OPENID_BASE_SCOPES,
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
        extra_authorize_params={
            "access_type": "offline",  # richiesto per refresh_token
            "prompt": "consent",  # forza emissione refresh_token sul primo grant
            "include_granted_scopes": "true",
        },
    ),
    "google-calendar": ProviderConfig(
        slug="google-calendar",
        name="Google Calendar",
        oauth_provider="google",
        auth_url=_GOOGLE_AUTH_URL,
        token_url=_GOOGLE_TOKEN_URL,
        revoke_url=_GOOGLE_REVOKE_URL,
        userinfo_url=_GOOGLE_USERINFO_URL,
        # Read-only su events. Per create_event servirà
        # https://www.googleapis.com/auth/calendar.events (incremental authz).
        scopes=[
            *_OPENID_BASE_SCOPES,
            "https://www.googleapis.com/auth/calendar.events.readonly",
        ],
        extra_authorize_params={
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        },
    ),
    "google-drive": ProviderConfig(
        slug="google-drive",
        name="Google Drive",
        oauth_provider="google",
        auth_url=_GOOGLE_AUTH_URL,
        token_url=_GOOGLE_TOKEN_URL,
        revoke_url=_GOOGLE_REVOKE_URL,
        userinfo_url=_GOOGLE_USERINFO_URL,
        # Read-only su tutto il drive utente. Per upload servirà
        # https://www.googleapis.com/auth/drive.file (incremental authz scoped al file).
        scopes=[
            *_OPENID_BASE_SCOPES,
            "https://www.googleapis.com/auth/drive.readonly",
        ],
        extra_authorize_params={
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        },
    ),
}


# ─────────────────────────────────────────────────────────────────────
# Lettura client_id + client_secret dal file di config locale
# ─────────────────────────────────────────────────────────────────────

# TODO ANTONIO — SETUP GOOGLE CLOUD PROJECT (UNA VOLTA):
#
# 1. Apri https://console.cloud.google.com/apis/credentials
# 2. Crea un nuovo OAuth 2.0 Client ID:
#       - Type: "Desktop application" (NON "Web application")
#       - Name: "SCO Compliance OS"
#       - (Per Desktop app non serve redirect_uri whitelisted: Google accetta
#         tutti i ``http://localhost:*/callback``.)
# 3. Abilita le API necessarie su https://console.cloud.google.com/apis/library:
#       - Gmail API
#       - Google Calendar API
#       - Google Drive API
# 4. Configura OAuth Consent Screen:
#       - User Type: External (se vuoi distribuire ai clienti) o Internal (Google Workspace).
#       - Scopes da dichiarare: openid, email, profile, gmail.readonly,
#         calendar.events.readonly, drive.readonly.
#       - In Testing mode aggiungi gli email autorizzati come Test Users.
# 5. Scarica client_secret.json e copia client_id + client_secret in:
#       ``~/.sco-compliance-os/oauth-config.json``  (Windows: ``%USERPROFILE%\.sco-compliance-os\oauth-config.json``)
#
#    Schema atteso:
#    {
#        "google": {
#            "client_id": "1234567890-abc.apps.googleusercontent.com",
#            "client_secret": "GOCSPX-..."
#        }
#    }
#
# Nota multi-provider: lo stesso client_id Google copre Gmail + GCal + GDrive
# (sono tutti scope dello stesso provider OAuth Google). Non servono 3 client_id distinti.


_OAUTH_CONFIG_PATH = Path.home() / ".sco-compliance-os" / "oauth-config.json"


def _load_provider_credentials(oauth_provider: str) -> tuple[str, str]:
    """Carica client_id + client_secret per il provider OAuth dato.

    Args:
        oauth_provider: identificatore provider (``"google"``, ``"microsoft"``, ...).

    Returns:
        Tupla ``(client_id, client_secret)``.

    Raises:
        OAuthError: se il file di config manca o non contiene il provider.
    """
    if not _OAUTH_CONFIG_PATH.exists():
        raise OAuthError(
            code="oauth_config_missing",
            message=(
                f"File di config OAuth non trovato: {_OAUTH_CONFIG_PATH}. "
                "Vedi TODO ANTONIO in oauth.py per setup Google Cloud Project."
            ),
            provider=oauth_provider,
        )
    try:
        config = json.loads(_OAUTH_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OAuthError(
            code="oauth_config_corrupted",
            message=f"Impossibile leggere {_OAUTH_CONFIG_PATH}: {exc}",
            provider=oauth_provider,
        ) from exc
    provider_block = config.get(oauth_provider)
    if not provider_block or not isinstance(provider_block, dict):
        raise OAuthError(
            code="oauth_provider_not_configured",
            message=(
                f"Provider '{oauth_provider}' non configurato in {_OAUTH_CONFIG_PATH}. "
                "Aggiungi un blocco con 'client_id' e 'client_secret'."
            ),
            provider=oauth_provider,
        )
    client_id = provider_block.get("client_id")
    client_secret = provider_block.get("client_secret")
    if not client_id or not client_secret:
        raise OAuthError(
            code="oauth_credentials_incomplete",
            message=f"client_id o client_secret mancanti per provider '{oauth_provider}'.",
            provider=oauth_provider,
        )
    return client_id, client_secret


# ─────────────────────────────────────────────────────────────────────
# State parameter anti-CSRF (in-memory store)
# ─────────────────────────────────────────────────────────────────────

# Nota: per single-process desktop app un in-memory dict basta. Per deployment
# multi-process (SaaS proxy futuro) servirà uno store condiviso (Redis).
_STATE_STORE: dict[str, dict[str, Any]] = {}
_STATE_TTL_SECONDS = 600  # 10 minuti per completare il flow


def _generate_state(provider_slug: str, tenant_id: str) -> str:
    """Genera state parameter crittografico anti-CSRF + lo memorizza."""
    state = secrets.token_urlsafe(32)
    _STATE_STORE[state] = {
        "provider_slug": provider_slug,
        "tenant_id": tenant_id,
        "created_at": datetime.now(UTC),
    }
    # Pulizia opportunistica state scaduti
    _cleanup_expired_states()
    return state


def _validate_state(state: str, expected_provider: str, expected_tenant: str) -> bool:
    """Valida lo state ricevuto in callback contro lo store."""
    entry = _STATE_STORE.pop(state, None)
    if entry is None:
        return False
    age = (datetime.now(UTC) - entry["created_at"]).total_seconds()
    if age > _STATE_TTL_SECONDS:
        return False
    return bool(
        entry["provider_slug"] == expected_provider and entry["tenant_id"] == expected_tenant
    )


def _cleanup_expired_states() -> None:
    """Rimuove dagli state in store quelli scaduti (opportunistic GC)."""
    now = datetime.now(UTC)
    expired = [
        s
        for s, e in _STATE_STORE.items()
        if (now - e["created_at"]).total_seconds() > _STATE_TTL_SECONDS
    ]
    for s in expired:
        _STATE_STORE.pop(s, None)


# ─────────────────────────────────────────────────────────────────────
# Helper pubblici: start / complete / refresh
# ─────────────────────────────────────────────────────────────────────


def start_oauth_flow(provider: str, redirect_uri: str, tenant_id: str = "default") -> str:
    """Genera l'URL di authorize Google da aprire nel browser dell'utente.

    Args:
        provider: slug del connector (``"gmail"``, ``"google-calendar"``, ``"google-drive"``).
        redirect_uri: URI di callback che l'app desktop espone (es.
            ``"http://localhost:7800/api/integrations/gmail/callback"``).
        tenant_id: identificatore tenant/utente per state validation + token storage.
            Default ``"default"`` per single-tenant desktop app.

    Returns:
        URL completo di authorize endpoint con query string OAuth.

    Raises:
        OAuthError: se il provider non è supportato o se le credenziali OAuth
            applicative non sono configurate.
    """
    cfg = PROVIDERS.get(provider)
    if cfg is None:
        raise OAuthError(
            code="provider_not_supported",
            message=f"Provider '{provider}' non supportato. Disponibili: {list(PROVIDERS)}.",
            provider=provider,
        )
    client_id, _ = _load_provider_credentials(cfg.oauth_provider)
    state = _generate_state(provider, tenant_id)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(cfg.scopes),
        "state": state,
        **cfg.extra_authorize_params,
    }
    auth_url = f"{cfg.auth_url}?{urlencode(params)}"
    logger.info(
        "oauth start | provider=%s tenant=%s redirect=%s scopes=%d",
        provider,
        tenant_id,
        redirect_uri,
        len(cfg.scopes),
    )
    return auth_url


async def complete_oauth_flow(
    provider: str,
    code: str,
    redirect_uri: str,
    tenant_id: str = "default",
    state: str | None = None,
) -> dict[str, Any]:
    """Scambia code ricevuto in callback per access_token + refresh_token.

    Persiste i token risultanti nel keyring OS via ``store_oauth_credentials``,
    quindi recupera l'email dell'utente OAuth dal token endpoint userinfo.

    Args:
        provider: slug del connector.
        code: authorization code ricevuto sulla redirect_uri.
        redirect_uri: stessa URI usata in ``start_oauth_flow`` (Google la valida).
        tenant_id: identificatore tenant/utente.
        state: parametro state da validare contro lo store (opzionale ma raccomandato).

    Returns:
        Dict con ``{connected: True, email: str, scopes: list[str], expires_at: ISO8601}``.

    Raises:
        OAuthError: se lo scambio fallisce (code invalido, state mismatch, network).
    """
    cfg = PROVIDERS.get(provider)
    if cfg is None:
        raise OAuthError(
            code="provider_not_supported",
            message=f"Provider '{provider}' non supportato.",
            provider=provider,
        )

    # Validazione state anti-CSRF (se fornito)
    if state is not None and not _validate_state(state, provider, tenant_id):
        raise OAuthError(
            code="state_invalid",
            message="State parameter non valido o scaduto (possibile CSRF attack o flow timeout).",
            provider=provider,
        )

    client_id, client_secret = _load_provider_credentials(cfg.oauth_provider)
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(cfg.token_url, data=payload)
    except httpx.RequestError as exc:
        raise OAuthError(
            code="network_error",
            message=f"Errore network durante scambio code→token: {exc}",
            provider=provider,
        ) from exc

    if response.status_code != 200:
        # Google ritorna body JSON con error + error_description su 400/401
        try:
            err_body = response.json()
        except ValueError:
            err_body = {"raw": response.text[:500]}
        raise OAuthError(
            code=err_body.get("error", "token_exchange_failed"),
            message=err_body.get("error_description", f"HTTP {response.status_code}"),
            provider=provider,
            http_status=response.status_code,
            raw_response=err_body,
        )

    token_data = response.json()
    expires_in_sec = int(token_data.get("expires_in", 3600))
    tokens = OAuthTokens(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        expires_at=datetime.now(UTC) + timedelta(seconds=expires_in_sec),
        scopes_granted=token_data.get("scope", "").split() or cfg.scopes,
        token_type=token_data.get("token_type", "Bearer"),
        raw_response=token_data,
    )

    # Recupera email utente OAuth via userinfo endpoint (richiede scope openid+email)
    email = await _fetch_user_email(cfg.userinfo_url, tokens.access_token, provider)

    # Persiste nel keyring OS con chiave composta {provider}/{tenant_id}
    store_oauth_credentials(provider, tenant_id, tokens, email=email)

    logger.info(
        "oauth complete | provider=%s tenant=%s email=%s expires_in=%ds has_refresh=%s",
        provider,
        tenant_id,
        email,
        expires_in_sec,
        tokens.refresh_token is not None,
    )

    return {
        "connected": True,
        "email": email,
        "scopes": tokens.scopes_granted,
        "expires_at": tokens.expires_at.isoformat(),
    }


async def refresh_token(
    provider: str, refresh_token_value: str, tenant_id: str = "default"
) -> OAuthTokens:
    """Rinnova un access_token scaduto usando il refresh_token persistito.

    Args:
        provider: slug del connector.
        refresh_token_value: refresh_token ottenuto al primo grant OAuth.
        tenant_id: identificatore tenant/utente (per persistere il nuovo access_token).

    Returns:
        ``OAuthTokens`` aggiornati con nuovo access_token e nuova expires_at.

    Raises:
        OAuthError: se il refresh fallisce (refresh_token revocato, network).
    """
    cfg = PROVIDERS.get(provider)
    if cfg is None:
        raise OAuthError(
            code="provider_not_supported",
            message=f"Provider '{provider}' non supportato.",
            provider=provider,
        )
    client_id, client_secret = _load_provider_credentials(cfg.oauth_provider)
    payload = {
        "refresh_token": refresh_token_value,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(cfg.token_url, data=payload)
    except httpx.RequestError as exc:
        raise OAuthError(
            code="network_error",
            message=f"Errore network durante refresh token: {exc}",
            provider=provider,
        ) from exc

    if response.status_code != 200:
        try:
            err_body = response.json()
        except ValueError:
            err_body = {"raw": response.text[:500]}
        raise OAuthError(
            code=err_body.get("error", "refresh_failed"),
            message=err_body.get("error_description", f"HTTP {response.status_code}"),
            provider=provider,
            http_status=response.status_code,
            raw_response=err_body,
        )

    token_data = response.json()
    expires_in_sec = int(token_data.get("expires_in", 3600))
    new_tokens = OAuthTokens(
        access_token=token_data["access_token"],
        # Google NON sempre ritorna un nuovo refresh_token sul refresh (preserva quello vecchio).
        refresh_token=token_data.get("refresh_token") or refresh_token_value,
        expires_at=datetime.now(UTC) + timedelta(seconds=expires_in_sec),
        scopes_granted=token_data.get("scope", "").split() or cfg.scopes,
        token_type=token_data.get("token_type", "Bearer"),
        raw_response=token_data,
    )

    # Aggiorna il keyring con i nuovi token (preservando email se già nota)
    existing_email = _get_stored_email(provider, tenant_id)
    store_oauth_credentials(provider, tenant_id, new_tokens, email=existing_email)

    logger.info(
        "oauth refresh | provider=%s tenant=%s expires_in=%ds",
        provider,
        tenant_id,
        expires_in_sec,
    )
    return new_tokens


async def revoke_oauth_credentials(provider: str, tenant_id: str = "default") -> bool:
    """Revoca i token presso Google + cancella dal keyring (disconnect).

    Args:
        provider: slug del connector.
        tenant_id: identificatore tenant/utente.

    Returns:
        ``True`` se la revoca è andata a buon fine (anche idempotent no-op).

    Raises:
        OAuthError: se la cancellazione dal keyring fallisce con errore critico.
    """
    cfg = PROVIDERS.get(provider)
    if cfg is None:
        raise OAuthError(
            code="provider_not_supported",
            message=f"Provider '{provider}' non supportato.",
            provider=provider,
        )
    tokens = get_oauth_credentials(provider, tenant_id)
    if tokens is None:
        # Nessun token in storage — no-op idempotente
        logger.info("oauth revoke no-op | provider=%s tenant=%s (no tokens)", provider, tenant_id)
        return True

    # Revoca presso Google (best-effort, non blocca cancellazione keyring se fallisce)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                cfg.revoke_url,
                params={"token": tokens.access_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if response.status_code not in (200, 400):
            # 400 = token già invalido/scaduto, accettabile come no-op
            logger.warning(
                "oauth revoke server returned %d | provider=%s body=%s",
                response.status_code,
                provider,
                response.text[:200],
            )
    except httpx.RequestError as exc:
        logger.warning("oauth revoke network error (proceeding with local delete) | err=%s", exc)

    # Cancella sempre dal keyring (anche se la revoca Google ha fallito)
    _delete_tokens_kr(provider, _compose_keyring_user(tenant_id))
    _delete_email(provider, tenant_id)
    logger.info("oauth revoked | provider=%s tenant=%s", provider, tenant_id)
    return True


# ─────────────────────────────────────────────────────────────────────
# Storage wrapper sopra token_store (formato chiave {provider}/{tenant})
# ─────────────────────────────────────────────────────────────────────


def _compose_keyring_user(tenant_id: str) -> str:
    """Compone l'username keyring includendo tenant_id per multi-tenant safety."""
    return tenant_id


def store_oauth_credentials(
    provider: str,
    tenant_id: str,
    tokens: OAuthTokens,
    email: str | None = None,
) -> None:
    """Persiste i token OAuth nel keyring OS con metadata email.

    Args:
        provider: slug del connector.
        tenant_id: identificatore tenant/utente.
        tokens: token da memorizzare.
        email: email dell'account OAuth (mostrata in UI come account connesso).
    """
    _store_tokens_kr(provider, _compose_keyring_user(tenant_id), tokens)
    if email is not None:
        _store_email(provider, tenant_id, email)


def get_oauth_credentials(provider: str, tenant_id: str = "default") -> OAuthTokens | None:
    """Recupera i token OAuth dal keyring. ``None`` se l'utente non ha connesso."""
    return _get_tokens_kr(provider, _compose_keyring_user(tenant_id))


async def get_valid_access_token(provider: str, tenant_id: str = "default") -> str:
    """Ritorna un access_token valido per il provider, refreshing se serve.

    Helper di alto livello: la maggior parte dei chiamanti (provider Gmail/GCal/GDrive)
    vuole solo "dammi un access_token utilizzabile adesso", senza preoccuparsi di
    scadenza o refresh. Questa funzione orchestrra tutto.

    Args:
        provider: slug del connector.
        tenant_id: identificatore tenant/utente.

    Returns:
        access_token stringa, garantito non-scaduto (con leeway 60s).

    Raises:
        OAuthError: se non esistono token in storage (utente da connettere)
            oppure se il refresh fallisce.
    """
    tokens = get_oauth_credentials(provider, tenant_id)
    if tokens is None:
        raise OAuthError(
            code="not_connected",
            message=f"Provider '{provider}' non connesso per tenant '{tenant_id}'.",
            provider=provider,
        )
    if not tokens.is_expired():
        return tokens.access_token
    # Refresh richiesto
    if tokens.refresh_token is None:
        raise OAuthError(
            code="missing_refresh_token",
            message="Token scaduto e refresh_token assente. Richiedere nuova autorizzazione.",
            provider=provider,
        )
    new_tokens = await refresh_token(provider, tokens.refresh_token, tenant_id)
    return new_tokens.access_token


# ─────────────────────────────────────────────────────────────────────
# Storage email account OAuth (sidecar al keyring)
# ─────────────────────────────────────────────────────────────────────

# L'email account OAuth è metadata non-secret. La mettiamo nel keyring per
# semplicità di lifecycle (delete contestuale ai token), con service_name
# distinto per non confonderla con i token veri.

_EMAIL_SERVICE_SUFFIX = ":email"


def _email_service_name(provider_slug: str) -> str:
    """Service name keyring per metadata email del provider."""
    return f"{SERVICE_NAME_PREFIX}:{provider_slug}{_EMAIL_SERVICE_SUFFIX}"


def _store_email(provider_slug: str, tenant_id: str, email: str) -> None:
    """Persiste l'email account OAuth nel keyring (metadata)."""
    import keyring

    keyring.set_password(_email_service_name(provider_slug), tenant_id, email)


def _get_stored_email(provider_slug: str, tenant_id: str) -> str | None:
    """Recupera l'email account OAuth dal keyring, ``None`` se non presente."""
    import keyring
    from keyring.errors import KeyringError

    try:
        return keyring.get_password(_email_service_name(provider_slug), tenant_id)
    except KeyringError:
        return None


def _delete_email(provider_slug: str, tenant_id: str) -> None:
    """Cancella l'email account OAuth dal keyring (idempotent)."""
    import keyring
    from keyring.errors import KeyringError, PasswordDeleteError

    try:
        keyring.delete_password(_email_service_name(provider_slug), tenant_id)
    except (KeyringError, PasswordDeleteError):
        pass  # no-op idempotent


async def _fetch_user_email(userinfo_url: str, access_token: str, provider: str) -> str:
    """Recupera l'email dell'utente OAuth dal userinfo endpoint Google.

    Richiede scope ``openid email``. Ritorna stringa vuota se non disponibile
    (gracefully, non solleva — l'email è UX metadata, non bloccante).
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.status_code == 200:
            data = response.json()
            email = data.get("email") or ""
            return email
        logger.warning(
            "userinfo fetch returned %d | provider=%s body=%s",
            response.status_code,
            provider,
            response.text[:200],
        )
    except httpx.RequestError as exc:
        logger.warning("userinfo fetch network error | provider=%s err=%s", provider, exc)
    return ""


def get_connected_email(provider: str, tenant_id: str = "default") -> str | None:
    """Ritorna l'email account OAuth connesso per il provider, ``None`` altrimenti.

    Esposto come API pubblica per UI/endpoint che mostrano account_connected.
    """
    return _get_stored_email(provider, tenant_id)


# ─────────────────────────────────────────────────────────────────────
# Override redirect_uri da env var (test/dev)
# ─────────────────────────────────────────────────────────────────────


def default_redirect_uri(provider: str, port: int | None = None) -> str:
    """Ritorna la redirect_uri di default per il provider in modalità desktop.

    Pattern Google "Desktop application": ``http://localhost:{port}/callback``
    è sempre accettato senza dover whitelistare URL fissi.

    Args:
        provider: slug del connector.
        port: porta del backend FastAPI (default 7800, override via env SCO_BACKEND_PORT).

    Returns:
        URI di callback es. ``"http://localhost:7800/api/integrations/gmail/callback"``.
    """
    effective_port = port or int(os.environ.get("SCO_BACKEND_PORT", "7800"))
    return f"http://localhost:{effective_port}/api/integrations/{provider}/callback"
