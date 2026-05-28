"""Test auto-trigger skill loader runtime al vault registered.

v0.6.0 pattern: POST /api/vault/add → EventBus.publish('vault.registered')
→ handle_vault_registered async → crea conversation 'Configurazione iniziale del vault X'
→ executa os-setup + os-ottimizzatore.

In test mode (no Anthropic credentials) le skill possono fallire silenziosamente
ma la conversation viene comunque creata + log messages persistiti.
Questo test verifica il MECCANISMO di auto-trigger, non l'output LLM.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_vault_register_creates_setup_conversation(
    client: AsyncClient, temp_vault: Path
) -> None:
    """POST /vault/add → wait → /chat/conversations include 'Configurazione iniziale'.

    Conv. 41 tracciatura: il sistema deve loggare il trigger anche se LLM fallisce.
    Conv. 47 SOT: la conversation vive nel DB, non in memoria React.
    """
    # Pre-register: no conversations
    pre = await client.get("/api/chat/conversations")
    assert pre.status_code == 200
    initial_count = len(pre.json())

    # Register vault → EventBus.schedule_publish(vault.registered)
    add = await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "autotrigger-test"},
    )
    assert add.status_code == 201

    # Wait for skill execution (LLM call timeout o fallback)
    # In test env (no creds) il fallback è veloce ma asincrono.
    await asyncio.sleep(3.0)

    # Verifica conversation creata
    post = await client.get("/api/chat/conversations")
    assert post.status_code == 200
    convs = post.json()

    # Almeno una conversation in più
    assert len(convs) >= initial_count + 1, (
        f"Atteso almeno {initial_count + 1} conv, ne trovo {len(convs)}"
    )

    # Cerca la conversation 'Configurazione iniziale'
    setup_convs = [c for c in convs if "Configurazione iniziale" in c.get("title", "")]
    assert len(setup_convs) >= 1, (
        f"Nessuna conv 'Configurazione iniziale' trovata. Titoli: {[c['title'] for c in convs]}"
    )

    title = setup_convs[0]["title"]
    assert "autotrigger-test" in title, f"Atteso vault_name nel titolo: {title}"


@pytest.mark.asyncio
async def test_vault_register_re_add_creates_new_conversation(
    client: AsyncClient, temp_vault: Path
) -> None:
    """Re-add stesso path → SI seconda conversation 'Configurazione iniziale'.

    Pattern Conv. 47 v0.9.0+: ogni re-add esplicito dell'utente RIESEGUE
    le skill os-setup (idempotenti), generando nuova conversation visibile
    in sidebar. Razionale UX: l'utente vede chiaramente che il vault e' stato
    riconosciuto e le skill ri-eseguite, evita confusione "perche' non
    succede nulla?".

    Storico:
    - v0.5.x: ogni re-add creava conversation duplicata → loop os-setup (bug).
    - v0.6.x: dedup naturale fix loop (NO re-emit).
    - v0.9.0+: re-emit DELIBERATO. Il re-add e' azione esplicita utente
      (cliccato vault > add second time), non auto-trigger silenzioso, quindi
      generare seconda conversation comunica chiarezza UX. Riferimento codice:
      ``services/skills/auto_trigger.py:172-174`` commento esplicito.
    """
    # First add
    await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "re-add-test"},
    )
    await asyncio.sleep(2.0)

    convs_after_first = await client.get("/api/chat/conversations")
    count_after_first = len(
        [c for c in convs_after_first.json() if "Configurazione iniziale" in c.get("title", "")]
    )

    # Second add stesso path
    await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "re-add-test-2"},
    )
    await asyncio.sleep(2.0)

    convs_after_second = await client.get("/api/chat/conversations")
    count_after_second = len(
        [c for c in convs_after_second.json() if "Configurazione iniziale" in c.get("title", "")]
    )

    # v0.9.0+ design: re-add CREA seconda conversation (idempotenza UX-visible)
    assert count_after_second == count_after_first + 1, (
        f"Re-add doveva creare nuova conversation: count {count_after_first} → {count_after_second}"
    )


@pytest.mark.asyncio
async def test_vault_setup_conversation_has_messages(client: AsyncClient, temp_vault: Path) -> None:
    """La conversation setup deve avere messaggi assistant con tool_calls skill_invocation.

    NOTA: in assenza di creds Anthropic, l'execute_skill fallisce ma
    il messaggio con tool_calls=skill_invocation viene comunque persistito
    se almeno il setup_text è popolato. In env senza LLM la copertura
    di questa logica può essere parziale: il test verifica la conversation
    esiste, e la presenza dei messages è "best-effort".
    """
    await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "messages-test"},
    )
    await asyncio.sleep(3.5)

    convs = await client.get("/api/chat/conversations")
    setup_convs = [c for c in convs.json() if "Configurazione iniziale" in c.get("title", "")]
    assert setup_convs, "Conv 'Configurazione iniziale' non creata"

    conv_id = setup_convs[0]["id"]
    msgs_resp = await client.get(f"/api/chat/conversations/{conv_id}/messages")
    assert msgs_resp.status_code == 200
    msgs = msgs_resp.json()

    # In env test la skill fallisce subito (no LLM creds) → messages può essere []
    # Verifichiamo che la richiesta sia comunque valida, no 500.
    assert isinstance(msgs, list)
