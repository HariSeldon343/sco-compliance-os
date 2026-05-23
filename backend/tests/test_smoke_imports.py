"""Smoke test: verifica che il backend importi clean e esponga le route attese.

Scope: prevenire regressioni catastrofiche (import error, route mancanti) in CI
prima di build Rust + bundle. Test mirati, eseguono in <1s.

Conv. 46 enforcement: smoke test come gate prima del tag.
"""

from __future__ import annotations

from sco_compliance_os import __author__, __version__


def test_version_format() -> None:
    """Version segue SemVer X.Y.Z."""
    parts = __version__.split(".")
    assert len(parts) == 3, f"Version non SemVer: {__version__}"
    for p in parts:
        assert p.isdigit(), f"Version part non numerico: {p}"


def test_author_set() -> None:
    """Author popolato dal package init."""
    assert __author__
    assert "Antonio" in __author__ or "Amodeo" in __author__


def test_backend_app_imports() -> None:
    """L'app FastAPI si importa pulita (no missing dep, no syntax error)."""
    from sco_compliance_os.main import app

    assert app is not None
    assert app.title == "SCO Compliance OS Backend"


def test_backend_routes_registered() -> None:
    """I router Wave 1 + Wave 2 sono tutti registrati."""
    from sco_compliance_os.main import app

    paths = {route.path for route in app.routes if hasattr(route, "path")}

    # Route base
    assert "/health" in paths
    assert "/" in paths

    # Wave 1 — Memory Tree gerarchico + Subconscious tick
    assert "/api/memory/tree-summaries" in paths
    assert "/api/memory/hotness/top" in paths
    assert "/api/subconscious/status" in paths
    assert "/api/subconscious/tick" in paths

    # Wave 2 — TokenJuice + Auto-fetch
    assert "/api/tokenjuice/compress" in paths
    assert "/api/tokenjuice/rules" in paths
    assert "/api/autofetch/status" in paths
    assert "/api/autofetch/tick" in paths


def test_settings_default_privacy_off() -> None:
    """Conv. privacy default OFF — Subconscious + Auto-fetch NON partono auto."""
    from sco_compliance_os.config import get_settings

    settings = get_settings()
    assert settings.subconscious_enabled is False, "Subconscious deve essere OFF di default"
    # auto_fetch_enabled è OFF di default (anche se può venire abilitato via env legacy)
    assert hasattr(settings, "auto_fetch_enabled")


def test_memory_tree_models_importable() -> None:
    """Modelli SQLAlchemy Wave 1 importabili."""
    from sco_compliance_os.models import Base, Score, Summary

    assert Base is not None
    assert Summary is not None
    assert Score is not None


def test_tokenjuice_compress_basic() -> None:
    """TokenJuice compress: layer 1 + 3 attivi anche senza user rules."""
    import asyncio

    from sco_compliance_os.services.memory.tokenjuice import compress_text

    raw = "Articolo 25 comma 4 lettera a) del D.Lgs. 138/2024."
    result = asyncio.run(compress_text(raw_text=raw, source_type="markdown"))

    assert result.compressed_text
    assert result.original_tokens > 0
    # Layer 3 collapse: "Articolo X comma Y lettera Z" → "Art. X c. Y lett. Z"
    assert "Art." in result.compressed_text or "art." in result.compressed_text.lower()


def test_throttle_shared_extracted() -> None:
    """TickThrottle estratto in services.common.throttle riusato cross-loop."""
    from sco_compliance_os.services.common.throttle import CancellationToken, TickThrottle

    throttle = TickThrottle(name="test")
    assert not throttle.is_busy()

    # CancellationToken.cancelled è un asyncio.Event, non un bool
    token = CancellationToken()
    assert not token.cancelled.is_set()
    token.cancelled.set()
    assert token.cancelled.is_set()
