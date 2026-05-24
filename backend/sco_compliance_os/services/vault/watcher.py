"""File watcher per vault SCO con re-ingest live delle modifiche.

v0.6.0 DEV-VAULT-AUTOINGEST: ogni vault registrato attiva un VaultWatcher
in background che monitora il filesystem per create/modify/delete eventi
e propaga le modifiche a mem_tree_chunks delta-only.

Architettura:
    - watchdog.observers.Observer come backend (cross-platform).
    - Custom EventHandler che cattura created/modified/deleted/moved.
    - Debouncing: 5 secondi dopo ultimo modify event prima di processare.
      Previene storm su Office (Word/Excel salvano via .tmp + rename + multi-modify).
    - Coda asyncio thread-safe per propagare eventi dal thread watchdog
      al loop asyncio principale.
    - VaultWatcherManager: gestisce ciclo di vita di N watcher (uno per vault).

Pattern Conv. 44 lesson 1 (CircuitBreaker per file rotti):
    - Ereditato da autoingest.ingest_single_file (gia integrato).

Pattern Conv. 41 (tracciatura):
    - Logger structured per ogni evento ricevuto + decisione (debounce/process/skip).

Pattern SCO "single source of truth":
    - I chunks vivono in mem_tree_chunks, mai duplicati.
    - Watcher e' fire-and-forget: niente stato locale che possa drift dal DB.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# COSTANTI
# --------------------------------------------------------------------------

# Debounce window: aspetta N secondi dopo ultima modify prima di processare.
# Office salva via .tmp + rename + multi-event, debounce previene re-ingest x3.
_DEBOUNCE_SECONDS = 5.0

# Polling interval del watcher loop async (controlla coda eventi)
_QUEUE_POLL_INTERVAL = 0.5


# --------------------------------------------------------------------------
# DATACLASSES
# --------------------------------------------------------------------------


@dataclass(slots=True)
class FileEvent:
    """Evento filesystem catturato dal watcher."""

    event_type: str  # 'created' | 'modified' | 'deleted' | 'moved'
    src_path: str
    dest_path: str | None  # popolato solo per 'moved'
    timestamp: float
    vault_id: str


# --------------------------------------------------------------------------
# CHECK WATCHDOG AVAILABILITY (graceful degradation se non installato)
# --------------------------------------------------------------------------


def _watchdog_available() -> bool:
    """Verifica se watchdog e' disponibile (graceful degradation se manca)."""
    try:
        import watchdog  # type: ignore  # noqa: F401

        return True
    except ImportError:
        return False


# --------------------------------------------------------------------------
# WATCHDOG EVENT HANDLER
# --------------------------------------------------------------------------


