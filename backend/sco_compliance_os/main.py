"""Entry point FastAPI app del backend SCO Compliance OS.

Avvia uvicorn da CLI:
    sco-compliance-os
    # oppure
    python -m sco_compliance_os.main

Note Conv. 44 lesson 1: NON avviare con --reload da shell ephemeral
(zombie socket Windows). Per dev usa scripts/dev.ps1 in terminale persistente.
Note Conv. 44 lesson 2: CORS origin includono i 5 fallback Tauri 2 WebView2.
Note Conv. 44 lesson 3: hidden imports candidates listati in __init__.py per
generazione futura PyInstaller sidecar.
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

import sentry_sdk
import structlog
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sco_compliance_os import __version__
from sco_compliance_os.api import (
    chat_routes,
    integrations_routes,
    license_routes,
    memory_routes,
    onboarding_routes,
    subconscious_routes,
    vault_routes,
)
from sco_compliance_os.config import get_settings
from sco_compliance_os.core.logging_setup import configure_logging, set_request_id
from sco_compliance_os.core.migrations import apply_migrations
from sco_compliance_os.core.store import get_store
from sco_compliance_os.services.integrations.scheduler import ConnectorScheduler
from sco_compliance_os.services.memory.store import init_schema as init_memory_schema
from sco_compliance_os.services.subconscious.tick_loop import (
    SubconsciousTickLoop,
    set_active_loop,
)

# Carica .env override=True (Conv. 44 enforcement: override valori già in env)
load_dotenv(override=True)


# Global ref scheduler per shutdown pulito
_active_scheduler: ConnectorScheduler | None = None
_subconscious_loop: SubconsciousTickLoop | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan handler: init DB schema + Memory Tree + Auto-fetch scheduler + cleanup.

    Pattern Subconscio OpenHuman: scheduler ConnectorScheduler auto-start a 20 min
    interval su connettori attivi (token presenti nel keyring). Idempotente.
    """
    global _active_scheduler, _subconscious_loop
    settings = get_settings()
    settings.ensure_data_dir()

    # Init main DB (conversations + messages)
    store = get_store(settings.memory_tree_db_path)
    await store.init_schema()

    # Init Memory Tree DB schema (chunks per Subconscio)
    await init_memory_schema()

    # Apply migrations OpenHuman replica (W1-MEMORY: 0002_openhuman_features.sql)
    # Idempotente IF NOT EXISTS, sicuro da rieseguire ad ogni startup.
    try:
        migration_result = await apply_migrations()
        applied_count = len(migration_result.get("applied", []))
        if applied_count > 0:
            structlog.get_logger(__name__).info(
                "backend.startup.migrations_applied",
                count=applied_count,
                files=migration_result.get("applied", []),
            )
    except Exception as mig_err:
        structlog.get_logger(__name__).warning(
            "backend.startup.migration_failed",
            error=str(mig_err),
            note="migration apply failed but startup continues",
        )

    # Avvia auto-fetch scheduler se license_key presente (= cliente attivato)
    # Per ora scheduler disabilitato di default — abilitabile via env SCO_AUTO_FETCH_ENABLED=1
    auto_fetch_enabled = os.environ.get("SCO_AUTO_FETCH_ENABLED", "0") == "1"
    user_id = settings.user_email or "default-user"
    if auto_fetch_enabled and settings.user_email:
        _active_scheduler = ConnectorScheduler(user_id=user_id)
        await _active_scheduler.start()

    # Inizializza Subconscious tick loop sempre (registra ref globale per le route).
    # Avvia background task SOLO se settings.subconscious_enabled (default OFF privacy).
    _subconscious_loop = SubconsciousTickLoop(
        interval_seconds=settings.subconscious_interval_seconds,
        context_provider=None,  # context provider cabling -> Wave 2 (Memory Tree wiring)
    )
    set_active_loop(_subconscious_loop)
    if settings.subconscious_enabled:
        await _subconscious_loop.start()

    logger = structlog.get_logger(__name__)
    logger.info(
        "backend.startup.complete",
        version=__version__,
        port=settings.backend_port,
        data_dir=str(settings.data_dir),
        scheduler_active=_active_scheduler is not None,
        subconscious_enabled=settings.subconscious_enabled,
        subconscious_running=_subconscious_loop.is_running(),
        user_id=user_id,
    )

    yield

    # Shutdown pulito subconscious loop
    if _subconscious_loop is not None:
        await _subconscious_loop.stop()
        set_active_loop(None)
        _subconscious_loop = None

    # Shutdown pulito scheduler
    if _active_scheduler is not None:
        await _active_scheduler.stop()
        _active_scheduler = None

    await store.close()
    logger.info("backend.shutdown.complete")


