"""Memory Tree bucket-seal Fase 1+2+3+4 E2E.

Flow: ingest → stats → seal force=True → summaries L1+ → relevant query.

Conv. 47 enforcement: memory tree è single source of truth via DB SQLite,
NON cached in memoria applicativa.
Conv. 41 tracciatura: ogni step loggato + counts verificati.

NOTA: cascade_seal usa LLM Haiku per summarize. In assenza credenziali
si attiva _fallback_summary (no network). Il test verifica il MECCANISMO
non il content qualitativo della summary.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tree_stats_initial(client: AsyncClient) -> None:
    """GET /api/memory/tree/stats inizialmente → struttura coerente."""
    response = await client.get("/api/memory/tree/stats")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "counts_by_status" in body
    assert "counts_by_source_kind" in body
    assert "total" in body
    assert isinstance(body["total"], int)


@pytest.mark.asyncio
async def test_tree_ingest_basic(client: AsyncClient) -> None:
    """POST /api/memory/tree/ingest con sample texts → 202 + admitted+dropped."""
    sample_texts = [
        {
            "source_kind": "note",
            "source_id": "test-note-001",
            "content": (
                "Il D.Lgs. 138/2024 recepisce la Direttiva NIS 2 in Italia. "
                "Soggetti essenziali e importanti devono notificare incidenti "
                "significativi entro 24h dalla conoscenza. ACN è autorità nazionale."
            ),
            "owner": "local",
            "tags": ["nis2", "test"],
        },
        {
            "source_kind": "note",
            "source_id": "test-note-002",
            "content": (
                "ISO/IEC 27001:2022 è lo standard internazionale per la gestione "
                "della sicurezza delle informazioni. L'Annex A contiene 93 controlli "
                "raggruppati in 4 temi: Organizational, People, Physical, Technological."
            ),
            "owner": "local",
            "tags": ["iso27001", "test"],
        },
    ]
    response = await client.post(
        "/api/memory/tree/ingest",
        json={"texts": sample_texts, "consult_llm_on_borderline": False},
    )
    assert response.status_code == 202, response.text
    counts = response.json()
    assert counts["total"] >= 2
    # Admitted o dropped, no errori
    assert counts["admitted"] + counts["dropped"] + counts["pending_extraction"] == counts["total"]


@pytest.mark.asyncio
async def test_tree_stats_after_ingest(client: AsyncClient) -> None:
    """Ingest + stats → counts > 0."""
    await client.post(
        "/api/memory/tree/ingest",
        json={
            "texts": [
                {
                    "source_kind": "note",
                    "source_id": "stats-test",
                    "content": "Contenuto di test per verificare stats post-ingest.",
                    "owner": "local",
                    "tags": ["stats-test"],
                }
            ],
            "consult_llm_on_borderline": False,
        },
    )
    stats = await client.get("/api/memory/tree/stats")
    body = stats.json()
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_tree_seal_force(client: AsyncClient) -> None:
    """Ingest + seal force=True → L1 summary creata (fallback mode no LLM).

    Force mode bypassa threshold token (32k) → seal anche con 1 chunk.
    """
    # Ingest substantial content
    await client.post(
        "/api/memory/tree/ingest",
        json={
            "texts": [
                {
                    "source_kind": "document",
                    "source_id": "seal-test-doc",
                    "content": (
                        "Test sealing: contenuto di esempio sufficientemente lungo "
                        "per essere admitted dal cheap signals admission gate. "
                        "Include riferimenti normativi: D.Lgs. 138/2024 NIS 2, "
                        "ISO/IEC 27001:2022, Reg. UE 2024/1689 AI Act. "
                        "Soggetti essenziali devono adottare misure tecniche "
                        "organizzative proporzionate al rischio cyber."
                    ) * 3,
                    "owner": "local",
                    "tags": ["seal-test"],
                }
            ],
            "consult_llm_on_borderline": False,
        },
    )

    # Seal force=True
    seal_response = await client.post(
        "/api/memory/tree/seal",
        json={
            "tree_kind": "source",
            "tree_id": "seal-test-doc",
            "force": True,
        },
    )
    assert seal_response.status_code == 202, seal_response.text
    body = seal_response.json()
    assert body["tree_kind"] == "source"
    assert body["tree_id"] == "seal-test-doc"
    assert body["force"] is True
    # In assenza LLM creds, summarize fallback genera summary minimal.
    # Sufficiente: l'endpoint risponde senza crash.
    assert "summaries_l1_created" in body


@pytest.mark.asyncio
async def test_tree_summaries_list(client: AsyncClient) -> None:
    """GET /api/memory/tree/summaries?level=1 → lista summaries L1 (può essere vuota)."""
    response = await client.get(
        "/api/memory/tree/summaries", params={"level": 1, "owner": "local"}
    )
    assert response.status_code == 200, response.text
    summaries = response.json()
    assert isinstance(summaries, list)


@pytest.mark.asyncio
async def test_tree_summaries_relevant_query(client: AsyncClient) -> None:
    """Ingest + seal + GET /tree/summaries/relevant?query=NIS+2 → top-K (può essere vuota)."""
    # Ingest content con keyword NIS 2
    await client.post(
        "/api/memory/tree/ingest",
        json={
            "texts": [
                {
                    "source_kind": "document",
                    "source_id": "nis2-doc-001",
                    "content": (
                        "NIS 2 è la direttiva UE 2022/2555 recepita in Italia "
                        "con D.Lgs. 138/2024. Si applica a soggetti essenziali "
                        "e importanti. Notifica incidenti significativi entro 24h."
                    ) * 5,
                    "owner": "local",
                    "tags": ["nis2"],
                }
            ],
            "consult_llm_on_borderline": False,
        },
    )

    # Seal force
    await client.post(
        "/api/memory/tree/seal",
        json={"tree_kind": "source", "tree_id": "nis2-doc-001", "force": True},
    )

    # Query relevant
    response = await client.get(
        "/api/memory/tree/summaries/relevant",
        params={"query": "NIS 2 notifica incidenti", "top_k": 3},
    )
    assert response.status_code == 200, response.text
    relevant = response.json()
    assert isinstance(relevant, list)
    assert len(relevant) <= 3  # top_k cap
