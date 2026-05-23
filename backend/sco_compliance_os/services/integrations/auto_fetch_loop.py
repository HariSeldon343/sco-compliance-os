"""Orchestratore Auto-Fetch loop per i connettori OAuth (W2 v0.3.0).

Replica clean-room del "Auto-fetch walker 20min" di OpenHuman (sezione 2.5
del blueprint). Adotta lo stesso pattern di
:class:`sco_compliance_os.services.subconscious.tick_loop.SubconsciousTickLoop`
(W1 v0.2.0): :class:`TickThrottle` no-overlap + cancellation cooperativa +
activity log JSONL + status snapshot Conv. 41.

Vincoli (OpenHuman blueprint sezione 2.5 + Sezione 7 risk mitigations):

1. **Intervallo default 1200s (20 min)**. Hard floor 300s (5 min) — sotto questo
   valore il loop **clampa al floor** per evitare hammering OAuth verso Gmail /
   Google Calendar / Google Drive API (rate limit tipico Google: 250 quota
   units/utente/sec, sufficiente ma non infinito).
2. **No-overlap**: se un tick e' in corso e arriva quello dopo, il precedente
   viene cancellato cooperativamente (vedi :class:`TickThrottle`).
3. **Round-robin fair-share**: ogni tick fetcha **1 solo connettore**, ruotando
   nella lista ``connectors`` in ordine. Su 3 connettori (gmail, gcal, gdrive)
   con interval 20min, ogni connettore viene fetchato ogni 60 min.
4. **Error backoff per-connector**: se un connector fallisce N volte consecutive
   (default 3), entra in cooldown di 1h. Durante il cooldown il connector viene
   skippato e il round-robin passa al successivo.
5. **Activity log JSONL** append-only su
   ``~/.sco-compliance-os/autofetch_activity.jsonl`` (1 line per tick eseguito).
6. **Privacy default OFF**: opt-in via ``settings.auto_fetch_enabled = True``.
7. **Stop cooperativo**: ``stop()`` attende fino a 30s che il tick corrente
   esca al prossimo checkpoint del CancellationToken.

Lifecycle:

- ``start()``: avvia task asyncio in background. Idempotente.
- ``stop()``: ferma il loop in modo cooperativo (graceful, attende tick corrente).
- ``run_tick_now()``: esegue un tick *manuale* (non rispetta intervallo).
- ``get_status()``: snapshot stato corrente (running, last_*, round-robin, ...).

Stato esposto (Conv. 41 tracciatura):

- ``last_tick_started_at`` / ``last_tick_completed_at``: ISO timestamp UTC.
- ``connectors_round_robin_state``: dict per-connector con
  ``last_fetch_ts``, ``consecutive_failures``, ``cooldown_until``,
  ``fetched_total``, ``last_outcome``.
- ``total_ticks``: counter monotono dei tick (manual + scheduled).

Cabling OAuth reale: in W2 v0.3.0 i fetch handler concreti sono
**delegati** a :class:`ConnectorScheduler.fetch_connector` (vedi
``scheduler.py``). Se nessun handler e' iniettato, il loop fa
**stub-fetch** che logga ``autofetch.fetch.stub`` e ritorna
``fetched_count=0``. Il cabling reale dei 3 OAuth (gmail.readonly,
calendar.readonly, drive.metadata.readonly) e' carry-over Wave 3 v0.4.0.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from sco_compliance_os.services.common.throttle import TickThrottle

logger = structlog.get_logger(__name__)


# --------------------------------------------------------------------------------------
# Constants (OpenHuman blueprint sezione 2.5 replica)
# --------------------------------------------------------------------------------------

DEFAULT_INTERVAL_SECONDS: int = 1200
"""Intervallo default 20 minuti (blueprint OpenHuman sezione 2.5)."""

MIN_INTERVAL_SECONDS: int = 300
"""Hard floor 5 minuti. Intervalli inferiori vengono clampati per evitare
hammering rate-limit OAuth provider."""

DEFAULT_CONNECTORS: tuple[str, ...] = ("gmail", "gcal", "gdrive")
"""Default round-robin: 3 connettori Google nativi del blueprint."""

DEFAULT_FAILURE_THRESHOLD: int = 3
"""Soglia consecutive failures oltre la quale il connector entra in cooldown."""

DEFAULT_COOLDOWN_SECONDS: int = 3600
"""Durata cooldown 1h dopo threshold raggiunto. Skippa il connector nei tick
seguenti finche' ``cooldown_until > now()``."""