def create_app() -> FastAPI:
    """Factory FastAPI app + middleware + routers."""
    settings = get_settings()

    # Setup logging structured
    configure_logging(log_level=settings.log_level, json_output=False)

    # Sentry opzionale
    if settings.sentry_dsn and settings.sentry_dsn.get_secret_value():
        sentry_sdk.init(
            dsn=settings.sentry_dsn.get_secret_value(),
            traces_sample_rate=0.0,  # disable performance tracing by default
            send_default_pii=False,
        )

    app = FastAPI(
        title="SCO Compliance OS Backend",
        version=__version__,
        description=(
            "Backend FastAPI per l'app desktop SCO Compliance OS. "
            "AI assistant brandato SCO per consulenza compliance e normativa. "
            "Stack: FastAPI + Anthropic Agent SDK + MCP. Clean-room scratch."
        ),
        lifespan=lifespan,
    )

    # CORS — Conv. 44 lesson 2 enforcement (5 origin fallback Tauri 2 + dev Vite)
    cors_origins_env = os.environ.get("CORS_ORIGINS")
    if cors_origins_env:
        if cors_origins_env.strip() == "*":
            origins: list[str] = ["*"]
        else:
            origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    else:
        origins = settings.cors_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Middleware request_id propagation
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Any) -> Any:
        incoming = request.headers.get("X-Request-ID")
        rid = set_request_id(incoming or str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    # Health endpoint root-level
    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, Any]:
        """Health check semplice. Usato da Tauri sidecar per readiness probe."""
        return {
            "status": "ok",
            "service": "sco-compliance-os-backend",
            "version": __version__,
        }

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, Any]:
        """Welcome message."""
        return {
            "service": "SCO Compliance OS Backend",
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
        }

    # Handler generic 500
    @app.exception_handler(Exception)
    async def unhandled_exc(request: Request, exc: Exception) -> JSONResponse:
        logger = structlog.get_logger(__name__)
        logger.error("backend.unhandled_exception", error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc)},
        )

    # Routers
    app.include_router(chat_routes.router)
    app.include_router(vault_routes.router)
    app.include_router(memory_routes.router)
    app.include_router(integrations_routes.router)
    app.include_router(onboarding_routes.router)
    app.include_router(license_routes.router)
    app.include_router(subconscious_routes.router)

    return app


app = create_app()


def main() -> None:
    """CLI entrypoint: avvia uvicorn senza --reload (Conv. 44 lesson 1).

    PATTERN PyInstaller bundle (Conv. 44 lesson 3 enforcement): passa l'OGGETTO
    `app` direttamente a uvicorn.run() invece della stringa "module:attr".
    String import dinamico fallisce in bundle PyInstaller perché il modulo
    risiede dentro il pyz archive e uvicorn non sa risolverlo via importlib.

    Per development con auto-reload, usa scripts/dev.ps1 o scripts/dev.sh
    da un terminale PowerShell/bash PERSISTENTE (non shell ephemeral).
    """
    settings = get_settings()
    uvicorn.run(
        app,  # OGGETTO diretto, NON stringa (Conv. 44 lesson 3 PyInstaller-safe)
        host=settings.backend_host,
        port=settings.backend_port,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
