"""License activation flow: status → activate → status post-activate.

Mock strategy: pytest-httpx intercetta chiamate a SaaS proxy
sco-saas-claude.vercel.app/api/v1/license/validate.

Conv. 47 enforcement: backend single source of truth per status.
Frontend NON hardcoda, legge da /api/license/status.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock


@pytest.mark.asyncio
async def test_license_status_initial_unknown(client: AsyncClient) -> None:
    """GET /api/license/status senza activate → status=unknown is_valid=False."""
    response = await client.get("/api/license/status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "unknown"
    assert body["is_valid"] is False
    assert "Nessuna license attivata" in body["error_message"]


@pytest.mark.asyncio
async def test_license_activate_valid(
    client: AsyncClient,
    httpx_mock: HTTPXMock,
    mock_license_valid_payload: dict[str, Any],
) -> None:
    """POST /api/license/activate con SaaS mock valid → 200 + is_valid=True."""
    # Mock SaaS validate endpoint
    httpx_mock.add_response(
        url="https://sco-saas-claude.vercel.app/api/v1/license/validate",
        method="POST",
        json=mock_license_valid_payload,
        status_code=200,
    )

    payload = {
        "email": "test@sco.it",
        "license_key": "SCO-TEST-ACTIVATE-001",
    }
    response = await client.post("/api/license/activate", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_valid"] is True
    assert body["status"] == "valid"
    assert body["plan"] == "enterprise"
    assert body["tenant_id"] == "tnt_test_integration_001"


@pytest.mark.asyncio
async def test_license_activate_invalid(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    """POST activate con SaaS 401 → status=invalid is_valid=False."""
    httpx_mock.add_response(
        url="https://sco-saas-claude.vercel.app/api/v1/license/validate",
        method="POST",
        json={"status": "invalid", "error": "license_key not found"},
        status_code=401,
    )

    response = await client.post(
        "/api/license/activate",
        json={"email": "wrong@example.com", "license_key": "WRONG-KEY-XXX"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_valid"] is False
    assert body["status"] == "invalid"


@pytest.mark.asyncio
async def test_license_status_post_activate_cached(
    client: AsyncClient,
    httpx_mock: HTTPXMock,
    mock_license_valid_payload: dict[str, Any],
) -> None:
    """Activate poi /status → cache hit → no second SaaS call.

    Conv. 47 + SCO single source of truth:
    il cliente NON spamma il SaaS se la cache è fresca (<24h).
    """
    httpx_mock.add_response(
        url="https://sco-saas-claude.vercel.app/api/v1/license/validate",
        method="POST",
        json=mock_license_valid_payload,
        status_code=200,
    )
    # Activate
    activate_resp = await client.post(
        "/api/license/activate",
        json={"email": "test@sco.it", "license_key": "SCO-CACHE-TEST"},
    )
    assert activate_resp.status_code == 200

    # Status (cache TTL 24h dovrebbe servire dalla cache)
    status_resp = await client.get("/api/license/status")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["is_valid"] is True
    assert body["status"] == "valid"


@pytest.mark.asyncio
async def test_license_logout(
    client: AsyncClient,
    httpx_mock: HTTPXMock,
    mock_license_valid_payload: dict[str, Any],
) -> None:
    """Activate poi logout → status torna unknown."""
    httpx_mock.add_response(
        url="https://sco-saas-claude.vercel.app/api/v1/license/validate",
        method="POST",
        json=mock_license_valid_payload,
        status_code=200,
    )
    await client.post(
        "/api/license/activate",
        json={"email": "logout@sco.it", "license_key": "SCO-LOGOUT-TEST"},
    )

    logout = await client.post("/api/license/logout")
    assert logout.status_code == 200

    status = await client.get("/api/license/status")
    body = status.json()
    assert body["status"] == "unknown"
    assert body["is_valid"] is False
