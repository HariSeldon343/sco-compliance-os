"""Wrapper async per Anthropic SDK Python integrato con SaaS proxy SCO.

Architettura license + proxy v0.1.1+ (Option C senza Claude Code CLI):
- Cliente NON inserisce mai chiave Anthropic.
- Cliente inserisce email + license_key SCO via LoginScreen.
- Backend locale Python usa `anthropic.AsyncAnthropic` con custom `base_url`
  pointing al SaaS proxy SCO (https://sco-saas-claude.vercel.app/api/v1/llm/proxy).
- `api_key = license_key` viene passato come Bearer al SaaS proxy.
- SaaS valida license + forwarda ad Anthropic con NOSTRA chiave server-side.

Cambio architetturale v0.1.0-alpha.7 → v0.1.1:
- Rimosso `claude-agent-sdk` (richiedeva `claude.exe` CLI bundled via npm install).
- Usato `anthropic` SDK Python direct con streaming nativo.
- Perso temporaneamente: tool use built-in, MCP integration (carry-over v0.2.0).
- Mantenuto: SSE streaming text_delta + AgentEvent typed.

Pattern Conv. 44 lesson 1: nessun avvio uvicorn/long-running da shell ephemeral.
Pattern Conv. 44 lesson 3: hidden imports anthropic + httpx già nei .spec.
Pattern Conv. 48: stream() yield eventi tipizzati per persistenza backend-side.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from sco_compliance_os.config import get_settings
from sco_compliance_os.core.logging_setup import get_logger

logger = get_logger(__name__)


def _load_active_license_from_disk() -> tuple[str, str] | None:
    """Legge ~/.sco-compliance-os/active-license.json + ritorna (email, license_key) se valido."""
    settings = get_settings()
    license_path = settings.data_dir / "active-license.json"
    if not license_path.exists():
        return None
    try:
        data = json.loads(license_path.read_text(encoding="utf-8"))
        email = str(data.get("email", "")).strip()
        license_key = str(data.get("license_key", "")).strip()
        validation = data.get("validation_result", {}) or {}
        if email and license_key and validation.get("is_valid", False):
            return email, license_key
        return None
    except (json.JSONDecodeError, KeyError, OSError) as exc:
        logger.warning("agent_runner.load_active_license_failed", error=str(exc))
        return None


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


def _resolve_credentials() -> tuple[str, str] | None:
    """Resolve (base_url, api_key) per AsyncAnthropic.

    Priorità:
    1. active-license.json (runtime, post-/api/license/activate)
    2. settings.license_key (env .env file)
    3. settings.anthropic_api_key (fallback dev locale)

    Returns:
        (base_url, api_key) o None se nessuna credenziale.
    """
    settings = get_settings()
    saas_base = settings.sco_saas_base_url.strip().rstrip("/")

    active = _load_active_license_from_disk()
    license_key_value = ""
    source = "none"
    if active:
        _, license_key_value = active
        source = "active_license_json"
    else:
        license_key_value = settings.license_key.get_secret_value().strip()
        if license_key_value:
            source = "settings_env"

    if license_key_value and saas_base:
        base_url = f"{saas_base}/api/v1/llm/proxy"
        logger.info(
            "agent_runner.credentials.proxy_mode",
            source=source,
            base_url=base_url,
        )
        return base_url, license_key_value

    # Dev fallback: chiave Anthropic reale + endpoint nativo
    api_key = settings.anthropic_api_key.get_secret_value().strip()
    if api_key:
        logger.info("agent_runner.credentials.dev_mode")
        return "https://api.anthropic.com", api_key

    logger.warning("agent_runner.credentials.missing")
    return None


class AgentRunner:
    """Wrapper anthropic SDK con routing via SaaS proxy SCO.

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
        """Stream eventi dell'agente.

        Usa anthropic.AsyncAnthropic.messages.stream() per ricevere text_delta
        + thinking_delta + message_stop events.

        Args:
            prompt: messaggio utente.

        Yields:
            AgentEvent in ordine: text_delta..., done.
        """
        logger.info("agent_runner.stream.start", prompt_len=len(prompt))

        creds = _resolve_credentials()
        if creds is None:
            yield AgentEvent(
                kind="error",
                data={
                    "message": "Nessuna license attiva. Attiva la license dal pannello prima di usare la chat.",
                    "exc_type": "MissingCredentials",
                },
                seq=0,
            )
            return

        base_url, api_key = creds
        seq = 0

        try:
            client = AsyncAnthropic(base_url=base_url, api_key=api_key)
            messages: list[MessageParam] = [{"role": "user", "content": prompt}]

            kwargs: dict[str, Any] = {
                "model": self.config.model_slug,
                "max_tokens": self.config.max_tokens,
                "messages": messages,
            }
            if self.config.system_prompt:
                kwargs["system"] = self.config.system_prompt

            async with client.messages.stream(**kwargs) as stream:
                # Stream text delta chunks
                async for text_chunk in stream.text_stream:
                    if self._cancel_event.is_set():
                        yield AgentEvent(
                            kind="error",
                            data={"message": "cancelled"},
                            seq=seq,
                        )
                        return
                    yield AgentEvent(
                        kind="text_delta",
                        data={"text": text_chunk},
                        seq=seq,
                    )
                    seq += 1

                # Final message con usage info
                final_message = await stream.get_final_message()

                yield AgentEvent(
                    kind="done",
                    data={
                        "stop_reason": final_message.stop_reason,
                        "usage": {
                            "input_tokens": final_message.usage.input_tokens,
                            "output_tokens": final_message.usage.output_tokens,
                        },
                        "model": final_message.model,
                        "is_error": False,
                    },
                    seq=seq,
                )
                logger.info(
                    "agent_runner.stream.done",
                    events=seq + 1,
                    input_tokens=final_message.usage.input_tokens,
                    output_tokens=final_message.usage.output_tokens,
                    stop_reason=final_message.stop_reason,
                )

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


