"""Router /api/chat — streaming SSE + conversations CRUD.

Pattern Conv. 48 SINGLE SOURCE OF TRUTH BACKEND per stato widget post-streaming:
quando lo stream emette `ask_user_question`, il backend persiste il payload sul
messaggio assistant (campo ask_user_question_json). Il frontend NON deve
preservare lo stato widget da React state — lo legge dal fetch della conversation.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.agent_sdk_runner import _DEFAULT_SYSTEM_PROMPT
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.core.post_turn_hook import schedule_on_turn_complete
from sco_compliance_os.core.store import get_store
from sco_compliance_os.services.chat.prompt_optimizer import optimize_prompt
from sco_compliance_os.services.chat.skill_proposer import (
    clear_pending,
    get_pending,
    propose_skills,
    set_pending,
)
from sco_compliance_os.services.learning.profile_renderer import (
    render_profile_markdown,
)
from sco_compliance_os.services.learning.profile_store import list_preferences
from sco_compliance_os.services.learning.setup_answer_persistor import (
    is_setup_step_user_answer,
    persist_setup_answer,
)
from sco_compliance_os.services.llm.provider import LLMProvider, ProviderError
from sco_compliance_os.services.llm.router import (
    Tier,
    get_tenant_llm_config,
    record_failure,
    route,
)
from sco_compliance_os.services.skills.loader import SkillMeta, discover_skills


def _get_skill_catalog_for_prompt(vault_root: Path | None = None) -> str:
    """Ritorna la lista competenze disponibili formattata come bullet list.

    Pattern: il catalogo (User + Project + Legacy bundled, dedupe by name) viene
    iniettato in coda al system prompt come riferimento per il pattern di
    proposta competenze obbligatorio a ogni nuovo task sostantivo. NON distingue
    fra skill di sistema e skill utente (single experience dal punto di vista
    dell'operatore).

    Cap: 50 competenze max per evitare overflow context window. Se la discovery
    ritorna più di 50 elementi, vengono troncate con marker esplicito.

    Args:
        vault_root: path vault attivo per scope Project (se None, scope Project
            viene saltato e si usano solo User + Legacy).

    Returns:
        Markdown formattato come "## Catalogo competenze disponibili" + bullet
        list, oppure stringa vuota se discovery fallisce o non trova competenze.
    """
    try:
        skills = discover_skills(vault_root)
    except Exception as exc:
        logger.warning("chat_stream.skill_catalog_discover_failed", error=str(exc))
        return ""

    if not skills:
        return ""

    cap = 50
    if len(skills) > cap:
        truncated_marker = (
            f"\n- [... {len(skills) - cap} competenze aggiuntive omesse per cap context ...]"
        )
        skills = skills[:cap]
    else:
        truncated_marker = ""

    lines = ["## Catalogo competenze disponibili"]
    lines.append(
        "Usa queste competenze come opzioni nel widget di proposta a ogni nuovo task sostantivo. "
        "Proponi le 3-4 più pertinenti, max 6 options totali (incluse 'Nessuna' + 'altro')."
    )
    lines.append("")
    for skill in skills:
        description = skill.description.strip() or "(nessuna descrizione disponibile)"
        # Compatta description a 1 riga (rimuove a-capo interni).
        description_oneline = " ".join(description.split())
        # Cap descrizione a 200 char per evitare prompt bloat.
        if len(description_oneline) > 200:
            description_oneline = description_oneline[:200].rstrip() + "..."
        lines.append(f"- {skill.name}: {description_oneline}")
    if truncated_marker:
        lines.append(truncated_marker)
    return "\n".join(lines)


logger = get_logger(__name__)

ChatModeLiteral = Literal["plan", "ask", "auto", "yolo"]

AGENT_MODE_PERMISSION_MAP: dict[str, str] = {
    "plan": "plan",
    "ask": "default",
    "auto": "acceptEdits",
    "yolo": "bypassPermissions",
}

DEFAULT_PERMISSION_MODE = "default"

router = APIRouter(prefix="/api/chat", tags=["chat"])


AgentModeLiteral = Literal["plan", "ask", "auto", "yolo"]
PERMISSION_MODE_MAP: dict[AgentModeLiteral, str] = {
    "plan": "plan",
    "ask": "default",
    "auto": "acceptEdits",
    "yolo": "bypassPermissions",
}

# ----- Schemi Pydantic -----


class ChatStreamRequest(BaseModel):
    """Richiesta di streaming chat."""

    conversation_id: str = Field(..., description="ID conversation di destinazione.")
    message: str = Field(..., min_length=1, description="Messaggio utente.")
    agent_mode: ChatModeLiteral = Field(
        default="auto",
        description="Modalità operativa dell'agente per questa conversazione.",
    )
    model_slug: str | None = Field(
        default=None,
        description="Override modello (default da settings.model_default).",
    )
    agent: str | None = Field(
        default=None,
        description="Nome agent/subagent da usare (es. compliance-os, dev, etc).",
    )
    project_path: str | None = Field(
        default=None,
        description="Cartella lavoro progetto attivo (override working directory).",
    )
    tier: str | None = Field(
        default=None,
        description=(
            "Tier workload v0.7.0 multi-LLM router: reasoning-v1 | fast-v1 | "
            "agentic-v1 | coding-v1 | summarization-v1. Default 'agentic-v1' "
            "(backward-compat chat). Override model_slug ha priorità su tier."
        ),
    )


class ConversationCreateRequest(BaseModel):
    """Richiesta creazione conversation."""

    title: str | None = Field(default=None, max_length=200)


class ConversationUpdateRequest(BaseModel):
    """Richiesta aggiornamento conversation."""

    agent_mode: ChatModeLiteral | None = Field(
        default=None,
        description="Nuova modalità agente per la conversazione.",
    )


class ConversationOut(BaseModel):
    """Schema response conversation."""

    id: str
    title: str
    created_at: str
    updated_at: str
    agent_mode: ChatModeLiteral = "auto"


class MessageOut(BaseModel):
    """Schema response message.

    Pattern Conv. 48: ask_user_question + tool_calls sempre nel payload.
    """

    id: str
    conversation_id: str
    role: str
    content: str
    ask_user_question: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    created_at: str


# ----- Dependency helpers -----


def _get_store(settings: Settings = Depends(get_settings)) -> Any:
    return get_store(settings.memory_tree_db_path)


# ----- Endpoint: streaming SSE -----


@router.post("/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Endpoint SSE per streaming risposta agente.

    Eventi SSE emessi:
    - text_delta: chunk di testo
    - tool_use: tool call iniziata
    - tool_result: risultato tool
    - ask_user_question: richiesta domanda strutturata all'utente (Conv. 48 persisted)
    - error: errore durante stream
    - done: fine stream con usage + stop_reason
    """
    store = get_store(settings.memory_tree_db_path)
    conv = await store.get_conversation(payload.conversation_id)
    effective_cwd = payload.project_path
    logger.info(
        "chat_stream conversation=%s project_path=%s", payload.conversation_id, effective_cwd
    )
    if conv is None:
        raise HTTPException(
            status_code=404, detail=f"Conversation {payload.conversation_id} non trovata"
        )

    agent_mode_value = payload.agent_mode or conv.agent_mode or "auto"
    if agent_mode_value not in AGENT_MODE_PERMISSION_MAP:
        agent_mode_value = "auto"
    if agent_mode_value != conv.agent_mode:
        await store.set_agent_mode(payload.conversation_id, agent_mode_value)
        conv.agent_mode = agent_mode_value
    permission_mode = AGENT_MODE_PERMISSION_MAP.get(agent_mode_value, DEFAULT_PERMISSION_MODE)

    # Persisti messaggio utente prima dello stream
    user_msg = await store.append_message(
        conversation_id=payload.conversation_id,
        role="user",
        content=payload.message,
    )

    # Note: payload.model_slug se valorizzato fa short-circuit a Anthropic con
    # quel modello nel router; altrimenti il router applica tier+chain.
    # settings.model_default rimane disponibile come fallback semantico (non usato
    # attivamente, il router ha le sue default chain).
    _ = settings.model_default  # backward-compat marker

    # Profile injection: fetch preferenze profilo + render markdown da
    # prepend al system prompt LLM (single source of truth backend, Conv. 47).
    # Best-effort: errori loggati ma NON bloccano lo stream chat.
    profile_markdown = ""
    try:
        profile_prefs = await list_preferences(tenant_id="local", limit=50)
        profile_markdown = render_profile_markdown(profile_prefs)
    except Exception as exc:
        logger.warning(
            "chat_stream.profile_inject_failed",
            error=str(exc),
        )

    # Memory Tree summaries RAG-like injection (v0.6.0 Fase 4 wire):
    # query top-3 summaries pertinenti al user message, prepend al system prompt.
    # Cap totale 4000 char per evitare overflow context window.
    # Pattern SCO "no vector DB": BM25 lite stateless.
    # Best-effort: errori loggati ma NON bloccano lo stream chat.
    memory_context_markdown = ""
    try:
        from sco_compliance_os.services.memory.tree_summaries import (
            query_relevant_summaries,
        )

        relevant = await query_relevant_summaries(payload.message, top_k=3)
        if relevant:
            parts = ["## Contesto rilevante dalla memoria\n"]
            cumulative_chars = len(parts[0])
            for s in relevant:
                snippet = f"\n### [{s.tree_kind}:{s.tree_id} L{s.level}]\n{s.content_summary}\n"
                if cumulative_chars + len(snippet) > 4000:
                    parts.append("\n[...summary aggiuntive omesse per cap context...]\n")
                    break
                parts.append(snippet)
                cumulative_chars += len(snippet)
            memory_context_markdown = "".join(parts) + "\n"
            logger.info(
                "chat_stream.memory_inject.success",
                summaries_count=len(relevant),
                cumulative_chars=cumulative_chars,
            )
    except Exception as exc:
        logger.warning(
            "chat_stream.memory_inject_failed",
            error=str(exc),
        )

    # Combina profile + memory context come prepend al system prompt.
    if memory_context_markdown:
        if profile_markdown:
            profile_markdown = f"{memory_context_markdown}\n{profile_markdown}"
        else:
            profile_markdown = memory_context_markdown

    async def event_generator() -> AsyncIterator[str]:
        """Yield SSE events in formato `data: {json}\\n\\n`.

        v0.7.0 multi-LLM router: invece di hard-codare Anthropic via build_runner,
        risolvi tier+provider via route() con tenant_config. Backward-compat:
        tenant_config vuoto -> default chain -> Anthropic Opus 4.7 (agentic-v1,
        bumped v0.12.0 25/05/2026 da Sonnet 4.6 per allineamento al SaaS default).
        Override model_slug nella request: forza Anthropic con quel modello.
        """
        assistant_text_buf: list[str] = []
        ask_user_question_payload: dict[str, Any] | None = None
        tool_calls_buf: list[dict[str, Any]] = []
        active_provider_name = "unknown"

        proposal_none_label = "Nessuna, procedi senza skill"

        try:
            pending_options = await get_pending(payload.conversation_id)
        except Exception as exc:
            pending_options = None
            logger.warning(
                "chat_stream.skill_proposal_pending_fetch_failed",
                error=str(exc),
                conversation_id=payload.conversation_id,
            )

        selected_skill_from_proposal: str | None = None

        if pending_options is not None:
            normalized_message = payload.message.strip().lower()
            selected_option: str | None = None
            for opt in pending_options:
                opt_lower = opt.lower()
                if opt_lower == normalized_message:
                    selected_option = opt
                    break
            if selected_option is None:
                for opt in pending_options:
                    if opt.lower() in normalized_message:
                        selected_option = opt
                        break

            try:
                await clear_pending(payload.conversation_id)
            except Exception as exc:
                logger.warning(
                    "chat_stream.skill_proposal_pending_clear_failed",
                    error=str(exc),
                    conversation_id=payload.conversation_id,
                )

            if selected_option is None:
                logger.warning(
                    "chat_stream.skill_proposal_selection_unmatched",
                    conversation_id=payload.conversation_id,
                    user_reply=payload.message,
                )
            elif selected_option.lower() == proposal_none_label.lower():
                logger.info(
                    "chat_stream.skill_proposal_skipped",
                    conversation_id=payload.conversation_id,
                    user_reply=payload.message,
                )
            else:
                selected_skill_from_proposal = selected_option
                try:
                    if conv.active_skill != selected_option or (conv.active_skill_step or 0) != 0:
                        await store.set_active_skill(payload.conversation_id, selected_option, step=0)
                    conv.active_skill = selected_option
                    conv.active_skill_step = 0
                except Exception as exc:
                    logger.warning(
                        "chat_stream.skill_proposal_set_active_failed",
                        conversation_id=payload.conversation_id,
                        selected_skill=selected_option,
                        error=str(exc),
                    )
                else:
                    logger.info(
                        "chat_stream.skill_proposal_confirmed",
                        conversation_id=payload.conversation_id,
                        selected_skill=selected_option,
                    )
        else:
            discovered_skills: list[SkillMeta] = []
            try:
                discovered_skills = discover_skills(vault_root=None)
            except Exception as exc:
                logger.warning(
                    "chat_stream.skill_proposal_discover_failed",
                    error=str(exc),
                )

            if discovered_skills:
                try:
                    proposed_skills = propose_skills(payload.message, discovered_skills)
                except Exception as exc:
                    logger.warning(
                        "chat_stream.skill_proposal_match_failed",
                        error=str(exc),
                    )
                else:
                    if proposed_skills:
                        options_payload: list[dict[str, str]] = []
                        for skill in proposed_skills:
                            description = (skill.description or "").strip()
                            if len(description) > 160:
                                description = description[:160].rstrip() + "..."
                            option_data: dict[str, str] = {
                                "label": skill.name,
                                "value": skill.name,
                            }
                            if description:
                                option_data["description"] = description
                            options_payload.append(option_data)

                        options_payload.append(
                            {
                                "label": proposal_none_label,
                                "value": proposal_none_label,
                                "description": "Procedi senza attivare competenze aggiuntive.",
                            }
                        )

                        try:
                            await set_pending(
                                payload.conversation_id,
                                [opt["value"] for opt in options_payload],
                            )
                        except Exception as exc:
                            logger.warning(
                                "chat_stream.skill_proposal_pending_set_failed",
                                error=str(exc),
                                conversation_id=payload.conversation_id,
                            )
                        else:
                            ask_user_question_payload = {
                                "question": "Ho individuato alcune competenze pertinenti. Quale vuoi attivare?",
                                "options": options_payload,
                                "multi_select": False,
                                "context": "skill_proposal",
                            }
                            try:
                                await store.append_message(
                                    conversation_id=payload.conversation_id,
                                    role="assistant",
                                    content="",
                                    ask_user_question=ask_user_question_payload,
                                    tool_calls=None,
                                )
                            except Exception as exc:
                                logger.warning(
                                    "chat_stream.skill_proposal_persist_failed",
                                    conversation_id=payload.conversation_id,
                                    error=str(exc),
                                )
                            event_payload = {
                                "kind": "ask_user_question",
                                "data": ask_user_question_payload,
                                "seq": 0,
                            }
                            yield f"data: {json.dumps(event_payload, ensure_ascii=False)}\n\n"
                            logger.info(
                                "chat_stream.skill_proposal_emitted",
                                conversation_id=payload.conversation_id,
                                options=[opt["value"] for opt in options_payload],
                            )
                            return

        # Combina profile + memory + default system prompt SCO Compliance OS +
        # catalogo competenze disponibili (per il pattern di proposta a ogni nuovo
        # task sostantivo). Il catalogo è appended in coda al DEFAULT prompt,
        # MAI prepended (il DEFAULT contiene le istruzioni di metodo, il catalogo
        # è il dato di riferimento operativo).
        # Pattern Conv. 47 single source of truth: catalogo discovered runtime,
        # MAI hardcoded nel system prompt template.
        skill_catalog_markdown = _get_skill_catalog_for_prompt(vault_root=None)
        if skill_catalog_markdown:
            base_system_prompt = f"{_DEFAULT_SYSTEM_PROMPT}\n\n{skill_catalog_markdown}"
        else:
            base_system_prompt = _DEFAULT_SYSTEM_PROMPT

        # v0.13.3 Antonio feedback fix: ONBOARDING_STATUS placeholder substitution
        # Pattern Conv. 47 SSOT backend: count user_profile fields popolati,
        # sostituisce nel system prompt cosi LLM applica VINCOLO ONBOARDING
        # (refuse task sostantivi se profilo incompleto, redirect a Q1-Q10).
        # Threshold 10/10 perche os-setup richiede tutte 10 risposte per
        # calibrazione completa. Soglia ammorbidita a 5/10 se utente vuole
        # bypassare ("salta onboarding") + agente segnala profilo vuoto.
        onboarding_status_str = "complete"
        try:
            profile_count = len(profile_prefs) if profile_prefs else 0
            if profile_count < 10:
                onboarding_status_str = f"incomplete ({profile_count}/10)"
        except Exception:
            # Best-effort: se DB unreachable, assume incomplete per safety
            onboarding_status_str = "incomplete (sconosciuto)"

        base_system_prompt = base_system_prompt.replace(
            "{ONBOARDING_STATUS}", onboarding_status_str
        )

        effective_system_prompt = base_system_prompt
        if profile_markdown:
            effective_system_prompt = f"{profile_markdown}\n\n{base_system_prompt}"

        if selected_skill_from_proposal:
            effective_system_prompt = (
                f"{effective_system_prompt}\n\nSkill attiva richiesta dall'utente: {selected_skill_from_proposal}"
            )

        # Risolvi tenant config + tier
        tier_value: Tier = payload.tier if payload.tier else "agentic-v1"  # type: ignore[assignment]
        try:
            tenant_config = await get_tenant_llm_config(tenant_id="local")

            # Override esplicito model_slug nella request: short-circuit a Anthropic
            # con quel modello, bypassando router per backward-compat.
            provider: LLMProvider | None = None

            if payload.model_slug:
                from sco_compliance_os.services.llm.providers.anthropic import (
                    build_anthropic_provider_from_license,
                )

                provider = build_anthropic_provider_from_license()
                if provider is None:
                    yield f"data: {json.dumps({'kind': 'error', 'data': {'message': 'Nessuna license attiva.'}})}\n\n"
                    return
                active_provider_name = "anthropic"
                resolved_model = payload.model_slug
            else:
                decision = await route(tier=tier_value, tenant_config=tenant_config)
                provider = decision.provider
                active_provider_name = decision.provider_name
                resolved_model = decision.model
                logger.info(
                    "chat_stream.routing_decision",
                    tier=tier_value,
                    provider=decision.provider_name,
                    model=decision.model,
                    fallback_used=decision.fallback_used,
                    attempted=decision.fallback_chain_attempted,
                )
        except ProviderError as perr:
            logger.error("chat_stream.router_error", error=str(perr))
            yield f"data: {json.dumps({'kind': 'error', 'data': {'message': str(perr), 'exc_type': perr.exc_type}})}\n\n"
            return
        except Exception as exc:
            logger.exception("chat_stream.router_unexpected_error", error=str(exc))
            yield f"data: {json.dumps({'kind': 'error', 'data': {'message': str(exc)}})}\n\n"
            return

        # v0.9.0 multi-turn skill fix:
        # 1. Carico la history completa della conversation per passarla al LLM
        #    (prima si passava solo il messaggio corrente, rendendo impossibile
        #    qualsiasi flow conversazionale tipo le 10 domande di os-setup).
        # 2. Se la conversation ha ``active_skill`` set, prepende il body SKILL.md
        #    al system prompt cosi' il modello mantiene il flow turn-by-turn.
        # 3. Detect completamento skill (matching "Profilo registrato:" in
        #    text_delta accumulato) per clear active_skill a fine flow.
        skill_body_prepend = ""
        if conv.active_skill:
            try:
                from sco_compliance_os.services.skills.loader import get_skill

                skill_meta = get_skill(conv.active_skill, vault_root=None)
                if skill_meta is not None:
                    skill_body_prepend = (
                        f"# Skill attiva: {skill_meta.name}\n\n{skill_meta.load_body()}\n\n---\n\n"
                    )
                    logger.info(
                        "chat_stream.skill_body_prepended",
                        skill_name=conv.active_skill,
                        skill_step=conv.active_skill_step,
                        body_len=len(skill_body_prepend),
                    )
            except Exception as exc:
                logger.warning(
                    "chat_stream.skill_body_load_failed",
                    skill_name=conv.active_skill,
                    error=str(exc),
                )

        if skill_body_prepend:
            effective_system_prompt = f"{skill_body_prepend}{effective_system_prompt}"

        try:
            # Carico history piena della conversation dal DB e la passo al LLM
            # come messages array. Pattern Conv. 48 + multi-turn skill flow.
            history_msgs = await store.list_messages(payload.conversation_id)
            messages_list: list[dict[str, Any]] = []
            for hm in history_msgs:
                # Skippa eventuali messaggi tool/system, mantieni solo user+assistant.
                if hm.role not in ("user", "assistant"):
                    continue
                # Se il content e' vuoto (placeholder), salta.
                if not hm.content or not hm.content.strip():
                    continue
                messages_list.append({"role": hm.role, "content": hm.content})

            # Assicurati che l'ultimo messaggio sia quello user appena persistito.
            # In caso di append_message duplicato (rare), filtra.
            if not messages_list or messages_list[-1].get("role") != "user":
                messages_list.append({"role": "user", "content": payload.message})

            # Feature 4 componente A: ottimizzazione SILENZIOSA del prompt utente.
            # Arricchisce SOLO la copia inviata all'LLM (ultimo messaggio user di
            # messages_list); il DB e la UI conservano il messaggio originale
            # (gia persistito sopra). L'utente non vede la versione ottimizzata.
            if messages_list and messages_list[-1].get("role") == "user":
                _optimized, _was_optimized = optimize_prompt(messages_list[-1]["content"])
                if _was_optimized:
                    messages_list[-1]["content"] = _optimized
                    logger.info(
                        "chat_stream.prompt_optimized",
                        conversation_id=payload.conversation_id,
                    )

            logger.info(
                "chat_stream.history_loaded",
                conversation_id=payload.conversation_id,
                history_count=len(messages_list),
                active_skill=conv.active_skill,
            )

            provider_extra: dict[str, Any] = {}
            if permission_mode:
                provider_extra["permission_mode"] = permission_mode
                provider_extra["metadata"] = {"permission_mode": permission_mode}
            if effective_cwd:
                provider_extra["working_directory"] = effective_cwd

            if provider is None:
                raise RuntimeError("Provider non inizializzato")

            async for ev in provider.stream(
                messages=messages_list,
                model=resolved_model,
                max_tokens=4096,
                system_prompt=effective_system_prompt,
                extra=provider_extra or None,
            ):
                # Accumula contenuto per persistenza finale
                if ev.kind == "text_delta":
                    assistant_text_buf.append(ev.data.get("text", ""))
                elif ev.kind == "ask_user_question":
                    ask_user_question_payload = ev.data
                elif ev.kind == "tool_use":
                    tool_calls_buf.append(ev.data)
                elif ev.kind == "error":
                    # Provider ha emesso error event -> registra failure per health scoring
                    try:
                        await record_failure(active_provider_name)  # type: ignore[arg-type]
                    except Exception:
                        pass

                # Emit SSE (ChunkEvent.kind values matchano il set EventKind esistente)
                event_payload = {"kind": ev.kind, "data": ev.data, "seq": ev.seq}
                yield f"data: {json.dumps(event_payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.error("chat_stream.error", error=str(exc), exc_info=True)
            try:
                await record_failure(active_provider_name)  # type: ignore[arg-type]
            except Exception:
                pass
            yield f"data: {json.dumps({'kind': 'error', 'data': {'message': str(exc)}})}\n\n"
        finally:
            # Persisti messaggio assistant con stato widget Conv. 48
            final_text = "".join(assistant_text_buf)

            # v0.13.4 Bug B fix (Antonio feedback 26/05): defensive persistence.
            # Diagnosi root cause subagent: Claude rifiuta task per VINCOLO
            # ONBOARDING strict (v0.13.3) → zero text_delta emessi → final_text
            # vuoto → frontend mostra bubble fantasma.
            # Defensive: se nessun text emesso E nessun widget E nessun
            # tool_call → log warning diagnostico + inietta fallback message
            # visibile invece di persistere content="" silente.
            if not final_text.strip() and ask_user_question_payload is None and not tool_calls_buf:
                logger.warning(
                    "chat_stream.empty_assistant_response",
                    conversation_id=payload.conversation_id,
                    active_skill=conv.active_skill,
                    onboarding_status=onboarding_status_str
                    if "onboarding_status_str" in dir()
                    else None,
                    history_count=len(messages_list) if "messages_list" in dir() else None,
                    model=resolved_model if "resolved_model" in dir() else None,
                )
                # Inietta messaggio di refusal trasparente con suggerimento.
                final_text = (
                    "Non ho potuto generare una risposta per questa richiesta. "
                    "Possibile causa: il vincolo onboarding e' ancora attivo. "
                    "Prova a scrivere 'salta onboarding' per procedere senza "
                    "completare il profilo, oppure rispondi alle 10 domande "
                    "di profilazione iniziali."
                )

            assistant_msg = await store.append_message(
                conversation_id=payload.conversation_id,
                role="assistant",
                content=final_text,
                ask_user_question=ask_user_question_payload,
                tool_calls=tool_calls_buf or None,
            )

            # v0.9.0 multi-turn skill: detect skill completion + auto-advance step.
            # Pattern: se la skill os-setup emette riepilogo finale "Profilo
            # registrato:" o "Profilo salvato", clear active_skill. Altrimenti
            # increment step counter.
            # v0.13.0 OMEGA: aggiunto persist_setup_answer pre-increment per
            # popolare user_profile.db con le risposte Q1-Q10 (gap regex
            # extract_preferences che non matcha single-token answers).
            if conv.active_skill:
                try:
                    # Pre-increment: la risposta dell'utente al turno corrente
                    # appartiene allo step active_skill_step+1 (se era 0 alla
                    # creazione conv, la risposta a Q1 e' step=1).
                    # NB: conv.active_skill_step refletta lo stato PRIMA
                    # dell'increment del finally block.
                    current_answer_step = (conv.active_skill_step or 0) + 1

                    if is_setup_step_user_answer(
                        active_skill=conv.active_skill,
                        active_skill_step=current_answer_step,
                    ):
                        persist_result = await persist_setup_answer(
                            user_message=payload.message,
                            active_skill_step=current_answer_step,
                            conversation_id=payload.conversation_id,
                            message_id=user_msg.id,
                            tenant_id="local",
                        )
                        logger.info(
                            "chat_stream.setup_answer_persisted",
                            conversation_id=payload.conversation_id,
                            step=persist_result.get("step_key"),
                            persisted=persist_result.get("persisted"),
                            slug=persist_result.get("preference_slug"),
                            team_member_updated=persist_result.get("team_member_updated"),
                            reason=persist_result.get("reason"),
                        )

                    completion_markers = (
                        "Profilo registrato:",
                        "Profilo salvato. Procedo",
                        "Onboarding saltato",
                    )
                    is_completed = any(m in final_text for m in completion_markers)
                    if is_completed:
                        await store.set_active_skill(payload.conversation_id, None, None)
                        logger.info(
                            "chat_stream.skill_completed",
                            conversation_id=payload.conversation_id,
                            skill_name=conv.active_skill,
                            final_step=conv.active_skill_step,
                        )

                        # v0.13.2 DEV-AUTO-OPTIMIZER: emit setup.completed event
                        # post-os-setup completion. Subscriber:
                        # optimizer_trigger.handle_setup_completed (registered
                        # by main.py lifespan via register_default_subscribers()).
                        # Pattern Conv. 47 SSOT: emit SEMPRE su completion marker,
                        # subscriber decide ramo (toggle env, fallback graceful).
                        if conv.active_skill == "os-setup":
                            try:
                                from sco_compliance_os.core.events import EventBus
                                from sco_compliance_os.services.skills.auto_trigger import (
                                    EVENT_SETUP_COMPLETED,
                                )

                                # Risolvi vault_path/vault_name dal vault registry
                                # (single source of truth filesystem).
                                vault_path_resolved = ""
                                vault_name_resolved = "Vault"
                                vault_id_resolved = ""
                                try:
                                    from pathlib import Path as _Path

                                    from sco_compliance_os.api.vault_routes import (
                                        _load_registry,
                                    )

                                    registry_path = _Path(settings.vault_registry_path)
                                    entries = _load_registry(registry_path)
                                    if entries:
                                        # Usa l'ultima entry attiva come default.
                                        # Carry-over v0.13.3: conversation -> vault
                                        # binding strutturato (per ora single-vault MVP).
                                        last_entry = entries[-1]
                                        vault_path_resolved = str(last_entry.get("path", ""))
                                        vault_name_resolved = str(last_entry.get("name", "Vault"))
                                        vault_id_resolved = str(last_entry.get("id", ""))
                                except Exception as reg_exc:
                                    logger.warning(
                                        "chat_stream.optimizer_vault_lookup_failed",
                                        error=str(reg_exc),
                                    )

                                EventBus.instance().schedule_publish(
                                    EVENT_SETUP_COMPLETED,
                                    {
                                        "vault_id": vault_id_resolved,
                                        "vault_path": vault_path_resolved,
                                        "vault_name": vault_name_resolved,
                                        "completion_conv_id": payload.conversation_id,
                                        "completion_skill_name": conv.active_skill,
                                    },
                                )
                                logger.info(
                                    "chat_stream.optimizer_event_published",
                                    event_type=EVENT_SETUP_COMPLETED,
                                    conv_id=payload.conversation_id,
                                    vault_id=vault_id_resolved,
                                    vault_path=vault_path_resolved,
                                )
                            except Exception as opt_exc:
                                logger.warning(
                                    "chat_stream.optimizer_event_publish_failed",
                                    error=str(opt_exc),
                                )
                    else:
                        next_step = (conv.active_skill_step or 0) + 1
                        await store.set_active_skill(
                            payload.conversation_id,
                            conv.active_skill,
                            next_step,
                        )
                except Exception as exc:
                    logger.warning(
                        "chat_stream.skill_step_update_failed",
                        error=str(exc),
                    )

            # v0.8.1 hook proposta ingest wiki: analizza il contenuto + tool_calls
            # web_search per detectare allegati / URL / search results candidati
            # all'ingest nel wiki. Emette evento SSE wiki_ingest_proposal se ci
            # sono candidati. Best-effort: errori loggati ma NON bloccano lo stream.
            try:
                from sco_compliance_os.services.chat.wiki_proposal import (
                    analyze_message_for_wiki_ingest,
                )

                # Estrai search results dai tool_calls web_search (se presenti).
                search_hits: list[dict[str, Any]] = []
                for tc in tool_calls_buf:
                    tool_name = (tc.get("tool_name") or tc.get("name") or "").lower()
                    if "web_search" not in tool_name and "search" not in tool_name:
                        continue
                    # I risultati possono vivere in result, content, output.
                    raw_result = tc.get("result") or tc.get("content") or tc.get("output")
                    if isinstance(raw_result, list):
                        for hit in raw_result:
                            if isinstance(hit, dict):
                                search_hits.append(hit)
                    elif isinstance(raw_result, dict):
                        hits_list = raw_result.get("hits") or raw_result.get("results", [])
                        if isinstance(hits_list, list):
                            for hit in hits_list:
                                if isinstance(hit, dict):
                                    search_hits.append(hit)

                # Estrai allegati dai tool_calls Read/upload (heuristica).
                attachment_hits: list[dict[str, Any]] = []
                for tc in tool_calls_buf:
                    tool_name = (tc.get("tool_name") or tc.get("name") or "").lower()
                    if tool_name in {"read", "upload", "attachment_extract"}:
                        # Cerca path nei common args.
                        args = tc.get("args") or tc.get("input") or {}
                        if isinstance(args, dict):
                            file_path = (
                                args.get("file_path") or args.get("path") or args.get("filename")
                            )
                            if file_path:
                                attachment_hits.append(
                                    {
                                        "path": str(file_path),
                                        "mime_type": "",
                                        "content_preview": str(tc.get("result", ""))[:4000],
                                    }
                                )

                proposal = analyze_message_for_wiki_ingest(
                    conversation_id=payload.conversation_id,
                    message_id=assistant_msg.id,
                    message_content="".join(assistant_text_buf),
                    attachments=attachment_hits,
                    search_results=search_hits,
                )
                if not proposal.is_empty:
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "kind": "wiki_ingest_proposal",
                                "data": proposal.to_dict(),
                            },
                            ensure_ascii=False,
                        )
                        + "\n\n"
                    )
                    logger.info(
                        "chat_stream.wiki_ingest_proposal_emitted",
                        proposal_id=proposal.proposal_id,
                        slots=len(proposal.slots),
                        has_strong=proposal.has_strong_candidate,
                    )
            except Exception as wp_exc:
                logger.warning(
                    "chat_stream.wiki_ingest_proposal_failed",
                    error=str(wp_exc),
                )

            # Post-turn hook: estrazione preferenze fire-and-forget.
            # Pattern best-effort: errori loggati internamente ma NON bloccano
            # la chiusura dello StreamingResponse SSE.
            try:
                schedule_on_turn_complete(
                    {
                        "user_message": payload.message,
                        "assistant_response": "".join(assistant_text_buf),
                        "turn_id": f"{payload.conversation_id}__{user_msg.id}",
                    },
                    tenant_id="local",
                )
            except Exception as exc:
                logger.warning("chat_stream.post_turn_hook_failed", error=str(exc))

            # v0.13.0 OMEGA: ingest chat turn in memory_tree per recall futuro.
            # Pattern Conv. 47 single source of truth: ogni turn (user_msg +
            # assistant_response combined) viene chunked + admission-graded e
            # persisted in `mem_tree_chunks`. Il flusso BM25 di
            # tree_summaries.query_relevant_summaries gia' integrato nel system
            # prompt (linee 215-247 sopra) potra' poi recuperare il contesto
            # sealed L1/L2 in nuove chat sequenti.
            # Best-effort: errori NON bloccanti per lo stream SSE.
            try:
                from sco_compliance_os.services.memory.tree_ingester import (
                    IngestInput,
                    ingest_inputs,
                )

                turn_combined = (
                    f"[USER]\n{payload.message}\n\n[ASSISTANT]\n{''.join(assistant_text_buf)}"
                )
                # Trim long content per evitare bloat memoria (cap 8000 char).
                if len(turn_combined) > 8000:
                    turn_combined = turn_combined[:8000] + "\n[TRUNCATED]"

                # Fire-and-forget: non await il task (lo schedula come bg).
                import asyncio as _asyncio

                _asyncio.create_task(  # noqa: RUF006 — fire-and-forget bg ingest intenzionale
                    ingest_inputs(
                        [
                            IngestInput(
                                source_kind="chat",
                                source_id=payload.conversation_id,
                                content=turn_combined,
                                owner="local",
                                tags=[
                                    "chat-turn",
                                    f"conv:{payload.conversation_id}",
                                ],
                            )
                        ],
                    ),
                    name=f"chat-ingest-{payload.conversation_id}",
                )
                logger.info(
                    "chat_stream.memory_ingest_scheduled",
                    conversation_id=payload.conversation_id,
                    content_chars=len(turn_combined),
                )
            except Exception as exc:
                logger.warning(
                    "chat_stream.memory_ingest_failed",
                    error=str(exc),
                )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ----- Endpoint: conversations CRUD -----


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    settings: Settings = Depends(get_settings),
) -> list[ConversationOut]:
    """Lista conversation ordinate per updated_at DESC."""
    store = get_store(settings.memory_tree_db_path)
    convs = await store.list_conversations()
    return [
        ConversationOut(
            id=c.id,
            title=c.title,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
            agent_mode=cast(ChatModeLiteral, c.agent_mode or "auto"),
        )
        for c in convs
    ]


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    payload: ConversationCreateRequest,
    settings: Settings = Depends(get_settings),
) -> ConversationOut:
    """Crea nuova conversation."""
    store = get_store(settings.memory_tree_db_path)
    conv = await store.create_conversation(title=payload.title or "Nuova conversazione")
    return ConversationOut(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        agent_mode=cast(ChatModeLiteral, conv.agent_mode or "auto"),
    )


