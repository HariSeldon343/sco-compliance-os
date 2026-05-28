"""Router /api/integrations — connettori OAuth e ingestione dati esterni.

3 connettori Google cablati end-to-end (Gmail, Google Calendar, Google Drive):
flow OAuth 2.0 reale via ``services/integrations/oauth.py`` + chiamate REST
ai provider via ``services/integrations/providers/{gmail,gcal,gdrive}.py``.

Architettura endpoint:

    GET /api/integrations/available
        Lista i 3 connettori Google con scope OAuth, descrizione, connection_url
        e stato connessione (dedotto da keyring OS).

    POST /api/integrations/{slug}/connect
        Avvia il flow OAuth: ritorna ``oauth_url`` da aprire nel browser.

    POST /api/integrations/{slug}/exchange-code
        Scambia il ``code`` ricevuto in callback per token + persiste nel keyring.
        Body: ``{code: string, state?: string}``.

    GET /api/integrations/{slug}/callback
        Endpoint di redirect_uri per il flow OAuth desktop (Google redirige qui
        dopo che l'utente accetta nel browser).

    GET /api/integrations/{slug}/data?query=...
        Wraps il fetch dati provider-specifico: gmail.list_messages,
        gcal.list_events, gdrive.list_files.

    DELETE /api/integrations/{slug}
        Disconnette (revoca presso Google + cancella keyring).

Pattern Conv. 48 SINGLE SOURCE OF TRUTH BACKEND: lo stato connection +
email account vivono SOLO nel keyring OS lato backend. Il frontend deduce
status + account dal fetch ``GET /available``, mai da localStorage React.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.integrations.base import OAuthError
from sco_compliance_os.services.integrations.oauth import (
    PROVIDERS,
    complete_oauth_flow,
    default_redirect_uri,
    get_connected_email,
    get_oauth_credentials,
    get_valid_access_token,
    revoke_oauth_credentials,
    start_oauth_flow,
)
from sco_compliance_os.services.integrations.providers import gcal, gdrive, gmail

logger = get_logger(__name__)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


IntegrationStatus = Literal["pending", "connected", "error", "disconnected"]


# ─────────────────────────────────────────────────────────────────────
# Schemi Pydantic (response shape stabile per il frontend)
# ─────────────────────────────────────────────────────────────────────


class IntegrationInfo(BaseModel):
    """Metadati connettore + stato connessione (Conv. 48 single source of truth)."""

    slug: str
    name: str
    description: str
    status: IntegrationStatus = "pending"
    icon_slug: str | None = None
    last_sync_at: datetime | None = None
    # Account connesso (Conv. 48: backend è source of truth). None se disconnected.
    account: str | None = None
    # Scope OAuth richiesti (mostrati in UI prima del consent)
    scopes_required: list[str] = Field(default_factory=list)
    # connection_url da aprire nel browser per avviare OAuth (vuota se già connesso)
    connection_url: str | None = None


class IntegrationConnectResponse(BaseModel):
    """Response OAuth start: contiene l'URL Google da aprire nel browser."""

    slug: str
    oauth_url: str
    state_token: str
    message: str


class IntegrationExchangeCodeRequest(BaseModel):
    """Body POST /{slug}/exchange-code: code ricevuto dal callback OAuth."""

    code: str = Field(..., min_length=1, description="Authorization code Google")
    state: str | None = Field(None, description="State anti-CSRF da validare")


class IntegrationConnectedResponse(BaseModel):
    """Response OAuth complete: connessione attiva + email account."""

    slug: str
    connected: bool
    email: str | None = None
    scopes: list[str] = Field(default_factory=list)
    expires_at: str | None = None
    message: str | None = None


class IntegrationDataResponse(BaseModel):
    """Response generic per dati fetched dal provider."""

    slug: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: str | None = None
    fetched_at: datetime


# ─────────────────────────────────────────────────────────────────────
# Catalogo statico (UI metadata, indipendente dai PROVIDERS OAuth)
# ─────────────────────────────────────────────────────────────────────

_INTEGRATIONS_CATALOG: dict[str, dict[str, str]] = {
    "gmail": {
        "name": "Gmail",
        "description": "Lettura email dall'account Google dell'utente (read-only).",
        "icon_slug": "gmail",
    },
    "google-calendar": {
        "name": "Google Calendar",
        "description": "Lettura eventi e disponibilità calendario (read-only).",
        "icon_slug": "google-calendar",
    },
    "google-drive": {
        "name": "Google Drive",
        "description": "Lettura file e documenti dal Drive personale (read-only).",
        "icon_slug": "google-drive",
    },
}


# ─────────────────────────────────────────────────────────────────────
# Helper interni
# ─────────────────────────────────────────────────────────────────────