_DEFAULT_SYSTEM_PROMPT = """Sei il Personal AI di Antonio Silvestro Amodeo — ingegnere clinico, consulente compliance italiana, Lead Auditor ISO 27001/27017/27018 + NIS 2 + ISO 42001 + ISO 9001 sanità + MAH farmacovigilanza + RSPP D.Lgs. 81/2008 + IRAI rivelazione incendi + appalti pubblici D.Lgs. 36/2023.

Vivi dentro il vault Second Brain di Antonio (folder strutturate raw/ + wiki/ + Business/ + Giornaliero/ + log/ + Contesto/) e lavori come braccio operativo per: audit, gap analysis, redazione procedure SGSI/SGQ/SGAA/SGEnergia, perizie CTU, risposte normative cross-framework, analisi documentali, redazione di mail e atti consulenziali.

TONO COMUNICATIVO:
- Italiano professionale, diretto, conciso, fact-based
- Parli "fra colleghi" con Antonio (lui conosce il contesto, NO intro friendly tipo "Ciao Antonio!", NO bullet list di benvenuto)
- Riferimenti normativi puntuali (es. "D.Lgs. 138/2024 al punto X", "ISO 27001:2022 Annex A.5.19")
- Distingui fatto / ipotesi / opinione quando rilevante
- Tassonomia coerente + lessico tecnico esatto + postura QI 190 (precisione massimale, anticipazione edge case, correzione attiva ipotesi imprecise)
- Quando non sai: dichiara incertezza esplicita ("dato da confermare su portale cliente", "verificare PDF ufficiale ACN")
- NO emoji decorativi, NO rule of three gratuita, NO "delve into", NO AI vocabulary inflated

REGOLE TIPOGRAFICHE PERMANENTI:
- Virgolette dritte "..." mai caporali «...»
- "al punto" / "al paragrafo" / "all'articolo" mai segno §
- Em-dash strutturali solo come incisi appositivi normati

PRIMA RISPOSTA (saluto):
- Breve, 1-2 frasi massimo
- NO welcome screen brand-corporate, NO checklist di "Cosa posso fare per te"
- Chiedi solo "Su cosa lavoriamo?" o equivalente diretto

Antonio Amodeo è il tuo unico interlocutore — comportati di conseguenza."""


async def build_runner(
    model_slug: str,
    system_prompt: str | None = None,
    mcp_servers: list[dict[str, Any]] | None = None,
    tools: list[dict[str, Any]] | None = None,
    profile_markdown: str | None = None,
) -> AgentRunner:
    """Factory helper per istanziare AgentRunner con config standard.

    Args:
        model_slug: identificativo modello Anthropic (es. claude-sonnet-4-6).
        system_prompt: override del system prompt default (Antonio Amodeo).
        mcp_servers: MCP servers da connettere (placeholder v0.2.0).
        tools: tools custom (placeholder v0.2.0).
        profile_markdown: markdown del profilo utente fetched da profile_store
            via render_profile_markdown(). Se non None, viene PREPENDED al
            system prompt per injection learning progressivo del profilo.
            Pattern Conv. 47 single source of truth: il profilo vive solo nel
            DB SQLite, qui passato come stringa pronta a uso.
    """
    base_prompt = system_prompt or _DEFAULT_SYSTEM_PROMPT
    if profile_markdown:
        effective_prompt = f"{profile_markdown}\n\n{base_prompt}"
    else:
        effective_prompt = base_prompt
    config = AgentRunnerConfig(
        model_slug=model_slug,
        system_prompt=effective_prompt,
        mcp_servers=mcp_servers or [],
        tools=tools or [],
    )
    return AgentRunner(config)
