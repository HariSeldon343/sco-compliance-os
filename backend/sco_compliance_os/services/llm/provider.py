"""Protocol astratto LLMProvider + ChunkEvent tipizzato.

Tutti i provider concreti (Anthropic/OpenAI/Gemini/Ollama) implementano
questa interfaccia uniforme. Il router invoca `stream()` senza conoscere
il provider sottostante.

Design clean-room: nessuna copia da SDK terzi. Astrazione pensata per
streaming chunk-based comune ai 4 provider con normalizzazione delta.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

# Kind di chunk emesso durante lo stream. Set chiuso comune ai 4 provider.
# Mapping al sistema AgentEvent esistente:
# - text_delta -> AgentEvent kind="text_delta"
# - tool_use -> AgentEvent kind="tool_use"
# - tool_result -> AgentEvent kind="tool_result"
# - thinking -> AgentEvent kind="thinking"
# - done -> AgentEvent kind="done" (con usage finale)
# - error -> AgentEvent kind="error"
ChunkKind = Literal[
    "text_delta",
    "tool_use",
    "tool_result",
    "thinking",
    "done",
    "error",
]


@dataclass
class ChunkEvent:
    """Evento normalizzato emesso da un LLMProvider durante lo stream.

    Schema dati uniforme:
    - text_delta: data={"text": str}
    - tool_use: data={"tool_name": str, "tool_input": dict, "tool_use_id": str}
    - tool_result: data={"tool_use_id": str, "content": Any}
    - thinking: data={"text": str}
    - done: data={"stop_reason": str, "usage": {"input_tokens": int, "output_tokens": int}, "model": str}
    - error: data={"message": str, "exc_type": str}
    """

    kind: ChunkKind
    data: dict[str, Any] = field(default_factory=dict)
    seq: int = 0


class ProviderError(Exception):
    """Errore lato provider (auth, rate limit, network, parse).

    Sottoclassi possibili in futuro: AuthError, RateLimitError, TimeoutError.
    Per ora wrapper unico con .provider_name + .exc_type.
    """

    def __init__(
        self,
        message: str,
        provider_name: str,
        exc_type: str = "",
    ) -> None:
        super().__init__(message)
        self.provider_name = provider_name
        self.exc_type = exc_type or self.__class__.__name__


@dataclass
class ProviderConfig:
    """Config runtime per un provider concreto.

    Campo `extra` per opzioni provider-specific (es. Gemini safety_settings,
    OpenAI organization, Ollama keep_alive).
    """

    name: str  # "anthropic" | "openai" | "gemini" | "ollama"
    api_key: str = ""  # license_key per anthropic-proxy, API key per BYOK
    base_url: str = ""  # endpoint override (SaaS proxy o local)
    timeout_seconds: float = 30.0
    max_retries: int = 1
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    """Interfaccia uniforme per provider LLM streaming.

    Tutti i provider concreti devono esporre:
    - name: identificatore stringa ("anthropic" | "openai" | "gemini" | "ollama")
    - stream(): AsyncIterator[ChunkEvent] con eventi normalizzati
    - health_check(): probe leggero per scoring fallback
    """

    name: str

    async def stream(
        self,
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
        temperature: float = 1.0,
        extra: dict[str, Any] | None = None,
    ) -> AsyncIterator[ChunkEvent]:
        """Stream eventi LLM normalizzati.

        Args:
            messages: lista di {role: "user"|"assistant", content: str}.
            model: model slug provider-specific (es. "claude-sonnet-4-6", "gpt-5").
            max_tokens: limite output tokens.
            system_prompt: optional system prompt.
            temperature: sampling temperature.
            extra: opzioni provider-specific (tool_use, thinking budget, etc).

        Yields:
            ChunkEvent normalizzati. L'ultimo deve essere kind="done" o kind="error".
        """
        ...

    async def health_check(self) -> bool:
        """Probe leggero del provider.

        Returns:
            True se il provider risponde (auth + endpoint reachable),
            False altrimenti. Non solleva eccezioni — l'errore è normalizzato
            come False per usabilità in scoring fallback.
        """
        ...

    async def list_models(self) -> list[str]:
        """Lista modelli disponibili runtime (per discovery UI admin SaaS).

        Returns:
            Lista di model slug. Vuota se non determinabile o errore.
        """
        ...
