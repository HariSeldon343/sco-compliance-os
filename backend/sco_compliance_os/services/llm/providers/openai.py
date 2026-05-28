"""Adapter OpenAI SDK Python.

Modelli supportati v0.7.0:
- gpt-5 (reasoning-v1, coding-v1 fallback)
- gpt-5-codex (coding-v1 fallback specializzato)
- gpt-4-mini / gpt-4o-mini (fast-v1 fallback)

Pattern Conv. 47: api_key fetchata da tenant_config server-side via SaaS admin,
NON da settings locali (BYOK enterprise tenant).
Pattern Conv. 44 lesson 1: timeout 30s + retry 1 con backoff esponenziale SDK-native.

Streaming normalizzato:
- OpenAI chat.completions.stream() yield ChatCompletionChunk con choices[0].delta.content
- Normalizzato a ChunkEvent(kind="text_delta", data={"text": ...})
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.llm.provider import (
    ChunkEvent,
    LLMProvider,
    ProviderConfig,
    ProviderError,
)

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """Provider OpenAI via openai.AsyncOpenAI SDK.

    Import lazy: il pacchetto `openai` è opzionale per ridurre footprint
    bundle quando l'utente non ha BYOK OpenAI configurata.
    """

    name = "openai"

    # Modelli canonici v0.7.0. Aggiornati manualmente.
    KNOWN_MODELS = [
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-codex",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-mini",
    ]

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_key:
            raise ProviderError(
                "OpenAI provider richiede api_key (BYOK)",
                provider_name=self.name,
                exc_type="MissingCredentials",
            )
        self.config = config
        # Default base_url ufficiale
        if not self.config.base_url:
            self.config.base_url = "https://api.openai.com/v1"
        # Lazy client: instantiated on first stream() per evitare import error
        # quando openai SDK non è installato.
        self._client: Any | None = None
        logger.info(
            "openai_provider.init",
            base_url=self.config.base_url,
            timeout=config.timeout_seconds,
        )

    def _get_client(self) -> Any:
        """Lazy init client OpenAI. Solleva ProviderError se SDK mancante."""
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ProviderError(
                "Pacchetto 'openai' non installato. pip install openai>=1.40.0",
                provider_name=self.name,
                exc_type="MissingDependency",
            ) from exc

        self._client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
            max_retries=self.config.max_retries,
        )
        return self._client

    def stream(
        self,
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
        temperature: float = 1.0,
        extra: dict[str, Any] | None = None,
    ) -> AsyncIterator[ChunkEvent]:
        """Stream OpenAI chat.completions normalizzato a ChunkEvent."""

        async def iterator() -> AsyncIterator[ChunkEvent]:
            logger.info(
                "openai_provider.stream.start",
                model=model,
                messages_count=len(messages),
                max_tokens=max_tokens,
            )

            try:
                client = self._get_client()
            except ProviderError as perr:
                yield ChunkEvent(
                    kind="error",
                    data={
                        "message": str(perr),
                        "exc_type": perr.exc_type,
                        "provider": self.name,
                    },
                    seq=0,
                )
                return

            # OpenAI chat schema: messages list con system come primo elemento se presente
            openai_messages: list[dict[str, Any]] = []
            if system_prompt:
                openai_messages.append({"role": "system", "content": system_prompt})
            openai_messages.extend(messages)

            kwargs: dict[str, Any] = {
                "model": model,
                "messages": openai_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if extra:
                for k, v in extra.items():
                    if k in ("tools", "tool_choice", "response_format", "seed"):
                        kwargs[k] = v

            seq = 0
            final_usage: dict[str, int] = {}
            final_stop_reason: str | None = None
            final_model: str = model

            try:
                stream = await client.chat.completions.create(**kwargs)
                async for chunk in stream:
                    # Chunk shape: choices[0].delta.content (text) + finish_reason
                    # Ultimo chunk con stream_options include_usage ha chunk.usage
                    if hasattr(chunk, "usage") and chunk.usage is not None:
                        final_usage = {
                            "input_tokens": chunk.usage.prompt_tokens,
                            "output_tokens": chunk.usage.completion_tokens,
                        }
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    delta = getattr(choice, "delta", None)
                    if delta is not None and delta.content:
                        yield ChunkEvent(
                            kind="text_delta",
                            data={"text": delta.content},
                            seq=seq,
                        )
                        seq += 1
                    if choice.finish_reason is not None:
                        final_stop_reason = choice.finish_reason
                    if hasattr(chunk, "model") and chunk.model:
                        final_model = chunk.model

                yield ChunkEvent(
                    kind="done",
                    data={
                        "stop_reason": final_stop_reason or "end_turn",
                        "usage": final_usage or {"input_tokens": 0, "output_tokens": 0},
                        "model": final_model,
                        "provider": self.name,
                    },
                    seq=seq,
                )
                logger.info(
                    "openai_provider.stream.done",
                    events=seq + 1,
                    input_tokens=final_usage.get("input_tokens", 0),
                    output_tokens=final_usage.get("output_tokens", 0),
                    stop_reason=final_stop_reason,
                )
            except Exception as exc:
                logger.exception("openai_provider.stream.error", error=str(exc))
                yield ChunkEvent(
                    kind="error",
                    data={
                        "message": str(exc),
                        "exc_type": type(exc).__name__,
                        "provider": self.name,
                    },
                    seq=seq,
                )

        return iterator()

    async def health_check(self) -> bool:
        """Probe: list models endpoint OpenAI."""
        try:
            client = self._get_client()
            # OpenAI list models -> 200 se auth ok
            models = await client.models.list()
            # Iter solo primo elemento per evitare paginazione completa
            count = 0
            async for _ in models:
                count += 1
                if count >= 1:
                    break
            return True
        except Exception as exc:
            logger.warning("openai_provider.health_check_failed", error=str(exc))
            return False

    async def list_models(self) -> list[str]:
        """Discovery modelli OpenAI runtime via /v1/models.

        Filtra ai modelli chat/completions noti per evitare clutter
        (embedding models, dall-e, whisper, etc).
        """
        try:
            client = self._get_client()
            models = await client.models.list()
            ids: list[str] = []
            async for m in models:
                mid = getattr(m, "id", "")
                # Filtra chat-capable: prefisso gpt- o o1- o o3- o equivalenti
                if mid and (mid.startswith(("gpt-", "o1-", "o3-", "chatgpt"))):
                    ids.append(mid)
            return ids or list(self.KNOWN_MODELS)
        except Exception as exc:
            logger.warning("openai_provider.list_models_failed", error=str(exc))
            return list(self.KNOWN_MODELS)
