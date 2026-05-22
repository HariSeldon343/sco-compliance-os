"""License key validation + SaaS proxy client.

Pattern modello commerciale SCO Compliance OS:
- Cliente paga abbonamento → SCO emette license_key tramite admin UI Vercel.
- Cliente installa app desktop + LoginScreen: email + license_key.
- Backend locale valida license_key via HTTPS chiamata al SaaS sco-saas-claude:
    POST https://sco-saas-claude.vercel.app/api/v1/license/validate
    Body: {"email": "...", "license_key": "..."}
    Response: 200 {valid, status, expires_at, tenant_id} | 401 invalid | 403 revoked | 410 expired
- Se license valida, cliente NON vede mai chiave Anthropic.
- L'app desktop chiama Anthropic via NOSTRO proxy:
    Anthropic SDK Python con base_url custom = sco-saas-claude proxy endpoint.
    api_key = license_key (cliente passa la sua, server-side valida + sostituisce con NOSTRA chiave).
- License revocabile (status='revoked'/'expired') → app smette di funzionare
  al successivo health check (max 24h cache locale).

Componenti:
- client.py: HTTP client per SaaS license validate + cache 24h.
- middleware.py: dependency injection FastAPI per validare ogni request.
- models.py: dataclass LicenseStatus + LicenseValidationResult.

Pattern Karpathy single source of truth: lo stato license vive sul SaaS,
mai duplicato in più posti locali (cache TTL bassa per safety).
"""

from sco_compliance_os.services.license.client import (
    LicenseClient,
    LicenseValidationError,
    get_license_client,
)
from sco_compliance_os.services.license.models import (
    LicenseStatus,
    LicenseValidationResult,
)

__all__ = [
    "LicenseClient",
    "LicenseStatus",
    "LicenseValidationError",
    "LicenseValidationResult",
    "get_license_client",
]
