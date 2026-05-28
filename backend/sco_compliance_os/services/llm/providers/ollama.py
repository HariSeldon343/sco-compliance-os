"""Adapter Ollama HTTP client per modelli locali.

Modelli supportati v0.7.0 (default install Ollama):
- llama3.2:3b (summarization-v1 default local)
- llama3.2:1b (ultra-fast local)
- qwen2.5:7b
- mistral:7b
- phi3.5

Pattern Conv. 47: nessuna api_key (Ollama localhost-only by default).
Pattern Conv. 44 lesson 1: timeout 30s + retry 1.

API Ollama:
- POST /api/chat con {model, messages, stream: true} -> NDJSON streaming
  Ogni linea: {message: {content: str}, done: bool, ...}
- GET /api/tags -> {models: [{name, size, ...}]} per list modelli installati
- GET / -> "Ollama is running" healthcheck

Vantaggio Ollama: zero cost, privacy local, supportato come fallback
summarization-v1 quando il SaaS proxy è down o per dev offline.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.llm.provider import (
    ChunkEvent,
    LLMProvider,
    ProviderConfig,
)

logger = get_logger(__name__)

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaProvider(LLMProvider):
    """Provider Ollama local-only via httpx.

    `local=True`: marker per UI admin SaaS che lo distingue dai cloud provider.
    Nessuna BYOK richiesta (l'utente installa Ollama localmente).
    """

    name = "ollama"
    local = True

    KNOWN_MODELS = [
        "llama3.2:3b",
        "llama3.2:1b",
        "qwen2.5:7b",
        "mistral:7b",
        "phi3.5",
    ]

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        # api_key è opzionale per Ollama. base_url default a localhost:11434
        if not self.config.base_url:
            self.config.base_url = DEFAULT_OLLAMA_BASE_URL
        logger.info(
            "ollama_provider.init",
            base_url=self.config.base_url,
            timeout=config.timeout_seconds,
        )

    def stream(
        self,
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
        temperature: float = 1.0,
        extra: dict[str, Any] | None = None,
    ) -> AsyncIterator[ChunkEvent]:
        """Stream Ollama /api/chat NDJSON normalizzato a ChunkEvent."""

        async def iterator() -> AsyncIterator[ChunkEvent]:
            logger.info(
                "ollama_provider.stream.start",
                model=model,
                messages_count=len(messages),
                max_tokens=max_tokens,
            )

            # Ollama messages schema: list di {role, content} (compatibile OpenAI-like)
            ollama_messages: list[dict[str, Any]] = []
            if system_prompt:
                ollama_messages.append({"role": "system", "content": system_prompt})
            ollama_messages.extend(messages)

            options: dict[str, Any] = {
                "num_predict": max_tokens,
                "temperature": temperature,
            }
            if extra:
                for k, v in extra.items():
                    if k in ("top_p", "top_k", "stop", "seed", "num_ctx"):
                        options[k] = v

            payload: dict[str, Any] = {
                "model": model,
                "messages": ollama_messages,
                "stream": True,
                "options": options,
            }

            url = f"{self.config.base_url.rstrip('/')}/api/chat"
            timeout = httpx.Timeout(self.config.timeout_seconds)
            seq = 0
            final_usage: dict[str, int] = {}
            final_stop_reason: str | None = None
            final_model: str = model

            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        if response.status_code != 200:
                            body = await response.aread()
                            msg = (
                                f"Ollama HTTP {response.status_code}: "
                                f"{body.decode('utf-8', errors='replace')[:200]}"
                            )
                            yield ChunkEvent(
                                kind="error",
                                data={
                                    "message": msg,
                                    "exc_type": "HTTPError",
                                    "provider": self.name,
                                },
                                seq=seq,
                            )
                            return

                        async for line in response.aiter_lines():
                            if not line.strip():
                                continue
                            try:
                                chunk = json.loads(line)
                            except json.JSONDecodeError as jdec:
                                logger.warning(
                                    "ollama_provider.stream.parse_error",
                                    error=str(jdec),
                                    line_preview=line[:200],
                                )
                                continue

                            # Chunk schema: {message: {role, content}, done: bool, ...}
                            msg_obj = chunk.get("message") or {}
                            content = msg_obj.get("content", "")
                            if content:
                                yield ChunkEvent(
                                    kind="text_delta",
                                    data={"text": content},
                                    seq=seq,
                                )
                                seq += 1

                            # Ultimo chunk: done=true + eval_count + prompt_eval_count
                            if chunk.get("done", False):
                                prompt_count = chunk.get("prompt_eval_count", 0)
                                eval_count = chunk.get("eval_count", 0)
                                final_usage = {
                                    "input_tokens": prompt_count,
                                    "output_tokens": eval_count,
                                }
                                final_stop_reason = chunk.get("done_reason", "end_turn")
                                final_model = chunk.get("model", model)

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
                    "ollama_provider.stream.done",
                    events=seq + 1,
                    input_tokens=final_usage.get("input_tokens", 0),
                    output_tokens=final_usage.get("output_tokens", 0),
                    stop_reason=final_stop_reason,
                )
            except httpx.ConnectError as cerr:
                # Tipico: Ollama non installato o servizio non avviato
                logger.warning(
                    "ollama_provider.stream.connect_error",
                    base_url=self.config.base_url,
                    error=str(cerr),
                )
                yield ChunkEvent(
                    kind="error",
                    data={
                        "message": (
                            f"Ollama non raggiungibile a {self.config.base_url}. "
                            "Installa Ollama (https://ollama.com) e avvia il servizio."
                        ),
                        "exc_type": "ConnectError",
                        "provider": self.name,
                    },
                    seq=seq,
                )
            except Exception as exc:
                logger.exception("ollama_provider.stream.error", error=str(exc))
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
        """Probe: GET / che ritorna 'Ollama is running' (200 OK) se servizio up."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
                resp = await client.get(self.config.base_url.rstrip("/"))
                # Ollama root endpoint risponde "Ollama is running" text/plain
                return resp.status_code == 200
        except Exception as exc:
            logger.warning("ollama_provider.health_check_failed", error=str(exc))
            return False

    async def list_models(self) -> list[str]:
        """Discovery modelli installati localmente via GET /api/tags."""
        try:
            url = f"{self.config.base_url.rstrip('/')}/api/tags"
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                data = resp.json()
                models = data.get("models", [])
                return [m.get("name", "") for m in models if isinstance(m, dict) and m.get("name")]
        except Exception as exc:
            logger.warning("ollama_provider.list_models_failed", error=str(exc))
            return []