DEFAULT_ACTIVITY_LOG_PATH: Path = (
    Path.home() / ".sco-compliance-os" / "autofetch_activity.jsonl"
)

STOP_TIMEOUT_SECONDS: float = 30.0
"""Timeout cooperativo stop: oltre questo, fallback a task.cancel()."""


# --------------------------------------------------------------------------------------
# Outcome dataclass
# --------------------------------------------------------------------------------------


@dataclass(slots=True)
class AutoFetchOutcome:
    """Esito strutturato di un singolo tick auto-fetch.

    Un tick = 1 connector fetchato (round-robin). I campi ``errors``,
    ``used_oauth`` sono utili per il logging + per il future UI debug.
    """

    connector_name: str
    fetched_count: int
    errors: list[str] = field(default_factory=list)
    used_oauth: bool = False
    duration_seconds: float = 0.0
    cancelled: bool = False


# --------------------------------------------------------------------------------------
# Per-connector state (round-robin)
# --------------------------------------------------------------------------------------


@dataclass(slots=True)
class _ConnectorState:
    """Stato per-connector tenuto in-memory (single-process).

    Serializzabile via :func:`dataclasses.asdict` per il status snapshot.
    """

    name: str
    last_fetch_ts: str | None = None
    consecutive_failures: int = 0
    cooldown_until: str | None = None  # ISO timestamp UTC, None se non in cooldown
    fetched_total: int = 0
    last_outcome: str | None = None  # "ok" | "error" | "skipped_cooldown" | "stub"


# --------------------------------------------------------------------------------------
# Status snapshot
# --------------------------------------------------------------------------------------


@dataclass(slots=True)
class _LoopStatus:
    """Stato interno serializzabile del loop."""

    running: bool = False
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    last_tick_started_at: str | None = None
    last_tick_completed_at: str | None = None
    last_tick_connector: str | None = None
    last_tick_fetched_count: int = 0
    last_tick_errors: list[str] = field(default_factory=list)
    total_ticks: int = 0
    rr_cursor: int = 0  # indice round-robin corrente


# --------------------------------------------------------------------------------------
# Fetch handler type
# --------------------------------------------------------------------------------------


# Signature del fetch handler iniettabile (interface stable W3 cabling).
# Riceve (connector_name, user_id) e ritorna AutoFetchOutcome parziale
# (almeno fetched_count + used_oauth + errors). duration_seconds + cancelled
# vengono settati dal loop stesso (non dall'handler).
FetchHandler = Callable[[str, str], Awaitable[AutoFetchOutcome]]


# --------------------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------------------


