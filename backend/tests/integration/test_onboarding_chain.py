"""Onboarding endpoint chain: status → eula → privacy → demo → tutorial.

Conv. 47 enforcement: backend espone current_eula_version /
current_privacy_version / current_demo_version. Frontend deve leggerli
da qui (single source of truth). MAI hardcoded.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_onboarding_status_initial(client: AsyncClient) -> None:
    """GET /api/onboarding/status senza accept → tutto False + version backend."""
    response = await client.get("/api/onboarding/status")
    assert response.status_code == 200, response.text
    body = response.json()

    # State iniziale: nulla accettato
    assert body["eula_accepted"] is False
    assert body["privacy_accepted"] is False
    assert body["demo_seen"] is False
    assert body["tutorial_done"] is False

    # Version Conv. 47 (backend single source of truth)
    assert body["current_eula_version"] == "1.0"
    assert body["current_privacy_version"] == "1.0"
    assert body["current_demo_version"] == "1.0"


@pytest.mark.asyncio
async def test_eula_accept(client: AsyncClient) -> None:
    """POST /api/onboarding/eula/accept con version → eula_accepted=True."""
    response = await client.post(
        "/api/onboarding/eula/accept",
        json={"version": "1.0"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["eula_accepted"] is True
    assert body["eula_accepted_version"] == "1.0"
    assert body["eula_accepted_at"] is not None


@pytest.mark.asyncio
async def test_privacy_accept(client: AsyncClient) -> None:
    """POST /api/onboarding/privacy/accept con version → privacy_accepted=True."""
    response = await client.post(
        "/api/onboarding/privacy/accept",
        json={"version": "1.0"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["privacy_accepted"] is True
    assert body["privacy_accepted_version"] == "1.0"


@pytest.mark.asyncio
async def test_demo_seen(client: AsyncClient) -> None:
    """POST /api/onboarding/demo/seen con version → demo_seen=True."""
    response = await client.post(
        "/api/onboarding/demo/seen",
        json={"version": "1.0"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["demo_seen"] is True
    assert body["demo_seen_version"] == "1.0"


@pytest.mark.asyncio
async def test_tutorial_done(client: AsyncClient) -> None:
    """POST /api/onboarding/tutorial/done → tutorial_done=True."""
    response = await client.post("/api/onboarding/tutorial/done")
    assert response.status_code == 200
    body = response.json()
    assert body["tutorial_done"] is True
    assert body["tutorial_done_at"] is not None


@pytest.mark.asyncio
async def test_onboarding_full_chain(client: AsyncClient) -> None:
    """E2E completo: EULA → Privacy → Demo → Tutorial → status finale tutto True."""
    # Chain
    await client.post("/api/onboarding/eula/accept", json={"version": "1.0"})
    await client.post("/api/onboarding/privacy/accept", json={"version": "1.0"})
    await client.post("/api/onboarding/demo/seen", json={"version": "1.0"})
    await client.post("/api/onboarding/tutorial/done")

    # Status finale
    response = await client.get("/api/onboarding/status")
    body = response.json()
    assert body["eula_accepted"] is True
    assert body["privacy_accepted"] is True
    assert body["demo_seen"] is True
    assert body["tutorial_done"] is True


@pytest.mark.asyncio
async def test_eula_accept_old_version_then_new(client: AsyncClient) -> None:
    """Conv. 47 simulation: version backend bump → re-accept richiesto.

    User accetta 1.0, backend ora a 1.0 → ok.
    Se backend bumpasse a 2.0, eula_accepted_version=1.0 != current_eula_version=2.0
    → frontend mostrerebbe EULA di nuovo (logica nel client UI, NON backend).
    Qui verifichiamo solo che il backend espone entrambi i campi.
    """
    await client.post("/api/onboarding/eula/accept", json={"version": "1.0"})

    response = await client.get("/api/onboarding/status")
    body = response.json()
    # Campi entrambi presenti per matching frontend Conv. 47
    assert body["eula_accepted_version"] == "1.0"
    assert body["current_eula_version"] == "1.0"
