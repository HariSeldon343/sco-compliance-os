"""Router policy-driven multi-LLM con 5 tier workload + fallback automatico.

5 tier workload:
- reasoning-v1: task complessi multi-step
- fast-v1: risposte rapide
- agentic-v1: tool use intensive
- coding-v1: code generation
- summarization-v1: sealing memory tree + RAG

Routing decisionale per tier:
1. Override tenant_config (BYOK preferenza per tier specifico).
2. Default mapping tier -> (provider primario, fallback chain).
3. Health check: se primario fail 3x consecutive in sliding window 5min,
   fallback automatico al prossimo della catena.

Pattern Conv. 47: tenant_config dal SaaS, cache memory 5 min TTL.
Pattern Conv. 41 tracciatura: ogni routing decision loggato structured.
Pattern SCO "no rocket science": dispatch table + health scoring.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.llm.provider import (
    LLMProvider,
    ProviderConfig,
    ProviderError,
)
from sco_compliance_os.services.llm.providers.anthropic import AnthropicProvider
from sco_compliance_os.services.llm.providers.gemini import GeminiProvider
from sco_compliance_os.services.llm.providers.ollama import OllamaProvider
from sco_compliance_os.services.llm.providers.openai import OpenAIProvider

logger = get_logger(__name__)

# Tier workload disponibili nel router v0.7.0
Tier = Literal[
    "reasoning-v1",
    "fast-v1",
    "agentic-v1",
    "coding-v1",
    "summarization-v1",
]

ProviderName = Literal["anthropic", "openai", "gemini", "ollama"]


@dataclass
class ProviderSpec:
    """Spec di un provider in fallback chain.

    `pinned=True` significa che il fallback automatico è disabilitato per quel
    tier specifico (es. agentic-v1 hard-pinned su anthropic perché tool use
    nativo Anthropic non è 1:1 portabile su altri provider).
    """

    provider_name: ProviderName
    model: str
    pinned: bool = False


# Default tier -> chain mapping v0.7.0.
# Ogni tier ha una catena ordinata di provider; il primo è il primario,
# i successivi sono fallback in ordine di preferenza.
#
# v0.12.0 (25/05/2026): bump default chat (tier agentic-v1) da Sonnet 4.6 a
# Opus 4.7 per allineamento al SaaS default (schema.ts:209). Pinned=True
# mantenuto: tool use nativo Anthropic non è 1:1 portabile su altri provider.
# Overridabile per tenant via tenant_config.llm_providers["agentic-v1"]
# (single source of truth backend, Conv. 47 enforcement).
DEFAULT_TIER_CHAINS: dict[Tier, list[ProviderSpec]] = {
    "reasoning-v1": [
        ProviderSpec("anthropic", "claude-opus-4-7"),
        ProviderSpec("openai", "gpt-5"),
        ProviderSpec("gemini", "gemini-2-pro"),
    ],
    "fast-v1": [
        ProviderSpec("anthropic", "claude-haiku-4-5-20251001"),
        ProviderSpec("openai", "gpt-4o-mini"),
        ProviderSpec("gemini", "gemini-1.5-flash"),
    ],
    "agentic-v1": [
        ProviderSpec("anthropic", "claude-opus-4-7", pinned=True),
    ],
    "coding-v1": [
        ProviderSpec("anthropic", "claude-opus-4-7"),
        ProviderSpec("openai", "gpt-5-codex"),
    ],
    "summarization-v1": [
        ProviderSpec("ollama", "llama3.2:3b"),
        ProviderSpec("anthropic", "claude-haiku-4-5-20251001"),
    ],
}


@dataclass
class RoutingDecision:
    """Risultato di una route() — provider + model + razionale tracciabile."""

    provider: LLMProvider
    provider_name: ProviderName
    model: str
    tier: Tier
    fallback_used: bool = False
    fallback_chain_attempted: list[str] = field(default_factory=list)


# ----- Health scoring cache -----


@dataclass
class _ProviderHealthState:
    """Stato di health di un provider in sliding window 5 min."""

    failure_timestamps: list[float] = field(default_factory=list)
    last_check_ts: float = 0.0
    last_healthy: bool = True


# Sliding window per failure counter (5 minuti).
_HEALTH_WINDOW_SECONDS = 300.0
# Threshold consecutive failures che triggera fallback.
_HEALTH_FAILURE_THRESHOLD = 3

# In-memory health state per provider_name.
_health_state: dict[ProviderName, _ProviderHealthState] = {}
_health_lock = asyncio.Lock()


def _prune_old_failures(state: _ProviderHealthState, now: float) -> None:
    """Rimuove timestamp failure più vecchi della window."""
    cutoff = now - _HEALTH_WINDOW_SECONDS
    state.failure_timestamps = [t for t in state.failure_timestamps if t >= cutoff]


async def record_failure(provider_name: ProviderName) -> None:
    """Registra un failure per il provider. Triggera fallback se threshold."""
    async with _health_lock:
        state = _health_state.setdefault(provider_name, _ProviderHealthState())
        now = time.time()
        state.failure_timestamps.append(now)
        _prune_old_failures(state, now)
        state.last_healthy = len(state.failure_timestamps) < _HEALTH_FAILURE_THRESHOLD
        logger.warning(
            "llm_router.failure_recorded",
            provider=provider_name,
            failures_in_window=len(state.failure_timestamps),
            threshold=_HEALTH_FAILURE_THRESHOLD,
            still_healthy=state.last_healthy,
        )


async def is_healthy(provider_name: ProviderName) -> bool:
    """True se provider sotto soglia failures in window."""
    async with _health_lock:
        state = _health_state.get(provider_name)
        if state is None:
            return True
        now = time.time()
        _prune_old_failures(state, now)
        return len(state.failure_timestamps) < _HEALTH_FAILURE_THRESHOLD


# ----- Tenant config cache -----


@dataclass
class _TenantConfigCacheEntry:
    """Entry cache tenant_config con TTL."""

    config: dict[str, Any]
    fetched_at: float


_TENANT_CONFIG_TTL_SECONDS = 300.0  # 5 min
_tenant_config_cache: dict[str, _TenantConfigCacheEntry] = {}
_tenant_config_lock = asyncio.Lock()


async def get_tenant_llm_config(tenant_id: str = "local") -> dict[str, Any]:
    """Fetch tenant LLM config dal SaaS con cache 5 min TTL.

    Args:
        tenant_id: identificativo tenant. "local" per dev/single-tenant.

    Returns:
        Dict con schema:
        {
            "llm_providers": {
                "reasoning-v1": {"provider": "anthropic", "model": "claude-opus-4-7", "byok_key_ref": "..."},
                ...
            },
            "byok_keys": {
                "openai": "sk-...",
                "gemini": "AIza...",
            }
        }

        Vuoto se SaaS non raggiungibile o tenant non configurato (default chain).
    """
    async with _tenant_config_lock:
        now = time.time()
        entry = _tenant_config_cache.get(tenant_id)
        if entry and (now - entry.fetched_at) < _TENANT_CONFIG_TTL_SECONDS:
            return dict(entry.config)

    # Cache miss o stale: fetch da SaaS
    config = await _fetch_tenant_config_from_saas(tenant_id)

    async with _tenant_config_lock:
        _tenant_config_cache[tenant_id] = _TenantConfigCacheEntry(
            config=config,
            fetched_at=time.time(),
        )

    return config


async def _fetch_tenant_config_from_saas(tenant_id: str) -> dict[str, Any]:
    """Fetch effettivo da SaaS endpoint /api/v1/tenant/{id}/llm-config.

    Best-effort: errori loggati, ritorna {} per fallback a default chain.
    """
    from sco_compliance_os.config import get_settings

    settings = get_settings()
    saas_base = settings.sco_saas_base_url.strip().rstrip("/")
    if not saas_base:
        logger.info("llm_router.tenant_config.no_saas_configured", tenant_id=tenant_id)
        return {}

    # Per "local" tenant: nessuna chiamata SaaS, ritorna dict vuoto (default chain)
    if tenant_id == "local":
        return {}

    license_key = settings.license_key.get_secret_value().strip()
    if not license_key:
        logger.info("llm_router.tenant_config.no_license_key", tenant_id=tenant_id)
        return {}

    import httpx

    url = f"{saas_base}/api/v1/tenant/{tenant_id}/llm-config"
    headers = {"Authorization": f"Bearer {license_key}"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data: dict[str, Any] = resp.json()
                logger.info(
                    "llm_router.tenant_config.fetched",
                    tenant_id=tenant_id,
                    has_providers=bool(data.get("llm_providers")),
                )
                return data
            logger.warning(
                "llm_router.tenant_config.fetch_failed",
                tenant_id=tenant_id,
                status=resp.status_code,
            )
            return {}
    except Exception as exc:
        logger.warning(
            "llm_router.tenant_config.fetch_error",
            tenant_id=tenant_id,
            error=str(exc),
        )
        return {}


def invalidate_tenant_config_cache(tenant_id: str | None = None) -> None:
    """Invalida cache (tutta o per tenant). Per admin UI dopo save config."""
    if tenant_id is None:
        _tenant_config_cache.clear()
        logger.info("llm_router.tenant_config_cache.cleared_all")
    else:
        _tenant_config_cache.pop(tenant_id, None)
        logger.info("llm_router.tenant_config_cache.cleared_tenant", tenant_id=tenant_id)


# ----- Provider factory -----


def _build_provider(
    provider_name: ProviderName,
    model: str,
    tenant_config: dict[str, Any],
) -> LLMProvider:
    """Istanzia provider concreto con credentials risolte da tenant_config.

    Precedenza credentials:
    1. tenant_config.byok_keys[provider_name] (BYOK enterprise tenant)
    2. Anthropic: fallback _resolve_credentials() (license_key SaaS proxy)
    3. Errore ProviderError per provider non-anthropic senza BYOK
    """
    byok_keys: dict[str, str] = tenant_config.get("byok_keys", {}) or {}
    api_key = byok_keys.get(provider_name, "")
    base_url = ""

    if provider_name == "anthropic":
        # Anthropic special: se BYOK non presente, usa license SaaS proxy
        if not api_key:
            from sco_compliance_os.core.agent_sdk_runner import _resolve_credentials

            creds = _resolve_credentials()
            if creds is None:
                raise ProviderError(
                    "Nessuna license attiva e nessuna BYOK Anthropic configurata.",
                    provider_name="anthropic",
                    exc_type="MissingCredentials",
                )
            base_url, api_key = creds
        config = ProviderConfig(
            name="anthropic",
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=30.0,
            max_retries=1,
        )
        return AnthropicProvider(config)

    if provider_name == "openai":
        if not api_key:
            raise ProviderError(
                "OpenAI richiede BYOK key in tenant_config.byok_keys.openai",
                provider_name="openai",
                exc_type="MissingCredentials",
            )
        config = ProviderConfig(
            name="openai",
            api_key=api_key,
            timeout_seconds=30.0,
            max_retries=1,
        )
        return OpenAIProvider(config)

    if provider_name == "gemini":
        if not api_key:
            raise ProviderError(
                "Gemini richiede BYOK key in tenant_config.byok_keys.gemini",
                provider_name="gemini",
                exc_type="MissingCredentials",
            )
        config = ProviderConfig(
            name="gemini",
            api_key=api_key,
            timeout_seconds=30.0,
            max_retries=1,
        )
        return GeminiProvider(config)

    if provider_name == "ollama":
        # Ollama: nessuna API key richiesta, base_url default localhost
        ollama_base = tenant_config.get("ollama_base_url", "") or ""
        config = ProviderConfig(
            name="ollama",
            api_key="",
            base_url=ollama_base,
            timeout_seconds=60.0,  # Ollama locale può essere più lento
            max_retries=1,
        )
        return OllamaProvider(config)

    raise ProviderError(
        f"Provider name sconosciuto: {provider_name}",
        provider_name=str(provider_name),
        exc_type="UnknownProvider",
    )


# ----- Core route() function -----


def _resolve_tier_chain(
    tier: Tier,
    tenant_config: dict[str, Any],
) -> list[ProviderSpec]:
    """Risolve chain per tier: applica eventuale override tenant + default.

    Override tenant_config:
        {
            "llm_providers": {
                "reasoning-v1": {"provider": "openai", "model": "gpt-5"}
            }
        }
    Quando il tenant ha override per il tier, il primario è quello scelto;
    la chain di fallback default viene preservata escludendo l'override
    (per evitare duplicati) e accodata dopo l'override.
    """
    default_chain = DEFAULT_TIER_CHAINS.get(tier, [])

    overrides: dict[str, Any] = tenant_config.get("llm_providers", {}) or {}
    tier_override = overrides.get(tier)
    if not tier_override:
        return list(default_chain)

    override_provider = tier_override.get("provider")
    override_model = tier_override.get("model")
    if not override_provider or not override_model:
        return list(default_chain)

    override_spec = ProviderSpec(
        provider_name=override_provider,
        model=override_model,
        pinned=False,
    )
    # Preserva default chain escludendo eventuale duplicato dell'override
    rest = [
        s
        for s in default_chain
        if not (s.provider_name == override_provider and s.model == override_model)
    ]
    return [override_spec, *rest]


async def route(
    tier: Tier = "agentic-v1",
    tenant_config: dict[str, Any] | None = None,
    skip_health_check: bool = False,
) -> RoutingDecision:
    """Selezione policy-driven del provider per il tier richiesto.

    Args:
        tier: tier workload (default "agentic-v1" backward-compat chat).
        tenant_config: config tenant fetched da get_tenant_llm_config() o {}
            per default chain.
        skip_health_check: se True, prende il primario senza health scoring.
            Usato per testing/debug o quando il caller ha già fatto check.

    Returns:
        RoutingDecision con provider istanziato + tracciabilità chain.

    Raises:
        ProviderError se nessun provider della chain è istanziabile (es. tutte
        le credential mancanti).
    """
    tenant_config = tenant_config or {}
    chain = _resolve_tier_chain(tier, tenant_config)
    if not chain:
        raise ProviderError(
            f"Nessun provider chain configurato per tier '{tier}'",
            provider_name="unknown",
            exc_type="NoChainConfigured",
        )

    chain_attempted: list[str] = []
    last_error: Exception | None = None

    for idx, spec in enumerate(chain):
        attempted_label = f"{spec.provider_name}:{spec.model}"
        chain_attempted.append(attempted_label)

        # Health scoring: skip provider unhealthy (eccetto pinned)
        if not skip_health_check and not spec.pinned:
            healthy = await is_healthy(spec.provider_name)
            if not healthy:
                logger.warning(
                    "llm_router.skip_unhealthy",
                    tier=tier,
                    provider=spec.provider_name,
                    model=spec.model,
                    position=idx,
                )
                continue

        # Tenta build provider
        try:
            provider = _build_provider(spec.provider_name, spec.model, tenant_config)
        except ProviderError as perr:
            last_error = perr
            logger.warning(
                "llm_router.build_failed",
                tier=tier,
                provider=spec.provider_name,
                model=spec.model,
                position=idx,
                error=str(perr),
            )
            continue
        except Exception as exc:
            last_error = exc
            logger.exception(
                "llm_router.build_unexpected_error",
                tier=tier,
                provider=spec.provider_name,
                model=spec.model,
                position=idx,
            )
            continue

        # Success
        fallback_used = idx > 0
        decision = RoutingDecision(
            provider=provider,
            provider_name=spec.provider_name,
            model=spec.model,
            tier=tier,
            fallback_used=fallback_used,
            fallback_chain_attempted=chain_attempted,
        )
        logger.info(
            "llm_router.routed",
            tier=tier,
            provider=spec.provider_name,
            model=spec.model,
            fallback_used=fallback_used,
            attempted=chain_attempted,
        )
        return decision

    # Tutta la chain ha fallito
    raise ProviderError(
        f"Tutta la chain per tier '{tier}' ha fallito. Tentati: {chain_attempted}. "
        f"Ultimo errore: {last_error}",
        provider_name="unknown",
        exc_type="ChainExhausted",
    )


# ----- Discovery helpers per endpoint /api/llm/* -----


async def discover_providers(tenant_config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Discovery dei 4 provider con stato available + lista modelli.

    Usato dal endpoint GET /api/llm/providers.
    """
    tenant_config = tenant_config or {}
    providers_info: list[dict[str, Any]] = []

    for provider_name in ("anthropic", "openai", "gemini", "ollama"):
        # Tenta build per scoprire se credentials presenti
        available = False
        models: list[str] = []
        error_msg = ""
        local_marker = provider_name == "ollama"

        try:
            # Per build usiamo il default tier appropriato per ogni provider
            # (model "any" purché sia istanziabile).
            placeholder_model = {
                "anthropic": "claude-opus-4-7",
                "openai": "gpt-4o-mini",
                "gemini": "gemini-1.5-flash",
                "ollama": "llama3.2:3b",
            }[provider_name]

            provider = _build_provider(provider_name, placeholder_model, tenant_config)
            # health check
            healthy = await provider.health_check()
            available = healthy
            if healthy:
                models = await provider.list_models()
        except ProviderError as perr:
            error_msg = str(perr)
            available = False
        except Exception as exc:
            error_msg = str(exc)
            available = False
            logger.warning(
                "llm_router.discover.provider_error",
                provider=provider_name,
                error=error_msg,
            )

        info: dict[str, Any] = {
            "name": provider_name,
            "available": available,
            "models": models,
            "local": local_marker,
        }
        if error_msg:
            info["error"] = error_msg
        providers_info.append(info)

    return providers_info


async def health_all_providers(
    tenant_config: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Health check di tutti e 4 i provider.

    Usato dal endpoint GET /api/llm/health.
    """
    tenant_config = tenant_config or {}
    results: dict[str, dict[str, Any]] = {}
    for provider_name in ("anthropic", "openai", "gemini", "ollama"):
        try:
            placeholder_model = {
                "anthropic": "claude-opus-4-7",
                "openai": "gpt-4o-mini",
                "gemini": "gemini-1.5-flash",
                "ollama": "llama3.2:3b",
            }[provider_name]
            provider = _build_provider(provider_name, placeholder_model, tenant_config)
            healthy = await provider.health_check()
            results[provider_name] = {
                "healthy": healthy,
                "circuit_open": not await is_healthy(provider_name),
            }
        except ProviderError as perr:
            results[provider_name] = {
                "healthy": False,
                "error": str(perr),
                "circuit_open": not await is_healthy(provider_name),
            }
        except Exception as exc:
            results[provider_name] = {
                "healthy": False,
                "error": str(exc),
                "circuit_open": not await is_healthy(provider_name),
            }
    return results
