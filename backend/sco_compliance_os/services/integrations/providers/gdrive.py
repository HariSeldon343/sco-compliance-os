"""
gdrive.py — Wrapper Google Drive API v3 (REST) per SCO Compliance OS.

Architettura: wrapper sottile sopra ``httpx.AsyncClient`` che chiama gli
endpoint REST ufficiali Google Drive API v3.

Endpoint Drive API v3 usati (docs ufficiali Pattern Conv. 35):
    - GET /drive/v3/files
      https://developers.google.com/drive/api/v3/reference/files/list
    - GET /drive/v3/files/{id}?alt=media (binary download)
      https://developers.google.com/drive/api/v3/reference/files/get
    - POST https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart
      https://developers.google.com/drive/api/guides/manage-uploads

Scope richiesti:
    - ``https://www.googleapis.com/auth/drive.readonly`` per list_files + download_file
    - ``https://www.googleapis.com/auth/drive.file`` per upload_file (INCREMENTAL
      authorization: scope ristretto ai soli file creati dall'app, raccomandato
      per privacy invece di drive read-write completo).

Nota Google Workspace docs: i file Google nativi (Docs, Sheets, Slides) non
si scaricano direttamente con ``alt=media`` ma richiedono ``files/export``
con mime_type target (es. ``application/pdf``). Questa funzione non è ancora
implementata; usare ``download_file`` solo su MIME binari standard.
"""

from __future__ import annotations

import logging
import mimetypes
from typing import Any

import httpx

from ..base import OAuthError

logger = logging.getLogger(__name__)

# Base URL Google Drive API v3 — fonte: https://developers.google.com/drive/api/v3/reference
_GDRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
_GDRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"

_DEFAULT_TIMEOUT_SECONDS = 60.0  # upload/download possono essere lunghi

# Fields selector di default — limita la response shape (riduce bandwidth)
_DEFAULT_FILE_FIELDS = (
    "id,name,mimeType,size,createdTime,modifiedTime,owners(emailAddress,displayName),"
    "webViewLink,webContentLink,parents,trashed,iconLink,thumbnailLink"
)


# ─────────────────────────────────────────────────────────────────────
# Helper interni
# ─────────────────────────────────────────────────────────────────────


def _auth_headers(access_token: str) -> dict[str, str]:
    """Compone gli headers di autenticazione Bearer per Drive API."""
    return {"Authorization": f"Bearer {access_token}"}


def _raise_if_error(response: httpx.Response, operation: str) -> None:
    """Solleva ``OAuthError`` tipizzato se la response Drive API non è 2xx."""
    if 200 <= response.status_code < 300:
        return
    try:
        err_body = response.json()
    except ValueError:
        err_body = {"raw": response.text[:500]}
    err_obj = err_body.get("error", {}) if isinstance(err_body, dict) else {}
    raise OAuthError(
        code=err_obj.get("status", "gdrive_api_error"),
        message=f"Google Drive {operation} failed: {err_obj.get('message', 'unknown')}",
        provider="google-drive",
        http_status=response.status_code,
        raw_response=err_body if isinstance(err_body, dict) else {"raw": str(err_body)},
    )


