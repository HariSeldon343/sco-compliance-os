"""Router /api/llm — discovery providers + health + tenant llm-config.

Endpoint:
- GET  /api/llm/providers          → lista 4 provider con available + models
- GET  /api/llm/health             → ping ogni provider + circuit state
- GET  /api/v1/tenant/me/llm-config → effective config tenant (defaults + overrides)
- POST /api/v1/tenant/me/llm-config/invalidate → invalida cache (per UI admin SaaS sync)

Pattern Conv. 47: tenant_config single source of truth lato SaaS. Backend locale
SOLO lettura via /api/llm/* per discovery UI (settings desktop NON tocca selezione,
quella vive in Vercel admin via subagent DEV-SAAS-SPRINT2 separato).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.llm.config import (
    get_effective_llm_config,
    invalidate_tenant_config_cache,
)
from sco_compliance_os.services.llm.router import (
    discover_providers,
    get_tenant_llm_config,
    health_all_providers,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])


# ----- Discovery providers -----


@router.get("/providers")
async def list_providers(
    tenant_id: str = Query(
        default="local",
        description="Tenant ID per fetch BYOK keys. 'local' per single-tenant.",
    ),
) -> list[dict[str, Any]]:
    """Lista 4 provider con stato available + lista modelli runtime.

    Response:
        [
            {"name": "anthropic", "available": true, "models": [...], "local": false},
            {"name": "openai", "available": false, "models": [], "local": false, "error": "..."},
            {"name": "gemini", "available": false, "models": [], "local": false, "error": "..."},
            {"name": "ollama", "available": true, "models": ["llama3.2:3b"], "local": true},
        ]

    `available=False` non è errore HTTP: indica solo che il provider non è
    configurato/raggiungibile (es. BYOK mancante, Ollama non installato).
    """
    tenant_config = await get_tenant_llm_config(tenant_id)
    return await discover_providers(tenant_config)


@router.get("/health")
async def health_providers(
    tenant_id: str = Query(
        default="local",
        description="Tenant ID per fetch BYOK keys.",
    ),
) -> dict[str, dict[str, Any]]:
    """Health check di tutti e 4 i provider + circuit state.

    Response:
        {
            "anthropic": {"healthy": true, "circuit_open": false},
            "openai": {"healthy": false, "error": "...", "circuit_open": true},
            "gemini": {"healthy": false, "error": "...", "circuit_open": false},
            "ollama": {"healthy": true, "circuit_open": false}
        }

    `circuit_open=true` significa che il router lo sta saltando per fallback
    (3+ failures consecutive in 5min window).
    """
    tenant_config = await get_tenant_llm_config(tenant_id)
    return await health_all_providers(tenant_config)


# ----- Tenant config (read-only, SaaS è source of truth) -----


@router.get("/tenant/me/llm-config")
async def get_my_llm_config(
    tenant_id: str = Query(
        default="local",
        description="Tenant ID (typicamente 'me' che il backend risolve).",
    ),
) -> dict[str, Any]:
    """Effective LLM config del tenant corrente.

    Response:
        {
            "tenant_id": "local",
            "defaults": {tier: [{provider, model, pinned}, ...]},
            "overrides": {tier: {provider, model}},
            "effective": {tier: {provider, model, source}}
        }
    """
    try:
        return await get_effective_llm_config(tenant_id)
    except Exception as exc:
        logger.exception("llm_routes.get_my_llm_config.error", tenant_id=tenant_id, error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Errore fetch tenant LLM config: {exc}",
        ) from exc


@router.post("/tenant/me/llm-config/invalidate")
async def invalidate_my_llm_config_cache(
    tenant_id: str = Query(
        default="local",
        description="Tenant ID di cui invalidare la cache.",
    ),
) -> dict[str, str]:
    """Invalida cache tenant_config (per sync immediato dopo save admin SaaS).

    Da chiamare quando l'admin UI SaaS Vercel cambia llm_providers di un tenant:
    il backend locale può ricevere notifica e svuotare cache per pickup immediato.
    """
    invalidate_tenant_config_cache(tenant_id)
    return {"status": "invalidated", "tenant_id": tenant_id}
