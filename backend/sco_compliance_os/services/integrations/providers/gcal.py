"""
gcal.py — Wrapper Google Calendar API v3 (REST) per SCO Compliance OS.

Architettura: wrapper sottile sopra ``httpx.AsyncClient`` che chiama gli
endpoint REST ufficiali Google Calendar API v3.

Endpoint Calendar API v3 usati (docs ufficiali Pattern Conv. 35):
    - GET /calendar/v3/calendars/{calendarId}/events
      https://developers.google.com/calendar/api/v3/reference/events/list
    - POST /calendar/v3/calendars/{calendarId}/events
      https://developers.google.com/calendar/api/v3/reference/events/insert

Scope richiesti:
    - ``https://www.googleapis.com/auth/calendar.events.readonly`` per list_events
    - ``https://www.googleapis.com/auth/calendar.events`` per create_event
      (INCREMENTAL authorization: nuovo OAuth consent richiesto).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from ..base import OAuthError

logger = logging.getLogger(__name__)

# Base URL Google Calendar API v3 — fonte: https://developers.google.com/calendar/api/v3/reference
_GCAL_API_BASE = "https://www.googleapis.com/calendar/v3"

_DEFAULT_TIMEOUT_SECONDS = 30.0


# ─────────────────────────────────────────────────────────────────────
# Helper interni
# ─────────────────────────────────────────────────────────────────────


def _auth_headers(access_token: str) -> dict[str, str]:
    """Compone gli headers di autenticazione Bearer per Calendar API."""
    return {"Authorization": f"Bearer {access_token}"}


def _raise_if_error(response: httpx.Response, operation: str) -> None:
    """Solleva ``OAuthError`` tipizzato se la response Calendar API non è 2xx."""
    if 200 <= response.status_code < 300:
        return
    try:
        err_body = response.json()
    except ValueError:
        err_body = {"raw": response.text[:500]}
    err_obj = err_body.get("error", {}) if isinstance(err_body, dict) else {}
    raise OAuthError(
        code=err_obj.get("status", "gcal_api_error"),
        message=f"Google Calendar {operation} failed: {err_obj.get('message', 'unknown')}",
        provider="google-calendar",
        http_status=response.status_code,
        raw_response=err_body if isinstance(err_body, dict) else {"raw": str(err_body)},
    )


def _to_rfc3339(dt: datetime | str) -> str:
    """Converte un datetime in RFC 3339 string (formato richiesto da Calendar API).

    Calendar API accetta sia stringhe RFC 3339 sia datetime aware con timezone.
    Le datetime naive vengono assunte UTC.
    """
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        # Treat naive as UTC (consigliato esplicitare timezone lato chiamante)
        return dt.isoformat() + "Z"
    return dt.isoformat()


def _normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalizza la struct Calendar API event in dict snello per consumer downstream.

    Calendar API ritorna oggetti event con shape complessa: ``start.dateTime`` o
    ``start.date`` (all-day), ``attendees[].email/responseStatus``, ``creator``,
    ``organizer``, ecc. Estraiamo i campi più rilevanti.
    """
    start = raw.get("start", {}) or {}
    end = raw.get("end", {}) or {}
    return {
        "id": raw.get("id"),
        "summary": raw.get("summary", ""),
        "description": raw.get("description", ""),
        "location": raw.get("location"),
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "all_day": "date" in start and "dateTime" not in start,
        "status": raw.get("status", "confirmed"),
        "html_link": raw.get("htmlLink"),
        "created": raw.get("created"),
        "updated": raw.get("updated"),
        "organizer_email": (raw.get("organizer") or {}).get("email"),
        "attendees": [
            {
                "email": a.get("email"),
                "response_status": a.get("responseStatus", "needsAction"),
                "display_name": a.get("displayName"),
                "optional": a.get("optional", False),
            }
            for a in (raw.get("attendees") or [])
        ],
        "recurring_event_id": raw.get("recurringEventId"),
        "hangout_link": raw.get("hangoutLink"),
        "conference_data": raw.get("conferenceData"),
    }


# ─────────────────────────────────────────────────────────────────────
# API pubbliche
# ─────────────────────────────────────────────────────────────────────


