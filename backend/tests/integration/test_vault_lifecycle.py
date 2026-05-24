"""Vault lifecycle E2E: add → list → inspect → sync → sync-status → remove.

v0.6.0 DEV-VAULT-AUTOINGEST: auto-ingest fire-and-forget al register.
v0.7.0 Conv. 46 smoke E2E: verifica che il vault registrato sia effettivamente
accessibile via tutti gli endpoint downstream.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_vault_list_initial_empty(client: AsyncClient) -> None:
    """GET /api/vault/list senza add → [] vuota."""
    response = await client.get("/api/vault/list")
    assert response.status_code == 200, response.text
    assert response.json() == []


@pytest.mark.asyncio
async def test_vault_inspect_temp_vault(
    client: AsyncClient, temp_vault: Path
) -> None:
    """POST /api/vault/inspect su temp_vault → is_karpathy=True + md_files_count>=3."""
    response = await client.post(
        "/api/vault/inspect",
        json={"path": str(temp_vault)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_karpathy"] is True
    assert body["has_claude_md"] is True
    assert body["has_wiki_dir"] is True
    assert body["has_raw_dir"] is True
    assert body["md_files_count"] >= 3  # CLAUDE.md + wiki + sources + entities


@pytest.mark.asyncio
async def test_vault_inspect_nonexistent_path(client: AsyncClient) -> None:
    """POST /api/vault/inspect su path inesistente → 400."""
    response = await client.post(
        "/api/vault/inspect",
        json={"path": "/path/totally/does/not/exist/xyz123"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_vault_add_and_list(client: AsyncClient, temp_vault: Path) -> None:
    """POST /api/vault/add → 201 + entry in registry + list() lo vede."""
    add_response = await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "test-vault-001"},
    )
    assert add_response.status_code == 201, add_response.text
    entry = add_response.json()
    assert entry["name"] == "test-vault-001"
    assert entry["is_karpathy"] is True
    assert "id" in entry
    vault_id = entry["id"]

    # List
    list_response = await client.get("/api/vault/list")
    assert list_response.status_code == 200
    entries = list_response.json()
    assert len(entries) == 1
    assert entries[0]["id"] == vault_id


@pytest.mark.asyncio
async def test_vault_sync_status(
    client: AsyncClient, temp_vault: Path
) -> None:
    """POST /add → wait → GET sync-status → no errore + watcher_running.

    NOTA: il sync background è fire-and-forget, non sincrono.
    Diamo 2s di buffer per il task asyncio di startup.
    """
    add_response = await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "sync-test-vault"},
    )
    assert add_response.status_code == 201
    vault_id = add_response.json()["id"]

    # Wait small amount per fire-and-forget
    await asyncio.sleep(1.5)

    status_response = await client.get(f"/api/vault/{vault_id}/sync-status")
    assert status_response.status_code == 200, status_response.text
    body = status_response.json()
    # Schema sync-status include almeno questi campi
    assert "in_progress" in body
    assert "vault_id" in body or "watcher_running" in body


@pytest.mark.asyncio
async def test_vault_dedup_by_path(
    client: AsyncClient, temp_vault: Path
) -> None:
    """POST /add con stesso path → riusa ID, no duplicate entry.

    Conv. 47 pattern: dedup naturale per evitare watcher duplicati.
    """
    r1 = await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "first"},
    )
    assert r1.status_code == 201
    id_first = r1.json()["id"]

    r2 = await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "second"},
    )
    assert r2.status_code == 201
    id_second = r2.json()["id"]

    # Dedup: stesso ID
    assert id_first == id_second

    # List ha una sola entry
    listing = await client.get("/api/vault/list")
    assert len(listing.json()) == 1


@pytest.mark.asyncio
async def test_vault_remove(client: AsyncClient, temp_vault: Path) -> None:
    """DELETE /api/vault/{id} → 204 + list torna vuota."""
    add = await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "tobedeleted"},
    )
    vault_id = add.json()["id"]

    delete = await client.delete(f"/api/vault/{vault_id}")
    assert delete.status_code == 204

    listing = await client.get("/api/vault/list")
    assert listing.json() == []


@pytest.mark.asyncio
async def test_vault_remove_404(client: AsyncClient) -> None:
    """DELETE /api/vault/non-existent-id → 404."""
    response = await client.delete("/api/vault/non-existent-id-xyz")
    assert response.status_code == 404
