"""
gmail.py — Wrapper Gmail API v1 (REST) per SCO Compliance OS.

Architettura: wrapper sottile sopra ``httpx.AsyncClient`` che chiama gli
endpoint REST ufficiali Gmail API v1. Ogni funzione riceve un
``access_token`` valido (ottenuto via ``..oauth.get_valid_access_token``)
e ritorna dict tipizzati con il subset di campi rilevanti per l'app.

Scelta architetturale (Pattern Conv. 35 RESEARCH-BEFORE-ACT):
    Non usiamo direttamente ``googleapiclient.discovery.build()`` perché:
    1. La library Google API client carica un large discovery document
       a ogni init (~2-3MB), gonfiando il bundle PyInstaller.
    2. Richiama internamente sync HTTP, non async — incompatible con FastAPI.
    3. Per i ~5 endpoint che ci servono, httpx async + REST diretto è
       più snello, testabile e debuggabile.

Endpoint Gmail API v1 usati (docs ufficiali Pattern Conv. 35):
    - GET /gmail/v1/users/{userId}/messages
      https://developers.google.com/gmail/api/reference/rest/v1/users.messages/list
    - GET /gmail/v1/users/{userId}/messages/{id}
      https://developers.google.com/gmail/api/reference/rest/v1/users.messages/get
    - POST /gmail/v1/users/{userId}/messages/send
      https://developers.google.com/gmail/api/reference/rest/v1/users.messages/send

Scope richiesti:
    - ``https://www.googleapis.com/auth/gmail.readonly`` per list_messages + get_message
    - ``https://www.googleapis.com/auth/gmail.send`` per send_message (INCREMENTAL
      authorization: richiede nuovo OAuth consent perché non incluso nello scope
      minimo definito in ``oauth.PROVIDERS["gmail"]``).
"""

from __future__ import annotations

import base64
import logging
from email.message import EmailMessage
from typing import Any

import httpx

from ..base import OAuthError

logger = logging.getLogger(__name__)

# Base URL Gmail API v1 — fonte: https://developers.google.com/gmail/api/reference/rest
_GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"

# Timeout di default per le chiamate Gmail (i fetch full body possono essere lenti)
_DEFAULT_TIMEOUT_SECONDS = 30.0


# ─────────────────────────────────────────────────────────────────────
# Helper interni
# ─────────────────────────────────────────────────────────────────────


def _auth_headers(access_token: str) -> dict[str, str]:
    """Compone gli headers di autenticazione Bearer per Gmail API."""
    return {"Authorization": f"Bearer {access_token}"}


def _raise_if_error(response: httpx.Response, operation: str) -> None:
    """Solleva ``OAuthError`` tipizzato se la response Gmail API non è 2xx."""
    if 200 <= response.status_code < 300:
        return
    try:
        err_body = response.json()
    except ValueError:
        err_body = {"raw": response.text[:500]}
    err_obj = err_body.get("error", {}) if isinstance(err_body, dict) else {}
    raise OAuthError(
        code=err_obj.get("status", "gmail_api_error"),
        message=f"Gmail {operation} failed: {err_obj.get('message', 'unknown')}",
        provider="gmail",
        http_status=response.status_code,
        raw_response=err_body if isinstance(err_body, dict) else {"raw": str(err_body)},
    )


def _decode_base64url(data: str) -> str:
    """Decodifica un payload base64url Gmail in stringa UTF-8.

    Gmail usa base64url (RFC 4648 sect. 5) per i body MIME. Il padding può
    essere omesso, quindi lo ricostruiamo manualmente.
    """
    padded = data + "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except (ValueError, UnicodeDecodeError) as exc:
        logger.warning("gmail base64 decode failed | err=%s", exc)
        return ""


def _extract_headers(payload: dict[str, Any]) -> dict[str, str]:
    """Estrae gli header MIME principali (From, To, Subject, Date) dal payload."""
    headers_list = payload.get("headers", []) or []
    wanted = {"from", "to", "subject", "date", "cc", "bcc", "reply-to", "message-id"}
    out: dict[str, str] = {}
    for h in headers_list:
        name = h.get("name", "").lower()
        if name in wanted:
            out[name] = h.get("value", "")
    return out