class AutoFetchLoop:
    """Orchestratore tick loop auto-fetch connettori OAuth (20 min default).

    Args:
        user_id: utente SCO per cui fare fetch (es. email license-bound).
        interval_seconds: intervallo desiderato in secondi.
            Clampato a :data:`MIN_INTERVAL_SECONDS` se inferiore (hard floor 5 min).
        connectors: lista round-robin dei connector da fetchare. Default
            :data:`DEFAULT_CONNECTORS` (gmail, gcal, gdrive).
        activity_log_path: path file JSONL append-only. Default
            ``~/.sco-compliance-os/autofetch_activity.jsonl``.
        fetch_handler: funzione async iniettabile che esegue il fetch
            concreto per un dato connector_name. Se ``None``, il loop esegue
            uno **stub-fetch** che logga ``autofetch.fetch.stub`` e ritorna
            ``fetched_count=0``. Il cabling reale OAuth e' Wave 3.
        failure_threshold: soglia consecutive failures (default 3) oltre la
            quale il connector entra in cooldown.
        cooldown_seconds: durata cooldown (default 1h) dopo soglia raggiunta.

    Note Conv. 44 lesson 3 PyInstaller: nessuna nuova dipendenza esterna
    introdotta da questo modulo (usa solo stdlib + structlog gia' presente).
    """

    def __init__(
        self,
        user_id: str,
        *,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        connectors: list[str] | None = None,
        activity_log_path: Path | None = None,
        fetch_handler: FetchHandler | None = None,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        if not user_id:
            raise ValueError("AutoFetchLoop: user_id obbligatorio (non vuoto).")
        self._user_id = user_id
        self._interval = max(MIN_INTERVAL_SECONDS, int(interval_seconds))
        connectors_list = list(connectors) if connectors is not None else list(DEFAULT_CONNECTORS)
        if not connectors_list:
            raise ValueError(
                "AutoFetchLoop: connectors deve avere almeno 1 elemento."
            )
        self._connectors: list[str] = connectors_list
        self._activity_log = activity_log_path or DEFAULT_ACTIVITY_LOG_PATH
        self._activity_log.parent.mkdir(parents=True, exist_ok=True)
        self._fetch_handler = fetch_handler
        self._failure_threshold = max(1, int(failure_threshold))
        self._cooldown_seconds = max(0, int(cooldown_seconds))

        # name="autofetch" -> log namespace autofetch.throttle.*
        self._throttle = TickThrottle(name="autofetch")
        self._status = _LoopStatus(interval_seconds=self._interval)
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._connector_state: dict[str, _ConnectorState] = {
            name: _ConnectorState(name=name) for name in self._connectors
        }

    # -- Lifecycle ---------------------------------------------------------------------

    async def start(self) -> bool:
        """Avvia il loop asincrono in background.

        Idempotente: se gia' running, ritorna False senza avviare un secondo task.

        Returns:
            True se il loop e' stato effettivamente avviato in questa chiamata.
        """
        if self._status.running:
            logger.info("autofetch.loop.start.skip_already_running")
            return False
        self._stop_event.clear()
        self._status.running = True
        self._task = asyncio.create_task(self._run_forever(), name="autofetch-loop")
        logger.info(
            "autofetch.loop.start",
            user_id=self._user_id,
            interval_seconds=self._interval,
            connectors=self._connectors,
            activity_log=str(self._activity_log),
        )
        return True

    async def stop(self) -> bool:
        """Ferma il loop in modo cooperativo. Attende il task corrente fino a
        :data:`STOP_TIMEOUT_SECONDS`, poi fallback a task.cancel().

        Returns:
            True se il loop era running ed e' stato fermato.
        """
        if not self._status.running:
            return False
        logger.info("autofetch.loop.stop.requested")
        self._stop_event.set()
        self._throttle.cancel_current()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=STOP_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                logger.warning("autofetch.loop.stop.timeout_force_cancel")
                self._task.cancel()
                try:
                    await self._task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
        self._status.running = False
        self._task = None
        logger.info("autofetch.loop.stop.complete")
        return True

    def is_running(self) -> bool:
        """True se il task background e' attivo e non terminato."""
        return self._status.running and self._task is not None and not self._task.done()

    def get_status(self) -> dict[str, Any]:
        """Snapshot stato corrente serializzabile (Conv. 41 tracciatura)."""
        d = asdict(self._status)
        d["interval_seconds_effective"] = self._interval
        d["is_throttle_busy"] = self._throttle.is_busy()
        d["connectors_round_robin_state"] = {
            name: asdict(state) for name, state in self._connector_state.items()
        }
        d["connectors"] = list(self._connectors)
        d["user_id"] = self._user_id
        d["failure_threshold"] = self._failure_threshold
        d["cooldown_seconds"] = self._cooldown_seconds
        return d

    # -- Tick execution ----------------------------------------------------------------

    async def run_tick_now(self) -> AutoFetchOutcome:
        """Esegue un tick manuale (sync, attende completion).

        Returns:
            AutoFetchOutcome del tick (1 connector fetchato round-robin).
        """
        return await self._execute_one_tick(manual=True)

    async def _run_forever(self) -> None:
        """Loop principale del task background."""
        try:
            while not self._stop_event.is_set():
                try:
                    await self._execute_one_tick(manual=False)
                except Exception as e:  # noqa: BLE001
                    # mai uccidere il loop per eccezioni applicative
                    logger.error(
                        "autofetch.loop.tick_unhandled_error",
                        error=str(e),
                        error_type=type(e).__name__,
                    )

                # Sleep fino al prossimo tick. Esce in anticipo se stop_event.
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=float(self._interval)
                    )
                except asyncio.TimeoutError:
                    pass  # timeout = e' ora del prossimo tick
        except asyncio.CancelledError:
            logger.info("autofetch.loop.cancelled")
            raise

    async def _execute_one_tick(self, *, manual: bool) -> AutoFetchOutcome:
        """Esegue un singolo tick attraverso il throttle.

        Seleziona il prossimo connector via round-robin (skipping cooldown),
        invoca il fetch handler (o stub-fetch se assente), aggiorna lo stato
        per-connector, appende activity log.
        """
        async with self._throttle.acquire() as token:
            tick_start_iso = _utc_now_iso()
            tick_start_ts = datetime.now(timezone.utc)
            self._status.last_tick_started_at = tick_start_iso

            # 1. Seleziona prossimo connector skippando quelli in cooldown.
            connector = self._pick_next_connector()
            if connector is None:
                # Tutti i connector sono in cooldown: registra outcome neutro
                outcome = AutoFetchOutcome(
                    connector_name="(all_in_cooldown)",
                    fetched_count=0,
                    errors=[],
                    used_oauth=False,
                    duration_seconds=0.0,
                    cancelled=False,
                )
                self._status.total_ticks += 1
                self._status.last_tick_completed_at = _utc_now_iso()
                self._status.last_tick_connector = outcome.connector_name
                self._status.last_tick_fetched_count = 0
                self._status.last_tick_errors = []
                self._append_activity_log(outcome, manual=manual)
                logger.info(
                    "autofetch.tick.all_in_cooldown",
                    manual=manual,
                )
                return outcome

            if token.cancelled.is_set():
                outcome = AutoFetchOutcome(
                    connector_name=connector,
                    fetched_count=0,
                    cancelled=True,
                )
                self._append_activity_log(outcome, manual=manual)
                return outcome

            # 2. Invoca fetch handler (o stub) cattura eccezioni come errors[].
            handler_outcome = await self._invoke_fetch(connector)
            duration = (datetime.now(timezone.utc) - tick_start_ts).total_seconds()
            handler_outcome.duration_seconds = duration

            if token.cancelled.is_set():
                handler_outcome.cancelled = True

            # 3. Aggiorna stato per-connector.
            self._update_connector_state(connector, handler_outcome)

            # 4. Update status globale + append activity log.
            self._status.last_tick_completed_at = _utc_now_iso()
            self._status.last_tick_connector = connector
            self._status.last_tick_fetched_count = handler_outcome.fetched_count
            self._status.last_tick_errors = list(handler_outcome.errors)
            self._status.total_ticks += 1

            self._append_activity_log(handler_outcome, manual=manual)
            logger.info(
                "autofetch.tick.complete",
                connector=connector,
                fetched=handler_outcome.fetched_count,
                errors_count=len(handler_outcome.errors),
                used_oauth=handler_outcome.used_oauth,
                duration_seconds=round(duration, 3),
                manual=manual,
                cancelled=handler_outcome.cancelled,
            )
            return handler_outcome

    async def _invoke_fetch(self, connector: str) -> AutoFetchOutcome:
        """Invoca il fetch handler iniettato, fallback a stub-fetch.

        Errors sono catturati e restituiti come ``errors[]`` in outcome:
        il loop non si ferma mai per un'eccezione di fetch (responsabilita'
        del handler aggiornare i contatori di cooldown via outcome.errors).
        """
        if self._fetch_handler is None:
            logger.info(
                "autofetch.fetch.stub",
                connector=connector,
                note="no fetch_handler injected, returning fetched_count=0",
            )
            return AutoFetchOutcome(
                connector_name=connector,
                fetched_count=0,
                errors=[],
                used_oauth=False,
            )
        try:
            outcome = await self._fetch_handler(connector, self._user_id)
            # Coerce: assicura che il connector_name sia quello pickato.
            if outcome.connector_name != connector:
                outcome.connector_name = connector
            return outcome
        except Exception as e:  # noqa: BLE001
            error_str = f"{type(e).__name__}: {e}"
            logger.warning(
                "autofetch.fetch.handler_error",
                connector=connector,
                error=error_str,
            )
            return AutoFetchOutcome(
                connector_name=connector,
                fetched_count=0,
                errors=[error_str],
                used_oauth=False,
            )

    # -- Connector state management ----------------------------------------------------

    def _pick_next_connector(self) -> str | None:
        """Seleziona il prossimo connector via round-robin, skipping cooldown.

        Avanza il cursor ``rr_cursor`` di una posizione per ciascun connector
        considerato; se trova un connector non in cooldown lo restituisce,
        altrimenti continua. Se TUTTI i connector sono in cooldown, ritorna
        ``None`` (caller registra outcome neutro).

        Returns:
            Nome del connector da fetchare, oppure None se tutti in cooldown.
        """
        n = len(self._connectors)
        for _ in range(n):
            idx = self._status.rr_cursor % n
            candidate = self._connectors[idx]
            # Avanza il cursor PRIMA del check, cosi' anche il caller si muove
            # se questo candidato e' selezionato (round-robin proprio).
            self._status.rr_cursor = (self._status.rr_cursor + 1) % n
            state = self._connector_state[candidate]
            if not self._is_in_cooldown(state):
                return candidate
            logger.debug(
                "autofetch.rr.skip_cooldown",
                connector=candidate,
                cooldown_until=state.cooldown_until,
            )
            state.last_outcome = "skipped_cooldown"
        # Tutti in cooldown
        return None

    def _is_in_cooldown(self, state: _ConnectorState) -> bool:
        """True se il connector e' in cooldown attivo (cooldown_until > now())."""
        if state.cooldown_until is None:
            return False
        try:
            until = datetime.fromisoformat(state.cooldown_until)
        except ValueError:
            # ISO malformato -> resetta cooldown (fail-safe)
            state.cooldown_until = None
            return False
        if datetime.now(timezone.utc) >= until:
            # Cooldown scaduto: pulisci e considera non in cooldown.
            state.cooldown_until = None
            state.consecutive_failures = 0
            return False
        return True

    def _update_connector_state(
        self, connector: str, outcome: AutoFetchOutcome
    ) -> None:
        """Aggiorna lo state per-connector dopo un tick eseguito.

        Logica:

        - Success (no errors): reset ``consecutive_failures`` a 0,
          ``last_outcome = "ok"`` (o ``"stub"`` se used_oauth=False).
        - Error: incrementa ``consecutive_failures``; se raggiunge
          ``failure_threshold`` attiva cooldown ``cooldown_seconds``.
        """
        state = self._connector_state[connector]
        state.last_fetch_ts = _utc_now_iso()
        state.fetched_total += outcome.fetched_count

        if outcome.errors:
            state.consecutive_failures += 1
            state.last_outcome = "error"
            logger.warning(
                "autofetch.connector.error",
                connector=connector,
                consecutive_failures=state.consecutive_failures,
                errors=outcome.errors[:3],  # cap per evitare log gigantesco
            )
            if state.consecutive_failures >= self._failure_threshold:
                # Attiva cooldown
                cooldown_until = datetime.now(timezone.utc) + _seconds_to_timedelta(
                    self._cooldown_seconds
                )
                state.cooldown_until = cooldown_until.isoformat()
                logger.warning(
                    "autofetch.connector.cooldown_activated",
                    connector=connector,
                    consecutive_failures=state.consecutive_failures,
                    cooldown_until=state.cooldown_until,
                    cooldown_seconds=self._cooldown_seconds,
                )
        else:
            state.consecutive_failures = 0
            state.last_outcome = "ok" if outcome.used_oauth else "stub"
            state.cooldown_until = None  # success resetta cooldown

    # -- Activity log ------------------------------------------------------------------

    def _append_activity_log(
        self,
        outcome: AutoFetchOutcome,
        *,
        manual: bool,
    ) -> None:
        """Append entry JSONL al activity log (1 line per tick).

        Schema entry (blueprint Wave 2):
        ``{ts, connector_name, fetched_count, errors, used_oauth,
        duration_seconds, manual, cancelled}``.
        """
        entry: dict[str, Any] = {
            "ts": _utc_now_iso(),
            "connector_name": outcome.connector_name,
            "fetched_count": outcome.fetched_count,
            "errors": list(outcome.errors),
            "used_oauth": outcome.used_oauth,
            "duration_seconds": round(outcome.duration_seconds, 3),
            "manual": manual,
            "cancelled": outcome.cancelled,
        }
        try:
            with self._activity_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.warning("autofetch.activity_log.write_failed", error=str(e))

    def read_activity_log(self, n: int = 50) -> list[dict[str, Any]]:
        """Legge le ultime N entry dell'activity log.

        Args:
            n: numero di entry da restituire (default 50, cap implicito da
               file system: legge tutto il file e fa slicing).

        Returns:
            Lista delle ultime N entry parsate (entry malformate skippate).
            Ritorna lista vuota se il file non esiste.
        """
        if not self._activity_log.exists():
            return []
        try:
            with self._activity_log.open("r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            return []
        out: list[dict[str, Any]] = []
        for line in lines[-n:]:
            text = line.strip()
            if not text:
                continue
            try:
                out.append(json.loads(text))
            except json.JSONDecodeError:
                continue
        return out


# --------------------------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------------------------


def _utc_now_iso() -> str:
    """Timestamp UTC ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def _seconds_to_timedelta(seconds: int) -> Any:
    """Helper per costruire timedelta evitando import top-level."""
    from datetime import timedelta

    return timedelta(seconds=seconds)


# Default singleton-like ref per accesso da api/autofetch_routes.py.
# Inizializzato/Sostituito dal lifespan() in main.py.
_active_loop: AutoFetchLoop | None = None


def get_active_loop() -> AutoFetchLoop | None:
    """Ritorna il loop attivo registrato dal lifespan (o None se non avviato)."""
    return _active_loop


def set_active_loop(loop: AutoFetchLoop | None) -> None:
    """Registra il loop attivo (chiamato da lifespan)."""
    global _active_loop
    _active_loop = loop
