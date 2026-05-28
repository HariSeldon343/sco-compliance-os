"""Pytest wrapper per autotest E2E user journey.

Invocabile via: `uv run pytest backend/tests/autotest_e2e/ -v -s --tb=short`

Le fixture sono asincrone (pytest-asyncio). Backend live richiesto su 7800.

Per CI: se backend non raggiungibile, tutti i test sono auto-skipped.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

try:
    from sco_compliance_os.backend.tests.autotest_e2e.test_user_journey import (  # type: ignore[import-not-found]
        DEFAULT_BACKEND_URL,
        DEFAULT_USER_DATA_DIR,
        DEFAULT_VAULT_PATH,
        JourneyReport,
        run_user_journey,
        step_01_health_check,
        step_02_license_status,
        step_03_onboarding_status,
    )
except ModuleNotFoundError:  # pragma: no cover - ambiente test minimal
    pytest.skip(
        "Modulo autotest E2E non disponibile (installazione minimal)",
        allow_module_level=True,
    )

# Permetti override via env
BACKEND_URL = os.environ.get("SCO_AUTOTEST_BACKEND_URL", DEFAULT_BACKEND_URL)
VAULT_PATH = os.environ.get("SCO_AUTOTEST_VAULT_PATH", DEFAULT_VAULT_PATH)
USER_DATA_DIR = Path(os.environ.get("SCO_AUTOTEST_USER_DATA_DIR", str(DEFAULT_USER_DATA_DIR)))
SKIP_LLM = os.environ.get("SCO_AUTOTEST_SKIP_LLM", "1") == "1"


async def _backend_available() -> bool:
    """Check rapido backend health."""
    try:
        async with httpx.AsyncClient(base_url=BACKEND_URL) as client:
            r = await client.get("/health", timeout=2.0)
            return r.status_code == 200
    except Exception:
        return False


@pytest.fixture
async def autotest_backend_available() -> bool:
    """Fixture skip-on-fail se backend non raggiungibile."""
    available = await _backend_available()
    if not available:
        pytest.skip(f"Backend {BACKEND_URL} non raggiungibile - skip autotest E2E")
    return available


@pytest.mark.asyncio
async def test_e2e_health(autotest_backend_available: bool) -> None:
    """Step 1: backend /health PASS."""
    async with httpx.AsyncClient(base_url=BACKEND_URL) as client:
        result = await step_01_health_check(client)
    assert result.status == "PASS", (
        f"Health check FAILED: {result.error_message} | details={result.details}"
    )


@pytest.mark.asyncio
async def test_e2e_license(autotest_backend_available: bool) -> None:
    """Step 2: license valid."""
    async with httpx.AsyncClient(base_url=BACKEND_URL) as client:
        result = await step_02_license_status(client)
    assert result.status == "PASS", (
        f"License invalid: {result.error_message} | details={result.details}"
    )


@pytest.mark.asyncio
async def test_e2e_onboarding(autotest_backend_available: bool) -> None:
    """Step 3: onboarding completo."""
    async with httpx.AsyncClient(base_url=BACKEND_URL) as client:
        result = await step_03_onboarding_status(client)
    assert result.status == "PASS", (
        f"Onboarding incomplete: {result.error_message} | details={result.details}"
    )


@pytest.mark.asyncio
async def test_e2e_full_journey(autotest_backend_available: bool) -> None:
    """Esegue il journey completo + log report markdown su FAIL."""
    report: JourneyReport = await run_user_journey(
        backend_url=BACKEND_URL,
        vault_path=VAULT_PATH,
        user_data_dir=USER_DATA_DIR,
        do_backup=False,  # CI non fa backup
        skip_llm_stream=SKIP_LLM,
    )
    # Stampa il report markdown per visibilita' (anche su PASS).
    print("\n\n" + report.to_markdown() + "\n")

    # Required PASS: step 1+2+3 (env baseline). Step 4+ best-effort.
    required = [s for s in report.steps if s.step_num in (1, 2, 3)]
    fails = [s for s in required if s.status == "FAIL"]
    assert not fails, (
        f"Required steps FAILED: {[(s.step_num, s.name, s.error_message) for s in fails]}"
    )
