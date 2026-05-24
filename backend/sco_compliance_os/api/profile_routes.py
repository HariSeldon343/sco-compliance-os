"""Router /api/profile — CRUD e debug del profilo utente.

Endpoint:
- GET    /api/profile               lista preferenze ordinate (pinned + seen)
- GET    /api/profile/markdown      markdown rendered (debug/preview)
- DELETE /api/profile/{slug}        rimuovi preferenza
- POST   /api/profile/{slug}/pin    pin (sale in cima al system prompt)
- POST   /api/profile/{slug}/unpin  rimuovi pin
- POST   /api/profile/extract       endpoint debug per estrarre da testo (no persist)

Pattern Conv. 47 SINGLE SOURCE OF TRUTH: ogni endpoint legge da profile_store
SQLite, mai da cache process-local o env. Pattern Conv. 41 tracciatura: ogni
endpoint logga con structlog request count + outcome.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.learning.profile_renderer import (
    render_profile_markdown,
)
from sco_compliance_os.services.learning.profile_store import (
    count_preferences,
    delete_preference,
    list_preferences,
    pin_preference,
    unpin_preference,
)
from sco_compliance_os.services.learning.user_profile import (
    Preference,
    ProfileCategory,
    extract_preferences,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


# ----- Schemi Pydantic -----


class PreferenceOut(BaseModel):
    """Schema response preferenza."""

    text: str
    slug: str
    category: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    extracted_at: str
    source_turn_id: str | None = None


class ProfileListResponse(BaseModel):
    """Response /api/profile."""

    preferences: list[PreferenceOut] = Field(default_factory=list)
    total_count: int = 0
    tenant_id: str = "local"


class ProfileMarkdownResponse(BaseModel):
    """Response /api/profile/markdown."""

    markdown: str
    char_count: int
    preferences_count: int


class ExtractRequest(BaseModel):
    """Richiesta /api/profile/extract — debug estrazione senza persist."""

    text: str = Field(..., min_length=1, max_length=5000)


class ExtractResponse(BaseModel):
    """Response /api/profile/extract."""

    preferences: list[PreferenceOut] = Field(default_factory=list)
    count: int = 0


class ProfileActionResponse(BaseModel):
    """Response generic per delete/pin/unpin."""

    success: bool
    slug: str
    action: str
    message: str | None = None


# ----- Helpers -----


def _pref_to_out(pref: Preference) -> PreferenceOut:
    """Adatta Preference dataclass a PreferenceOut Pydantic."""
    return PreferenceOut(
        text=pref.text,
        slug=pref.slug,
        category=pref.category.value,
        confidence=pref.confidence,
        extracted_at=pref.extracted_at.isoformat(),
        source_turn_id=pref.source_turn_id,
    )


def _parse_category(value: str | None) -> ProfileCategory | None:
    """Parse query string category in enum, None se vuoto, 422 se invalido."""
    if not value:
        return None
    try:
        return ProfileCategory(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Categoria non valida: '{value}'. Valori ammessi: "
                f"{[c.value for c in ProfileCategory]}"
            ),
        ) from exc


# ----- Endpoint -----


@router.get("", response_model=ProfileListResponse)
async def get_profile(
    category: str | None = Query(default=None, description="Filtra per categoria."),
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: str = Query(default="local"),
) -> ProfileListResponse:
    """Ritorna lista preferenze ordinate per display priority.

    Order: pinned DESC, seen_count DESC, confidence DESC, last_seen_at DESC.
    """
    cat = _parse_category(category)
    prefs = await list_preferences(
        tenant_id=tenant_id,
        category=cat,
        limit=limit,
    )
    total = await count_preferences(tenant_id=tenant_id)
    logger.info(
        "profile.list",
        tenant_id=tenant_id,
        category=category,
        returned=len(prefs),
        total=total,
    )
    return ProfileListResponse(
        preferences=[_pref_to_out(p) for p in prefs],
        total_count=total,
        tenant_id=tenant_id,
    )


@router.get("/markdown", response_model=ProfileMarkdownResponse)
async def get_profile_markdown(
    tenant_id: str = Query(default="local"),
    max_chars: int = Query(default=2000, ge=200, le=10000),
) -> ProfileMarkdownResponse:
    """Ritorna markdown rendered del profilo (debug/preview system prompt)."""
    prefs = await list_preferences(tenant_id=tenant_id, limit=200)
    markdown = render_profile_markdown(prefs, max_chars=max_chars)
    logger.info(
        "profile.markdown",
        tenant_id=tenant_id,
        char_count=len(markdown),
        preferences_count=len(prefs),
    )
    return ProfileMarkdownResponse(
        markdown=markdown,
        char_count=len(markdown),
        preferences_count=len(prefs),
    )


@router.post("/extract", response_model=ExtractResponse)
async def extract_from_text(payload: ExtractRequest) -> ExtractResponse:
    """Debug endpoint: estrae preferenze da testo arbitrario SENZA persistere.

    Utile per testing dei pattern regex senza modificare il DB profilo.
    """
    prefs = extract_preferences(payload.text, cap=10)
    logger.info(
        "profile.extract_debug",
        text_len=len(payload.text),
        extracted=len(prefs),
    )
    return ExtractResponse(
        preferences=[_pref_to_out(p) for p in prefs],
        count=len(prefs),
    )


@router.delete("/{slug}", response_model=ProfileActionResponse)
async def delete_pref(
    slug: str,
    tenant_id: str = Query(default="local"),
) -> ProfileActionResponse:
    """Rimuovi preferenza dal profilo per (tenant_id, slug)."""
    deleted = await delete_preference(slug, tenant_id=tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Preferenza '{slug}' non trovata per tenant '{tenant_id}'",
        )
    logger.info("profile.delete", tenant_id=tenant_id, slug=slug)
    return ProfileActionResponse(
        success=True,
        slug=slug,
        action="delete",
        message=f"Preferenza '{slug}' rimossa dal profilo.",
    )


@router.post("/{slug}/pin", response_model=ProfileActionResponse)
async def pin_pref(
    slug: str,
    tenant_id: str = Query(default="local"),
) -> ProfileActionResponse:
    """Pin preferenza (sale in cima al system prompt + visivamente all'utente)."""
    pinned = await pin_preference(slug, tenant_id=tenant_id)
    if not pinned:
        raise HTTPException(
            status_code=404,
            detail=f"Preferenza '{slug}' non trovata per tenant '{tenant_id}'",
        )
    logger.info("profile.pin", tenant_id=tenant_id, slug=slug)
    return ProfileActionResponse(
        success=True,
        slug=slug,
        action="pin",
        message=f"Preferenza '{slug}' pinned.",
    )


@router.post("/{slug}/unpin", response_model=ProfileActionResponse)
async def unpin_pref(
    slug: str,
    tenant_id: str = Query(default="local"),
) -> ProfileActionResponse:
    """Rimuovi pin da preferenza."""
    unpinned = await unpin_preference(slug, tenant_id=tenant_id)
    if not unpinned:
        raise HTTPException(
            status_code=404,
            detail=f"Preferenza '{slug}' non trovata per tenant '{tenant_id}'",
        )
    logger.info("profile.unpin", tenant_id=tenant_id, slug=slug)
    return ProfileActionResponse(
        success=True,
        slug=slug,
        action="unpin",
        message=f"Preferenza '{slug}' unpinned.",
    )


# Export-friendly per debug/testing
__all__ = ["router"]
_ = Any  # silence unused import in some lint configs
