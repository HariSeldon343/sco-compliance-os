"""Smoke base: health endpoint + openapi + count routes registrate.

Conv. 46 enforcement: il primo checkpoint dello smoke E2E.
Se questo fallisce, tutto il resto non parte.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    """GET /health → 200 + {status: ok, version: X.Y.Z}."""
    response = await client.get("/health")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "sco-compliance-os-backend"
    assert "." in body["version"]  # SemVer


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient) -> None:
    """GET / → 200 + welcome message."""
    response = await client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "SCO Compliance OS Backend"
    assert body["docs"] == "/docs"


@pytest.mark.asyncio
async def test_openapi_json_loads(client: AsyncClient) -> None:
    """GET /openapi.json → 200 + valid OpenAPI 3.x spec."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"] == "SCO Compliance OS Backend"


@pytest.mark.asyncio
async def test_route_count_above_threshold(app: Any) -> None:
    """v0.6.0 ha registrate >40 route. Smoke regression check.

    Pattern Conv. 46: count baseline per intercettare router missing.
    """
    paths = [getattr(r, "path", "") for r in app.routes]
    paths = [p for p in paths if p]
    assert len(paths) > 40, f"Solo {len(paths)} route registrate: {paths[:10]}"


@pytest.mark.asyncio
async def test_critical_routes_present(app: Any) -> None:
    """Smoke: tutti i router critici v0.6.0 registrati.

    Lista esplicita dei path che il frontend chiama in produzione.
    Se uno manca, l'app desktop fallisce runtime.
    """
    paths = {getattr(r, "path", "") for r in app.routes}

    critical_paths = [
        # Health + root
        "/health",
        "/",
        # License (Conv. 47 single source of truth version)
        "/api/license/status",
        "/api/license/activate",
        # Onboarding (Conv. 47 single source of truth version)
        "/api/onboarding/status",
        "/api/onboarding/eula/accept",
        "/api/onboarding/privacy/accept",
        "/api/onboarding/demo/seen",
        "/api/onboarding/tutorial/done",
        # Vault auto-ingest v0.6.0
        "/api/vault/add",
        "/api/vault/list",
        "/api/vault/inspect",
        # Chat streaming Conv. 48 single source of truth widget
        "/api/chat/stream",
        "/api/chat/conversations",
        # Memory tree bucket-seal v0.6.0
        "/api/memory/tree/ingest",
        "/api/memory/tree/stats",
        "/api/memory/tree/seal",
        # Wiki readers v0.6.0
        "/api/wiki/stats",
        "/api/wiki/sources",
        "/api/wiki/entities",
    ]
    missing = [p for p in critical_paths if p not in paths]
    assert not missing, f"Route critiche mancanti: {missing}"
