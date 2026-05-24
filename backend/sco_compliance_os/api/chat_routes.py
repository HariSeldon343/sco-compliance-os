"""Router /api/chat — streaming SSE + conversations CRUD.

Pattern Conv. 48 SINGLE SOURCE OF TRUTH BACKEND per stato widget post-streaming:
quando lo stream emette `ask_user_question`, il backend persiste il payload sul
messaggio assistant (campo ask_user_question_json). Il frontend NON deve
preservare lo stato widget da React state — lo legge dal fetch della conversation.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.agent_sdk_runner import _DEFAULT_SYSTEM_PROMPT
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.core.post_turn_hook import schedule_on_turn_complete
from sco_compliance_os.core.store import get_store
from sco_compliance_os.services.learning.profile_renderer import (
    render_profile_markdown,
)
from sco_compliance_os.services.learning.profile_store import list_preferences
from sco_compliance_os.services.llm.provider import ProviderError
from sco_compliance_os.services.llm.router import (
    Tier,
    get_tenant_llm_config,
    record_failure,
    route,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ----- Schemi Pydantic -----


class ChatStreamRequest(BaseModel):
    """Richiesta di streaming chat."""

    conversation_id: str = Field(..., description="ID conversation di destinazione.")
    message: str = Field(..., min_length=1, description="Messaggio utente.")
    model_slug: str | None = Field(
        default=None,
        description="Override modello (default da settings.model_default).",
    )
    agent: str | None = Field(
        default=None,
        description="Nome agent/subagent da usare (es. compliance-os, dev, etc).",
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


class ConversationOut(BaseModel):
    """Schema response conversation."""

    id: str
    title: str
    created_at: str
    updated_at: str


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
    if conv is None:
        raise HTTPException(
            status_code=404, detail=f"Conversation {payload.conversation_id} non trovata"
        )

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
    # Pattern Karpathy "no vector DB": BM25 lite stateless.
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
                snippet = (
                    f"\n### [{s.tree_kind}:{s.tree_id} L{s.level}]\n"
                    f"{s.content_summary}\n"
                )
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
        tenant_config vuoto -> default chain -> Anthropic Sonnet 4.6 (agentic-v1).
        Override model_slug nella request: forza Anthropic con quel modello.
        """
        assistant_text_buf: list[str] = []
        ask_user_question_payload: dict[str, Any] | None = None
        tool_calls_buf: list[dict[str, Any]] = []
        active_provider_name = "unknown"

        # Combina profile + memory + default system prompt Antonio Amodeo
        effective_system_prompt = _DEFAULT_SYSTEM_PROMPT
        if profile_markdown:
            effective_system_prompt = (
                f"{profile_markdown}\n\n{_DEFAULT_SYSTEM_PROMPT}"
            )

        # Risolvi tenant config + tier
        tier_value: Tier = payload.tier if payload.tier else "agentic-v1"  # type: ignore[assignment]
        try:
            tenant_config = await get_tenant_llm_config(tenant_id="local")

            # Override esplicito model_slug nella request: short-circuit a Anthropic
            # con quel modello, bypassando router per backward-compat.
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
                decision = await route(
                    tier=tier_value, tenant_config=tenant_config
                )
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

        try:
            messages_list: list[dict[str, Any]] = [
                {"role": "user", "content": payload.message}
            ]
            async for ev in provider.stream(
                messages=messages_list,
                model=resolved_model,
                max_tokens=4096,
                system_prompt=effective_system_prompt,
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
            await store.append_message(
                conversation_id=payload.conversation_id,
                role="assistant",
                content="".join(assistant_text_buf),
                ask_user_question=ask_user_question_payload,
                tool_calls=tool_calls_buf or None,
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