class _VaultEventHandler:
    """Handler watchdog che pusha eventi in una coda thread-safe.

    Non eredita FileSystemEventHandler in modo statico per evitare import
    fail a top-level se watchdog non installato. Il bind effettivo avviene
    dentro VaultWatcher.start() dopo check disponibilita'.
    """

    def __init__(self, vault_id: str, queue: "queue.Queue[FileEvent]") -> None:  # type: ignore[name-defined]
        self.vault_id = vault_id
        self.queue = queue

    def on_created(self, event: Any) -> None:  # noqa: ARG002
        if event.is_directory:
            return
        self._enqueue("created", event.src_path, None)

    def on_modified(self, event: Any) -> None:  # noqa: ARG002
        if event.is_directory:
            return
        self._enqueue("modified", event.src_path, None)

    def on_deleted(self, event: Any) -> None:  # noqa: ARG002
        if event.is_directory:
            return
        self._enqueue("deleted", event.src_path, None)

    def on_moved(self, event: Any) -> None:  # noqa: ARG002
        if event.is_directory:
            return
        self._enqueue("moved", event.src_path, event.dest_path)

    def _enqueue(self, event_type: str, src: str, dest: str | None) -> None:
        try:
            self.queue.put(
                FileEvent(
                    event_type=event_type,
                    src_path=src,
                    dest_path=dest,
                    timestamp=time.monotonic(),
                    vault_id=self.vault_id,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("watcher enqueue error: %s", exc)


# --------------------------------------------------------------------------
# VAULT WATCHER (uno per vault registrato)
# --------------------------------------------------------------------------


import queue  # noqa: E402  -- placed late per evitare unused se watchdog assente


class VaultWatcher:
    """Watcher per un singolo vault path con debounce + async processing.

    Lifecycle:
        - start(): inizializza watchdog Observer + thread evento + task async loop.
        - stop(): ferma observer + cancella task async.

    Pattern: Observer thread (watchdog) -> Queue -> async loop polling +
    debounce buffer + chiamata processor async (es. ingest_single_file).
    """

    def __init__(
        self,
        vault_id: str,
        vault_path: Path,
        *,
        on_event: Callable[[FileEvent], Any],
        debounce_seconds: float = _DEBOUNCE_SECONDS,
    ) -> None:
        """Init VaultWatcher.

        Args:
            vault_id: ID vault dal registry.
            vault_path: directory root da monitorare (recursivo).
            on_event: callback async che riceve FileEvent debounced.
                      Deve essere coroutine function (async def).
            debounce_seconds: finestra debounce per modify events.
        """
        self.vault_id = vault_id
        self.vault_path = vault_path
        self.on_event = on_event
        self.debounce_seconds = debounce_seconds

        self._observer: Any | None = None
        self._handler: _VaultEventHandler | None = None
        self._queue: queue.Queue[FileEvent] = queue.Queue(maxsize=10_000)
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()
        # Debounce buffer: {src_path: (event, last_seen_monotonic)}
        self._debounce_buffer: dict[str, tuple[FileEvent, float]] = {}

    async def start(self) -> bool:
        """Avvia watcher. Ritorna False se watchdog non disponibile o path invalido.

        Idempotente: chiamate ripetute su istanza gia avviata sono no-op.
        """
        if self._observer is not None:
            logger.debug("VaultWatcher already running: vault_id=%s", self.vault_id)
            return True

        if not _watchdog_available():
            logger.warning(
                "watchdog non installato, watcher disabilitato vault_id=%s",
                self.vault_id,
            )
            return False

        if not self.vault_path.exists() or not self.vault_path.is_dir():
            logger.warning(
                "vault_path invalido per watcher vault_id=%s path=%s",
                self.vault_id,
                self.vault_path,
            )
            return False

        # Import lazy: solo quando watchdog e' confermato disponibile.
        from watchdog.events import FileSystemEventHandler  # type: ignore
        from watchdog.observers import Observer  # type: ignore

        # Bind dinamicamente i metodi handler a una sottoclasse vera.
        class _RealHandler(FileSystemEventHandler):  # type: ignore[misc, no-any-unimported]
            def __init__(self, base: _VaultEventHandler) -> None:
                super().__init__()
                self._base = base

            def on_created(self, event: Any) -> None:  # noqa: ARG002
                self._base.on_created(event)

            def on_modified(self, event: Any) -> None:  # noqa: ARG002
                self._base.on_modified(event)

            def on_deleted(self, event: Any) -> None:  # noqa: ARG002
                self._base.on_deleted(event)

            def on_moved(self, event: Any) -> None:  # noqa: ARG002
                self._base.on_moved(event)

        self._handler = _VaultEventHandler(self.vault_id, self._queue)
        observer_handler = _RealHandler(self._handler)

        self._observer = Observer()
        self._observer.schedule(observer_handler, str(self.vault_path), recursive=True)
        self._observer.start()

        # Avvia loop async per consumare eventi + debounce
        self._stopped.clear()
        self._task = asyncio.create_task(self._consume_loop(), name=f"watcher-{self.vault_id}")

        logger.info(
            "VaultWatcher started vault_id=%s path=%s debounce_sec=%.1f",
            self.vault_id,
            self.vault_path,
            self.debounce_seconds,
        )
        return True

    async def stop(self) -> None:
        """Ferma watcher pulito. Idempotente."""
        if self._observer is None:
            return
        try:
            self._observer.stop()
            # join in thread separato per non bloccare async loop
            await asyncio.get_running_loop().run_in_executor(
                None, self._observer.join, 5.0
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("VaultWatcher.stop observer error: %s", exc)
        self._observer = None
        self._handler = None

        # Stop async consumer
        self._stopped.set()
        if self._task is not None:
            try:
                # Aspetta cancellazione max 2 secondi
                await asyncio.wait_for(self._task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._task.cancel()
                try:
                    await self._task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001, S110
                    pass
            self._task = None

        logger.info("VaultWatcher stopped vault_id=%s", self.vault_id)

    def is_running(self) -> bool:
        """True se observer attivo."""
        return self._observer is not None

    async def _consume_loop(self) -> None:
        """Loop async che consuma eventi + applica debounce + chiama on_event."""
        try:
            while not self._stopped.is_set():
                # Drain coda watchdog (non-blocking)
                await self._drain_queue()
                # Processa eventi debounced pronti
                await self._flush_debounced()
                # Pausa breve prima del prossimo poll
                try:
                    await asyncio.wait_for(
                        self._stopped.wait(), timeout=_QUEUE_POLL_INTERVAL
                    )
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.debug("VaultWatcher consume_loop cancelled vault_id=%s", self.vault_id)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("VaultWatcher consume_loop error: %s", exc)

    async def _drain_queue(self) -> None:
        """Drena tutti gli eventi pending da queue thread-safe."""
        drained = 0
        while drained < 500:  # cap per non monopolizzare loop
            try:
                event = self._queue.get_nowait()
            except queue.Empty:
                return
            self._handle_event(event)
            drained += 1

    def _handle_event(self, event: FileEvent) -> None:
        """Decide se aggiungere a debounce buffer o gestire subito.

        Eventi 'deleted' e 'moved' (rename) processati subito (no debounce):
        meno frequenti, semantica chiara.
        Eventi 'created' e 'modified' vanno in debounce buffer.
        """
        if event.event_type in ("deleted", "moved"):
            # Push diretto su task async (no debounce)
            asyncio.create_task(self._safe_dispatch(event))
            return

        # Skip file non supportati per evitare debounce buffer crescita
        # con file dot-prefix, temp, lock, ecc.
        from .extractors import is_supported  # lazy import

        src = Path(event.src_path)
        if not is_supported(src):
            return

        # Skip cartelle escluse (Office temp .~lock, .tmp di Word)
        if any(
            part.startswith("~$") or part.endswith(".tmp")
            for part in src.parts
        ):
            return

        # Aggiungi/aggiorna debounce buffer
        self._debounce_buffer[event.src_path] = (event, time.monotonic())

    async def _flush_debounced(self) -> None:
        """Processa eventi nel buffer la cui last_seen e' scaduta debounce_seconds."""
        now = time.monotonic()
        to_flush: list[FileEvent] = []
        for path_str, (event, last_seen) in list(self._debounce_buffer.items()):
            if now - last_seen >= self.debounce_seconds:
                to_flush.append(event)
                del self._debounce_buffer[path_str]

        for event in to_flush:
            await self._safe_dispatch(event)

    async def _safe_dispatch(self, event: FileEvent) -> None:
        """Chiama on_event catturando eccezioni per non crashare il loop."""
        try:
            logger.info(
                "watcher.dispatch vault_id=%s type=%s path=%s",
                self.vault_id,
                event.event_type,
                event.src_path,
            )
            result = self.on_event(event)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "watcher.dispatch error vault_id=%s path=%s: %s",
                self.vault_id,
                event.src_path,
                exc,
            )


# --------------------------------------------------------------------------
# VAULT WATCHER MANAGER (singleton di processo)
# --------------------------------------------------------------------------


class VaultWatcherManager:
    """Gestisce N VaultWatcher (uno per vault registrato).

    Lifecycle integrato in main.py lifespan:
        - startup: per ogni vault nel registry -> start_watcher(vault_id, path)
        - shutdown: stop_all()
        - add_vault REST endpoint -> start_watcher dinamico
        - delete_vault REST endpoint -> stop_watcher dinamico
    """

    def __init__(self) -> None:
        self._watchers: dict[str, VaultWatcher] = {}
        self._lock = asyncio.Lock()
        self._on_event_cb: Callable[[FileEvent], Any] | None = None

    def set_event_callback(self, cb: Callable[[FileEvent], Any]) -> None:
        """Setta il callback globale invocato per ogni FileEvent (post-debounce).

        Wire in main.py lifespan: cb = handle_file_event (ingest_single_file).
        """
        self._on_event_cb = cb

    async def start_watcher(self, vault_id: str, vault_path: Path) -> bool:
        """Avvia watcher per vault_id. Idempotente: skip se gia avviato."""
        async with self._lock:
            if vault_id in self._watchers:
                logger.debug("VaultWatcherManager: watcher gia attivo vault_id=%s", vault_id)
                return True
            if self._on_event_cb is None:
                logger.warning(
                    "VaultWatcherManager: callback non configurato, "
                    "watcher non avviato vault_id=%s",
                    vault_id,
                )
                return False

            watcher = VaultWatcher(
                vault_id=vault_id,
                vault_path=vault_path,
                on_event=self._on_event_cb,
            )
            started = await watcher.start()
            if started:
                self._watchers[vault_id] = watcher
            return started

    async def stop_watcher(self, vault_id: str) -> None:
        """Ferma watcher per vault_id."""
        async with self._lock:
            watcher = self._watchers.pop(vault_id, None)
        if watcher is not None:
            await watcher.stop()

    async def stop_all(self) -> None:
        """Ferma tutti i watchers (chiamato da lifespan shutdown)."""
        async with self._lock:
            watchers = list(self._watchers.items())
            self._watchers.clear()
        for vault_id, watcher in watchers:
            try:
                await watcher.stop()
            except Exception as exc:  # noqa: BLE001
                logger.warning("stop_all: error stopping vault_id=%s: %s", vault_id, exc)

    async def list_watchers(self) -> dict[str, bool]:
        """Ritorna mappa {vault_id: is_running}."""
        async with self._lock:
            return {vid: w.is_running() for vid, w in self._watchers.items()}


# Singleton di processo (Conv. 47 single source of truth)
_manager = VaultWatcherManager()


def get_watcher_manager() -> VaultWatcherManager:
    """Ritorna singleton VaultWatcherManager."""
    return _manager


__all__ = [
    "FileEvent",
    "VaultWatcher",
    "VaultWatcherManager",
    "get_watcher_manager",
]
