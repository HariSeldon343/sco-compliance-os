"""Lock manager + cancellation per il Subconscious tick loop.

Vincolo OpenHuman: i tick NON si accumulano mai. Se mentre un tick T_n e' in
esecuzione arriva il momento di T_{n+1} (manual trigger o scadenza intervallo),
T_{n+1} prende posto e T_n viene marcato come ``cancelled`` via
:class:`asyncio.Event` di cancellation. Il vecchio coroutine puo' controllare
``token.cancelled.is_set()`` ai checkpoint e abortire in modo cooperativo.

Pattern asyncio:
- ``asyncio.Lock`` per la mutua esclusione del corpo del tick (chi entra esegue,
  chi prova a entrare mentre la lock e' tenuta marca il precedente come
  cancelled).
- ``asyncio.Event`` come cancellation token (cooperativo, non kill).
- Single-process backend FastAPI: nessun bisogno di lock filesystem o DB.

Esempio uso (idiomatico)::

    throttle = TickThrottle()
    async with throttle.acquire() as token:
        # ...lavoro pesante, occasionalmente check token.cancelled.is_set()
        if token.cancelled.is_set():
            return
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator

import structlog

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class CancellationToken:
    """Token cooperativo di cancellazione di un tick.

    Il consumer del token (corpo del tick) deve controllare ``cancelled.is_set()``
    ai checkpoint sicuri (prima di chiamate LLM costose, prima di scrivere DB,
    prima di append a activity.jsonl).
    """

    cancelled: asyncio.Event = field(default_factory=asyncio.Event)


class TickThrottle:
    """Garantisce ``no-overlap + no-accumulation`` dei tick subconscious.

    Stato interno (in-memory, single-process):
    - ``_lock``: asyncio.Lock per mutua esclusione.
    - ``_current_token``: token del tick attualmente in esecuzione (o None).
    - ``_holders_count``: contatore monotono di tick avviati (debug/log).
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._current_token: CancellationToken | None = None
        self._holders_count: int = 0

    def is_busy(self) -> bool:
        """True se un tick e' attualmente in esecuzione."""
        return self._lock.locked()

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[CancellationToken]:
        """Prende possesso del tick slot. Cancella il precedente se in corso.

        Behavior:
        1. Se un altro tick e' in esecuzione (``_current_token`` non None),
           viene marcato come cancelled (``cancelled.set()``).
        2. Attende che la lock sia rilasciata dal precedente (cooperativo;
           il precedente, controllando ``cancelled.is_set()``, dovrebbe
           uscire rapidamente al prossimo checkpoint).
        3. Acquisisce la lock, registra il proprio token come current,
           yielda il token al chiamante.
        4. Al rilascio del context manager, libera la lock e azzera
           ``_current_token`` se ancora puntato a self.
        """
        # Marca eventuale tick precedente come cancellato (cooperativo).
        if self._current_token is not None and not self._current_token.cancelled.is_set():
            logger.info("subconscious.throttle.preempt", reason="new_tick_requested")
            self._current_token.cancelled.set()

        # Acquisisce la lock (attende che il precedente esca al checkpoint).
        await self._lock.acquire()
        self._holders_count += 1
        my_token = CancellationToken()
        self._current_token = my_token
        logger.debug(
            "subconscious.throttle.acquired",
            holder_id=self._holders_count,
        )
        try:
            yield my_token
        finally:
            # Pulisce stato solo se non e' stato gia' sovrascritto da un nuovo tick.
            if self._current_token is my_token:
                self._current_token = None
            self._lock.release()
            logger.debug(
                "subconscious.throttle.released",
                holder_id=self._holders_count,
                cancelled=my_token.cancelled.is_set(),
            )

    def cancel_current(self) -> bool:
        """Marca esplicitamente il tick corrente come cancellato.

        Returns:
            True se c'era un tick attivo da cancellare, False altrimenti.
        """
        if self._current_token is None:
            return False
        if self._current_token.cancelled.is_set():
            return False
        self._current_token.cancelled.set()
        logger.info("subconscious.throttle.external_cancel")
        return True
