"""Smoke test E2E Wave 2 OpenHuman replica W2-AUTOFETCH.

6 step di verifica del :class:`AutoFetchLoop`:

1. Create AutoFetchLoop con 3 fake connectors stub (no OAuth reale).
2. start() -> verifica is_running() == True.
3. run_tick_now() 1 volta -> verifica AutoFetchOutcome ha connector_name valido
   + fetched_count >= 0.
4. Round-robin: 3 manual tick -> ogni connettore fetchato esattamente 1 volta.
5. Error backoff: simula 3 fail consecutivi su 1 connettore -> verifica
   cooldown attivato (consecutive_failures >= threshold + cooldown_until set).
6. stop() -> verifica is_running() == False entro 30s.

Esecuzione: cd backend && uv run python scripts/smoke_w2_autofetch.py
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

# Ensure backend package in path (pyproject install handles this normally)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import structlog  # noqa: E402

from sco_compliance_os.services.integrations.auto_fetch_loop import (  # noqa: E402
    AutoFetchLoop,
    AutoFetchOutcome,
)

logger = structlog.get_logger(__name__)


# ----- Fake connectors stub --------------------------------------------------------


# Contatori globali per verificare round-robin + error simulation
_call_counts: dict[str, int] = {"alpha": 0, "beta": 0, "gamma": 0}
_inject_errors_for: set[str] = set()


async def _ok_handler(connector_name: str, user_id: str) -> AutoFetchOutcome:
    """Handler stub che ritorna success con fetched_count incrementale.

    Se ``connector_name`` e' in ``_inject_errors_for``, ritorna outcome con
    errors[] per simulare failure repeat (per Step 5).
    """
    _call_counts[connector_name] = _call_counts.get(connector_name, 0) + 1

    if connector_name in _inject_errors_for:
        return AutoFetchOutcome(
            connector_name=connector_name,
            fetched_count=0,
            errors=[f"simulated_error_for_{connector_name}_call_{_call_counts[connector_name]}"],
            used_oauth=True,
        )

    return AutoFetchOutcome(
        connector_name=connector_name,
        fetched_count=_call_counts[connector_name],  # 1, 2, 3 per call
        errors=[],
        used_oauth=True,
    )


# ----- Main smoke pipeline ---------------------------------------------------------


async def main() -> int:
    """Smoke test E2E. Ritorna 0 se PASS, !=0 se FAIL."""
    structlog.configure(
        processors=[
            structlog.dev.ConsoleRenderer(colors=False),
        ],
    )

    print("\n=== SMOKE W2-AUTOFETCH ===\n")

    # Activity log temporaneo per non sporcare ~/.sco-compliance-os/
    tmp_dir = Path(tempfile.mkdtemp(prefix="sco-smoke-w2-"))
    activity_log = tmp_dir / "autofetch_activity.jsonl"
    print(f"Activity log temporaneo: {activity_log}\n")

    connectors = ["alpha", "beta", "gamma"]

    # ---------------------------------------------------------------------------------
    # Step 1: Create AutoFetchLoop con 3 fake connectors
    # ---------------------------------------------------------------------------------
    print("[1/6] Create AutoFetchLoop con 3 connectors stub (alpha, beta, gamma)...")
    try:
        loop = AutoFetchLoop(
            user_id="smoke-test@example.com",
            interval_seconds=3600,  # 1h: troppo lungo per scattare in 30s di smoke
            connectors=connectors,
            activity_log_path=activity_log,
            fetch_handler=_ok_handler,
            failure_threshold=3,
            cooldown_seconds=3600,
        )
    except Exception as e:
        print(f"      FAIL: AutoFetchLoop ctor crashed: {e}")
        return 1
    if loop is None:
        print("      FAIL: loop is None")
        return 1
    if loop.is_running():
        print("      FAIL: loop.is_running() True prima di start()")
        return 1
    print(f"      OK loop created, connectors={connectors}, running=False")

    # ---------------------------------------------------------------------------------
    # Step 2: start() -> is_running() == True
    # ---------------------------------------------------------------------------------
    print("[2/6] start() + verifica is_running() == True...")
    started = await loop.start()
    if not started:
        print("      FAIL: start() ha ritornato False (gia' running?)")
        return 2
    # Lascia il loop respirare un istante (task scheduling)
    await asyncio.sleep(0.05)
    if not loop.is_running():
        print("      FAIL: is_running() == False subito dopo start()")
        return 2
    # start() idempotente: secondo start() ritorna False
    started_again = await loop.start()
    if started_again:
        print("      FAIL: secondo start() doveva ritornare False (idempotente)")
        return 2
    print("      OK started + idempotent")

    # ---------------------------------------------------------------------------------
    # Step 3: run_tick_now() 1 volta -> verifica outcome
    # ---------------------------------------------------------------------------------
    print("[3/6] run_tick_now() 1 volta -> verifica outcome...")
    outcome = await loop.run_tick_now()
    if outcome.connector_name not in connectors:
        print(f"      FAIL: connector_name='{outcome.connector_name}' non in {connectors}")
        return 3
    if outcome.fetched_count < 0:
        print(f"      FAIL: fetched_count={outcome.fetched_count} < 0")
        return 3
    if outcome.cancelled:
        print("      FAIL: outcome.cancelled=True non atteso")
        return 3
    print(
        f"      OK connector={outcome.connector_name}, fetched={outcome.fetched_count}, "
        f"used_oauth={outcome.used_oauth}, duration={outcome.duration_seconds:.3f}s"
    )

    # ---------------------------------------------------------------------------------
    # Step 4: Round-robin 3 manual tick -> ogni connettore fetchato 1 volta extra
    # ---------------------------------------------------------------------------------
    print("[4/6] Round-robin: 3 manual tick consecutivi...")
    # Reset counters; lo Step 3 + start() implicito hanno gia' tirato 1 tick scheduled
    # forse, ma la verifica e' che dopo 3 manual tick SUCCESSIVI ogni connector e'
    # fetchato esattamente 1 volta (round-robin proprio).
    pre_counts = dict(_call_counts)
    outcomes: list[AutoFetchOutcome] = []
    for _ in range(3):
        o = await loop.run_tick_now()
        outcomes.append(o)
    # Verifica round-robin: i 3 outcome devono coprire tutti e 3 i connector
    picked = {o.connector_name for o in outcomes}
    if picked != set(connectors):
        print(
            f"      FAIL: round-robin non ha coperto tutti: picked={picked}, expected={set(connectors)}"
        )
        return 4
    # Inoltre: i counter dei 3 connector devono essere tutti incrementati di +1
    for name in connectors:
        delta = _call_counts[name] - pre_counts.get(name, 0)
        if delta != 1:
            print(f"      FAIL: connector {name} fetchato {delta} volte (atteso 1)")
            return 4
    print(f"      OK round-robin coprende {picked}, ogni connector +1 call")

    # ---------------------------------------------------------------------------------
    # Step 5: Error backoff -> 3 fail consecutivi su 'alpha' -> cooldown attivato
    # ---------------------------------------------------------------------------------
    print("[5/6] Error backoff: simula 3 fail consecutivi su 'alpha' -> cooldown...")
    _inject_errors_for.add("alpha")
    # Per costringere il loop a fetchare alpha 3 volte di seguito, settiamo il cursor
    # round-robin manualmente sul connector_state. Strategia: chiamo run_tick_now() in
    # un ciclo finche' il cursor non passa per 'alpha' 3 volte. Conta solo i tick che
    # toccano alpha.
    alpha_failures = 0
    max_iters = 30  # safety net
    iter_count = 0
    while alpha_failures < 3 and iter_count < max_iters:
        o = await loop.run_tick_now()
        iter_count += 1
        if o.connector_name == "alpha":
            if o.errors:
                alpha_failures += 1
            else:
                # Inatteso: alpha senza errors quando _inject_errors_for contiene alpha
                print("      FAIL: alpha tick senza errors malgrado _inject_errors_for")
                return 5
    if alpha_failures < 3:
        print(f"      FAIL: solo {alpha_failures} fail su alpha in {iter_count} iterazioni")
        return 5
    # Ora verifica lo stato del connector alpha: consecutive_failures >= 3
    # e cooldown_until valorizzato.
    status = loop.get_status()
    rr = status["connectors_round_robin_state"]
    alpha_state = rr.get("alpha", {})
    if alpha_state.get("consecutive_failures", 0) < 3:
        print(
            f"      FAIL: alpha consecutive_failures={alpha_state.get('consecutive_failures')} < 3"
        )
        return 5
    if alpha_state.get("cooldown_until") is None:
        print("      FAIL: alpha cooldown_until is None dopo 3 fail")
        return 5
    print(
        f"      OK alpha cooldown attivato: consecutive_failures="
        f"{alpha_state['consecutive_failures']}, cooldown_until={alpha_state['cooldown_until']}"
    )

    # ---------------------------------------------------------------------------------
    # Step 6: stop() -> is_running() == False entro 30s
    # ---------------------------------------------------------------------------------
    print("[6/6] stop() cooperativo + verifica is_running() == False...")
    import time

    t0 = time.monotonic()
    stopped = await loop.stop()
    elapsed = time.monotonic() - t0
    if not stopped:
        print("      FAIL: stop() ha ritornato False (loop non era running?)")
        return 6
    if loop.is_running():
        print("      FAIL: is_running() == True dopo stop()")
        return 6
    if elapsed > 30.0:
        print(f"      FAIL: stop() ha richiesto {elapsed:.1f}s > 30s")
        return 6
    print(f"      OK stop() completato in {elapsed:.3f}s")

    # Stop idempotente
    stopped_again = await loop.stop()
    if stopped_again:
        print("      FAIL: secondo stop() doveva ritornare False (idempotente)")
        return 6
    print("      OK stop() idempotent")

    # ---------------------------------------------------------------------------------
    # Verifica finale: activity log popolato + read_activity_log() funziona
    # ---------------------------------------------------------------------------------
    print("\n[verify] read_activity_log() -> entries totali appese al file...")
    entries = loop.read_activity_log(n=100)
    if not entries:
        print("      FAIL: activity log vuoto, atteso almeno 7 entry (1+3+3 tick)")
        return 7
    expected_keys = {
        "ts",
        "connector_name",
        "fetched_count",
        "errors",
        "used_oauth",
        "duration_seconds",
        "manual",
        "cancelled",
    }
    sample = entries[-1]
    missing = expected_keys - set(sample.keys())
    if missing:
        print(f"      FAIL: activity entry manca chiavi: {missing}")
        return 7
    print(f"      OK {len(entries)} entry letti dal log, schema coerente")

    print("\n=== SMOKE W2-AUTOFETCH: PASS ===")
    print(f"Activity log restato in: {activity_log}")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except Exception as e:
        print(f"\nFATAL: {e}")
        import traceback

        traceback.print_exc()
        exit_code = 99
    sys.exit(exit_code)