def _build_integration_info(
    slug: str,
    tenant_id: str = "default",
    include_connection_url: bool = True,
) -> IntegrationInfo:
    """Compone ``IntegrationInfo`` con stato connessione dedotto dal keyring."""
    meta = _INTEGRATIONS_CATALOG.get(slug)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Connettore '{slug}' non trovato")
    provider_cfg = PROVIDERS.get(slug)
    if provider_cfg is None:
        raise HTTPException(
            status_code=500, detail=f"Provider '{slug}' non configurato in oauth.PROVIDERS"
        )

    # Stato connessione: presenza di token nel keyring + non-expired
    tokens = get_oauth_credentials(slug, tenant_id)
    if tokens is None:
        status: IntegrationStatus = "disconnected"
        account: str | None = None
        last_sync: datetime | None = None
    else:
        status = "connected"
        account = get_connected_email(slug, tenant_id) or None
        # last_sync_at non tracciato esplicitamente — usiamo expires_at come proxy
        last_sync = None

    connection_url: str | None = None
    if include_connection_url and status == "disconnected":
        try:
            redirect_uri = default_redirect_uri(slug)
            connection_url = start_oauth_flow(slug, redirect_uri, tenant_id)
        except OAuthError as exc:
            logger.warning(
                "cannot build connection_url",
                slug=slug,
                err_code=exc.code,
                err_msg=exc.message,
            )
            # Non blocchiamo l'endpoint /available: ritorniamo None come
            # connection_url, la UI mostrerà l'errore di config solo al click.
            connection_url = None

    return IntegrationInfo(
        slug=slug,
        name=meta["name"],
        description=meta["description"],
        status=status,
        icon_slug=meta.get("icon_slug"),
        last_sync_at=last_sync,
        account=account,
        scopes_required=provider_cfg.scopes,
        connection_url=connection_url,
    )


