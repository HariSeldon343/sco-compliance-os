"""Orchestratore Subconscious tick loop (5 minuti default, OFF default v0.2.0).

Vincoli OpenHuman replica clean-room:
1. Intervallo default 300s (5 minuti). NON scendibile sotto 300s (hard floor).
2. I tick NON si accumulano mai (throttle no-overlap, vedi throttle.py).
3. Backoff esponenziale su failure consecutive: 600s, 1200s, 2400s, cap 3600s.
4. Activity log append-only su ``~/.sco-compliance-os/subconscious-activity.jsonl``
   (1 line JSON per tick: timestamp + decision + rationale + cancelled).
5. Default OFF (privacy): opt-in via ``settings.subconscious_enabled = True``.
6. Hard cap 200 ticks/day (safety net cost runaway, blueprint Sezione 7).

Lifecycle:
- ``start()``: avvia task asyncio in background. Idempotente.
- ``stop()``: ferma il loop in modo cooperativo (graceful, attende tick corrente).
- ``run_tick_now()``: esegue un tick *manuale* (non rispetta intervallo). Useful
  per debug e per ``POST /api/subconscious/tick``.
- ``get_status()``: snapshot stato corrente (running, last_tick_*, failures, ...).

Stato esposto (Conv. 41 tracciatura):
- last_tick_started_at: ISO timestamp UTC ultimo tick avviato
- last_tick_completed_at: ISO timestamp UTC ultimo tick completato
- last_tick_decision: ultimo Decision enum value
- last_tick_rationale: ultimo rationale stringa
- consecutive_failures: counter failure consecutive (azzera su success)
- ticks_today: contatore ticks oggi (reset midnight UTC)
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from .decision_engine import (
    Decision,
    DecisionEngine,
    DecisionOutcome,
    SubconsciousContext,
)
from .throttle import TickThrottle

logger = structlog.get_logger(__name__)


# --------------------------------------------------------------------------------------
# Constants (OpenHuman docs replica)
# --------------------------------------------------------------------------------------

MIN_INTERVAL_SECONDS: int = 300
"""Hard floor 5 minuti (vincolo OpenHuman docs). Tick piu' frequenti non ammessi."""

MAX_TICKS_PER_DAY: int = 200
"""Hard cap safety net cost runaway (blueprint Sezione 7)."""

BACKOFF_BASE_SECONDS: int = 600
"""Backoff base: 10 minuti dopo prima failure consecutiva."""

BACKOFF_CAP_SECONDS: int = 3600
"""Backoff cap: 60 minuti massimo."""

BACKOFF_FAILURE_THRESHOLD: int = 3
"""Soglia consecutive_failures oltre la quale attiva backoff esponenziale."""

DEFAULT_ACTIVITY_LOG_PATH: Path = Path.home() / ".sco-compliance-os" / "subconscious-activity.jsonl"


# --------------------------------------------------------------------------------------
# Status snapshot
# --------------------------------------------------------------------------------------


@dataclass(slots=True)
class _LoopStatus:
    """Stato interno serializzabile del loop."""

    running: bool = False
    interval_seconds: int = MIN_INTERVAL_SECONDS
    last_tick_started_at: str | None = None
    last_tick_completed_at: str | None = None
    last_tick_decision: str | None = None
    last_tick_rationale: str | None = None
    last_tick_cancelled: bool = False
    last_tick_used_llm: bool = False
    consecutive_failures: int = 0
    ticks_today: int = 0
    ticks_today_date: str | None = None  # ISO date (UTC) per reset midnight
    total_ticks: int = 0


# Type hint per fornitore di contesto (iniettabile da main.py)
ContextProvider = Callable[[], Awaitable[SubconsciousContext]]


# --------------------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------------------


