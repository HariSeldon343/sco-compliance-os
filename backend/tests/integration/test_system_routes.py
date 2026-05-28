"""Integration test per /api/system — data-status + reset-data (Feature 1 v0.15.0).

Pattern conftest: client httpx ASGITransport + temp_data_dir (override data_dir +
reset singleton store). Tutti i test async (asyncio_mode=auto).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from sco_compliance_os.config import get_settings
from sco_compliance_os.core.store import get_store


@pytest.mark.asyncio
async def test_data_status_fresh_has_no_meaningful_data(
    client: AsyncClient, temp_data_dir: Path
) -> None:
    """Su install pulito (solo DB vuoto creato a startup) has_data deve essere False."""
    response = await client.get("/api/system/data-status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["has_data"] is False
    assert body["conversations"] == 0
    assert body["vaults"] == 0
    assert body["onboarding_done"] is False


@pytest.mark.asyncio
async def test_data_status_with_conversation(client: AsyncClient, temp_data_dir: Path) -> None:
    """Con almeno una conversation reale, conversations>=1 e has_data True."""
    settings = get_settings()
    store = get_store(settings.memory_tree_db_path)
    await store.init_schema()
    await store.create_conversation(title="Conversazione di test")

    response = await client.get("/api/system/data-status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["conversations"] >= 1
    assert body["has_data"] is True


@pytest.mark.asyncio
async def test_data_status_with_only_autofetch_log(
    client: AsyncClient, temp_data_dir: Path
) -> None:
    """Anche il solo log Auto-Fetch conta come dato (catch review codex)."""
    (temp_data_dir / "autofetch_activity.jsonl").write_text("{}\n", encoding="utf-8")
    response = await client.get("/api/system/data-status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["has_data"] is True


@pytest.mark.asyncio
async def test_reset_data_wrong_confirm_returns_400(
    client: AsyncClient, temp_data_dir: Path
) -> None:
    """confirm diverso da 'RESET' -> 400, nessuna cancellazione."""
    marker = temp_data_dir / "marker.txt"
    marker.write_text("non cancellarmi", encoding="utf-8")

    response = await client.post("/api/system/reset-data", json={"confirm": "nope"})
    assert response.status_code == 400, response.text
    assert marker.exists()  # niente e' stato cancellato


@pytest.mark.asyncio
async def test_reset_data_wipes_and_is_idempotent(client: AsyncClient, temp_data_dir: Path) -> None:
    """confirm='RESET' cancella il contenuto di data_dir e lo ricrea vuoto.

    Doppia chiamata: la seconda ritorna comunque 200 (idempotente).
    """
    # Popola data_dir: una conversation reale + un file marker.
    settings = get_settings()
    store = get_store(settings.memory_tree_db_path)
    await store.init_schema()
    await store.create_conversation(title="Da cancellare")
    (temp_data_dir / "marker.txt").write_text("bye", encoding="utf-8")

    # Primo reset
    response = await client.post("/api/system/reset-data", json={"confirm": "RESET"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert isinstance(body["deleted"], list)
    assert len(body["deleted"]) >= 1
    # data_dir ricreata vuota
    assert temp_data_dir.exists()
    assert list(temp_data_dir.iterdir()) == []

    # Dopo il reset non ci sono piu' dati
    status_after = await client.get("/api/system/data-status")
    assert status_after.status_code == 200, status_after.text
    assert status_after.json()["has_data"] is False

    # Secondo reset: idempotente, 200 anche con data_dir gia' vuota
    response2 = await client.post("/api/system/reset-data", json={"confirm": "RESET"})
    assert response2.status_code == 200, response2.text
    assert response2.json()["ok"] is True


@pytest.mark.asyncio
async def test_reset_data_requires_confirm_field(client: AsyncClient, temp_data_dir: Path) -> None:
    """Body senza il campo confirm -> 422 (validazione Pydantic)."""
    response = await client.post("/api/system/reset-data", json={})
    assert response.status_code == 422, response.text