@router.patch("/conversations/{conv_id}", response_model=ConversationOut)
async def update_conversation(
    conv_id: str,
    payload: ConversationUpdateRequest,
    settings: Settings = Depends(get_settings),
) -> ConversationOut:
    """Aggiorna metadata della conversation (attualmente agent_mode)."""

    store = get_store(settings.memory_tree_db_path)
    conv = await store.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail=f"Conversation {conv_id} non trovata")

    if payload.agent_mode is not None:
        await store.set_agent_mode(conv_id, payload.agent_mode)
        conv = await store.get_conversation(conv_id)
        if conv is None:
            raise HTTPException(status_code=404, detail=f"Conversation {conv_id} non trovata")

    return ConversationOut(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        agent_mode=cast(ChatModeLiteral, conv.agent_mode or "auto"),
    )


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def get_conversation_messages(
    conv_id: str,
    settings: Settings = Depends(get_settings),
) -> list[MessageOut]:
    """Ritorna i messaggi della conversation.

    Pattern Conv. 48: deserializza ask_user_question_json + tool_calls_json
    e li include nella response per ricostruire stato widget UI al fetch.
    """
    store = get_store(settings.memory_tree_db_path)
    conv = await store.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail=f"Conversation {conv_id} non trovata")
    msgs = await store.list_messages(conv_id)
    out: list[MessageOut] = []
    for m in msgs:
        out.append(
            MessageOut(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                ask_user_question=(
                    json.loads(m.ask_user_question_json) if m.ask_user_question_json else None
                ),
                tool_calls=(json.loads(m.tool_calls_json) if m.tool_calls_json else None),
                created_at=m.created_at.isoformat(),
            )
        )
    return out


@router.delete(
    "/conversations/{conv_id}", status_code=204, response_class=Response, response_model=None
)
async def delete_conversation(
    conv_id: str,
    settings: Settings = Depends(get_settings),
) -> Response:
    """Cancella conversation + messaggi + artifacts memory tree."""
    store = get_store(settings.memory_tree_db_path)
    deleted = await store.delete_conversation(conv_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Conversation {conv_id} non trovata")
    return Response(status_code=204)
