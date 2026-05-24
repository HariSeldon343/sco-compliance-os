"""Chat streaming SSE E2E test.

POST /api/chat/stream con conversation creata → SSE events.

In test env senza credenziali Anthropic, l'agent_runner emette:
    - kind='error' + data.message='Nessuna license attiva...' + return

Verifichiamo:
1. La conversation viene creata
2. POST stream non crasha, ritorna 200 con Content-Type: text/event-stream
3. Almeno UN evento SSE viene emesso (error in test env)
4. Il messaggio user viene persistito anche se assistant fallisce
5. Pattern Conv. 48: il payload finale include ask_user_question + tool_calls
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient) -> None:
    """POST /api/chat/conversations → 201 + ID generato."""
    response = await client.post(
        "/api/chat/conversations",
        json={"title": "Test conversation chat streaming"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"]
    assert body["title"] == "Test conversation chat streaming"


@pytest.mark.asyncio
async def test_list_conversations_empty(client: AsyncClient) -> None:
    """GET /api/chat/conversations inizialmente → []."""
    response = await client.get("/api/chat/conversations")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_chat_stream_no_credentials_error_event(
    client: AsyncClient, mock_no_anthropic_credentials: None
) -> None:
    """POST /chat/stream senza creds → SSE error event chiaro.

    Conv. 41 enforcement: il fallback NON crasha, emette evento esplicito
    leggibile dal frontend.
    """
    # Crea conversation
    conv_resp = await client.post(
        "/api/chat/conversations",
        json={"title": "stream-test-conv"},
    )
    conv_id = conv_resp.json()["id"]

    # Stream
    async with client.stream(
        "POST",
        "/api/chat/stream",
        json={
            "conversation_id": conv_id,
            "message": "Ciao test streaming",
        },
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Raccogli i primi N eventi
        events: list[str] = []
        async for chunk in response.aiter_text():
            events.append(chunk)
            if len(events) >= 3:
                break

    full_text = "".join(events)
    # In test env atteso: evento error per missing credentials
    # Almeno un "data:" SSE event deve essere stato emesso
    assert "data:" in full_text, f"No SSE data emesso, raw: {full_text[:500]}"


@pytest.mark.asyncio
async def test_chat_stream_persists_user_message(
    client: AsyncClient, mock_no_anthropic_credentials: None
) -> None:
    """POST /stream → messaggio user salvato in DB anche se LLM fallisce.

    Conv. 48 enforcement: persisted state via DB, non React state.
    """
    conv_resp = await client.post(
        "/api/chat/conversations",
        json={"title": "persistence-test"},
    )
    conv_id = conv_resp.json()["id"]

    user_msg = "Messaggio test per verificare persistenza user message"

    async with client.stream(
        "POST",
        "/api/chat/stream",
        json={"conversation_id": conv_id, "message": user_msg},
    ) as response:
        # Consuma stream
        async for _ in response.aiter_text():
            pass

    # Verifica user message persistito
    msgs_resp = await client.get(f"/api/chat/conversations/{conv_id}/messages")
    assert msgs_resp.status_code == 200
    msgs = msgs_resp.json()

    # Almeno il messaggio user deve essere salvato
    user_msgs = [m for m in msgs if m["role"] == "user"]
    assert len(user_msgs) >= 1
    assert user_msgs[0]["content"] == user_msg


@pytest.mark.asyncio
async def test_chat_stream_nonexistent_conversation_404(
    client: AsyncClient,
) -> None:
    """POST /stream con conv_id inesistente → 404."""
    response = await client.post(
        "/api/chat/stream",
        json={
            "conversation_id": "nonexistent-conv-xyz-123",
            "message": "test",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_message_schema_includes_widget_fields(
    client: AsyncClient, mock_no_anthropic_credentials: None
) -> None:
    """Conv. 48: il messaggio in GET /messages include ask_user_question + tool_calls.

    Anche se null/None, i campi devono essere PRESENTI nel JSON response per
    matching frontend.
    """
    conv_resp = await client.post(
        "/api/chat/conversations",
        json={"title": "widget-schema-test"},
    )
    conv_id = conv_resp.json()["id"]

    async with client.stream(
        "POST",
        "/api/chat/stream",
        json={"conversation_id": conv_id, "message": "test widget fields"},
    ) as response:
        async for _ in response.aiter_text():
            pass

    msgs_resp = await client.get(f"/api/chat/conversations/{conv_id}/messages")
    msgs = msgs_resp.json()

    for msg in msgs:
        # Schema MessageOut Conv. 48: ask_user_question + tool_calls always present
        assert "ask_user_question" in msg
        assert "tool_calls" in msg
