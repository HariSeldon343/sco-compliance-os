"""Wrapper async per Claude Agent SDK integrato con SaaS proxy SCO.

Architettura license + proxy:
- Cliente NON inserisce mai chiave Anthropic.
- Cliente inserisce email + license_key SCO via LoginScreen.
- Backend locale Python usa `ANTHROPIC_BASE_URL` custom che punta al backend SaaS
  SCO (https://sco-saas-claude.vercel.app/api/v1/llm/proxy).
- Backend locale usa `ANTHROPIC_AUTH_TOKEN = license_key` (passato come Bearer).
- SaaS valida license + forwarda a Anthropic con chiave server-side.

Fallback dev mode: se license_key vuoto OR sco_saas_base_url empty → fallback a
env vars standard `ANTHROPIC_API_KEY` (per testing locale su PC sviluppatore con
chiave reale).

Pattern Conv. 44 lesson 1: nessun avvio uvicorn/long-running da shell ephemeral.
Pattern Conv. 44 lesson 3: hidden imports per PyInstaller (claude_agent_sdk + mcp)
da dichiarare nel .spec quando si farà il sidecar bundle.
Pattern Conv. 48: stream() yield eventi tipizzati che includono ask_user_question
e tool_calls per persistenza backend-side.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

from sco_compliance_os.config import get_settings
from sco_compliance_os.core.logging_setup import get_logger

logger = get_logger(__name__)


EventKind = Literal[
    "text_delta",
    "tool_use",
    "tool_result",
    "ask_user_question",
    "thinking",
    "error",
    "done",
]


@dataclass
class AgentEvent:
    """Evento emesso dal runner durante lo streaming.

    Pattern Conv. 48: ogni evento è auto-contenuto e serializzabile come SSE.
    """

    kind: EventKind
    data: dict[str, Any] = field(default_factory=dict)
    seq: int = 0


@dataclass
class AgentRunnerConfig:
    """Configurazione per AgentRunner."""

    model_slug: str
    max_tokens: int = 4096
    temperature: float = 1.0
    system_prompt: str | None = None
    mcp_servers: list[dict[str, Any]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)


def _configure_anthropic_env() -> dict[str, str]:
    """Configura env vars Anthropic per routing via SaaS proxy SCO.

    Strategia:
    1. Se settings.license_key valorizzato AND settings.sco_saas_base_url valorizzato
       → set ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN (modalità production proxy).
    2. Altrimenti fallback: usa ANTHROPIC_API_KEY da settings.anthropic_api_key
       (modalità dev locale con chiave reale).

    Le env vars sono settate sia in os.environ (per il subprocess claude.exe del
    SDK) sia ritornate come dict per essere passate via ClaudeAgentOptions(env=...)
    in modo esplicito (defensive — alcune versioni del SDK ignorano os.environ).

    Returns:
        dict env vars da passare a ClaudeAgentOptions(env=...).
    """
    settings = get_settings()
    license_key_value = settings.license_key.get_secret_value().strip()
    saas_base = settings.sco_saas_base_url.strip().rstrip("/")

    env_overrides: dict[str, str] = {}

    if license_key_value and saas_base:
        # Production proxy mode: routing via SaaS SCO
        base_url = f"{saas_base}/api/v1/llm/proxy"
        env_overrides["ANTHROPIC_BASE_URL"] = base_url
        env_overrides["ANTHROPIC_AUTH_TOKEN"] = license_key_value
        # Rimuovi eventuale ANTHROPIC_API_KEY conflittuale dall'env corrente
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ["ANTHROPIC_BASE_URL"] = base_url
        os.environ["ANTHROPIC_AUTH_TOKEN"] = license_key_value
        logger.info(
            "agent_runner.env.proxy_mode",
            saas_base=saas_base,
            license_set=True,
        )
    else:
        # Dev fallback: usa ANTHROPIC_API_KEY da settings (chiave reale Anthropic)
        api_key = settings.anthropic_api_key.get_secret_value().strip()
        if api_key:
            env_overrides["ANTHROPIC_API_KEY"] = api_key
            os.environ["ANTHROPIC_API_KEY"] = api_key
            # Pulisci override custom se presenti
            os.environ.pop("ANTHROPIC_BASE_URL", None)
            os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
            logger.info("agent_runner.env.dev_mode", api_key_set=True)
        else:
            logger.warning(
                "agent_runner.env.no_credentials",
                hint="Set license_key+sco_saas_base_url OR anthropic_api_key.",
            )

    return env_overrides


class AgentRunner:
    """Wrapper attorno a Claude Agent SDK con routing via SaaS proxy SCO.

    Esposizione minimale:
    - stream(prompt): AsyncIterator[AgentEvent]
    - cancel(): interrompe lo stream corrente
    """

    def __init__(self, config: AgentRunnerConfig) -> None:
        self.config = config
        self._cancel_event = asyncio.Event()
        logger.info(
            "agent_runner.init",
            model=config.model_slug,
            mcp_servers_count=len(config.mcp_servers),
            tools_count=len(config.tools),
        )

    def _build_options(self) -> ClaudeAgentOptions:
        """Costruisce ClaudeAgentOptions con env proxy configurato."""
        env_overrides = _configure_anthropic_env()

        # MCP servers: per ora dict vuoto (Sessione successiva: cablatura)
        # Il SDK accetta dict[str, McpServerConfig] | str | Path
        mcp_dict: dict[str, Any] = {}

        options = ClaudeAgentOptions(
            model=self.config.model_slug,
            system_prompt=self.config.system_prompt,
            mcp_servers=mcp_dict,
            permission_mode="default",  # production-safe
            include_partial_messages=True,  # per text_delta granulare via StreamEvent
            env=env_overrides,
        )
        return options

    async def stream(self, prompt: str) -> AsyncIterator[AgentEvent]:
        """Stream eventi dell'agente durante l'esecuzione.

        Usa ClaudeSDKClient (chat multi-turn) e itera receive_response() per
        ricevere AssistantMessage + ResultMessage + StreamEvent (delta).

        Args:
            prompt: messaggio utente.

        Yields:
            AgentEvent in ordine: text_delta..., (eventuale tool_use/tool_result),
            (eventuale thinking), done.
        """
        logger.info("agent_runner.stream.start", prompt_len=len(prompt))

        options = self._build_options()
        seq = 0

        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)

                async for message in client.receive_response():
                    if self._cancel_event.is_set():
                        yield AgentEvent(
                            kind="error",
                            data={"message": "cancelled"},
                            seq=seq,
                        )
                        return

                    # StreamEvent: delta incrementale (text streaming granulare)
                    if isinstance(message, StreamEvent):
                        event_data = message.event
                        event_type = event_data.get("type")
                        if event_type == "content_block_delta":
                            delta = event_data.get("delta", {})
                            delta_type = delta.get("type")
                            if delta_type == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield AgentEvent(
                                        kind="text_delta",
                                        data={"text": text},
                                        seq=seq,
                                    )
                                    seq += 1
                            elif delta_type == "thinking_delta":
                                thinking_text = delta.get("thinking", "")
                                if thinking_text:
                                    yield AgentEvent(
                                        kind="thinking",
                                        data={"text": thinking_text},
                                        seq=seq,
                                    )
                                    seq += 1
                        # Altri stream events (message_start, message_delta, ecc.)
                        # sono ignorati: l'aggregato finale arriva via AssistantMessage.
                        continue

                    # AssistantMessage: blocchi consolidati (text, tool_use, tool_result)
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                # Se include_partial_messages=True, il testo è già stato
                                # emesso via StreamEvent text_delta. Saltiamo per evitare
                                # duplicazione. Se in futuro si disattiva partial, ri-emettere qui.
                                continue
                            elif isinstance(block, ToolUseBlock):
                                yield AgentEvent(
                                    kind="tool_use",
                                    data={
                                        "tool_use_id": block.id,
                                        "tool_name": block.name,
                                        "tool_input": block.input,
                                    },
                                    seq=seq,
                                )
                                seq += 1
                            elif isinstance(block, ToolResultBlock):
                                yield AgentEvent(
                                    kind="tool_result",
                                    data={
                                        "tool_use_id": block.tool_use_id,
                                        "content": block.content,
                                        "is_error": block.is_error,
                                    },
                                    seq=seq,
                                )
                                seq += 1
                            elif isinstance(block, ThinkingBlock):
                                # ThinkingBlock può arrivare consolidato (extended thinking)
                                # Se include_partial_messages=True è già stato emesso via
                                # thinking_delta. Saltiamo per evitare duplicazione.
                                continue
                            # Altri block types (ServerToolUseBlock, ServerToolResultBlock)
                            # ignorati in questa Sessione, cablatura futura.
                        continue

                    # ResultMessage: evento finale con cost/usage/stop_reason
                    if isinstance(message, ResultMessage):
                        yield AgentEvent(
                            kind="done",
                            data={
                                "stop_reason": message.stop_reason,
                                "usage": message.usage or {},
                                "total_cost_usd": message.total_cost_usd or 0.0,
                                "model": self.config.model_slug,
                                "num_turns": message.num_turns,
                                "duration_ms": message.duration_ms,
                                "is_error": message.is_error,
                            },
                            seq=seq,
                        )
                        seq += 1
                        logger.info(
                            "agent_runner.stream.done",
                            events=seq,
                            cost_usd=message.total_cost_usd,
                            stop_reason=message.stop_reason,
                        )
                        return

        except Exception as exc:
            logger.exception("agent_runner.stream.error", error=str(exc))
            yield AgentEvent(
                kind="error",
                data={"message": str(exc), "exc_type": type(exc).__name__},
                seq=seq,
            )

    def cancel(self) -> None:
        """Setta evento di cancellazione per interrompere stream in corso."""
        self._cancel_event.set()
        logger.info("agent_runner.cancel.requested")


async def build_runner(
    model_slug: str,
    system_prompt: str | None = None,
    mcp_servers: list[dict[str, Any]] | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> AgentRunner:
    """Factory helper per istanziare AgentRunner con config standard."""
    config = AgentRunnerConfig(
        model_slug=model_slug,
        system_prompt=system_prompt,
        mcp_servers=mcp_servers or [],
        tools=tools or [],
    )
    return AgentRunner(config)