def _extract_body(payload: dict[str, Any]) -> str:
    """Estrae il body testuale (text/plain preferito, fallback text/html).

    Gmail messages.get ritorna il payload come tree MIME ricorsivo. Cerchiamo
    in ordine: text/plain top-level, text/plain in parts, text/html fallback.
    """
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")
    if mime_type.startswith("text/plain") and body_data:
        return _decode_base64url(body_data)

    # Cerca ricorsivamente nelle parts
    text_plain = ""
    text_html = ""
    for part in payload.get("parts", []) or []:
        sub_mime = part.get("mimeType", "")
        sub_data = part.get("body", {}).get("data")
        if sub_mime == "text/plain" and sub_data and not text_plain:
            text_plain = _decode_base64url(sub_data)
        elif sub_mime == "text/html" and sub_data and not text_html:
            text_html = _decode_base64url(sub_data)
        elif sub_mime.startswith("multipart/"):
            # Recurse into multipart/alternative, multipart/mixed
            nested = _extract_body(part)
            if nested and not text_plain:
                text_plain = nested

    return text_plain or text_html or ""


# ─────────────────────────────────────────────────────────────────────
# API pubbliche
# ─────────────────────────────────────────────────────────────────────


async def list_messages(
    access_token: str,
    query: str = "",
    max_results: int = 25,
    user_id: str = "me",
    label_ids: list[str] | None = None,
    page_token: str | None = None,
) -> dict[str, Any]:
    """Lista i messaggi Gmail con filtro opzionale via search query.

    Args:
        access_token: Bearer token OAuth valido (scope gmail.readonly).
        query: query in formato Gmail search (es. ``"from:foo@bar.com after:2024/01/01"``).
            Vedi: https://support.google.com/mail/answer/7190
        max_results: numero massimo di messaggi da ritornare (1-500, default 25).
        user_id: identificativo utente Gmail; ``"me"`` per l'utente autenticato.
        label_ids: lista di label ID da filtrare (es. ``["INBOX", "UNREAD"]``).
        page_token: token per paginazione (da response precedente).

    Returns:
        Dict con keys:
            - ``messages``: list di ``{id, threadId}`` (metadata minimale).
            - ``next_page_token``: token per pagina successiva (None se ultima).
            - ``result_size_estimate``: stima totale match query.

    Raises:
        OAuthError: se la chiamata Gmail API fallisce.
    """
    params: dict[str, Any] = {
        "maxResults": max(1, min(max_results, 500)),
    }
    if query:
        params["q"] = query
    if label_ids:
        params["labelIds"] = label_ids
    if page_token:
        params["pageToken"] = page_token

    url = f"{_GMAIL_API_BASE}/users/{user_id}/messages"
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=_auth_headers(access_token), params=params)
    except httpx.RequestError as exc:
        raise OAuthError(
            code="network_error",
            message=f"Network error during Gmail list_messages: {exc}",
            provider="gmail",
        ) from exc

    _raise_if_error(response, "list_messages")
    data = response.json()
    messages = data.get("messages", []) or []
    logger.info(
        "gmail list_messages | query=%s count=%d has_next=%s",
        query[:80] if query else "",
        len(messages),
        bool(data.get("nextPageToken")),
    )
    return {
        "messages": messages,
        "next_page_token": data.get("nextPageToken"),
        "result_size_estimate": data.get("resultSizeEstimate", 0),
    }


