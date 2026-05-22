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
from sco_compliance_os.core.agent_sdk_runner import build_runner
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.core.store import get_store

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
        raise HTTPException(status_code=404, detail=f"Conversation {payload.conversation_id} non trovata")

    # Persisti messaggio utente prima dello stream
    await store.append_message(
        conversation_id=payload.conversation_id,
        role="user",
        content=payload.message,
    )

    model_slug = payload.model_slug or settings.model_default

    async def event_generator() -> AsyncIterator[str]:
        """Yield SSE events in formato `data: {json}\\n\\n`."""
        runner = await build_runner(model_slug=model_slug)
        assistant_text_buf: list[str] = []
        ask_user_question_payload: dict[str, Any] | None = None
        tool_calls_buf: list[dict[str, Any]] = []

        try:
            async for ev in runner.stream(payload.message):
                # Accumula contenuto per persistenza finale
                if ev.kind == "text_delta":
                    assistant_text_buf.append(ev.data.get("text", ""))
                elif ev.kind == "ask_user_question":
                    ask_user_question_payload = ev.data
                elif ev.kind == "tool_use":
                    tool_calls_buf.append(ev.data)

                # Emit SSE
                event_payload = {"kind": ev.kind, "data": ev.data, "seq": ev.seq}
                yield f"data: {json.dumps(event_payload, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            logger.error("chat_stream.error", error=str(exc), exc_info=True)
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
                    json.loads(m.ask_user_question_json)
                    if m.ask_user_question_json
                    else None
                ),
                tool_calls=(
                    json.loads(m.tool_calls_json) if m.tool_calls_json else None
                ),
                created_at=m.created_at.isoformat(),
            )
        )
    return out
