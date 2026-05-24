"""Shared fixtures for integration tests.

Pattern Conv. 41 tracciatura: ogni fixture documenta scopo + isolamento.
Pattern Conv. 44 lesson 1: NO uvicorn run, NO real network. ASGITransport
in-memory + httpx-mock per stub SaaS.
Pattern Conv. 47 single source of truth: temp_data_dir override Settings,
nessun side-effect su filesystem utente reale.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ---------- Env tweaks PRIMA degli import del backend ----------

# Forza dev mode privacy-safe (no auto-fetch, no subconscious) per i test.
os.environ.setdefault("SCO_SEAL_SCHEDULER_ENABLED", "0")
os.environ.setdefault("SCO_AUTO_FETCH_ENABLED", "0")
# Disabilita Sentry per test.
os.environ.pop("SENTRY_DSN", None)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Force asyncio backend (no trio)."""
    return "asyncio"


@pytest.fixture
def temp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Crea data_dir isolata per test + override Settings + reset singleton.

    Resetta:
        - get_settings() lru_cache
        - get_license_client() lru_cache
        - core.store._store singleton (fresh DB per test)
        - HOME env var (per license cache file)
    """
    data_dir = tmp_path / "sco-compliance-os-data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Override HOME (license cache path = HOME/.sco-compliance-os/license-cache.json)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows

    # Forza Settings.data_dir
    from sco_compliance_os.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    monkeypatch.setattr(settings, "data_dir", data_dir)

    # Reset license client singleton
    from sco_compliance_os.services.license.client import get_license_client

    get_license_client.cache_clear()

    # Reset core store singleton (modulo-level _store)
    import sco_compliance_os.core.store as store_module

    store_module._store = None

    return data_dir


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """Crea un vault SCO minimo per test (CLAUDE.md + wiki/ + raw/ + Contesto/).

    Struttura:
        vault/
            CLAUDE.md              (marker SCO)
            wiki/
                _index.md
                sources/
                    sample-source.md
                entities/
                    sample-entity.md
                concepts/
                synthesis/
                glossari/
            raw/
                normativa/
            Contesto/
                Macro Contesto.md
            Giornaliero/
            Business/
    """
    vault = tmp_path / "test-vault"
    vault.mkdir()

    # CLAUDE.md (marker SCO)
    (vault / "CLAUDE.md").write_text(
        "# Test Vault SCO\n\nVault di test per integration tests v0.7.0.\n",
        encoding="utf-8",
    )

    # wiki/
    wiki = vault / "wiki"
    for sub in ("sources", "entities", "concepts", "synthesis", "glossari"):
        (wiki / sub).mkdir(parents=True)
    (wiki / "_index.md").write_text("# Wiki\n", encoding="utf-8")

    # wiki/sources/sample-source.md (schema standard B Ondata 4)
    (wiki / "sources" / "sample-source.md").write_text(
        "---\n"
        "type: source\n"
        'title: "Sample Source Test"\n'
        'ente_emittente: "TEST"\n'
        "data_pubblicazione: 2026\n"
        "data_import_vault: 2026-05-24\n"
        "status: active\n"
        "tags: [source, test]\n"
        "---\n\n"
        "Sample source body per test.\n",
        encoding="utf-8",
    )

    # wiki/entities/sample-entity.md (atto-normativo cybersicurezza)
    (wiki / "entities" / "sample-entity.md").write_text(
        "---\n"
        "type: entity\n"
        "entity_type: atto-normativo\n"
        "entity_subtype: decreto-legislativo\n"
        "ambito_canonico: cybersicurezza\n"
        'title: "Sample Atto Normativo Test"\n'
        "status: active\n"
        "tags: [entity, test, nis2]\n"
        "---\n\n"
        "Sample entity body per test.\n",
        encoding="utf-8",
    )

    # raw/
    (vault / "raw" / "normativa").mkdir(parents=True)
    (vault / "raw" / "normativa" / ".gitkeep").write_text("", encoding="utf-8")

    # Contesto/
    (vault / "Contesto").mkdir()
    (vault / "Contesto" / "Macro Contesto.md").write_text(
        "# Macro Contesto Test\n", encoding="utf-8"
    )

    # Giornaliero/ + Business/ (vuoti, presenti per matching struttura)
    (vault / "Giornaliero").mkdir()
    (vault / "Business").mkdir()

    return vault


@pytest_asyncio.fixture
async def app(temp_data_dir: Path) -> AsyncIterator[Any]:
    """FastAPI app instance con lifespan startup/shutdown.

    Auto-fetch + subconscious + seal scheduler disabilitati via env.
    """
    # Import deve venire DOPO temp_data_dir setup
    from sco_compliance_os.main import create_app

    application = create_app()
    yield application


@pytest_asyncio.fixture
async def client(app: Any) -> AsyncIterator[AsyncClient]:
    """HTTPX AsyncClient con ASGITransport (no real network).

    Esegue lifespan completo via LifespanManager pattern.
    """
    # Pattern lifespan manual: usa ASGITransport che richiama lifespan.
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        timeout=30.0,
    ) as ac:
        # Trigger lifespan startup
        async with app.router.lifespan_context(app):
            yield ac


# ---------- License mock helpers ----------


@pytest.fixture
def mock_license_valid_payload() -> dict[str, Any]:
    """Payload SaaS validate response per license VALID."""
    return {
        "status": "valid",
        "tenant_id": "tnt_test_integration_001",
        "expires_at": "2027-12-31T23:59:59Z",
        "plan": "enterprise",
    }


@pytest.fixture
def saved_active_license(
    temp_data_dir: Path, mock_license_valid_payload: dict[str, Any]
) -> dict[str, str]:
    """Salva active-license.json valido nel temp_data_dir.

    Simulate post-activate state per test che richiedono license attiva.
    Returns: dict con email + license_key per riuso nei test.
    """
    email = "test@sco.it"
    license_key = "SCO-TEST-INTEGRATION-001"

    from sco_compliance_os.services.license.models import (
        LicenseStatus,
        LicenseValidationResult,
    )

    result = LicenseValidationResult(
        status=LicenseStatus.VALID,
        email=email,
        license_key_hash="abc123def456",
        tenant_id=mock_license_valid_payload["tenant_id"],
        expires_at=mock_license_valid_payload["expires_at"],
        plan=mock_license_valid_payload["plan"],
    )
    payload = {
        "email": email,
        "license_key": license_key,
        "validation_result": result.to_dict(),
        "activated_at": "2026-05-24T10:00:00+00:00",
    }
    (temp_data_dir / "active-license.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return {"email": email, "license_key": license_key}


# ---------- Anthropic SDK mock helpers ----------


@pytest.fixture
def mock_no_anthropic_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forza assenza credenziali Anthropic + SaaS → agent_runner fallback error.

    Usato dai test chat_stream per evitare LLM calls reali.
    Conv. 41 enforcement: il fallback emette evento `error` chiaro,
    NON crasha né tenta connessione reale.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("LICENSE_KEY", "")


# ---------- Antonio vault reference (opzionale) ----------


@pytest.fixture
def antonio_vault_path() -> Path | None:
    """Path Second Brain vault Antonio se esiste, altrimenti None.

    Usato dal test wiki endpoints come dataset reale opzionale.
    Skip-friendly: i test devono gestire il None case.
    """
    candidates = [
        Path("C:/Users/aoedo/Desktop/Second Brain"),
        Path.home() / "Desktop" / "Second Brain",
    ]
    for p in candidates:
        if p.exists() and (p / "wiki").exists():
            return p
    return None


# ---------- Async event loop policy (Windows ProactorEventLoop) ----------


@pytest.fixture(scope="session", autouse=True)
def event_loop_policy() -> Iterator[None]:
    """Windows: usa ProactorEventLoop per subprocess + httpx compat."""
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    yield
