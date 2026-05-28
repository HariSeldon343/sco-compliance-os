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

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
    autofetch_routes,
    chat_routes,
    integrations_routes,
    license_routes,
    llm_routes,
    memory_routes,
    onboarding_routes,
    profile_routes,
    skill_builder_routes,
    skills_routes,
    subconscious_routes,
    tokenjuice_routes,
    vault_routes,
    voice_routes,
    wiki_routes,
)
from sco_compliance_os.config import get_settings
from sco_compliance_os.core.logging_setup import configure_logging, set_request_id
from sco_compliance_os.core.migrations import apply_migrations
from sco_compliance_os.core.store import get_store
from sco_compliance_os.services.integrations.auto_fetch_loop import (
    AutoFetchLoop,
    AutoFetchOutcome,
)
from sco_compliance_os.services.integrations.auto_fetch_loop import (
    set_active_loop as set_active_autofetch_loop,
)
from sco_compliance_os.services.integrations.scheduler import (
    ConnectorScheduler,
    fetch_connector,
)
from sco_compliance_os.services.learning.profile_store import (
    init_schema as init_user_profile_schema,
)
from sco_compliance_os.services.memory.store import init_schema as init_memory_schema
from sco_compliance_os.services.memory.tree_store import init_tree_schema
from sco_compliance_os.services.skills.auto_trigger import (
    register_default_subscribers as register_skill_subscribers,
)
from sco_compliance_os.services.subconscious.tick_loop import (
    SubconsciousTickLoop,
    set_active_loop,
)
from sco_compliance_os.services.vault.watcher import get_watcher_manager

# Carica .env override=True (Conv. 44 enforcement: override valori già in env)
load_dotenv(override=True)


# Global ref scheduler per shutdown pulito
_active_scheduler: ConnectorScheduler | None = None
_subconscious_loop: SubconsciousTickLoop | None = None
_autofetch_loop: AutoFetchLoop | None = None
_seal_scheduler_task: asyncio.Task[None] | None = None
_seal_scheduler_stop: asyncio.Event | None = None
_cache_refresh_task: asyncio.Task[None] | None = None
_cache_refresh_stop: asyncio.Event | None = None


# Default seal scheduler tick interval (5 min). Overridable via env
# SCO_SEAL_SCHEDULER_INTERVAL_SECONDS (hard floor 60s).
_SEAL_SCHEDULER_DEFAULT_INTERVAL_SECONDS = 300
_SEAL_SCHEDULER_MIN_INTERVAL_SECONDS = 60

# Default cache refresh interval (4 min, sotto TTL 5 min Anthropic ephemeral
# cache). Overridable via env SCO_CACHE_REFRESH_INTERVAL_SECONDS.
# v0.13.2 DEV-AUTO-OPTIMIZER: mantiene cache calda fra una chat e l'altra.
_CACHE_REFRESH_DEFAULT_INTERVAL_SECONDS = 240
_CACHE_REFRESH_MIN_INTERVAL_SECONDS = 60


async def _seal_scheduler_loop(interval_seconds: int, stop_event: asyncio.Event) -> None:
    """Background loop: chiama cascade_seal_all per tutti i tree ogni N secondi.

    Pattern Conv. 41 tracciatura: logger structured ogni tick con counts per livello.
    Pattern Conv. 44 lesson 1: protetto da stop_event invece di run_forever puro;
    cancellabile da shutdown lifespan.
    """
    from sco_compliance_os.services.memory.tree_summaries import cascade_seal_all

    log = structlog.get_logger(__name__)
    log.info(
        "seal_scheduler.start",
        interval_seconds=interval_seconds,
    )
    while not stop_event.is_set():
        try:
            # Wait con timeout: scatta stop_event O elapsed interval (chi prima).
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            # Se stop_event partito, esci.
            if stop_event.is_set():
                break
        except TimeoutError:
            # Timeout = tempo di tick.
            pass

        try:
            counts = await cascade_seal_all(owner="local", force=False)
            total_l1 = sum(v.get(1, 0) for v in counts.values())
            total_l2 = sum(v.get(2, 0) for v in counts.values())
            total_l3 = sum(v.get(3, 0) for v in counts.values())
            log.info(
                "seal_scheduler.tick_complete",
                trees_processed=len(counts),
                summaries_l1=total_l1,
                summaries_l2=total_l2,
                summaries_l3=total_l3,
            )
        except Exception as exc:
            log.warning(
                "seal_scheduler.tick_error",
                error=str(exc),
                exc_type=type(exc).__name__,
            )

    log.info("seal_scheduler.stop")


