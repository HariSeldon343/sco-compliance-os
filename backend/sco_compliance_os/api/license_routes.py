"""Router /api/license — attivazione + verifica license key cliente SCO.

Pattern Karpathy single source of truth: lo stato license vive sul SaaS,
NON sul backend locale. Il backend locale cache 24h via file JSON locale
(~/.sco-compliance-os/license-cache.json) per UX offline + grace period.

Endpoint:
- POST /api/license/activate {email, license_key} → valida SaaS + persiste su keyring
- GET  /api/license/status                         → ultimo stato license (cache + ping)
- POST /api/license/refresh                        → force re-validate (skip cache)
- POST /api/license/logout                         → cancella license da keyring

Pattern Conv. 47: la version dell'app + status license vivono nel backend,
il frontend NON le hardcoda — le legge dal /status endpoint.

Pattern Conv. 48: lo stato widget LicenseInvalidScreen persiste in conv. JSON
del messaggio assistant per sopravvivere ai cambi conversazione.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.license import (
    LicenseStatus,
    LicenseValidationResult,
    get_license_client,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/license", tags=["license"])


# ----- Pydantic schemas -----


class ActivateRequest(BaseModel):
    """Richiesta attivazione license key."""

    email: EmailStr = Field(..., description="Email cliente associata alla license.")
    license_key: str = Field(..., min_length=8, description="License key fornita da SCO.")


class LicenseStatusResponse(BaseModel):
    """Risposta status license."""

    status: str
    is_valid: bool
    email: str = ""
    license_key_hash: str = ""
    tenant_id: str = ""
    expires_at: str = ""
    plan: str = ""
    validated_at: str = ""
    error_message: str = ""
    # Version backend (Conv. 47 enforcement single source of truth v0.7.1).
    # Override runtime con __version__ in costruzione response, NON usare default.
    backend_version: str = ""


# ----- Helpers -----


def _license_state_path(settings: Settings) -> Path:
    """Path file JSON con last license attivata (email + license_key in cleartext)."""
    return settings.data_dir / "active-license.json"


def _save_active_license(
    settings: Settings, email: str, license_key: str, result: LicenseValidationResult
) -> None:
    """Persisti license attiva su file JSON locale (data_dir).

    Sicurezza: file in user-home, accessibile solo dall'utente OS corrente.
    Pattern future Wave 2: spostare in keyring OS (Windows Credential Manager).
    """
    path = _license_state_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "email": email,
        "license_key": license_key,  # plaintext temp; Wave 2 → keyring
        "validation_result": result.to_dict(),
        "activated_at": datetime.now(UTC).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_active_license(settings: Settings) -> dict[str, Any] | None:
    """Carica license attiva dal file JSON locale."""
    path = _license_state_path(settings)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning("license.load_failed", error=str(exc))
        return None


def _result_to_response(result: LicenseValidationResult) -> LicenseStatusResponse:
    """Mappa LicenseValidationResult → response Pydantic.

    Conv. 47 enforcement v0.7.1: backend_version popolata da __version__ runtime
    (mai usare default hardcoded "0.1.0-alpha" che era drift di 6 release).
    """
    from sco_compliance_os import __version__

    return LicenseStatusResponse(
        status=result.status.value,
        is_valid=result.is_valid,
        email=result.email,
        license_key_hash=result.license_key_hash,
        tenant_id=result.tenant_id,
        expires_at=result.expires_at,
        plan=result.plan,
        validated_at=result.validated_at,
        error_message=result.error_message,
        backend_version=__version__,
    )


# ----- Endpoint -----


@router.post("/activate", response_model=LicenseStatusResponse)
async def activate_license(
    payload: ActivateRequest, settings: Settings = Depends(get_settings)
) -> LicenseStatusResponse:
    """Attiva license key: valida con SaaS + persiste locale se valida."""
    client = get_license_client()
    result = await client.validate(payload.email, payload.license_key, force_refresh=True)

    if result.is_valid:
        # Persisti license attiva su disco (per riavvio app senza re-login)
        settings.ensure_data_dir()
        _save_active_license(settings, payload.email, payload.license_key, result)
        logger.info(
            "license.activated",
            email=payload.email,
            license_hash=result.license_key_hash,
            plan=result.plan,
            expires_at=result.expires_at,
        )
    else:
        logger.warning(
            "license.activation_failed",
            email=payload.email,
            status=result.status.value,
            error=result.error_message,
        )

    return _result_to_response(result)


@router.get("/status", response_model=LicenseStatusResponse)
async def get_license_status(
    settings: Settings = Depends(get_settings),
) -> LicenseStatusResponse:
    """Stato corrente license attiva (da cache + ping SaaS se TTL scaduto)."""
    from sco_compliance_os import __version__

    active = _load_active_license(settings)
    if not active:
        # Nessuna license attivata → status UNKNOWN
        return LicenseStatusResponse(
            status=LicenseStatus.UNKNOWN.value,
            is_valid=False,
            error_message="Nessuna license attivata. Inserisci email + license key.",
            backend_version=__version__,
        )

    email = active.get("email", "")
    license_key = active.get("license_key", "")
    if not email or not license_key:
        return LicenseStatusResponse(
            status=LicenseStatus.INVALID.value,
            is_valid=False,
            error_message="File license corrotto. Re-inserire credenziali.",
            backend_version=__version__,
        )

    # Valida via SaaS (con cache 24h)
    client = get_license_client()
    result = await client.validate(email, license_key, force_refresh=False)
    return _result_to_response(result)


@router.post("/refresh", response_model=LicenseStatusResponse)
async def refresh_license(
    settings: Settings = Depends(get_settings),
) -> LicenseStatusResponse:
    """Force re-validate license skip cache (per recovery)."""
    active = _load_active_license(settings)
    if not active:
        raise HTTPException(status_code=404, detail="Nessuna license attiva da refreshare")

    email = active.get("email", "")
    license_key = active.get("license_key", "")
    client = get_license_client()
    result = await client.validate(email, license_key, force_refresh=True)

    if result.is_valid:
        _save_active_license(settings, email, license_key, result)

    return _result_to_response(result)


@router.post("/logout")
async def logout_license(
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Cancella license attiva da disco (logout)."""
    path = _license_state_path(settings)
    if path.exists():
        path.unlink()
        logger.info("license.logout.success")
    return {"status": "ok", "message": "License rimossa. Re-inserire per riprendere."}
