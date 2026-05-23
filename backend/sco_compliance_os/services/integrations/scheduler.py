"""
scheduler.py — Loop di fetch periodico per i connettori attivi.

Pattern: ogni N minuti (default 20, configurabile) scorre i connettori
attivi (token presenti nel keyring) e invoca ``fetch_data()`` con
checkpoint incrementale ``since=last_fetch_at``. I MemoryChunk prodotti
vengono passati al Memory Tree (TODO Wave 2: integrazione concreta).

Tecnologia: ``asyncio`` task con loop ``while True`` + ``asyncio.sleep``.
Alternativa valutata: APScheduler — scartata per Wave 1 perché aggiunge
dipendenza extra senza valore concreto per il loop singolo.

Error handling:
    - Errori OAuth (token scaduto, refresh fallito): log + retry alla
      prossima iterazione (no escalation immediata).
    - Errori network / 5xx: backoff esponenziale (1m, 2m, 4m, max 30m).
    - Errori applicativi (parsing, schema): log + skip chunk corrotto.

Pattern Karpathy "single source of truth" applicato al checkpoint:
``last_fetch_at`` vive su filesystem (``~/.sco/integrations/checkpoints.json``)
o keyring; mai duplicato in più sorgenti.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .base import OAuthError
from .registry import ConnectorRegistry
from .token_store import get_tokens, list_providers, store_tokens

if TYPE_CHECKING:
    from .base import BaseConnector, MemoryChunk

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 20 * 60  # 20 min, pattern industry-standard
MAX_BACKOFF_SECONDS = 30 * 60


class ConnectorScheduler:
    """Scheduler asyncio per fetch periodico dei connettori attivi."""

    def __init__(
        self,
        user_id: str,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        connector_credentials: dict[str, tuple[str, str, str]] | None = None,
    ) -> None:
        """Inizializza scheduler.

        Args:
            user_id: utente SCO per cui fare fetch.
            interval_seconds: intervallo fra fetch (default 1200s = 20min).
            connector_credentials: mapping ``{slug: (client_id, client_secret, redirect_uri)}``.
                Necessario per istanziare i connector concreti.
        """
        self.user_id = user_id
        self.interval_seconds = interval_seconds
        self.connector_credentials = connector_credentials or {}
        self._task: asyncio.Task[None] | None = None
        self._running = False
        # backoff per-connector in caso di errori transitori
        self._backoff: dict[str, int] = {}
        # checkpoint per-connector
        self._last_fetch: dict[str, datetime] = {}

    async def start(self) -> None:
        """Avvia il loop di scheduling in background."""
        if self._running:
            logger.warning("scheduler already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="sco-integrations-scheduler")
        logger.info(
            "scheduler started | user=%s interval_seconds=%d",
            self.user_id,
            self.interval_seconds,
        )

    async def stop(self) -> None:
        """Stop graceful dello scheduler."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("scheduler stopped")

    async def _loop(self) -> None:
        """Loop principale: ogni N secondi scorri connettori attivi e fetch."""
        while self._running:
            try:
                await self._run_iteration()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # mai uccidere il loop per eccezioni applicative
                logger.exception("scheduler iteration crashed | err=%s", exc)
            await asyncio.sleep(self.interval_seconds)

    async def _run_iteration(self) -> None:
        """Singola iterazione di fetch su tutti i connettori attivi."""
        known_slugs = ConnectorRegistry.list_slugs()
        active_slugs = list_providers(self.user_id, known_slugs)
        logger.info("scheduler iteration | active_connectors=%d", len(active_slugs))
        for slug in active_slugs:
            # rispetta backoff se presente
            backoff = self._backoff.get(slug, 0)
            if backoff > 0:
                self._backoff[slug] = max(0, backoff - self.interval_seconds)
                if self._backoff[slug] > 0:
                    logger.debug("skip %s due to backoff %ds", slug, self._backoff[slug])
                    continue
            await self._fetch_one(slug)

    async def _fetch_one(self, slug: str) -> None:
        """Fetch da un singolo connector con error handling."""
        connector_cls = ConnectorRegistry.get(slug)
        if connector_cls is None:
            logger.warning("connector class not found in registry | slug=%s", slug)
            return
        creds = self.connector_credentials.get(slug)
        if creds is None:
            logger.warning("no OAuth credentials configured for connector | slug=%s", slug)
            return
        client_id, client_secret, redirect_uri = creds
        connector_instance: BaseConnector = connector_cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
        tokens = get_tokens(slug, self.user_id)
        if tokens is None:
            logger.info("no tokens for active connector — skip | slug=%s", slug)
            return
        try:
            refreshed = await connector_instance.refresh_token_if_needed(tokens)
            if refreshed is not tokens:
                store_tokens(slug, self.user_id, refreshed)
                tokens = refreshed
            since = self._last_fetch.get(slug)
            chunks: list[MemoryChunk] = await connector_instance.fetch_data(tokens, since=since)
            await self._dispatch_chunks(slug, chunks)
            self._last_fetch[slug] = datetime.now(UTC)
            self._backoff[slug] = 0  # reset backoff su successo
            logger.info("fetch ok | slug=%s chunks=%d", slug, len(chunks))
        except OAuthError as exc:
            logger.error("OAuth error during fetch | slug=%s err=%s", slug, exc)
            self._apply_backoff(slug)
        except Exception as exc:
            logger.exception("generic error during fetch | slug=%s err=%s", slug, exc)
            self._apply_backoff(slug)

    def _apply_backoff(self, slug: str) -> None:
        """Aumenta backoff exponential, capped a MAX_BACKOFF_SECONDS."""
        current = self._backoff.get(slug, 0)
        next_backoff = min(MAX_BACKOFF_SECONDS, max(60, current * 2))
        self._backoff[slug] = next_backoff
        logger.info("backoff applied | slug=%s next_seconds=%d", slug, next_backoff)

    async def _dispatch_chunks(self, slug: str, chunks: list[MemoryChunk]) -> None:
        """Ingest chunks dal connector → Memory Tree (Conv. 43 Smart File Injection).

        Pipeline: ogni MemoryChunk → markdown ben formato → ingest_text con provenance
        connector + external_id + occurred_at. Idempotente su source_id (dedupe MD5
        deterministico = sha256(connector + external_id)).
        """
        if not chunks:
            return

        # Import lazy per evitare circular dependency con services.memory
        from sco_compliance_os.services.memory.ingest import ingest_text

        ingested_count = 0
        for chunk in chunks:
            # Formato markdown del chunk per Memory Tree (heading + body + metadata)
            md_body = (
                f"# {chunk.title}\n\n"
                f"**Source**: {chunk.source_connector} | "
                f"**Kind**: {chunk.kind} | "
                f"**Occurred**: {chunk.occurred_at.isoformat()}\n\n"
                f"{chunk.body}\n"
            )
            # Provenance Conv. 43 enforcement
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
