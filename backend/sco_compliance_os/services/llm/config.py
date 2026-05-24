"""Service helpers per tenant LLM config (esposti via /api/v1/tenant/me/llm-config).

Wrapper alto livello attorno a router.get_tenant_llm_config + invalidate per UI admin.
"""

from __future__ import annotations

from typing import Any

from sco_compliance_os.services.llm.router import (
    DEFAULT_TIER_CHAINS,
    get_tenant_llm_config,
    invalidate_tenant_config_cache,
)

__all__ = [
    "get_effective_llm_config",
    "invalidate_tenant_config_cache",
]


def _serialize_default_chains() -> dict[str, list[dict[str, Any]]]:
    """Serializza le chain default a JSON-safe per response API."""
    out: dict[str, list[dict[str, Any]]] = {}
    for tier_key, chain in DEFAULT_TIER_CHAINS.items():
        out[tier_key] = [
            {
                "provider": s.provider_name,
                "model": s.model,
                "pinned": s.pinned,
            }
            for s in chain
        ]
    return out


async def get_effective_llm_config(tenant_id: str = "local") -> dict[str, Any]:
    """Ritorna effective config: tenant override merged con default chain.

    Schema response:
    {
        "tenant_id": "...",
        "defaults": {tier: [{provider, model, pinned}, ...], ...},
        "overrides": {tier: {provider, model}, ...},  # dal SaaS
        "effective": {tier: {provider, model, source: "tenant" | "default"}, ...}
    }
    """
    tenant_config = await get_tenant_llm_config(tenant_id)
    defaults = _serialize_default_chains()
    overrides: dict[str, Any] = tenant_config.get("llm_providers", {}) or {}

    effective: dict[str, dict[str, Any]] = {}
    for tier_key, chain in DEFAULT_TIER_CHAINS.items():
        if tier_key in overrides and overrides[tier_key].get("provider"):
            o = overrides[tier_key]
            effective[tier_key] = {
                "provider": o.get("provider"),
                "model": o.get("model"),
                "source": "tenant",
            }
        else:
            primary = chain[0]
            effective[tier_key] = {
                "provider": primary.provider_name,
                "model": primary.model,
                "source": "default",
            }

    return {
        "tenant_id": tenant_id,
        "defaults": defaults,
        "overrides": overrides,
        "effective": effective,
    }
