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

import json
import time
from typing import Any

import aiosqlite
import pytest
from httpx import AsyncClient

from sco_compliance_os.config import get_settings
from sco_compliance_os.core.store import get_store
from sco_compliance_os.services.llm.router import RoutingDecision
from sco_compliance_os.services.memory import tree_store
from sco_compliance_os.services.memory.tree_chunker import TreeChunkSourceKind


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
    assert body["agent_mode"] == "auto"


@pytest.mark.asyncio
async def test_list_conversations_empty(client: AsyncClient) -> None:
    """GET /api/chat/conversations inizialmente → []."""
    response = await client.get("/api/chat/conversations")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_update_conversation_agent_mode(client: AsyncClient) -> None:
    """PATCH /api/chat/conversations/{id} aggiorna agent_mode."""

    create_resp = await client.post(
        "/api/chat/conversations",
        json={"title": "conv-agent-mode"},
    )
    conv = create_resp.json()
    conv_id = conv["id"]

    patch_resp = await client.patch(
        f"/api/chat/conversations/{conv_id}",
        json={"agent_mode": "plan"},
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["agent_mode"] == "plan"

    list_resp = await client.get("/api/chat/conversations")
    assert list_resp.status_code == 200
    conversations = list_resp.json()
    assert any(c["id"] == conv_id and c["agent_mode"] == "plan" for c in conversations)


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
async def test_chat_stream_permission_mode_mapping(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stream con agent_mode yolo propaga permission_mode bypass."""

    class StubChunk:
        def __init__(self, kind: str, data: dict[str, Any], seq: int) -> None:
            self.kind = kind
            self.data = data
            self.seq = seq

    class StubProvider:
        def __init__(self) -> None:
            self.received_extra: dict[str, Any] | None = None

        async def stream(
            self,
            messages: list[dict[str, Any]],
            model: str,
            max_tokens: int = 4096,
            system_prompt: str | None = None,
            temperature: float = 1.0,
            extra: dict[str, Any] | None = None,
        ):
            self.received_extra = extra
            yield StubChunk("text_delta", {"text": "ok"}, 0)
            yield StubChunk(
                "done",
                {
                    "stop_reason": "stop",
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                    "model": model,
                },
                1,
            )

    stub_provider = StubProvider()

    async def fake_route(
        tier: str = "agentic-v1",
        tenant_config: dict[str, Any] | None = None,
        skip_health_check: bool = False,
    ) -> RoutingDecision:
        return RoutingDecision(
            provider=stub_provider,
            provider_name="anthropic",
            model="claude-opus-4-7",
            tier=tier,
            fallback_used=False,
            fallback_chain_attempted=[],
        )

    # chat_routes fa `from ...router import route`, quindi il nome `route` e'
    # un riferimento locale al modulo chat_routes: va patchato li, non sul
    # modulo router originale (altrimenti il route gia importato non cambia).
    monkeypatch.setattr("sco_compliance_os.api.chat_routes.route", fake_route)

    conv_resp = await client.post("/api/chat/conversations", json={"title": "perm-mode"})
    conv_id = conv_resp.json()["id"]

    async with client.stream(
        "POST",
        "/api/chat/stream",
        json={
            "conversation_id": conv_id,
            "message": "test perm",
            "agent_mode": "yolo",
        },
    ) as response:
        async for _ in response.aiter_text():
            pass

    assert stub_provider.received_extra is not None
    assert stub_provider.received_extra["permission_mode"] == "bypassPermissions"
    metadata = stub_provider.received_extra.get("metadata") or {}
    assert metadata.get("permission_mode") == "bypassPermissions"

    list_resp = await client.get("/api/chat/conversations")
    conversations = list_resp.json()
    stored_mode = next(c["agent_mode"] for c in conversations if c["id"] == conv_id)
    assert stored_mode == "yolo"


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


@pytest.mark.asyncio
async def test_delete_conversation_cascade(client: AsyncClient) -> None:
    """DELETE /conversations/{id} cancella messaggi + memory tree artifacts."""

    resp = await client.post(
        "/api/chat/conversations",
        json={"title": "conv da cancellare"},
    )
    assert resp.status_code == 201
    conv_id = resp.json()["id"]

    settings = get_settings()
    store = get_store(settings.memory_tree_db_path)

    await tree_store.init_tree_schema(settings.memory_tree_db_path)

    await store.append_message(
        conversation_id=conv_id,
        role="user",
        content="Messaggio da eliminare",
    )

    now_ms = int(time.time() * 1000)
    chunk_id = f"chunk-{conv_id}"
    async with aiosqlite.connect(settings.memory_tree_db_path) as db:
        await db.execute(
            """
            INSERT INTO mem_tree_chunks (
                id, source_kind, source_id, owner, timestamp_ms, time_range_start_ms,
                time_range_end_ms, tags_json, content, token_count, seq_in_source,
                created_at_ms, status, cheap_total, llm_score, admission_reasoning, parent_summary_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL)
            """,
            (
                chunk_id,
                TreeChunkSourceKind.CHAT.value,
                conv_id,
                "local",
                now_ms,
                now_ms,
                now_ms,
                json.dumps(["test"]),
                "Chunk test conv-delete",
                12,
                0,
                now_ms,
                "pending_extraction",
            ),
        )
        await db.execute(
            """
            INSERT INTO mem_tree_summaries (
                id, tree_kind, tree_id, level, content_summary, parent_summary_id,
                children_chunk_ids_json, children_summary_ids_json, token_count,
                source_kind_hint, owner, created_at_ms, sealed_at_ms, status
            ) VALUES (?, 'source', ?, 1, ?, NULL, '[]', '[]', ?, NULL, 'local', ?, NULL, 'sealed')
            """,
            (
                f"summary-{conv_id}",
                conv_id,
                "Sommario test",
                5,
                now_ms,
            ),
        )
        await db.commit()

    delete_resp = await client.delete(f"/api/chat/conversations/{conv_id}")
    assert delete_resp.status_code == 204

    assert await store.get_conversation(conv_id) is None
    msgs_after = await store.list_messages(conv_id)
    assert msgs_after == []

    chunks_after = await tree_store.list_chunks(
        source_kind=TreeChunkSourceKind.CHAT.value,
        source_id=conv_id,
        db_path=settings.memory_tree_db_path,
    )
    assert chunks_after == []

    async with aiosqlite.connect(settings.memory_tree_db_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM mem_tree_summaries WHERE tree_kind = 'source' AND tree_id = ?",
            (conv_id,),
        ) as cur:
            row = await cur.fetchone()
            assert row is not None and row[0] == 0
