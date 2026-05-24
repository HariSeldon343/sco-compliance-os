"""
scheduler.py — Provider di fetch handlers per i connettori OAuth.

**Refactor W2 v0.3.0**: la responsabilita' di "scheduling/timing" (loop
periodico, throttle no-overlap, activity log, round-robin, cooldown) e' stata
estratta in :class:`sco_compliance_os.services.integrations.auto_fetch_loop.AutoFetchLoop`.

Questo modulo mantiene:

1. La logica **stable** di **fetch concreto per-connector** (chiamata
   keyring token store + connector class + ``fetch_data`` + dispatch chunk
   verso Memory Tree). Esposta come :func:`fetch_connector` (interfaccia
   stabile).
2. Una classe **legacy proxy** :class:`ConnectorScheduler` che mantiene
   l'API ``start()`` / ``stop()`` chiamata da ``main.py`` esistente.
   Internamente delega tutto a :class:`AutoFetchLoop`. Emette
   ``DeprecationWarning`` via logger (Conv. 35 enforcement) ma non rompe.

Error handling (invariato W1):

- Errori OAuth (token scaduto, refresh fallito): catturati come ``errors[]``
  nell'``AutoFetchOutcome``. Il loop incrementa ``consecutive_failures``
  per quel connector; al raggiungimento di ``failure_threshold`` attiva
  cooldown.
- Errori network / 5xx: stesso pattern (catturati come errors[]).
- Errori applicativi (parsing, schema): log + chunk corrotto skippato in
  :func:`_dispatch_chunks`.

Pattern SCO "single source of truth" applicato al checkpoint:
``last_fetch_at`` per-connector vive sul ``connector_state`` interno dello
:class:`AutoFetchLoop` (in-memory, no DB). Pattern intenzionalmente diverso da
W1 "checkpoints.json filesystem": il loop e' single-process e i checkpoint
persistenti non sono richiesti per il blueprint Wave 2.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .auto_fetch_loop import (
    DEFAULT_INTERVAL_SECONDS as AUTOFETCH_DEFAULT_INTERVAL_SECONDS,
)
from .auto_fetch_loop import (
    AutoFetchLoop,
    AutoFetchOutcome,
)
from .base import OAuthError
from .registry import ConnectorRegistry
from .token_store import get_tokens, list_providers, store_tokens

if TYPE_CHECKING:
    from .base import BaseConnector, MemoryChunk

logger = logging.getLogger(__name__)

# Re-export costanti per backwards-compat con codice esistente che le importava
# da .scheduler (es. main.py pre-refactor).
DEFAULT_INTERVAL_SECONDS = AUTOFETCH_DEFAULT_INTERVAL_SECONDS  # 1200s = 20min
MAX_BACKOFF_SECONDS = 30 * 60  # 30 min, parametro storico W1


# --------------------------------------------------------------------------------------
# Public fetch handler — interface stable per AutoFetchLoop e altri caller
# --------------------------------------------------------------------------------------


async def fetch_connector(
    connector_name: str,
    user_id: str,
    *,
    connector_credentials: dict[str, tuple[str, str, str]] | None = None,
) -> AutoFetchOutcome:
    """Esegue il fetch concreto per UN connector e ritorna outcome strutturato.

    Interfaccia stable consumer del :class:`AutoFetchLoop`: il loop invoca
    questa funzione come ``fetch_handler`` e ne usa l'outcome per aggiornare
    lo stato round-robin + cooldown.

    Args:
        connector_name: nome del connector (slug del registry: ``"gmail"``,
            ``"gcal"``, ``"gdrive"``, ``"slack"``, ``"github"``, ...).
        user_id: identificatore utente SCO (email license-bound).
        connector_credentials: mapping ``{slug: (client_id, client_secret,
            redirect_uri)}``. Se None o slug mancante, viene loggato un
            warning ``no_credentials`` ma non sollevata eccezione (l'outcome
            riportera' un error string + fetched_count=0).

    Returns:
        :class:`AutoFetchOutcome` con:

        - ``connector_name``: nome del connector (passato in input).
        - ``fetched_count``: numero di :class:`MemoryChunk` ingestiti.
        - ``errors``: lista di stringhe di errore (vuoto se success totale).
        - ``used_oauth``: True se il fetch ha effettivamente usato token
          OAuth reali (False per stub / no-credentials / no-tokens).
        - ``duration_seconds``: 0.0 (settato dal loop, non da qui).
        - ``cancelled``: False (gestito dal loop tramite token).

    Nota cabling: in W2 v0.3.0 i 3 connector Google (gmail, gcal, gdrive) hanno
    implementazioni stub. Il cabling httpx reale e' carry-over Wave 3 v0.4.0
    (vedi blueprint Wave 3 sezione 4 + ``services.integrations.gmail_connector``,
    ``google_calendar_connector``, ``google_drive_connector``).
    """
    # 1. Lookup connector class nel registry.
    connector_cls = ConnectorRegistry.get(connector_name)
    if connector_cls is None:
        msg = f"connector_class_not_in_registry: {connector_name}"
        logger.warning(msg)
        return AutoFetchOutcome(
            connector_name=connector_name,
            fetched_count=0,
            errors=[msg],
            used_oauth=False,
        )

    # 2. Recupera credentials applicative (client_id/client_secret/redirect_uri).
    creds_map = connector_credentials or {}
    creds = creds_map.get(connector_name)
    if creds is None:
        msg = f"no_oauth_credentials_configured: {connector_name}"
        logger.info(msg)
        return AutoFetchOutcome(
            connector_name=connector_name,
            fetched_count=0,
            errors=[msg],
            used_oauth=False,
        )
    client_id, client_secret, redirect_uri = creds
    connector_instance: BaseConnector = connector_cls(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )

    # 3. Recupera token utente da keyring.
    tokens = get_tokens(connector_name, user_id)
    if tokens is None:
        msg = f"no_tokens_for_user: {connector_name}/{user_id}"
        logger.info(msg)
        return AutoFetchOutcome(
            connector_name=connector_name,
            fetched_count=0,
            errors=[msg],
            used_oauth=False,
        )

    # 4. Refresh + fetch + dispatch.
    errors: list[str] = []
    try:
        refreshed = await connector_instance.refresh_token_if_needed(tokens)
        if refreshed is not tokens:
            store_tokens(connector_name, user_id, refreshed)
            tokens = refreshed
        chunks: list[MemoryChunk] = await connector_instance.fetch_data(tokens, since=None)
        ingested = await _dispatch_chunks(connector_name, chunks)
        logger.info(
            "fetch ok | slug=%s chunks=%d ingested=%d",
            connector_name,
            len(chunks),
            ingested,
        )
        return AutoFetchOutcome(
            connector_name=connector_name,
            fetched_count=ingested,
            errors=[],
            used_oauth=True,
        )
    except OAuthError as exc:
        errors.append(f"OAuthError[{exc.code}]: {exc.message}")
        logger.error("OAuth error during fetch | slug=%s err=%s", connector_name, exc)
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        logger.exception("generic error during fetch | slug=%s err=%s", connector_name, exc)

    return AutoFetchOutcome(
        connector_name=connector_name,
        fetched_count=0,
        errors=errors,
        used_oauth=True,  # provato a usare OAuth ma fallito
    )


async def _dispatch_chunks(slug: str, chunks: list[MemoryChunk]) -> int:
    """Ingest chunks dal connector verso il Memory Tree (Conv. 43).

    Pipeline: ogni :class:`MemoryChunk` -> markdown ben formato -> ingest_text
    con provenance connector + external_id + occurred_at. Idempotente su
    source_id (dedupe MD5 deterministico = sha256(connector + external_id)).

    Returns:
        Numero di chunk effettivamente ingestiti (dedupe).
    """
    if not chunks:
        return 0
    # Import lazy per evitare circular dependency con services.memory
    from sco_compliance_os.services.memory.ingest import ingest_text

    ingested_count = 0
    for chunk in chunks:
        md_body = (
            f"# {chunk.title}\n\n"
            f"**Source**: {chunk.source_connector} | "
            f"**Kind**: {chunk.kind} | "
            f"**Occurred**: {chunk.occurred_at.isoformat()}\n\n"
            f"{chunk.body}\n"
        )
        provenance = {
            "connector_slug": slug,
            "external_id": chunk.external_id,
            "kind": chunk.kind,
            "occurred_at": chunk.occurred_at.isoformat(),
            "ingested_at": chunk.ingested_at.isoformat(),
            "tags": chunk.tags,
            **chunk.metadata,
        }
        try:
            await ingest_text(
                md_body,
                source_type="connector",
                source_id=f"{slug}:{chunk.external_id}",
                source_path=f"connector://{slug}/{chunk.external_id}",
                provenance=provenance,
            )
            ingested_count += 1
        except Exception as exc:
            logger.warning(
                "scheduler.dispatch.ingest_failed | slug=%s external_id=%s err=%s",
                slug,
                chunk.external_id,
                exc,
            )
    logger.info(
        "scheduler.dispatch | slug=%s chunks=%d ingested=%d",
        slug,
        len(chunks),
        ingested_count,
    )
    return ingested_count


# --------------------------------------------------------------------------------------
# Legacy proxy ConnectorScheduler (backwards-compat con main.py W1)
# --------------------------------------------------------------------------------------


class ConnectorScheduler:
    """**LEGACY PROXY (W1 backwards-compat)** verso :class:`AutoFetchLoop`.

    Mantiene l'API ``start()`` / ``stop()`` chiamata da ``main.py`` esistente
    senza modifiche al sito di chiamata. Internamente costruisce e delega a
    una istanza :class:`AutoFetchLoop`.

    Emette ``DeprecationWarning`` via logger (Conv. 35 enforcement):
    nuovo codice dovrebbe istanziare direttamente :class:`AutoFetchLoop`.
    """

    def __init__(
        self,
        user_id: str,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        connector_credentials: dict[str, tuple[str, str, str]] | None = None,
    ) -> None:
        """Inizializza il proxy.

        Args:
            user_id: utente SCO per cui fare fetch.
            interval_seconds: intervallo fra fetch (default 1200s = 20min).
            connector_credentials: mapping
                ``{slug: (client_id, client_secret, redirect_uri)}``.
        """
        logger.warning(
            "ConnectorScheduler is DEPRECATED — use AutoFetchLoop directly "
            "(legacy proxy, will be removed in v0.5.0). "
            "user_id=%s interval=%ds",
            user_id,
            interval_seconds,
        )
        self.user_id = user_id
        self.interval_seconds = interval_seconds
        self.connector_credentials = connector_credentials or {}

        # Cattura le credentials per closure dentro fetch_handler delegato.
        creds_capture = dict(self.connector_credentials)

        async def _handler(connector_name: str, uid: str) -> AutoFetchOutcome:
            return await fetch_connector(
                connector_name,
                uid,
                connector_credentials=creds_capture,
            )

        # Connectors round-robin: usa la lista di slug presenti nel registry
        # E che hanno gia' token nel keyring (list_providers). Se la lista
        # e' vuota, fallback ai 3 default Google del blueprint.
        known_slugs = ConnectorRegistry.list_slugs()
        active_slugs = list_providers(user_id, known_slugs) if known_slugs else []
        connectors = active_slugs if active_slugs else ["gmail", "gcal", "gdrive"]

        self._loop = AutoFetchLoop(
            user_id=user_id,
            interval_seconds=interval_seconds,
            connectors=connectors,
            fetch_handler=_handler,
        )

    async def start(self) -> None:
        """Avvia il loop di scheduling in background (delega a AutoFetchLoop)."""
        started = await self._loop.start()
        logger.info(
            "scheduler.legacy.start | user=%s interval=%ds started=%s",
            self.user_id,
            self.interval_seconds,
            started,
        )

    async def stop(self) -> None:
        """Stop graceful dello scheduler (delega a AutoFetchLoop)."""
        await self._loop.stop()
        logger.info("scheduler.legacy.stop")

    def is_running(self) -> bool:
        """True se il loop sottostante e' attivo."""
        return self._loop.is_running()

    @property
    def auto_fetch_loop(self) -> AutoFetchLoop:
        """Accesso diretto al :class:`AutoFetchLoop` sottostante (debug / test)."""
        return self._loop
