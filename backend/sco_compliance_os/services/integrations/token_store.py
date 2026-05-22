"""
token_store.py — Storage cifrato dei token OAuth via OS keyring.

Pattern di sicurezza: i token OAuth (access_token + refresh_token) vivono
SOLO nel keyring nativo del sistema operativo (Windows Credential Manager
su Win, Keychain su macOS, GNOME Keyring/KWallet su Linux). MAI plaintext
su disk, MAI in DB SQLite.

Libreria usata: ``keyring`` (Python, cross-platform).
    docs ufficiali: https://pypi.org/project/keyring/
    repo: https://github.com/jaraco/keyring

Pattern Conv. 35 RESEARCH-BEFORE-ACT enforcement: tutte le API usate sono
documentate ufficialmente sul repo keyring (`get_password`, `set_password`,
`delete_password`). Non si inventano API.

Format storage:

- ``service_name``: ``"sco-compliance-os:integrations:{provider_slug}"``
- ``username``: ``user_id`` dell'utente SCO
- ``password``: JSON serialized di ``OAuthTokens`` (con ISO 8601 per datetime)

Per multi-account stesso provider (es. 2 account Gmail) si può comporre
``user_id`` come ``"{user_id}:{account_label}"``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from .base import OAuthError, OAuthTokens

logger = logging.getLogger(__name__)

SERVICE_NAME_PREFIX = "sco-compliance-os:integrations"


def _service_name(provider_slug: str) -> str:
    """Compone il service_name del keyring per un dato provider."""
    return f"{SERVICE_NAME_PREFIX}:{provider_slug}"


def _serialize_tokens(tokens: OAuthTokens) -> str:
    """Serializza OAuthTokens in JSON stringa.

    Le datetime sono convertite in ISO 8601 (UTC). Il campo raw_response
    è incluso per audit / debug ma non è mai usato runtime.
    """
    payload = asdict(tokens)
    # datetime -> ISO 8601
    payload["expires_at"] = tokens.expires_at.isoformat()
    return json.dumps(payload, ensure_ascii=False)


def _deserialize_tokens(blob: str) -> OAuthTokens:
    """Deserializza JSON stringa in OAuthTokens."""
    data = json.loads(blob)
    data["expires_at"] = datetime.fromisoformat(data["expires_at"])
    return OAuthTokens(**data)


def store_tokens(provider_slug: str, user_id: str, tokens: OAuthTokens) -> None:
    """Cifra e persiste i token OAuth nel keyring OS.

    Args:
        provider_slug: slug del connector (es. ``"gmail"``).
        user_id: identificatore utente SCO.
        tokens: token da memorizzare.

    Raises:
        OAuthError: se il keyring non è disponibile o la scrittura fallisce.
    """
    try:
        blob = _serialize_tokens(tokens)
        keyring.set_password(_service_name(provider_slug), user_id, blob)
        logger.info(
            "tokens stored | provider=%s user=%s expires_at=%s",
            provider_slug,
            user_id,
            tokens.expires_at.isoformat(),
        )
    except KeyringError as exc:
        logger.error("keyring write failed | provider=%s err=%s", provider_slug, exc)
        raise OAuthError(
            code="keyring_write_failed",
            message=f"Impossibile salvare token nel keyring OS: {exc}",
            provider=provider_slug,
        ) from exc


def get_tokens(provider_slug: str, user_id: str) -> OAuthTokens | None:
    """Recupera i token OAuth dal keyring OS.

    Args:
        provider_slug: slug del connector.
        user_id: identificatore utente SCO.

    Returns:
        ``OAuthTokens`` se presenti, ``None`` se non esistono (utente
        non ha mai connesso questo provider).

    Raises:
        OAuthError: se il keyring è disponibile ma la lettura fallisce
            (es. payload corrotto).
    """
    try:
        blob = keyring.get_password(_service_name(provider_slug), user_id)
        if blob is None:
            return None
        return _deserialize_tokens(blob)
    except KeyringError as exc:
        logger.error("keyring read failed | provider=%s err=%s", provider_slug, exc)
        raise OAuthError(
            code="keyring_read_failed",
            message=f"Impossibile leggere token dal keyring OS: {exc}",
            provider=provider_slug,
        ) from exc
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.error(
            "keyring payload corrupted | provider=%s user=%s err=%s",
            provider_slug,
            user_id,
            exc,
        )
        raise OAuthError(
            code="token_payload_corrupted",
            message=f"Payload token corrotto: {exc}",
            provider=provider_slug,
        ) from exc


def delete_tokens(provider_slug: str, user_id: str) -> bool:
    """Rimuove i token OAuth dal keyring (su disconnect dall'utente).

    Args:
        provider_slug: slug del connector.
        user_id: identificatore utente SCO.

    Returns:
        ``True`` se i token erano presenti e sono stati rimossi, ``False``
        se non erano presenti (no-op idempotente).

    Raises:
        OAuthError: se il keyring è disponibile ma la cancellazione fallisce.
    """
    try:
        keyring.delete_password(_service_name(provider_slug), user_id)
        logger.info("tokens deleted | provider=%s user=%s", provider_slug, user_id)
        return True
    except PasswordDeleteError:
        # password non esisteva — comportamento idempotente OK
        return False
    except KeyringError as exc:
        logger.error("keyring delete failed | provider=%s err=%s", provider_slug, exc)
        raise OAuthError(
            code="keyring_delete_failed",
            message=f"Impossibile cancellare token dal keyring OS: {exc}",
            provider=provider_slug,
        ) from exc


def list_providers(user_id: str, known_slugs: list[str]) -> list[str]:
    """Ritorna gli slug dei provider connessi per l'utente.

    Nota: la libreria ``keyring`` cross-platform non espone una API
    di enumerazione universale (alcuni backend la supportano, altri no).
    Il workaround è iterare su ``known_slugs`` (forniti dal ``ConnectorRegistry``)
    e probare ``get_password`` per ciascuno.

    Args:
        user_id: identificatore utente SCO.
        known_slugs: lista degli slug noti (dal ``ConnectorRegistry``).

    Returns:
        Lista degli slug per cui esistono token nel keyring.
    """
    connected: list[str] = []
    for slug in known_slugs:
        try:
            if keyring.get_password(_service_name(slug), user_id) is not None:
                connected.append(slug)
        except KeyringError as exc:
            logger.warning(
                "keyring list probe failed | provider=%s err=%s", slug, exc
            )
            # Non escalate: il provider verrà semplicemente segnato come disconnected.
            continue
    return connected
