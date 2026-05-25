"""Adapter Anthropic SDK Python con routing via SaaS proxy SCO (default).

Refactor minimal di agent_sdk_runner: estrae la logica `AsyncAnthropic.messages.stream()`
in classe LLMProvider conforme. Mantiene base_url SaaS proxy + Bearer license_key.

Backward compat: la classe AgentRunner originale resta in agent_sdk_runner.py
fino a migrazione completa di chat_routes.py.

Pattern Conv. 47 single source of truth: legge credentials da _resolve_credentials()
runtime, nessun stato persistente fra chiamate stream().
Pattern Conv. 44 lesson 1: timeout configurabile (default 30s) + nessun background.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.llm.provider import (
    ChunkEvent,
    LLMProvider,
    ProviderConfig,
    ProviderError,
)

logger = get_logger(__name__)


class AnthropicProvider(LLMProvider):
    """Provider Anthropic via AsyncAnthropic SDK con SaaS proxy override.

    Modelli supportati v0.7.0 (default mapping v0.12.0 25/05/2026):
    - claude-opus-4-7 (reasoning-v1 + agentic-v1 + coding-v1, default chat)
    - claude-sonnet-4-6 (opzione legacy / fallback secondario)
    - claude-haiku-4-5-20251001 (fast-v1 + summarization-v1)
    """

    name = "anthropic"

    # Lista canonica modelli supportati. Aggiornata manualmente quando Anthropic
    # rilascia nuovi modelli (l'SDK non espone discovery /models endpoint pubblico).
    KNOWN_MODELS = [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
        "claude-haiku-4-5",
    ]

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_key:
            raise ProviderError(
                "Anthropic provider richiede api_key (license_key SaaS o BYOK)",
                provider_name=self.name,
                exc_type="MissingCredentials",
            )
        if not config.base_url:
            # Default: endpoint nativo Anthropic
            config.base_url = "https://api.anthropic.com"
        self.config = config
        logger.info(
            "anthropic_provider.init",
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
        temperature: float = 1.0,
        extra: dict[str, Any] | None = None,
    ) -> AsyncIterator[ChunkEvent]:
        """Stream da Anthropic messages.stream() normalizzato a ChunkEvent."""
        logger.info(
            "anthropic_provider.stream.start",
            model=model,
            messages_count=len(messages),
            max_tokens=max_tokens,
        )

        client = AsyncAnthropic(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            timeout=httpx.Timeout(self.config.timeout_seconds),
            max_retries=self.config.max_retries,
        )

        # Cast messages a MessageParam (richiede role + content compatibile)
        anthropic_messages: list[MessageParam] = [
            {"role": m["role"], "content": m["content"]} for m in messages
        ]

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": anthropic_messages,
            "temperature": temperature,
        }
        if system_prompt:
            # v0.13.1 fix latency Opus 4.7 + 22 skill catalog (~5400 input tokens):
            # prompt caching ephemeral riduce input tokens computati da 5400 a
            # ~200 dal 2 turn in poi (cache hit). Latency stimata -70%, costo -90%.
            # Pattern Anthropic: system come list di TextBlockParam con cache_control.
            # Fallback string se cache_control non supportato dal modello.
            if len(system_prompt) > 1024:  # cache solo se vale la pena (>1024 char minimum threshold Anthropic)
                kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                kwargs["system"] = system_prompt
        # Passthrough opzioni provider-specific (tools, thinking budget)
        if extra:
            for k, v in extra.items():
                if k in ("tools", "tool_choice", "thinking", "metadata"):
                    kwargs[k] = v

        seq = 0
        try:
            async with client.messages.stream(**kwargs) as stream:
                async for text_chunk in stream.text_stream:
                    yield ChunkEvent(
                        kind="text_delta",
                        data={"text": text_chunk},
                        seq=seq,
                    )
                    seq += 1

                final_message = await stream.get_final_message()
                # v0.13.2 Bug B fix OMEGA-2: espone cache_read_input_tokens +
                # cache_creation_input_tokens per validare cache hit ratio +
                # observability prompt caching ephemeral (Anthropic SDK >=0.96).
                usage_full: dict[str, Any] = {
                    "input_tokens": final_message.usage.input_tokens,
                    "output_tokens": final_message.usage.output_tokens,
                }
                cache_read = getattr(
                    final_message.usage, "cache_read_input_tokens", None
                )
                cache_create = getattr(
                    final_message.usage, "cache_creation_input_tokens", None
                )
                if cache_read is not None:
                    usage_full["cache_read_input_tokens"] = cache_read
                if cache_create is not None:
                    usage_full["cache_creation_input_tokens"] = cache_create
                yield ChunkEvent(
                    kind="done",
                    data={
                        "stop_reason": final_message.stop_reason,
                        "usage": usage_full,
                        "model": final_message.model,
                        "provider": self.name,
                    },
                    seq=seq,
                )
                logger.info(
                    "anthropic_provider.stream.done",
                    events=seq + 1,
                    input_tokens=final_message.usage.input_tokens,
                    output_tokens=final_message.usage.output_tokens,
                )
        except Exception as exc:
            logger.exception("anthropic_provider.stream.error", error=str(exc))
            yield ChunkEvent(
                kind="error",
                data={
                    "message": str(exc),
                    "exc_type": type(exc).__name__,
                    "provider": self.name,
                },
                seq=seq,
            )

    async def health_check(self) -> bool:
        """Probe: tenta una richiesta minima a `/v1/models` o equivalente.

        Anthropic SaaS proxy SCO non espone endpoint discovery dedicato.
        Strategia minimal: ping HTTP base_url (deve dare 401/403 senza auth
        o 200/redirect con auth — entrambi = "alive").
        """
        try:
            url = self.config.base_url.rstrip("/")
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(5.0)
            ) as client:
                # Anthropic non ha /health; ping GET /v1/messages senza body -> 405
                # accettabile come "reachable". Per SaaS proxy: GET /health se esiste.
                resp = await client.get(f"{url}/health")
                if resp.status_code < 500:
                    return True
                return False
        except Exception as exc:
            logger.warning(
                "anthropic_provider.health_check_failed",
                error=str(exc),
            )
            return False

    async def list_models(self) -> list[str]:
        """Ritorna lista modelli canonica.

        Anthropic SDK Python non espone discovery endpoint pubblico v0.7.0.
        """
        return list(self.KNOWN_MODELS)


def build_anthropic_provider_from_license() -> AnthropicProvider | None:
    """Factory helper: costruisce AnthropicProvider da credentials runtime.

    Riproduce la logica di _resolve_credentials() di agent_sdk_runner.py
    senza accoppiamento diretto al runner legacy. Backward-compat per chi
    vuole istanziare il provider senza passare via router.

    Returns:
        AnthropicProvider configurato, oppure None se nessuna credential.
    """
    from sco_compliance_os.core.agent_sdk_runner import _resolve_credentials

    creds = _resolve_credentials()
    if creds is None:
        return None
    base_url, api_key = creds
    config = ProviderConfig(
        name="anthropic",
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=30.0,
        max_retries=1,
    )
    return AnthropicProvider(config)
