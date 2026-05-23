"""Componenti riusabili condivisi tra i servizi del backend SCO Compliance OS.

Questo pacchetto raccoglie i pattern infrastrutturali generici (lock manager,
cancellation token, eventuali utility async future) che servono a piu' di un
servizio specifico. La regola e' semplice: se due servizi diversi (es.
``subconscious`` e ``integrations``) hanno bisogno della stessa primitive,
quella primitive vive qui.

Componenti esposti:

- :class:`TickThrottle` (``throttle.py``): lock manager + cancellation
  cooperativo per loop a tick periodici. Garantisce ``no-overlap +
  no-accumulation`` dei tick: se ne arriva uno nuovo mentre il precedente
  e' in esecuzione, il precedente viene marcato come cancelled tramite
  :class:`asyncio.Event` (cooperativo, mai kill).
- :class:`CancellationToken` (``throttle.py``): token dataclass riusabile.

Vincoli del pattern:

1. Single-process backend FastAPI: nessuna lock filesystem o DB necessaria.
2. asyncio-only: nessuna dipendenza threading (gli holder eseguono nello
   stesso event loop).
3. Stateless contract: l'holder controlla ``token.cancelled.is_set()`` ai
   checkpoint sicuri (prima di chiamate LLM costose, prima di scrivere DB,
   prima di append a file di log).

Storia: estratto Wave 2 v0.3.0 dal pacchetto ``services.subconscious.throttle``
per riuso nel nuovo ``services.integrations.auto_fetch_loop``. La versione
originale resta come re-export per backwards-compat (W1 smoke test continua
a passare).
"""

from __future__ import annotations

from .throttle import CancellationToken, TickThrottle

__all__ = [
    "CancellationToken",
    "TickThrottle",
]