class SubconsciousTickLoop:
    """Orchestratore tick loop subconscious 5 minuti.

    Args:
        interval_seconds: intervallo desiderato in secondi.
            Clampato a ``MIN_INTERVAL_SECONDS`` se inferiore (hard floor 5 min).
        context_provider: coroutine async che ritorna :class:`SubconsciousContext`.
            Se None, ad ogni tick il contesto e' vuoto (-> SKIP short-circuit).
            Iniettato esternamente per evitare dipendenza circolare con Memory Tree.
        decision_engine: engine custom (testing). Se None, ne crea uno default.
        activity_log_path: path file JSONL append-only. Default
            ``~/.sco-compliance-os/subconscious-activity.jsonl``.
    """

    def __init__(
        self,
        *,
        interval_seconds: int = MIN_INTERVAL_SECONDS,
        context_provider: ContextProvider | None = None,
        decision_engine: DecisionEngine | None = None,
        activity_log_path: Path | None = None,
    ) -> None:
        self._interval = max(MIN_INTERVAL_SECONDS, int(interval_seconds))
        self._context_provider = context_provider
        self._engine = decision_engine or DecisionEngine()
        self._activity_log = activity_log_path or DEFAULT_ACTIVITY_LOG_PATH
        self._activity_log.parent.mkdir(parents=True, exist_ok=True)

        # name="subconscious" preserva il namespace logger storico W1
        # (subconscious.throttle.preempt / acquired / released / external_cancel).
        self._throttle = TickThrottle(name="subconscious")
        self._status = _LoopStatus(interval_seconds=self._interval)
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    # -- Lifecycle ---------------------------------------------------------------------

    async def start(self) -> bool:
        """Avvia il loop asincrono in background.

        Idempotente: se gia' running, ritorna False senza avviare un secondo task.

        Returns:
            True se il loop e' stato effettivamente avviato in questa chiamata.
        """
        if self._status.running:
            logger.info("subconscious.loop.start.skip_already_running")
            return False
        self._stop_event.clear()
        self._status.running = True
        self._task = asyncio.create_task(self._run_forever(), name="subconscious-tick-loop")
        logger.info(
            "subconscious.loop.start",
            interval_seconds=self._interval,
            activity_log=str(self._activity_log),
        )
        return True

    async def stop(self) -> bool:
        """Ferma il loop in modo cooperativo. Attende il task corrente.

        Returns:
            True se il loop era running ed e' stato fermato.
        """
        if not self._status.running:
            return False
        logger.info("subconscious.loop.stop.requested")
        self._stop_event.set()
        # Cancella eventuale tick in corso per uscita rapida
        self._throttle.cancel_current()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=30.0)
            except TimeoutError:
                logger.warning("subconscious.loop.stop.timeout_force_cancel")
                self._task.cancel()
                try:
                    await self._task
                except (asyncio.CancelledError, Exception):
                    pass
        self._status.running = False
        self._task = None
        logger.info("subconscious.loop.stop.complete")
        return True

    def is_running(self) -> bool:
        """True se il task background e' attivo."""
        return self._status.running and self._task is not None and not self._task.done()

    def get_status(self) -> dict[str, Any]:
        """Snapshot stato corrente serializzabile (Conv. 41 tracciatura)."""
        d = asdict(self._status)
        d["interval_seconds_effective"] = self._effective_interval()
        d["is_throttle_busy"] = self._throttle.is_busy()
        return d

    # -- Tick execution ----------------------------------------------------------------

    async def run_tick_now(self) -> DecisionOutcome:
        """Esegue un tick manuale (sync, attende completion). Non bumpa ticks_today
        oltre l'hard cap, ma propaga eccezioni di backoff/cap.

        Returns:
            DecisionOutcome del tick.

        Raises:
            RuntimeError: se cap giornaliero raggiunto.
        """
        if self._status.ticks_today >= MAX_TICKS_PER_DAY:
            raise RuntimeError(
                f"daily tick cap reached ({MAX_TICKS_PER_DAY}); reset at midnight UTC"
            )
        return await self._execute_one_tick(manual=True)

    async def _run_forever(self) -> None:
        """Loop principale del task background."""
        try:
            while not self._stop_event.is_set():
                # Reset midnight UTC del contatore giornaliero
                self._maybe_reset_daily_counter()

                # Check hard cap giornaliero
                if self._status.ticks_today >= MAX_TICKS_PER_DAY:
                    logger.warning(
                        "subconscious.loop.daily_cap_reached",
                        ticks_today=self._status.ticks_today,
                    )
                    await self._sleep_until_next_day_or_stop()
                    continue

                # Esegui tick (cattura eccezioni per evitare crash loop)
                try:
                    await self._execute_one_tick(manual=False)
                except Exception as e:
                    self._status.consecutive_failures += 1
                    logger.error(
                        "subconscious.loop.tick_unhandled_error",
                        error=str(e),
                        error_type=type(e).__name__,
                        consecutive_failures=self._status.consecutive_failures,
                    )

                # Sleep fino al prossimo tick (con backoff se molte failure)
                wait = self._effective_interval()
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=wait)
                except TimeoutError:
                    pass  # timeout = e' ora del prossimo tick
        except asyncio.CancelledError:
            logger.info("subconscious.loop.cancelled")
            raise

    async def _execute_one_tick(self, *, manual: bool) -> DecisionOutcome:
        """Esegue un singolo tick attraverso il throttle + decision engine."""
        async with self._throttle.acquire() as token:
            self._status.last_tick_started_at = _utc_now_iso()
            self._status.last_tick_cancelled = False

            # 1. Build context (provider iniettato; fallback empty)
            ctx = await self._build_context_safe()
            if token.cancelled.is_set():
                return self._record_cancelled(reason="cancelled_before_decision")

            # 2. Decide (LLM o short-circuit)
            outcome = await self._engine.decide(ctx)
            if token.cancelled.is_set():
                return self._record_cancelled(
                    reason="cancelled_after_decision",
                    outcome=outcome,
                )

            # 3. Update status + append activity log
            self._status.last_tick_completed_at = _utc_now_iso()
            self._status.last_tick_decision = outcome.decision.value
            self._status.last_tick_rationale = outcome.rationale
            self._status.last_tick_used_llm = outcome.used_llm
            self._status.total_ticks += 1
            self._status.ticks_today += 1
            self._status.consecutive_failures = 0  # success -> reset

            self._append_activity_log(outcome, manual=manual, cancelled=False)
            logger.info(
                "subconscious.tick.complete",
                decision=outcome.decision.value,
                rationale=outcome.rationale[:120],
                used_llm=outcome.used_llm,
                manual=manual,
            )
            return outcome

    def _record_cancelled(
        self,
        *,
        reason: str,
        outcome: DecisionOutcome | None = None,
    ) -> DecisionOutcome:
        """Registra tick cancellato senza incrementare i contatori success."""
        cancelled_outcome = outcome or DecisionOutcome(
            decision=Decision.SKIP,
            rationale=reason,
            proposed_action=None,
            used_llm=False,
        )
        self._status.last_tick_completed_at = _utc_now_iso()
        self._status.last_tick_decision = cancelled_outcome.decision.value
        self._status.last_tick_rationale = f"cancelled: {reason}"
        self._status.last_tick_cancelled = True
        self._append_activity_log(cancelled_outcome, manual=False, cancelled=True)
        return cancelled_outcome

    async def _build_context_safe(self) -> SubconsciousContext:
        """Build context con try/except: in caso di errore restituisce vuoto."""
        if self._context_provider is None:
            return SubconsciousContext()
        try:
            return await self._context_provider()
        except Exception as e:
            logger.warning(
                "subconscious.context.build_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return SubconsciousContext()

    # -- Helpers -----------------------------------------------------------------------

    def _effective_interval(self) -> int:
        """Intervallo effettivo (con backoff esponenziale se molte failure)."""
        n_fail = self._status.consecutive_failures
        if n_fail <= BACKOFF_FAILURE_THRESHOLD:
            return self._interval
        # Failure > soglia: backoff esponenziale capped
        # n_fail=4 -> 600s, n_fail=5 -> 1200s, n_fail=6 -> 2400s, n_fail>=7 -> 3600s
        excess = n_fail - BACKOFF_FAILURE_THRESHOLD
        wait: int = BACKOFF_BASE_SECONDS * (2 ** (excess - 1))
        return min(wait, BACKOFF_CAP_SECONDS)

    def _maybe_reset_daily_counter(self) -> None:
        """Reset ticks_today se cambiata data UTC."""
        today_utc = datetime.now(UTC).date().isoformat()
        if self._status.ticks_today_date != today_utc:
            if self._status.ticks_today_date is not None:
                logger.info(
                    "subconscious.daily_reset",
                    previous_date=self._status.ticks_today_date,
                    previous_ticks=self._status.ticks_today,
                )
            self._status.ticks_today_date = today_utc
            self._status.ticks_today = 0

    async def _sleep_until_next_day_or_stop(self) -> None:
        """Sleep ~1h per controllare a breve cap reset midnight."""
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=3600.0)
        except TimeoutError:
            pass

    def _append_activity_log(
        self,
        outcome: DecisionOutcome,
        *,
        manual: bool,
        cancelled: bool,
    ) -> None:
        """Append entry JSONL al activity log (1 line per tick)."""
        entry = {
            "ts": _utc_now_iso(),
            "decision": outcome.decision.value,
            "rationale": outcome.rationale,
            "proposed_action": outcome.proposed_action,
            "used_llm": outcome.used_llm,
            "manual": manual,
            "cancelled": cancelled,
        }
        try:
            with self._activity_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.warning("subconscious.activity_log.write_failed", error=str(e))

    def read_activity_log(self, *, n: int = 50) -> list[dict[str, Any]]:
        """Legge le ultime N entry dell'activity log.

        Ritorna lista vuota se il file non esiste.
        """
        if not self._activity_log.exists():
            return []
        try:
            with self._activity_log.open("r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            return []
        # Ultime N parse-tollerante
        out: list[dict[str, Any]] = []
        for line in lines[-n:]:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out


# --------------------------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------------------------


def _utc_now_iso() -> str:
    """Timestamp UTC ISO 8601."""
    return datetime.now(UTC).isoformat()


# Default singleton-like ref per accesso da api/subconscious_routes.py.
# Inizializzato/Sostituito dal lifespan() in main.py.
_active_loop: SubconsciousTickLoop | None = None


def get_active_loop() -> SubconsciousTickLoop | None:
    """Ritorna il loop attivo registrato dal lifespan (o None se non avviato)."""
    return _active_loop


def set_active_loop(loop: SubconsciousTickLoop | None) -> None:
    """Registra il loop attivo (chiamato da lifespan)."""
    global _active_loop
    _active_loop = loop
