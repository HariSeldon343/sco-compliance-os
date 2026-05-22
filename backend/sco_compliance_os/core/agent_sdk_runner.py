"""Wrapper async per Claude Agent SDK + claude.exe subprocess.

STUB: l'implementazione concreta verrà cablata quando il modulo `claude_agent_sdk`
sarà installato e quando il pattern subprocess via `claude.exe` (Code SDK) sarà
definito di concerto con la WBS architetturale.

Pattern Conv. 44 lesson 1: nessun avvio uvicorn/long-running da shell ephemeral.
Pattern Conv. 44 lesson 3: hidden imports per PyInstaller (claude_agent_sdk + mcp)
da dichiarare nel .spec quando si farà il sidecar bundle.
Pattern Conv. 48: stream() yield eventi tipizzati che includono ask_user_question
e tool_calls per persistenza backend-side.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

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


class AgentRunner:
    """Wrapper attorno a Claude Agent SDK / subprocess claude.exe.

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

    async def stream(self, prompt: str) -> AsyncIterator[AgentEvent]:
        """Stream eventi dell'agente durante l'esecuzione.

        STUB CORRENTE: ritorna sequenza fake di 3 text_delta + done.
        TODO Sessione successiva: cablare a `claude_agent_sdk.query()` o
        subprocess `claude.exe` con parsing JSONL dello stdout.

        Args:
            prompt: messaggio utente.

        Yields:
            AgentEvent in ordine: text_delta..., (eventuale tool_use/tool_result),
            (eventuale ask_user_question), done.
        """
        logger.info("agent_runner.stream.start", prompt_len=len(prompt))

        # STUB: simula latency + 3 chunk + done
        fake_chunks = [
            "Ciao, sono lo stub di SCO Compliance OS. ",
            "Sto rispondendo al prompt: ",
            f"'{prompt[:80]}{'...' if len(prompt) > 80 else ''}'.",
        ]

        seq = 0
        for chunk in fake_chunks:
            if self._cancel_event.is_set():
                yield AgentEvent(kind="error", data={"message": "cancelled"}, seq=seq)
                return
            await asyncio.sleep(0.15)  # simula network latency
            yield AgentEvent(kind="text_delta", data={"text": chunk}, seq=seq)
            seq += 1

        # Done event finale
        yield AgentEvent(
            kind="done",
            data={
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                "total_cost_usd": 0.0,
                "model": self.config.model_slug,
            },
            seq=seq,
        )
        logger.info("agent_runner.stream.done", events=seq + 1)

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
