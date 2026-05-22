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
        default="claude-sonnet-4-6",
        description="Modello predefinito per chat e agent reasoning.",
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
        description="Path vault Karpathy di default da pre-caricare a startup (opzionale).",
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