def _normalize_file(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalizza la struct Drive API file in dict snello per consumer downstream."""
    owners = raw.get("owners", []) or []
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "mime_type": raw.get("mimeType"),
        "size_bytes": int(raw["size"]) if raw.get("size") else None,
        "created_time": raw.get("createdTime"),
        "modified_time": raw.get("modifiedTime"),
        "owner_email": owners[0].get("emailAddress") if owners else None,
        "owner_name": owners[0].get("displayName") if owners else None,
        "web_view_link": raw.get("webViewLink"),
        "web_content_link": raw.get("webContentLink"),
        "parents": raw.get("parents", []) or [],
        "trashed": raw.get("trashed", False),
        "icon_link": raw.get("iconLink"),
        "thumbnail_link": raw.get("thumbnailLink"),
    }


# ─────────────────────────────────────────────────────────────────────
# API pubbliche
# ─────────────────────────────────────────────────────────────────────


async def list_files(
    access_token: str,
    query: str | None = None,
    page_size: int = 50,
    page_token: str | None = None,
    order_by: str = "modifiedTime desc",
    include_trashed: bool = False,
    corpora: str = "user",
) -> dict[str, Any]:
    """Lista i file Google Drive con filtro opzionale via query syntax Drive.

    Args:
        access_token: Bearer token OAuth valido (scope drive.readonly).
        query: query Drive search (es. ``"mimeType='application/pdf' and modifiedTime > '2024-01-01T00:00:00'"``).
            Docs: https://developers.google.com/drive/api/guides/search-files
        page_size: numero file per pagina (1-1000, default 50).
        page_token: token paginazione.
        order_by: campo + direzione ordinamento (default ``modifiedTime desc``).
        include_trashed: se False (default) esclude i file nel cestino.
        corpora: scope ricerca: ``"user"`` (default, file utente),
            ``"drive"`` (specifico Shared Drive), ``"allDrives"`` (tutto).

    Returns:
        Dict con keys:
            - ``files``: list di file normalizzati (vedi ``_normalize_file``)
            - ``next_page_token``: token paginazione (None se ultima)
            - ``incomplete_search``: True se Drive non ha potuto cercare in tutti i corpora

    Raises:
        OAuthError: se la chiamata Drive API fallisce.
    """
    effective_query = query or ""
    if not include_trashed:
        # Compone la query escludendo i file trashed
        trash_filter = "trashed = false"
        effective_query = (
            f"({effective_query}) and {trash_filter}" if effective_query else trash_filter
        )

    params: dict[str, Any] = {
        "pageSize": max(1, min(page_size, 1000)),
        "orderBy": order_by,
        "fields": f"nextPageToken,incompleteSearch,files({_DEFAULT_FILE_FIELDS})",
        "corpora": corpora,
    }
    if effective_query:
        params["q"] = effective_query
    if page_token:
        params["pageToken"] = page_token

    url = f"{_GDRIVE_API_BASE}/files"
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=_auth_headers(access_token), params=params)
    except httpx.RequestError as exc:
        raise OAuthError(
            code="network_error",
            message=f"Network error during GDrive list_files: {exc}",
            provider="google-drive",
        ) from exc

    _raise_if_error(response, "list_files")
    data = response.json()
    items = data.get("files", []) or []
    files = [_normalize_file(f) for f in items]
    logger.info(
        "gdrive list_files | query=%s count=%d has_next=%s",
        effective_query[:80],
        len(files),
        bool(data.get("nextPageToken")),
    )
    return {
        "files": files,
        "next_page_token": data.get("nextPageToken"),
        "incomplete_search": data.get("incompleteSearch", False),
    }


async def download_file(
    access_token: str,
    file_id: str,
    acknowledge_abuse: bool = False,
) -> bytes:
    """Scarica il contenuto binario di un file Google Drive.

    Limitazioni:
        - Funziona per MIME standard (PDF, DOCX, immagini, ZIP, ecc.) tramite
          ``alt=media``.
        - NON funziona per file Google nativi (Docs/Sheets/Slides): per quelli
          serve l'endpoint ``files/{id}/export?mimeType=...`` (non implementato qui).
        - File >10MB ritornano ``acknowledgeAbuse=true`` se ritenuti potenzialmente
          malevoli da Google scan. Settare ``acknowledge_abuse=True`` per scaricarli.

    Args:
        access_token: Bearer token OAuth valido (scope drive.readonly).
        file_id: ID del file Drive (da ``list_files``).
        acknowledge_abuse: ack se Google flagga il file come potenziale rischio.

    Returns:
        Contenuto binario del file (bytes).

    Raises:
        OAuthError: se il download fallisce (insufficient_scope, file_not_found,
            abuse_warning senza ack, network).
    """
    params: dict[str, Any] = {"alt": "media"}
    if acknowledge_abuse:
        params["acknowledgeAbuse"] = "true"

    url = f"{_GDRIVE_API_BASE}/files/{file_id}"
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=_auth_headers(access_token), params=params)
    except httpx.RequestError as exc:
        raise OAuthError(
            code="network_error",
            message=f"Network error during GDrive download_file: {exc}",
            provider="google-drive",
        ) from exc

    _raise_if_error(response, "download_file")
    content = response.content
    logger.info(
        "gdrive download_file | file_id=%s size_bytes=%d", file_id, len(content)
    )
    return content


async def upload_file(
    access_token: str,
    name: str,
    content: bytes,
    mime_type: str | None = None,
    parents: list[str] | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Carica un nuovo file su Google Drive (multipart upload, fino a 5MB).

    Per file >5MB serve resumable upload (non implementato qui).
    Docs: https://developers.google.com/drive/api/guides/manage-uploads

    REQUISITO SCOPE: questa funzione richiede uno scope write tra:
        - ``https://www.googleapis.com/auth/drive.file`` (consigliato, scoped ai
          file creati dall'app)
        - ``https://www.googleapis.com/auth/drive`` (full access, sconsigliato)
    NON incluso nello scope minimo registrato per ``"google-drive"`` in
    ``oauth.PROVIDERS``. Implementare incremental authorization per chiamarla.

    Args:
        access_token: Bearer token OAuth con scope write (drive.file o drive).
        name: nome del file (es. ``"audit-report.pdf"``).
        content: contenuto binario.
        mime_type: MIME type (es. ``"application/pdf"``). Se None, inferito da name.
        parents: list di folder ID parenti (root utente se None).
        description: descrizione opzionale.

    Returns:
        File normalizzato (vedi ``_normalize_file``) con ``id`` e ``web_view_link``.

    Raises:
        OAuthError: se l'upload fallisce (insufficient_scope, quota, network).
    """
    if mime_type is None:
        guessed, _ = mimetypes.guess_type(name)
        mime_type = guessed or "application/octet-stream"

    metadata: dict[str, Any] = {"name": name, "mimeType": mime_type}
    if parents:
        metadata["parents"] = parents
    if description:
        metadata["description"] = description

    # Multipart upload: metadata JSON + content binary in un'unica request.
    # httpx supporta multipart via parameter `files` (dict di tuple
    # (filename, content, mime_type)).
    # Per multipart misto JSON+binary servono due "parts" — usiamo httpx Multipart
    # ricostruito manualmente come richiesto da Drive API.
    import json
    import secrets as _secrets

    boundary = f"sco_compliance_os_{_secrets.token_hex(8)}"
    body_parts = [
        f"--{boundary}",
        "Content-Type: application/json; charset=UTF-8",
        "",
        json.dumps(metadata),
        f"--{boundary}",
        f"Content-Type: {mime_type}",
        "",
    ]
    body_prefix = ("\r\n".join(body_parts) + "\r\n").encode("utf-8")
    body_suffix = (f"\r\n--{boundary}--\r\n").encode("utf-8")
    body = body_prefix + content + body_suffix

    url = f"{_GDRIVE_UPLOAD_BASE}/files?uploadType=multipart"
    headers = {
        **_auth_headers(access_token),
        "Content-Type": f"multipart/related; boundary={boundary}",
    }
    params = {"fields": _DEFAULT_FILE_FIELDS}

    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.post(url, headers=headers, content=body, params=params)
    except httpx.RequestError as exc:
        raise OAuthError(
            code="network_error",
            message=f"Network error during GDrive upload_file: {exc}",
            provider="google-drive",
        ) from exc

    _raise_if_error(response, "upload_file")
    data = response.json()
    file_obj = _normalize_file(data)
    logger.info(
        "gdrive upload_file | name=%s mime=%s size=%d id=%s",
        name,
        mime_type,
        len(content),
        file_obj.get("id"),
    )
    return file_obj
