"""Configurazione runtime del backend SCO Compliance OS.

Settings caricate da variabili d'ambiente (file .env via python-dotenv).
Usa pydantic-settings BaseSettings per validazione tipata.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings centrali del backend, lette da env / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- Anthropic API + modelli -----
    anthropic_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="API key per Anthropic Claude.",
    )
    model_default: str = Field(
        default="claude-opus-4-7",
        description=(
            "Modello predefinito per chat e agent reasoning. "
            "v0.12.0 (25/05/2026): bumped da claude-sonnet-4-6 a claude-opus-4-7 "
            "per allineare desktop app al SaaS default (schema.ts:209). "
            "Overridabile per tenant via SaaS /api/v1/tenant/me/llm-config "
            "(tenants.model_slug + tenant_memberships.model_slug_override). "
            "Per 1M context window: il sistema host dichiara model id nominale "
            "'claude-opus-4-7[1m]' ma l'Anthropic Python SDK accetta solo lo "
            "slug base 'claude-opus-4-7'. Il 1M ctx richiede header beta "
            "'anthropic-beta: context-1m-2025-08-07' (non ancora wirato qui — "
            "carry-over v0.12.1)."
        ),
    )
    model_fast: str = Field(
        default="claude-haiku-4-5-20251001",
        description="Modello veloce per task brevi (routing, summarization).",
    )

    # ----- Server -----
    backend_port: int = Field(
        default=7800,
        ge=1024,
        le=65535,
        description="Porta TCP del backend FastAPI. 7800 per evitare clash con sco-agent-local (7777).",
    )
    backend_host: str = Field(default="127.0.0.1", description="Host bind.")

    # ----- CORS (Conv. 44 lesson 2 — Tauri 2 WebView2 origin) -----
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:1420",
            "http://127.0.0.1:1420",
            "tauri://localhost",
            "http://tauri.localhost",
            "https://tauri.localhost",
        ],
        description="Origin CORS ammessi. Coprono Tauri 2 + dev server Vite.",
    )

    # ----- Filesystem -----
    data_dir: Path = Field(
        default_factory=lambda: Path.home() / ".sco-compliance-os",
        description="Directory dati locali utente (DB, log, cache vault registry).",
    )
    vault_default_path: Path | None = Field(
        default=None,
        description="Path vault SCO di default da pre-caricare a startup (opzionale).",
    )

    # ----- Logging + monitoring -----
    log_level: str = Field(default="INFO", description="Livello logging structlog.")
    sentry_dsn: SecretStr | None = Field(
        default=None,
        description="DSN Sentry opzionale. Se None, Sentry disabilitato.",
    )

    # ----- License + SaaS proxy -----
    sco_saas_base_url: str = Field(
        default="https://sco-saas-claude.vercel.app",
        description="Base URL del SaaS proxy LLM + license validate.",
    )
    license_key: SecretStr = Field(
        default=SecretStr(""),
        description="License key cliente, override anthropic_api_key per proxy.",
    )
    user_email: str = Field(
        default="",
        description="Email cliente associata alla license key.",
    )

    # ----- Subconscious tick loop (Wave 1 v0.2.0, blueprint OpenHuman replica) -----
    # Default OFF v0.2.0 (privacy enforcement, opt-in esplicito).
    subconscious_enabled: bool = Field(
        default=False,
        description=(
            "Abilita il Subconscious tick loop 5 min. Default OFF (privacy "
            "opt-in v0.2.0). Quando True, il lifespan avvia automaticamente "
            "il loop a startup."
        ),
    )
    subconscious_interval_seconds: int = Field(
        default=300,
        ge=300,
        description=(
            "Intervallo tick subconscious in secondi. Hard floor 300s (5 min, "
            "vincolo OpenHuman docs). Valori inferiori vengono clampati dal loop."
        ),
    )

    # ----- Auto-Fetch loop (Wave 2 v0.3.0, blueprint OpenHuman replica) -----
    # Default OFF v0.3.0 (privacy enforcement: opt-in esplicito,
    # blueprint Sezione 7 mitigazione "OAuth token leak via logs").
    auto_fetch_enabled: bool = Field(
        default=False,
        description=(
            "Abilita il Auto-Fetch loop 20 min walker connettori OAuth. "
            "Default OFF (privacy opt-in v0.3.0). Quando True, il lifespan "
            "avvia automaticamente il loop a startup."
        ),
    )
    auto_fetch_interval_seconds: int = Field(
        default=1200,
        ge=300,
        description=(
            "Intervallo tick auto-fetch in secondi. Hard floor 300s (5 min, "
            "anti-hammering OAuth rate limit). Default 1200s (20 min) blueprint."
        ),
    )
    auto_fetch_log_path: Path | None = Field(
        default=None,
        description=(
            "Path del file JSONL del activity log auto-fetch. Se None, "
            "default a ``~/.sco-compliance-os/autofetch_activity.jsonl``."
        ),
    )

    # ----- Storage paths derivati -----
    @property
    def memory_tree_db_path(self) -> Path:
        """Path al DB SQLite per memory tree + conversations."""
        return self.data_dir / "compliance_os.db"

    @property
    def onboarding_state_path(self) -> Path:
        """Path al file JSON onboarding state."""
        return self.data_dir / "onboarding.json"

    @property
    def vault_registry_path(self) -> Path:
        """Path al registry vault registrati."""
        return self.data_dir / "vault_registry.json"

    def ensure_data_dir(self) -> None:
        """Crea data_dir se non esiste (idempotente)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Ritorna le settings cached. Singleton per request."""
    return Settings()
