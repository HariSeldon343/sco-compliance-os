"""API router moduli FastAPI per SCO Compliance OS.

Routers:
- chat_routes: /api/chat — streaming SSE + conversations CRUD.
- vault_routes: /api/vault — registrazione + ispezione vault Karpathy.
- memory_routes: /api/memory — memory tree + ingest + search.
- integrations_routes: /api/integrations — connettori OAuth (Gmail, Drive, ecc.).
- onboarding_routes: /api/onboarding — stato EULA/Privacy/Demo/Tutorial.
- subconscious_routes: /api/subconscious — tick loop subconscious 5 min (Wave 1 v0.2.0).
- tokenjuice_routes: /api/tokenjuice — 3-layer compression engine (Wave 2 v0.3.0).
"""

from __future__ import annotations
