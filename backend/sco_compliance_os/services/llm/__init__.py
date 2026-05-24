"""Multi-LLM router policy-driven (v0.7.0 clean-room).

Modulo che astrae la scelta del provider LLM dietro un Protocol uniforme.
4 provider supportati:
- Anthropic (via SaaS proxy SCO, license_key Bearer)
- OpenAI (BYOK o via SaaS proxy futuro)
- Gemini (Google Generative AI)
- Ollama (local-only, http://localhost:11434)

Pattern Karpathy "no rocket science": dataclass + protocol + dispatch table.
Nessun copy da OpenHuman/altri router GPL: design clean-room basato su idee
architetturali astratte (provider abstraction, tiered routing, fallback).

Pattern Conv. 47 single source of truth: tenant_config dal SaaS, mai cached
persistente lato backend locale (cache memory 5 min TTL).
Pattern Conv. 41 tracciatura: ogni routing decision loggato.
Pattern Conv. 44 lesson 1: timeout HTTP 30s + retry 1 con backoff.
"""

from __future__ import annotations

from sco_compliance_os.services.llm.provider import (
    ChunkEvent,
    ChunkKind,
    LLMProvider,
    ProviderError,
)
from sco_compliance_os.services.llm.router import (
    RoutingDecision,
    Tier,
    route,
)

__all__ = [
    "ChunkEvent",
    "ChunkKind",
    "LLMProvider",
    "ProviderError",
    "RoutingDecision",
    "Tier",
    "route",
]