async def get_message(
    access_token: str,
    message_id: str,
    user_id: str = "me",
    fmt: str = "full",
) -> dict[str, Any]:
    """Recupera dettagli completi di un messaggio Gmail.

    Args:
        access_token: Bearer token OAuth valido.
        message_id: ID del messaggio (da ``list_messages``).
        user_id: identificativo utente Gmail; ``"me"`` per l'utente autenticato.
        fmt: formato response: ``"full"`` (default, MIME parts + body),
            ``"metadata"`` (solo headers), ``"minimal"`` (id + labels),
            ``"raw"`` (RFC 2822 base64url).

    Returns:
        Dict con keys:
            - ``id``, ``thread_id``, ``label_ids``, ``snippet``
            - ``headers``: dict header normalizzati (from, to, subject, date, ...)
            - ``body``: stringa text/plain (estratta dal MIME tree)
            - ``size_estimate``: dimensione in bytes
            - ``internal_date``: timestamp epoch ms

    Raises:
        OAuthError: se la chiamata Gmail API fallisce.
    """
    if fmt not in ("full", "metadata", "minimal", "raw"):
        raise ValueError(f"Invalid fmt '{fmt}'. Use full|metadata|minimal|raw.")

    url = f"{_GMAIL_API_BASE}/users/{user_id}/messages/{message_id}"
    params = {"format": fmt}
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=_auth_headers(access_token), params=params)
    except httpx.RequestError as exc:
        raise OAuthError(
            code="network_error",
            message=f"Network error during Gmail get_message: {exc}",
            provider="gmail",
        ) from exc

    _raise_if_error(response, "get_message")
    data = response.json()
    payload = data.get("payload", {}) or {}

    return {
        "id": data.get("id", message_id),
        "thread_id": data.get("threadId"),
        "label_ids": data.get("labelIds", []) or [],
        "snippet": data.get("snippet", ""),
        "headers": _extract_headers(payload),
        "body": _extract_body(payload) if fmt == "full" else "",
        "size_estimate": data.get("sizeEstimate", 0),
        "internal_date": data.get("internalDate"),
    }


async def send_message(
    access_token: str,
    to: str,
    subject: str,
    body: str,
    user_id: str = "me",
    cc: str | None = None,
    bcc: str | None = None,
    reply_to: str | None = None,
) -> dict[str, Any]:
    """Invia una email via Gmail API.

    REQUISITO SCOPE: questa funzione richiede lo scope
    ``https://www.googleapis.com/auth/gmail.send`` che NON è incluso nello scope
    minimo registrato per il provider ``"gmail"`` in ``oauth.PROVIDERS``.
    Per usarla servono due opzioni:
        (a) Estendere PROVIDERS["gmail"].scopes con gmail.send (impatta tutti gli utenti).
        (b) Implementare incremental authorization: nuovo flow OAuth dedicato.
    Default consigliato: opzione (b), per non chiedere scopes write a chi vuole solo leggere.

    Args:
        access_token: Bearer token OAuth con scope gmail.send.
        to: destinatario principale (es. ``"foo@bar.com"``).
        subject: oggetto email.
        body: corpo testuale (text/plain).
        user_id: identificativo utente Gmail; ``"me"`` per l'utente autenticato.
        cc, bcc, reply_to: header opzionali.

    Returns:
        Dict con ``{id, thread_id, label_ids}`` del messaggio inviato.

    Raises:
        OAuthError: se l'invio fallisce (insufficient_scope, network, quota).
    """
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)

    # Gmail API richiede il messaggio RFC 2822 codificato in base64url
    raw_b64url = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii").rstrip("=")

    url = f"{_GMAIL_API_BASE}/users/{user_id}/messages/send"
    payload = {"raw": raw_b64url}
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url, headers=_auth_headers(access_token), json=payload
            )
    except httpx.RequestError as exc:
        raise OAuthError(
            code="network_error",
            message=f"Network error during Gmail send_message: {exc}",
            provider="gmail",
        ) from exc

    _raise_if_error(response, "send_message")
    data = response.json()
    logger.info(
        "gmail send_message | to=%s subject=%s sent_id=%s",
        to,
        subject[:50],
        data.get("id"),
    )
    return {
        "id": data.get("id"),
        "thread_id": data.get("threadId"),
        "label_ids": data.get("labelIds", []) or [],
    }