def _oauth_error_to_http(exc: OAuthError) -> HTTPException:
    """Mappa OAuthError in HTTPException appropriato per il client."""
    if exc.code in ("not_connected",):
        return HTTPException(status_code=401, detail=str(exc))
    if exc.code in (
        "oauth_config_missing",
        "oauth_provider_not_configured",
        "oauth_credentials_incomplete",
        "oauth_config_corrupted",
    ):
        return HTTPException(status_code=503, detail=str(exc))
    if exc.code in ("state_invalid",):
        return HTTPException(status_code=400, detail=str(exc))
    if exc.code in ("provider_not_supported",):
        return HTTPException(status_code=404, detail=str(exc))
    # Default: errori token endpoint Google / network
    return HTTPException(status_code=exc.http_status or 500, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────


@router.get("/available", response_model=list[IntegrationInfo])
async def list_integrations() -> list[IntegrationInfo]:
    """Lista i 3 connettori Google con stato connessione dedotto dal keyring.

    Conv. 48 enforcement: lo stato connessione + email account vivono solo
    nel keyring OS lato backend. Questa response è source of truth per la UI.
    """
    return [_build_integration_info(slug, "default") for slug in _INTEGRATIONS_CATALOG]


@router.post("/{slug}/connect", response_model=IntegrationConnectResponse)
async def connect_integration(slug: str) -> IntegrationConnectResponse:
    """Avvia il flow OAuth Google: ritorna l'URL da aprire nel browser.

    Il flow è Desktop application Google: la redirect_uri è
    ``http://localhost:{port}/api/integrations/{slug}/callback``. Quando
    l'utente accetta nel browser, Google redirige qui con ``?code=...``
    e l'endpoint ``GET /{slug}/callback`` completa il flow.

    Raises:
        404: se il provider non esiste.
        503: se OAuth config locale mancante (vedi TODO ANTONIO in oauth.py).
    """
    if slug not in _INTEGRATIONS_CATALOG:
        raise HTTPException(status_code=404, detail=f"Connettore '{slug}' non trovato")
    try:
        redirect_uri = default_redirect_uri(slug)
        oauth_url = start_oauth_flow(slug, redirect_uri, "default")
    except OAuthError as exc:
        logger.warning(
            "integration.connect.failed", slug=slug, err_code=exc.code, err_msg=exc.message
        )
        raise _oauth_error_to_http(exc) from exc

    logger.info("integration.connect.requested", slug=slug, redirect_uri=redirect_uri)
    # state_token: estraibile dall'URL ma lo includiamo nella response per UX
    state_token = oauth_url.rsplit("state=", 1)[-1].split("&", 1)[0]
    name = _INTEGRATIONS_CATALOG[slug]["name"]
    return IntegrationConnectResponse(
        slug=slug,
        oauth_url=oauth_url,
        state_token=state_token,
        message=f"Apri l'URL nel browser per autorizzare l'accesso a {name}.",
    )


@router.post("/{slug}/exchange-code", response_model=IntegrationConnectedResponse)
async def exchange_oauth_code(
    slug: str, payload: IntegrationExchangeCodeRequest
) -> IntegrationConnectedResponse:
    """Scambia il code ricevuto in callback per access_token + refresh_token.

    Endpoint chiamato dalla UI quando il browser ha redirezionato sul callback
    e si vuole completare il flow OAuth lato app desktop.

    Body:
        ``{code: string, state?: string}``

    Returns:
        ``{connected: True, email: "user@example.com", scopes: [...], expires_at: ISO8601}``
    """
    if slug not in _INTEGRATIONS_CATALOG:
        raise HTTPException(status_code=404, detail=f"Connettore '{slug}' non trovato")
    try:
        redirect_uri = default_redirect_uri(slug)
        result = await complete_oauth_flow(
            provider=slug,
            code=payload.code,
            redirect_uri=redirect_uri,
            tenant_id="default",
            state=payload.state,
        )
    except OAuthError as exc:
        logger.warning(
            "integration.exchange.failed",
            slug=slug,
            err_code=exc.code,
            err_msg=exc.message,
        )
        raise _oauth_error_to_http(exc) from exc

    logger.info(
        "integration.exchange.completed",
        slug=slug,
        email=result.get("email"),
        scope_count=len(result.get("scopes", [])),
    )
    return IntegrationConnectedResponse(
        slug=slug,
        connected=True,
        email=result.get("email") or None,
        scopes=result.get("scopes", []),
        expires_at=result.get("expires_at"),
        message=f"Connessione {slug} completata con successo.",
    )


@router.get("/{slug}/callback", response_class=HTMLResponse)
async def oauth_callback(
    slug: str,
    code: str | None = Query(None, description="Authorization code Google"),
    state: str | None = Query(None, description="State anti-CSRF"),
    error: str | None = Query(None, description="Errore OAuth (es. access_denied)"),
) -> HTMLResponse:
    """Endpoint redirect_uri per il flow OAuth desktop.

    Google redirige il browser qui dopo che l'utente accetta (o rifiuta).
    Completiamo lo scambio code→token automaticamente, poi ritorniamo una
    pagina HTML che chiude la finestra e notifica l'app desktop tramite
    ``window.opener.postMessage`` (se presente).

    Note: questa pagina HTML è quella che l'utente vede al termine del flow.
    Per UX migliore l'app desktop può intercettare la chiusura del browser
    e mostrare il proprio toast di conferma.
    """
    if slug not in _INTEGRATIONS_CATALOG:
        raise HTTPException(status_code=404, detail=f"Connettore '{slug}' non trovato")

    # Caso utente ha rifiutato o errore Google
    if error:
        logger.warning("integration.callback.error", slug=slug, error=error)
        html = _render_callback_page(slug=slug, success=False, message=f"OAuth fallito: {error}")
        return HTMLResponse(content=html, status_code=200)

    if not code:
        logger.warning("integration.callback.missing_code", slug=slug)
        html = _render_callback_page(
            slug=slug, success=False, message="Authorization code mancante."
        )
        return HTMLResponse(content=html, status_code=400)

    try:
        redirect_uri = default_redirect_uri(slug)
        result = await complete_oauth_flow(
            provider=slug,
            code=code,
            redirect_uri=redirect_uri,
            tenant_id="default",
            state=state,
        )
    except OAuthError as exc:
        logger.warning(
            "integration.callback.exchange_failed",
            slug=slug,
            err_code=exc.code,
            err_msg=exc.message,
        )
        html = _render_callback_page(
            slug=slug,
            success=False,
            message=f"Errore scambio token: {exc.message}",
        )
        return HTMLResponse(content=html, status_code=200)

    logger.info("integration.callback.success", slug=slug, email=result.get("email"))
    html = _render_callback_page(
        slug=slug,
        success=True,
        message=f"Connesso come {result.get('email', 'utente sconosciuto')}.",
        email=result.get("email"),
    )
    return HTMLResponse(content=html, status_code=200)


def _render_callback_page(slug: str, success: bool, message: str, email: str | None = None) -> str:
    """Pagina HTML mostrata al termine del flow OAuth nel browser.

    Tenta di notificare l'app desktop via ``window.opener.postMessage`` e
    chiudere la finestra automaticamente dopo 2 secondi.
    """
    name = _INTEGRATIONS_CATALOG.get(slug, {}).get("name", slug)
    status_emoji = "OK" if success else "FAIL"
    color = "#10b981" if success else "#ef4444"
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>SCO Compliance OS - {name}</title>
<style>
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  margin: 0;
}}
.card {{
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  padding: 48px 32px;
  text-align: center;
  max-width: 480px;
}}
h1 {{ color: {color}; margin: 0 0 16px 0; font-size: 24px; }}
p {{ color: #475569; line-height: 1.5; }}
.hint {{ color: #94a3b8; font-size: 13px; margin-top: 24px; }}
</style>
</head>
<body>
<div class="card">
<h1>{status_emoji} {name} {"connesso" if success else "errore"}</h1>
<p>{message}</p>
<p class="hint">Questa finestra si chiudera' automaticamente. Puoi tornare all'app SCO Compliance OS.</p>
</div>
<script>
try {{
  if (window.opener) {{
    window.opener.postMessage({{
      type: 'sco-oauth-callback',
      slug: '{slug}',
      success: {str(success).lower()},
      email: {f'"{email}"' if email else "null"},
      message: {message!r}
    }}, '*');
  }}
}} catch (e) {{}}
setTimeout(function() {{ try {{ window.close(); }} catch (e) {{}} }}, 2000);
</script>
</body>
</html>"""


@router.delete("/{slug}", status_code=204, response_class=Response, response_model=None)
async def disconnect_integration(slug: str) -> None:
    """Revoca i token presso Google + cancella dal keyring (disconnect)."""
    if slug not in _INTEGRATIONS_CATALOG:
        raise HTTPException(status_code=404, detail=f"Connettore '{slug}' non trovato")
    try:
        await revoke_oauth_credentials(slug, "default")
    except OAuthError as exc:
        logger.warning(
            "integration.disconnect.failed",
            slug=slug,
            err_code=exc.code,
            err_msg=exc.message,
        )
        raise _oauth_error_to_http(exc) from exc
    logger.info("integration.disconnect.completed", slug=slug)


@router.get("/{slug}/data", response_model=IntegrationDataResponse)
async def fetch_integration_data(
    slug: str,
    query: str | None = Query(None, description="Query provider-specifica"),
    max_results: int = Query(25, ge=1, le=500, description="Numero massimo item"),
    cursor: str | None = Query(None, description="Page token paginazione"),
    since: datetime | None = Query(None, description="Filtro temporale incrementale"),
) -> IntegrationDataResponse:
    """Fetch dati dal provider OAuth (wraps provider-specifico).

    Mapping per slug:
        - ``gmail``: wraps ``gmail.list_messages(query, max_results)``.
            ``query`` in formato Gmail search (es. ``"from:foo after:2024/01/01"``).
        - ``google-calendar``: wraps ``gcal.list_events(time_min=since, max_results)``.
            ``query`` come full-text search su summary/description.
        - ``google-drive``: wraps ``gdrive.list_files(query, page_size=max_results)``.
            ``query`` in formato Drive search syntax.

    Auto-refresh trasparente: se l'access_token è scaduto, viene rinnovato
    automaticamente prima della chiamata API.

    Raises:
        401: se l'utente non è connesso (token non in keyring).
        503: se OAuth config mancante.
        4xx/5xx: pass-through degli errori Google API.
    """
    if slug not in _INTEGRATIONS_CATALOG:
        raise HTTPException(status_code=404, detail=f"Connettore '{slug}' non trovato")
    try:
        access_token = await get_valid_access_token(slug, "default")
    except OAuthError as exc:
        raise _oauth_error_to_http(exc) from exc

    try:
        if slug == "gmail":
            result = await gmail.list_messages(
                access_token=access_token,
                query=query or "",
                max_results=max_results,
                page_token=cursor,
            )
            items = result["messages"]
            next_cursor = result["next_page_token"]
        elif slug == "google-calendar":
            result = await gcal.list_events(
                access_token=access_token,
                time_min=since,
                max_results=max_results,
                query=query,
                page_token=cursor,
            )
            items = result["events"]
            next_cursor = result["next_page_token"]
        elif slug == "google-drive":
            result = await gdrive.list_files(
                access_token=access_token,
                query=query,
                page_size=max_results,
                page_token=cursor,
            )
            items = result["files"]
            next_cursor = result["next_page_token"]
        else:
            raise HTTPException(
                status_code=501, detail=f"Provider '{slug}' senza data fetcher implementato"
            )
    except OAuthError as exc:
        logger.warning("integration.data.failed", slug=slug, err_code=exc.code, err_msg=exc.message)
        raise _oauth_error_to_http(exc) from exc

    logger.info("integration.data.success", slug=slug, count=len(items))
    return IntegrationDataResponse(
        slug=slug,
        items=items,
        next_cursor=next_cursor,
        fetched_at=datetime.now(UTC),
    )