async def _cache_refresh_loop(interval_seconds: int, stop_event: asyncio.Event) -> None:
    """Background loop: chiama optimizer_trigger.refresh_cache ogni N secondi.

    Mantiene calda la cache ephemeral Anthropic (TTL 5 min) cosi' la prima
    chat utente non paga il cold-start. Tick default 4 min (240s).

    Pattern Conv. 41 tracciatura: logger structured ogni tick con input_tokens
    + success bool. Pattern Conv. 44 lesson 1: protetto da stop_event,
    cancellabile da shutdown lifespan.

    Disabilitabile via env ``SCO_AUTO_OPTIMIZER_ENABLED=0`` (stessa toggle del
    DEV-AUTO-OPTIMIZER, principio: se l'optimizer e' off, anche il keep-alive
    cache e' off — risparmio API call inutili).
    """
    from sco_compliance_os.services.skills.optimizer_trigger import (
        _is_auto_optimizer_enabled,
        refresh_cache,
    )

    log = structlog.get_logger(__name__)
    log.info(
        "cache_refresh.start",
        interval_seconds=interval_seconds,
    )
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            if stop_event.is_set():
                break
        except TimeoutError:
            pass

        # Re-check toggle a ogni tick: l'utente puo' aver disabilitato runtime.
        if not _is_auto_optimizer_enabled():
            log.debug("cache_refresh.tick_skipped_disabled")
            continue

        try:
            result = await refresh_cache()
            log.info(
                "cache_refresh.tick_complete",
                success=result.get("success", False),
                input_tokens=result.get("input_tokens", 0),
            )
        except Exception as exc:
            log.warning(
                "cache_refresh.tick_error",
                error=str(exc),
                exc_type=type(exc).__name__,
            )

    log.info("cache_refresh.stop")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan handler: init DB schema + Memory Tree + Auto-fetch scheduler + cleanup.

    Pattern Subconscio OpenHuman: scheduler ConnectorScheduler auto-start a 20 min
    interval su connettori attivi (token presenti nel keyring). Idempotente.
    """
    global _active_scheduler, _subconscious_loop, _autofetch_loop
    global _seal_scheduler_task, _seal_scheduler_stop
    global _cache_refresh_task, _cache_refresh_stop
    settings = get_settings()
    settings.ensure_data_dir()

    # Bug 3 fix: registry di tracking per task fire-and-forget.
    # Pattern FastAPI standard per evitare GC prematura di asyncio.create_task()
    # non assegnato. Senza, l'event loop scarta il task prima del completamento
    # e l'handler vault.registered NON viene mai eseguito (root cause Bug Antonio).
    app.state.background_tasks = set()

    # Init main DB (conversations + messages)
    store = get_store(settings.memory_tree_db_path)
    await store.init_schema()

    # Init Memory Tree DB schema (chunks per Subconscio)
    await init_memory_schema()

    # Init Memory Tree bucket-seal schema (mem_tree_chunks, 4 fasi pipeline)
    # Subagent DEV-MEMORY-TREE 24/05/2026: Fase 1+2+3 + admission gate.
    # Schema idempotente safe a ogni avvio (CHECK constraints + INDEX IF NOT EXISTS).
    await init_tree_schema()

    # Init User Profile DB schema (apprendimento profilo progressivo)
    await init_user_profile_schema()

    # Wire skill loader auto-trigger subscriber su event bus.
    # Pattern Conv. 47 single source of truth: registrazione in-process,
    # nessuna persistenza DB. Idempotente (skip se gia' registrato).
    register_skill_subscribers()

    # Apply migrations OpenHuman replica (W1-MEMORY: 0002_openhuman_features.sql)
    # Idempotente IF NOT EXISTS, sicuro da rieseguire ad ogni startup.
    try:
        migration_result = await apply_migrations()
        applied_files: list[str] = migration_result.get("applied", []) or []  # type: ignore[assignment]
        applied_count = len(applied_files)
        if applied_count > 0:
            structlog.get_logger(__name__).info(
                "backend.startup.migrations_applied",
                count=applied_count,
                files=applied_files,
            )
    except Exception as mig_err:
        structlog.get_logger(__name__).warning(
            "backend.startup.migration_failed",
            error=str(mig_err),
            note="migration apply failed but startup continues",
        )

    # Inizializza Auto-Fetch loop sempre (registra ref globale per le route W2).
    # Avvia background task SOLO se settings.auto_fetch_enabled OR
    # env SCO_AUTO_FETCH_ENABLED=1 (default OFF privacy v0.3.0).
    user_id = settings.user_email or "default-user"
    env_auto_fetch_enabled = os.environ.get("SCO_AUTO_FETCH_ENABLED", "0") == "1"
    effective_auto_fetch_enabled = settings.auto_fetch_enabled or env_auto_fetch_enabled

    # Wire fetch_handler: cattura settings + user_id come closure.
    # In v0.3.0 nessun connector_credentials e' configurato a startup;
    # quando il cabling W3 sara' attivo, le credentials verranno iniettate
    # via env var dedicate. Per ora il handler invoca fetch_connector senza
    # credentials -> outcome stub-like con errors[] "no_oauth_credentials".
    async def _autofetch_handler(connector_name: str, uid: str) -> AutoFetchOutcome:
        return await fetch_connector(connector_name, uid, connector_credentials=None)

    _autofetch_loop = AutoFetchLoop(
        user_id=user_id,
        interval_seconds=settings.auto_fetch_interval_seconds,
        activity_log_path=settings.auto_fetch_log_path,
        fetch_handler=_autofetch_handler,
    )
    set_active_autofetch_loop(_autofetch_loop)
    if effective_auto_fetch_enabled:
        await _autofetch_loop.start()

    # NOTE: legacy ConnectorScheduler resta disponibile per import esterni che
    # lo richiedano (backwards-compat W1). Non viene piu' istanziato in lifespan
    # dato che AutoFetchLoop copre lo use case 1:1. La variabile globale
    # _active_scheduler resta a None.

    # Inizializza Subconscious tick loop sempre (registra ref globale per le route).
    # Avvia background task SOLO se settings.subconscious_enabled (default OFF privacy).
    _subconscious_loop = SubconsciousTickLoop(
        interval_seconds=settings.subconscious_interval_seconds,
        context_provider=None,  # context provider cabling -> Wave 2 (Memory Tree wiring)
    )
    set_active_loop(_subconscious_loop)
    if settings.subconscious_enabled:
        await _subconscious_loop.start()

    # Memory Tree seal scheduler (v0.6.0 Fase 4): background task ogni 5 min
    # chiama cascade_seal_all() per consolidare chunks admitted -> summaries L1->L2->L3.
    # Default abilitato (cost basso via threshold 32k token cumulativi).
    # Disabilitabile via env SCO_SEAL_SCHEDULER_ENABLED=0 per dev / debug.
    seal_scheduler_enabled = os.environ.get("SCO_SEAL_SCHEDULER_ENABLED", "1") == "1"
    seal_interval_raw = int(
        os.environ.get(
            "SCO_SEAL_SCHEDULER_INTERVAL_SECONDS",
            str(_SEAL_SCHEDULER_DEFAULT_INTERVAL_SECONDS),
        )
    )
    seal_interval = max(_SEAL_SCHEDULER_MIN_INTERVAL_SECONDS, seal_interval_raw)
    if seal_scheduler_enabled:
        _seal_scheduler_stop = asyncio.Event()
        _seal_scheduler_task = asyncio.create_task(
            _seal_scheduler_loop(seal_interval, _seal_scheduler_stop),
            name="seal_scheduler",
        )

    # v0.13.2 DEV-AUTO-OPTIMIZER: cache refresh scheduler.
    # Mantiene calda la cache ephemeral Anthropic (TTL 5min, tick 4min).
    # Toggle via env SCO_AUTO_OPTIMIZER_ENABLED (default 1).
    auto_optimizer_enabled = os.environ.get("SCO_AUTO_OPTIMIZER_ENABLED", "1").strip() not in (
        "0",
        "false",
        "False",
        "no",
        "off",
    )
    cache_refresh_interval_raw = int(
        os.environ.get(
            "SCO_CACHE_REFRESH_INTERVAL_SECONDS",
            str(_CACHE_REFRESH_DEFAULT_INTERVAL_SECONDS),
        )
    )
    cache_refresh_interval = max(_CACHE_REFRESH_MIN_INTERVAL_SECONDS, cache_refresh_interval_raw)
    if auto_optimizer_enabled:
        _cache_refresh_stop = asyncio.Event()
        _cache_refresh_task = asyncio.create_task(
            _cache_refresh_loop(cache_refresh_interval, _cache_refresh_stop),
            name="cache_refresh_scheduler",
        )

    # v0.6.0 DEV-VAULT-AUTOINGEST: wire file event callback + avvia watcher
    # per ogni vault gia' registrato + lancia sync iniziale.
    # Import locale per evitare import circolare (vault_routes importa watcher).
    from sco_compliance_os.api.vault_routes import (
        _background_sync_and_watch,
        _load_registry,
        handle_file_event,
    )

    watcher_manager = get_watcher_manager()
    watcher_manager.set_event_callback(handle_file_event)

    # Per ogni vault gia' registrato: lancia sync iniziale fire-and-forget +
    # avvia watcher. Idempotente: dedup naturale (chunk_id stabile).
    try:
        registered_entries = _load_registry(settings.vault_registry_path)
        for entry in registered_entries:
            vault_id_existing = entry.get("id")
            path_existing = entry.get("path")
            if not vault_id_existing or not path_existing:
                continue
            from pathlib import Path as _PathLocal

            vault_path_existing = _PathLocal(path_existing)
            if not vault_path_existing.exists():
                structlog.get_logger(__name__).warning(
                    "startup.vault_path_missing",
                    vault_id=vault_id_existing,
                    path=path_existing,
                )
                continue
            asyncio.create_task(  # noqa: RUF006 — startup bg task long-lived intenzionale
                _background_sync_and_watch(vault_id_existing, vault_path_existing),
                name=f"startup-autoingest-{vault_id_existing}",
            )
    except Exception as start_exc:
        structlog.get_logger(__name__).warning(
            "startup.vault_autoingest_failed",
            error=str(start_exc),
        )

    logger = structlog.get_logger(__name__)
    logger.info(
        "backend.startup.complete",
        version=__version__,
        port=settings.backend_port,
        data_dir=str(settings.data_dir),
        autofetch_enabled=effective_auto_fetch_enabled,
        autofetch_running=_autofetch_loop.is_running(),
        subconscious_enabled=settings.subconscious_enabled,
        subconscious_running=_subconscious_loop.is_running(),
        seal_scheduler_enabled=seal_scheduler_enabled,
        seal_scheduler_interval=seal_interval,
        auto_optimizer_enabled=auto_optimizer_enabled,
        cache_refresh_interval=cache_refresh_interval,
        vault_watcher_enabled=True,
        user_id=user_id,
    )

    yield

    # Shutdown pulito seal scheduler (v0.6.0 Fase 4)
    if _seal_scheduler_stop is not None:
        _seal_scheduler_stop.set()
    if _seal_scheduler_task is not None:
        try:
            await asyncio.wait_for(_seal_scheduler_task, timeout=10.0)
        except TimeoutError:
            structlog.get_logger(__name__).warning("backend.shutdown.seal_scheduler_timeout")
            _seal_scheduler_task.cancel()
        _seal_scheduler_task = None
        _seal_scheduler_stop = None

    # Shutdown pulito cache refresh scheduler (v0.13.2 DEV-AUTO-OPTIMIZER)
    if _cache_refresh_stop is not None:
        _cache_refresh_stop.set()
    if _cache_refresh_task is not None:
        try:
            await asyncio.wait_for(_cache_refresh_task, timeout=10.0)
        except TimeoutError:
            structlog.get_logger(__name__).warning("backend.shutdown.cache_refresh_timeout")
            _cache_refresh_task.cancel()
        _cache_refresh_task = None
        _cache_refresh_stop = None

    # Shutdown pulito vault watchers (v0.6.0)
    try:
        await get_watcher_manager().stop_all()
    except Exception as wm_exc:
        structlog.get_logger(__name__).warning(
            "backend.shutdown.watcher_stop_failed",
            error=str(wm_exc),
        )

    # Shutdown pulito subconscious loop
    if _subconscious_loop is not None:
        await _subconscious_loop.stop()
        set_active_loop(None)
        _subconscious_loop = None

    # Shutdown pulito auto-fetch loop
    if _autofetch_loop is not None:
        await _autofetch_loop.stop()
        set_active_autofetch_loop(None)
        _autofetch_loop = None

    # Shutdown pulito scheduler legacy (se istanziato esternamente)
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
        """Health check semplice. Usato da Tauri sidecar per readiness probe.

        Conv. 47 enforcement v0.7.1: backend_version + version entrambi popolati
        da __version__ single source of truth (fix display drift sidebar pre-v0.7.1
        che mostrava "0.3.0" hardcoded su qualunque MSI installato).
        """
        return {
            "status": "ok",
            "service": "sco-compliance-os-backend",
            "version": __version__,
            "backend_version": __version__,
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
    app.include_router(wiki_routes.router)
    app.include_router(memory_routes.router)
    app.include_router(integrations_routes.router)
    app.include_router(onboarding_routes.router)
    app.include_router(license_routes.router)
    app.include_router(subconscious_routes.router)
    app.include_router(tokenjuice_routes.router)
    app.include_router(autofetch_routes.router)
    app.include_router(profile_routes.router)
    app.include_router(skills_routes.router)
    # v0.8.1 DEV-SUBAGENT-BUILDER: 2 router (builder POST + skills CRUD PATCH/DELETE)
    app.include_router(skill_builder_routes.router)
    app.include_router(skill_builder_routes.router_skills_crud)
    app.include_router(voice_routes.router)
    app.include_router(llm_routes.router)

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
