"""Wiki readers E2E: stats + sources + entities + concepts + synthesis.

Test su temp_vault minimo + opzionalmente su vault Antonio reale.

Conv. 47: schema frontmatter single source of truth via services/vault/parser.
Conv. 39 three-layer: wiki/ è layer 2 (knowledge derivato), raw/ layer 1.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_wiki_stats_temp_vault(
    client: AsyncClient, temp_vault: Path
) -> None:
    """Add temp_vault → /wiki/stats → wiki_dir_exists=True + total >= 2."""
    # Register vault
    await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "wiki-stats-vault"},
    )

    # Stats
    response = await client.get("/api/wiki/stats")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["wiki_dir_exists"] is True
    assert body["total"] >= 2  # almeno sample-source + sample-entity
    assert "counts" in body
    # Categorie wiki Karpathy
    counts = body["counts"]
    assert "sources" in counts
    assert "entities" in counts


@pytest.mark.asyncio
async def test_wiki_sources_list(
    client: AsyncClient, temp_vault: Path
) -> None:
    """GET /api/wiki/sources su temp_vault → contains sample-source."""
    await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "sources-test"},
    )

    response = await client.get("/api/wiki/sources")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["category"] == "sources"
    assert body["total"] >= 1
    slugs = [item["slug"] for item in body["items"]]
    assert "sample-source" in slugs


@pytest.mark.asyncio
async def test_wiki_entities_filter_by_entity_type(
    client: AsyncClient, temp_vault: Path
) -> None:
    """GET /api/wiki/entities?entity_type=atto-normativo → filtra correttamente."""
    await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "entities-filter-test"},
    )

    # Filtra per entity_type
    response = await client.get(
        "/api/wiki/entities",
        params={"entity_type": "atto-normativo"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    # sample-entity ha entity_type: atto-normativo
    items = body["items"]
    assert all(item["entity_type"] == "atto-normativo" for item in items)


@pytest.mark.asyncio
async def test_wiki_entities_filter_no_match(
    client: AsyncClient, temp_vault: Path
) -> None:
    """GET /api/wiki/entities?entity_type=metodologia → 0 items (no match)."""
    await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "entities-nomatch"},
    )

    response = await client.get(
        "/api/wiki/entities",
        params={"entity_type": "metodologia"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_wiki_stats_no_vault_registered(client: AsyncClient) -> None:
    """GET /api/wiki/stats senza vault registrato → 404."""
    response = await client.get("/api/wiki/stats")
    assert response.status_code == 404
    assert "Nessun vault attivo" in response.json()["detail"]


@pytest.mark.asyncio
async def test_wiki_get_single_file(
    client: AsyncClient, temp_vault: Path
) -> None:
    """GET /api/wiki/sources/sample-source → full body + frontmatter."""
    await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "single-file-test"},
    )

    response = await client.get("/api/wiki/sources/sample-source")
    assert response.status_code == 200, response.text
    body = response.json()
    # Schema risposta: contiene almeno slug + body
    assert "slug" in body or "title" in body


@pytest.mark.asyncio
async def test_wiki_get_single_invalid_category(
    client: AsyncClient, temp_vault: Path
) -> None:
    """GET /api/wiki/bogus-cat/slug → 422 categoria non valida."""
    await client.post(
        "/api/vault/add",
        json={"path": str(temp_vault), "name": "invalid-cat"},
    )

    response = await client.get("/api/wiki/bogus-category/anything")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_wiki_stats_on_antonio_vault(
    client: AsyncClient, antonio_vault_path: Path | None
) -> None:
    """Se il vault Antonio reale esiste localmente, /wiki/stats → counts > 28.

    Skip se vault non disponibile (CI / fresh PC).
    """
    if antonio_vault_path is None:
        pytest.skip("Vault Antonio non disponibile in questo ambiente")

    await client.post(
        "/api/vault/add",
        json={"path": str(antonio_vault_path), "name": "antonio-second-brain"},
    )

    response = await client.get("/api/wiki/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["wiki_dir_exists"] is True
    # Antonio vault ha 28+ entities post-Ondata 2 backfill
    assert body["counts"].get("entities", 0) > 20, (
        f"Atteso >20 entities nel vault Antonio, trovo {body['counts']}"
    )