async def list_events(
    access_token: str,
    time_min: datetime | str | None = None,
    time_max: datetime | str | None = None,
    max_results: int = 50,
    calendar_id: str = "primary",
    query: str | None = None,
    page_token: str | None = None,
) -> dict[str, Any]:
    """Lista gli eventi di un calendario Google con filtro temporale.

    Args:
        access_token: Bearer token OAuth valido (scope calendar.events.readonly).
        time_min: limite inferiore inclusivo (RFC 3339 string o datetime).
            Se None, defaults a "now" lato API.
        time_max: limite superiore esclusivo.
        max_results: numero massimo eventi per pagina (1-2500, default 50).
        calendar_id: ID del calendario; ``"primary"`` per quello principale.
            Altri esempi: ``"<email>@gmail.com"`` o secondary calendar IDs.
        query: ricerca testuale full-text su summary/description/location/attendees.
        page_token: token per paginazione (da response precedente).

    Returns:
        Dict con keys:
            - ``events``: list di event normalizzati (vedi ``_normalize_event``)
            - ``next_page_token``: token paginazione (None se ultima pagina)
            - ``time_zone``: timezone default del calendario

    Raises:
        OAuthError: se la chiamata Calendar API fallisce.
    """
    params: dict[str, Any] = {
        "maxResults": max(1, min(max_results, 2500)),
        "singleEvents": "true",  # espande eventi ricorrenti in istanze singole
        "orderBy": "startTime",
    }
    if time_min is not None:
        params["timeMin"] = _to_rfc3339(time_min)
    if time_max is not None:
        params["timeMax"] = _to_rfc3339(time_max)
    if query:
        params["q"] = query
    if page_token:
        params["pageToken"] = page_token

    url = f"{_GCAL_API_BASE}/calendars/{calendar_id}/events"
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=_auth_headers(access_token), params=params)
    except httpx.RequestError as exc:
        raise OAuthError(
            code="network_error",
            message=f"Network error during GCal list_events: {exc}",
            provider="google-calendar",
        ) from exc

    _raise_if_error(response, "list_events")
    data = response.json()
    items = data.get("items", []) or []
    events = [_normalize_event(e) for e in items]
    logger.info(
        "gcal list_events | calendar=%s count=%d query=%s",
        calendar_id,
        len(events),
        (query or "")[:60],
    )
    return {
        "events": events,
        "next_page_token": data.get("nextPageToken"),
        "time_zone": data.get("timeZone"),
    }


async def create_event(
    access_token: str,
    summary: str,
    start: datetime | str,
    end: datetime | str,
    attendees: list[str] | None = None,
    description: str = "",
    location: str | None = None,
    calendar_id: str = "primary",
    time_zone: str | None = None,
    send_updates: str = "none",
) -> dict[str, Any]:
    """Crea un nuovo evento su un calendario Google.

    REQUISITO SCOPE: questa funzione richiede lo scope
    ``https://www.googleapis.com/auth/calendar.events`` (read-write), NON
    incluso nello scope minimo registrato per ``"google-calendar"`` in
    ``oauth.PROVIDERS``. Implementare incremental authorization per chiamarla.

    Args:
        access_token: Bearer token OAuth con scope calendar.events (read-write).
        summary: titolo dell'evento.
        start: data/ora inizio (datetime aware o RFC 3339 string).
        end: data/ora fine.
        attendees: list di email partecipanti (es. ``["a@x.com", "b@y.com"]``).
        description: descrizione lunga (supporta HTML basic).
        location: testo location libero (es. ``"Negrar (VR)"`` o URL meeting).
        calendar_id: ID del calendario su cui creare l'evento.
        time_zone: IANA timezone string (es. ``"Europe/Rome"``). Default = TZ del calendar.
        send_updates: ``"all"`` (notifica tutti), ``"externalOnly"``, ``"none"`` (default).

    Returns:
        Event normalizzato (vedi ``_normalize_event``) con ``id`` e ``html_link``.

    Raises:
        OAuthError: se la creazione fallisce (insufficient_scope, network, quota).
    """
    start_str = _to_rfc3339(start)
    end_str = _to_rfc3339(end)

    body: dict[str, Any] = {
        "summary": summary,
        "start": {"dateTime": start_str},
        "end": {"dateTime": end_str},
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]
    if time_zone:
        body["start"]["timeZone"] = time_zone
        body["end"]["timeZone"] = time_zone

    url = f"{_GCAL_API_BASE}/calendars/{calendar_id}/events"
    params = {"sendUpdates": send_updates} if send_updates else {}

    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                headers=_auth_headers(access_token),
                json=body,
                params=params,
            )
    except httpx.RequestError as exc:
        raise OAuthError(
            code="network_error",
            message=f"Network error during GCal create_event: {exc}",
            provider="google-calendar",
        ) from exc

    _raise_if_error(response, "create_event")
    data = response.json()
    event = _normalize_event(data)
    logger.info(
        "gcal create_event | summary=%s start=%s attendees=%d id=%s",
        summary[:60],
        start_str,
        len(attendees or []),
        event.get("id"),
    )
    return event
