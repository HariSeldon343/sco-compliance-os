"""Router /api/tokenjuice — endpoint REST per 3-layer compression engine.

Endpoint:
- POST /api/tokenjuice/compress      -> comprime testo input, ritorna CompressResult.
- GET  /api/tokenjuice/rules         -> introspect config caricata (builtin/user/project).
- POST /api/tokenjuice/rules/reload  -> forza reload tokenjuice_rules.yaml dal disco.

Pattern endpoint identico a subconscious_routes.py (Pydantic models + APIRouter
prefix + structlog). Wave 2 v0.3.0 OpenHuman replica.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.memory.tokenjuice import (
    compress_text,
    describe_rules,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/tokenjuice", tags=["tokenjuice"])


# ----- Schemi Pydantic ---------------------------------------------------------------


class CompressRequest(BaseModel):
    """Payload POST /compress."""

    raw_text: str = Field(..., min_length=1, description="Testo grezzo da comprimere.")
    source_type: str = Field(
        default="manual",
        description="'html' | 'markdown' | 'transcript' | 'manual'.",
    )
    enable_layers: list[int] | None = Field(
        default=None,
        description="Layer abilitati (default tutti [1,2,3]).",
    )


class CompressResponse(BaseModel):
    """Esito di una compressione."""

    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    applied_rules: list[str]
    layer_stats: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Per layer (1/2/3) -> {tokens_before, tokens_after, tokens_saved, rules_count}.",
    )


class RulesResponse(BaseModel):
    """Snapshot config rules caricata."""

    builtin: list[str]
    user: dict[str, Any]
    project: list[dict[str, Any]]


class ReloadResponse(BaseModel):
    """Esito reload user rules."""

    reloaded: bool
    path: str
    count_loaded: int
    message: str


# ----- Endpoint ----------------------------------------------------------------------


@router.post("/compress", response_model=CompressResponse)
async def compress_endpoint(request: CompressRequest) -> CompressResponse:
    """Comprime testo input applicando 3-layer cascade.

    Layer attivi configurabili via ``enable_layers`` (default tutti).
    """
    # Default layers: tutti e 3 (clone tuple per immutabilita').
    layers_tuple: tuple[int, ...] = (
        tuple(request.enable_layers) if request.enable_layers is not None else (1, 2, 3)
    )

    # Validazione layers ammessi.
    for layer in layers_tuple:
        if layer not in (1, 2, 3):
            raise HTTPException(
                status_code=400,
                detail=f"Layer {layer} non valido. Ammessi: 1, 2, 3.",
            )

    try:
        result = await compress_text(
            request.raw_text,
            source_type=request.source_type,
            enable_layers=layers_tuple,
        )
    except Exception as e:
        logger.error("tokenjuice.compress.failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Pydantic dict keys must be strings, non int -> map layer keys to str.
    layer_stats_str: dict[str, dict[str, int]] = {str(k): v for k, v in result.layer_stats.items()}

    return CompressResponse(
        compressed_text=result.compressed_text,
        original_tokens=result.original_tokens,
        compressed_tokens=result.compressed_tokens,
        compression_ratio=result.compression_ratio,
        applied_rules=result.applied_rules,
        layer_stats=layer_stats_str,
    )


@router.get("/rules", response_model=RulesResponse)
async def get_rules() -> RulesResponse:
    """Ritorna config rules caricate (builtin + user + project) per ispezione UI."""
    try:
        payload = await describe_rules()
    except Exception as e:
        logger.error("tokenjuice.rules.describe_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
    return RulesResponse(**payload)


@router.post("/rules/reload", response_model=ReloadResponse)
async def reload_rules() -> ReloadResponse:
    """Forza reload tokenjuice_rules.yaml dal disco.

    Utile durante sviluppo o dopo edit manuale del file YAML user rules.
    Pattern: invoca describe_rules() che internamente esegue _load_user_rules()
    rilegga dal disco (no caching in-process attualmente).
    """
    try:
        payload = await describe_rules()
    except Exception as e:
        logger.error("tokenjuice.reload.failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

    user_block = payload.get("user", {})
    path = user_block.get("path", "")
    count = user_block.get("count", 0)
    exists = user_block.get("exists", False)

    return ReloadResponse(
        reloaded=True,
        path=path,
        count_loaded=count,
        message=(
            f"User rules reloaded from {Path(path).name}"
            if exists
            else "User rules file not found (silent skip)"
        ),
    )


__all__ = ["router"]
