"""Hook post-turn: estrazione preferenze utente + persistenza profile_store.

Chiamato async DOPO ogni response agent generata, riceve user_message +
optional assistant_response + optional turn_id (conversation+message ids).

Pattern Conv. 41 tracciatura: ogni invocazione logga count preferenze
estratte + persisted (zero se nessun pattern matched). Niente exception
propagation al chiamante: errori interni loggati ma NON bloccano lo stream
chat (l'apprendimento e best-effort, lo stream LLM e load-bearing).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.learning.profile_store import (
    upsert_preference,
)
from sco_compliance_os.services.learning.user_profile import (
    extract_preferences,
)

logger = get_logger(__name__)


async def on_turn_complete(
    turn_data: dict[str, Any],
    *,
    tenant_id: str = "local",
    db_path: Path | None = None,
) -> int:
    """Estrae preferenze da turn_data['user_message'] e persiste via profile_store.

    Args:
        turn_data: dict con almeno chiave 'user_message' (str). Chiavi opzionali:
            - 'assistant_response': str (non usata in v0.1, riservato a future
              estensioni come learning da risposte / clarification).
            - 'turn_id': str (es. "conv_<uuid>__msg_<uuid>") per audit trail.
        tenant_id: tenant ID (default 'local').
        db_path: override del path DB profile_store (testing).

    Returns:
        Numero di preferenze effettivamente persisted.

    Note:
        - Errori interni vengono loggati con logger.exception MA non sollevati.
          Il learning e best-effort, non load-bearing per lo stream chat.
        - Funzione async-safe: puo essere chiamata via asyncio.create_task()
          dal lifespan del chat_stream senza bloccare lo yield SSE.
    """
    user_message = turn_data.get("user_message", "") or ""
    turn_id = turn_data.get("turn_id")

    if not user_message.strip():
        logger.debug("post_turn_hook.skip empty_user_message")
        return 0

    try:
        preferences = extract_preferences(
            user_message,
            source_turn_id=turn_id,
            cap=5,
        )
    except Exception as exc:
        logger.exception(
            "post_turn_hook.extract_failed",
            error=str(exc),
            turn_id=turn_id,
        )
        return 0

    if not preferences:
        return 0

    persisted = 0
    for pref in preferences:
        try:
            await upsert_preference(pref, tenant_id=tenant_id, db_path=db_path)
            persisted += 1
        except Exception as exc:
            logger.exception(
                "post_turn_hook.upsert_failed",
                error=str(exc),
                slug=pref.slug,
                turn_id=turn_id,
            )

    logger.info(
        "post_turn_hook.completed",
        extracted=len(preferences),
        persisted=persisted,
        tenant_id=tenant_id,
        turn_id=turn_id,
    )
    return persisted


def schedule_on_turn_complete(
    turn_data: dict[str, Any],
    *,
    tenant_id: str = "local",
    db_path: Path | None = None,
) -> asyncio.Task[int]:
    """Schedula on_turn_complete come task background fire-and-forget.

    Usata dal chat_stream finally block per non bloccare la chiusura dello
    StreamingResponse SSE in attesa dell'estrazione + N upsert SQLite.

    Args:
        turn_data: dict come on_turn_complete.
        tenant_id: tenant ID.
        db_path: override del path DB.

    Returns:
        asyncio.Task non-awaited. Caller puo ignorare o awaitare per testing.
    """
    return asyncio.create_task(on_turn_complete(turn_data, tenant_id=tenant_id, db_path=db_path))
