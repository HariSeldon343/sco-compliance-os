"""Lock manager + cancellation per il Subconscious tick loop.

Modulo storico W1 v0.2.0. Da W2 v0.3.0 il pattern e' stato estratto in
:mod:`sco_compliance_os.services.common.throttle` per riuso anche dal
:mod:`sco_compliance_os.services.integrations.auto_fetch_loop`. Questo modulo
resta come **re-export di compatibilita'** per non rompere W1 (smoke
``smoke_w1_memory.py`` + import esistenti da ``tick_loop.py``).

Vincolo OpenHuman: i tick NON si accumulano mai. Se mentre un tick T_n e' in
esecuzione arriva il momento di T_{n+1} (manual trigger o scadenza intervallo),
T_{n+1} prende posto e T_n viene marcato come ``cancelled``. Il consumer
controlla ``token.cancelled.is_set()`` ai checkpoint e abortisce in modo
cooperativo.

Esempio uso (idiomatico, invariato W1)::

    throttle = TickThrottle(name="subconscious")  # preserva log namespace storico
    async with throttle.acquire() as token:
        # ...lavoro pesante, occasionalmente check token.cancelled.is_set()
        if token.cancelled.is_set():
            return
"""

from __future__ import annotations

# Re-export per compat W1 (no breaking change a tick_loop.py + smoke W1).
from sco_compliance_os.services.common.throttle import CancellationToken, TickThrottle

__all__ = ["CancellationToken", "TickThrottle"]
