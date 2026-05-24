"""Simple async pub/sub event bus singleton.

Pattern Conv. 41 tracciatura: ogni publish/subscribe loggato con event_type +
subscriber count. Errori nei subscriber catturati e loggati ma NON propagati al
publisher (best-effort delivery, isolamento blast radius).

Pattern Conv. 47 single source of truth: la singleton vive in-process, NON
persistita in DB. Ogni restart del backend resetta la subscription list.

Use case principale v0.6.0: auto-trigger skill loader runtime su evento
``vault.registered`` emesso da POST /api/vault/add. Background task
asyncio sottoscritto al lifespan, esegue os-setup + os-ottimizzatore in
sequenza creando una conversation system-generated.

Esempio:
    >>> bus = EventBus.instance()
    >>> async def handler(payload: dict[str, Any]) -> None:
    ...     print(payload["path"])
    >>> bus.subscribe("vault.registered", handler)
    >>> await bus.publish("vault.registered", {"path": "/tmp/vault"})
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from sco_compliance_os.core.logging_setup import get_logger

logger = get_logger(__name__)


# Type alias per handler async che riceve un dict payload.
EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    """Singleton async pub/sub bus.

    Le subscription vivono in memoria (no DB persistence). Multiple handler
    per stesso event_type ammessi. publish() invoca tutti i handler in
    parallelo via asyncio.gather() con return_exceptions=True per isolare
    errori (un handler che fallisce NON blocca gli altri).
    """

    _instance: EventBus | None = None

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = {}

    @classmethod
    def instance(cls) -> EventBus:
        """Ritorna singleton instance, creandola se necessario."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (utile per testing isolato)."""
        cls._instance = None

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Aggiungi un handler async per un event_type.

        Args:
            event_type: identificativo evento (es. "vault.registered").
            handler: callable async che riceve dict payload.
        """
        self._subscribers.setdefault(event_type, []).append(handler)
        logger.info(
            "event_bus.subscribed",
            event_type=event_type,
            handlers_count=len(self._subscribers[event_type]),
        )

    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """Rimuovi un handler. Ritorna True se rimosso, False se non trovato."""
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
            logger.info(
                "event_bus.unsubscribed",
                event_type=event_type,
                handlers_count=len(handlers),
            )
            return True
        return False

    async def publish(self, event_type: str, payload: dict[str, Any]) -> int:
        """Pubblica un evento a tutti i subscriber. Best-effort delivery.

        Args:
            event_type: identificativo evento.
            payload: dict con dati evento (path, conv_id, ecc.).

        Returns:
            Numero di handler invocati con successo (no exception).
        """
        handlers = list(self._subscribers.get(event_type, []))
        # Conv. 41 tracciatura: log dettagliato anche su zero subscriber
        # (sintomo diagnostico di mancato wiring lifespan).
        logger.info(
            "events.publish",
            event_type=event_type,
            subscribers_count=len(handlers),
            payload_keys=list(payload.keys()),
        )
        if not handlers:
            return 0

        results = await asyncio.gather(
            *(handler(payload) for handler in handlers),
            return_exceptions=True,
        )

        success_count = 0
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.exception(
                    "event_bus.handler_error",
                    event_type=event_type,
                    handler_idx=idx,
                    error=str(result),
                )
            else:
                success_count += 1
        logger.info(
            "events.publish.complete",
            event_type=event_type,
            success_count=success_count,
            total_handlers=len(handlers),
        )
        return success_count

    def schedule_publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        task_registry: set[asyncio.Task[int]] | None = None,
    ) -> asyncio.Task[int]:
        """Schedula publish come task background fire-and-forget.

        Usata da endpoint REST per non bloccare la response HTTP in attesa
        che tutti i handler asincroni completino.

        Args:
            event_type: identificativo evento.
            payload: dict con dati evento.
            task_registry: opzionale, set per tracciare il task e impedire GC
                prematura (Bug 3 fix: senza tracking il task viene raccolto dal
                GC asyncio prima del completamento, handler mai eseguito).
                Pattern FastAPI standard: ``app.state.background_tasks``.

        Returns:
            asyncio.Task wrapping publish().
        """
        task = asyncio.create_task(
            self.publish(event_type, payload),
            name=f"event_publish_{event_type}",
        )
        if task_registry is not None:
            task_registry.add(task)
            task.add_done_callback(task_registry.discard)
        return task


def get_event_bus() -> EventBus:
    """Helper FastAPI Depends per accedere al bus singleton."""
    return EventBus.instance()
