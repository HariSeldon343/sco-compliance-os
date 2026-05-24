"""Adapter Google Gemini SDK (google-generativeai package).

Modelli supportati v0.7.0:
- gemini-2-pro (reasoning-v1 fallback)
- gemini-1.5-flash (fast-v1 fallback)
- gemini-1.5-pro (general)

Pattern Conv. 47: api_key da tenant_config server-side via SaaS admin (BYOK).
Pattern Conv. 44 lesson 1: timeout 30s via httpx transport injection.

Streaming normalizzato:
- google.generativeai.GenerativeModel.generate_content_async(stream=True) yield chunks
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


class GeminiProvider(LLMProvider):
    """Provider Gemini via google-generativeai SDK."""

    name = "gemini"

    KNOWN_MODELS = [
        "gemini-2-pro",
        "gemini-2-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
    ]

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_key:
            raise ProviderError(
                "Gemini provider richiede api_key (BYOK Google AI Studio)",
                provider_name=self.name,
                exc_type="MissingCredentials",
            )
        self.config = config
        self._configured = False
        logger.info(
            "gemini_provider.init",
            timeout=config.timeout_seconds,
        )

    def _ensure_configured(self) -> None:
        """Lazy configure SDK Gemini al primo uso."""
        if self._configured:
            return
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ProviderError(
                "Pacchetto 'google-generativeai' non installato. "
                "pip install google-generativeai>=0.8.0",
                provider_name=self.name,
                exc_type="MissingDependency",
            ) from exc

        genai.configure(api_key=self.config.api_key)
        self._configured = True

    async def stream(
        self,
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
        temperature: float = 1.0,
        extra: dict[str, Any] | None = None,
    ) -> AsyncIterator[ChunkEvent]:
        """Stream Gemini generate_content_async(stream=True) normalizzato."""
        logger.info(
            "gemini_provider.stream.start",
            model=model,
            messages_count=len(messages),
            max_tokens=max_tokens,
        )

        try:
            self._ensure_configured()
            import google.generativeai as genai
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

        # Gemini schema: contents = list di {role: "user"|"model", parts: [{text}]}
        # Mapping: assistant -> model. system_prompt -> system_instruction kwarg.
        gemini_contents: list[dict[str, Any]] = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            content = m["content"]
            if isinstance(content, str):
                parts = [{"text": content}]
            elif isinstance(content, list):
                # Assume list di dict {text: ...} già normalizzato
                parts = content
            else:
                parts = [{"text": str(content)}]
            gemini_contents.append({"role": role, "parts": parts})

        generation_config: dict[str, Any] = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }
        if extra:
            for k, v in extra.items():
                if k in ("top_p", "top_k", "stop_sequences", "response_mime_type"):
                    generation_config[k] = v

        model_kwargs: dict[str, Any] = {
            "model_name": model,
            "generation_config": generation_config,
        }
        if system_prompt:
            model_kwargs["system_instruction"] = system_prompt

        seq = 0
        final_usage: dict[str, int] = {}
        final_stop_reason: str | None = None

        try:
            gen_model = genai.GenerativeModel(**model_kwargs)
            response = await gen_model.generate_content_async(
                contents=gemini_contents,
                stream=True,
            )
            async for chunk in response:
                # Chunk.text contiene il delta testuale aggregato (Gemini SDK
                # già fa concatenate sul chunk corrente)
                if hasattr(chunk, "text") and chunk.text:
                    yield ChunkEvent(
                        kind="text_delta",
                        data={"text": chunk.text},
                        seq=seq,
                    )
                    seq += 1
                # Cattura usage e finish_reason dall'ultimo chunk
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    final_usage = {
                        "input_tokens": getattr(
                            chunk.usage_metadata, "prompt_token_count", 0
                        ),
                        "output_tokens": getattr(
                            chunk.usage_metadata, "candidates_token_count", 0
                        ),
                    }
                if hasattr(chunk, "candidates") and chunk.candidates:
                    fr = getattr(chunk.candidates[0], "finish_reason", None)
                    if fr is not None:
                        final_stop_reason = str(fr)

            yield ChunkEvent(
                kind="done",
                data={
                    "stop_reason": final_stop_reason or "end_turn",
                    "usage": final_usage or {"input_tokens": 0, "output_tokens": 0},
                    "model": model,
                    "provider": self.name,
                },
                seq=seq,
            )
            logger.info(
                "gemini_provider.stream.done",
                events=seq + 1,
                input_tokens=final_usage.get("input_tokens", 0),
                output_tokens=final_usage.get("output_tokens", 0),
                stop_reason=final_stop_reason,
            )
        except Exception as exc:
            logger.exception("gemini_provider.stream.error", error=str(exc))
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
        """Probe: list_models discovery endpoint."""
        try:
            self._ensure_configured()
            import asyncio

            import google.generativeai as genai

            # genai.list_models() è sync, lo wrappiamo in asyncio executor
            loop = asyncio.get_running_loop()
            models = await loop.run_in_executor(None, lambda: list(genai.list_models()))
            return len(models) > 0
        except Exception as exc:
            logger.warning("gemini_provider.health_check_failed", error=str(exc))
            return False

    async def list_models(self) -> list[str]:
        """Discovery modelli Gemini runtime via genai.list_models()."""
        try:
            self._ensure_configured()
            import asyncio

            import google.generativeai as genai

            loop = asyncio.get_running_loop()
            models = await loop.run_in_executor(None, lambda: list(genai.list_models()))
            ids: list[str] = []
            for m in models:
                # m.name = "models/gemini-1.5-pro" -> strip prefix
                name = getattr(m, "name", "")
                if name.startswith("models/"):
                    name = name[len("models/") :]
                # Filtra modelli che supportano generateContent
                methods = getattr(m, "supported_generation_methods", [])
                if name and "generateContent" in methods:
                    ids.append(name)
            return ids or list(self.KNOWN_MODELS)
        except Exception as exc:
            logger.warning("gemini_provider.list_models_failed", error=str(exc))
            return list(self.KNOWN_MODELS)
