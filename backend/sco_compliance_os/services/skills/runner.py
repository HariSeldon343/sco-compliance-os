"""Skill executor: carica body SKILL.md + prepend al system prompt + invoca runner.

Pattern: il body markdown della skill diventa addendum al system prompt
dell'AgentRunner. Il prompt utente passato a stream() e' costruito a runtime
sulla base del context (es. info vault per os-setup, struttura folder per
os-ottimizzatore).

Per ora il runner NON espone tool registration dinamica (claude-agent-sdk
rimosso v0.1.1, anthropic SDK direct senza tool use built-in). Le skill
operano in modalita "prompt-driven only": istruiscono il modello a fare
osservazioni testuali, NON a chiamare API. Tool registration dinamica
e' carry-over v0.7.0 quando MCP integration sara' riabilitato.

Pattern Conv. 41 tracciatura: ogni execute_skill loggato con skill_name +
scope + duration + event count.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sco_compliance_os.config import get_settings
from sco_compliance_os.core.agent_sdk_runner import (
    AgentEvent,
    build_runner,
)
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.skills.loader import (
    SkillMeta,
    get_skill,
)

logger = get_logger(__name__)


@dataclass
class SkillExecutionResult:
    """Esito di una esecuzione skill.

    Attributes:
        skill_name: nome skill eseguita.
        success: True se nessun error event emesso, False altrimenti.
        events_count: numero totale eventi yieldati dal runner.
        assistant_text: testo accumulato dei text_delta concatenati.
        error_message: messaggio errore se success=False.
    """

    skill_name: str
    success: bool
    events_count: int = 0
    assistant_text: str = ""
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# Type alias per callback eventi.
SkillEventCallback = Callable[[AgentEvent], Awaitable[None]] | None


def _build_skill_system_prompt(
    skill: SkillMeta,
    context: dict[str, Any],
) -> str:
    """Costruisce il system prompt per l'esecuzione skill.

    Pattern: SKILL.md body diventa addendum al prompt base + render context
    come block di dati strutturati che la skill puo' leggere.
    """
    body = skill.load_body()
    context_block_lines = ["## Context runtime"]
    for key, value in context.items():
        if isinstance(value, str | int | float | bool) or value is None:
            context_block_lines.append(f"- {key}: {value}")
        else:
            # Rappresenta valori complessi in forma JSON-like compatto.
            context_block_lines.append(f"- {key}: {value!r}")
    context_block = "\n".join(context_block_lines)

    return (
        f"# Skill: {skill.name}\n\n"
        f"{body}\n\n"
        f"{context_block}\n\n"
        "Rispondi seguendo le istruzioni della skill sopra, usando il context come dati di input."
    )


def _build_skill_user_prompt(
    skill: SkillMeta,
    context: dict[str, Any],
) -> str:
    """Costruisce il prompt utente iniziale per skill auto-triggered.

    Per skill con auto_trigger (es. vault_registered), il prompt utente e'
    generato dal sistema: contiene un breve "trigger di apertura" che istruisce
    il modello a partire seguendo la skill body senza attendere input umano.
    """
    trigger = skill.auto_trigger or "manual"
    vault_path = context.get("vault_path", "(non specificato)")
    vault_name = context.get("vault_name", "(non specificato)")
    return (
        f"Auto-trigger: {trigger}.\n"
        f"Vault: {vault_name} ({vault_path}).\n"
        "Avvia la skill secondo le istruzioni del system prompt."
    )


async def execute_skill(
    skill_name: str,
    *,
    vault_root: Path | None = None,
    context: dict[str, Any] | None = None,
    on_event: SkillEventCallback = None,
    model_slug: str | None = None,
) -> SkillExecutionResult:
    """Esegue una skill yield-by-yield invocando il runner Anthropic.

    Args:
        skill_name: nome skill da eseguire (deve essere discovered).
        vault_root: path vault attivo per scope Project + context.
        context: dict di context da iniettare nel system prompt + user prompt.
        on_event: callback opzionale invocato per ogni AgentEvent emesso.
            Pattern fire-and-forget: errori del callback loggati ma NON propagati.
        model_slug: override modello (default da settings.model_default).

    Returns:
        SkillExecutionResult con success + counts + testo accumulato.
    """
    skill = get_skill(skill_name, vault_root)
    if skill is None:
        logger.warning(
            "skill_runner.skill_not_found",
            skill_name=skill_name,
            vault_root=str(vault_root) if vault_root else None,
        )
        return SkillExecutionResult(
            skill_name=skill_name,
            success=False,
            error_message=f"Skill '{skill_name}' non trovata in nessuno scope.",
        )

    settings = get_settings()
    effective_model = model_slug or settings.model_default

    ctx = dict(context or {})
    if vault_root is not None and "vault_path" not in ctx:
        ctx["vault_path"] = str(vault_root)

    system_prompt = _build_skill_system_prompt(skill, ctx)
    user_prompt = _build_skill_user_prompt(skill, ctx)

    logger.info(
        "skill_runner.execute.start",
        skill_name=skill.name,
        skill_scope=skill.scope,
        auto_trigger=skill.auto_trigger,
        vault_root=str(vault_root) if vault_root else None,
        model=effective_model,
    )

    runner = await build_runner(
        model_slug=effective_model,
        system_prompt=system_prompt,
    )

    assistant_buf: list[str] = []
    events_count = 0
    error_message: str | None = None

    try:
        async for event in runner.stream(user_prompt):
            events_count += 1
            if event.kind == "text_delta":
                assistant_buf.append(event.data.get("text", ""))
            elif event.kind == "error":
                error_message = str(event.data.get("message", "unknown error"))

            if on_event is not None:
                try:
                    await on_event(event)
                except Exception as cb_exc:
                    logger.exception(
                        "skill_runner.on_event_callback_failed",
                        skill_name=skill.name,
                        error=str(cb_exc),
                    )
    except Exception as exc:
        logger.exception(
            "skill_runner.execute.error",
            skill_name=skill.name,
            error=str(exc),
        )
        return SkillExecutionResult(
            skill_name=skill.name,
            success=False,
            events_count=events_count,
            assistant_text="".join(assistant_buf),
            error_message=str(exc),
        )

    assistant_text = "".join(assistant_buf)
    success = error_message is None

    logger.info(
        "skill_runner.execute.completed",
        skill_name=skill.name,
        success=success,
        events_count=events_count,
        text_length=len(assistant_text),
    )

    return SkillExecutionResult(
        skill_name=skill.name,
        success=success,
        events_count=events_count,
        assistant_text=assistant_text,
        error_message=error_message,
    )


async def execute_skill_stream(
    skill_name: str,
    *,
    vault_root: Path | None = None,
    context: dict[str, Any] | None = None,
    model_slug: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """Variante streaming di execute_skill che yield AgentEvent direttamente.

    Usata da endpoint che vogliono forwarding SSE diretto al frontend.
    """
    skill = get_skill(skill_name, vault_root)
    if skill is None:
        yield AgentEvent(
            kind="error",
            data={
                "message": f"Skill '{skill_name}' non trovata in nessuno scope.",
                "exc_type": "SkillNotFound",
            },
        )
        return

    settings = get_settings()
    effective_model = model_slug or settings.model_default

    ctx = dict(context or {})
    if vault_root is not None and "vault_path" not in ctx:
        ctx["vault_path"] = str(vault_root)

    system_prompt = _build_skill_system_prompt(skill, ctx)
    user_prompt = _build_skill_user_prompt(skill, ctx)

    runner = await build_runner(
        model_slug=effective_model,
        system_prompt=system_prompt,
    )

    logger.info(
        "skill_runner.execute_stream.start",
        skill_name=skill.name,
        skill_scope=skill.scope,
        model=effective_model,
    )

    async for event in runner.stream(user_prompt):
        yield event
