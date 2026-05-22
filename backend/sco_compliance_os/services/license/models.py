"""Dataclass per license validation result."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class LicenseStatus(str, Enum):
    """Stati possibili di una license key."""

    VALID = "valid"          # license attiva e valida
    INVALID = "invalid"      # license non esiste o malformata
    REVOKED = "revoked"      # license revocata da admin
    EXPIRED = "expired"      # license scaduta (oltre expires_at)
    NETWORK_ERROR = "network_error"  # validazione fallita (rete giù) - cache fallback
    UNKNOWN = "unknown"      # stato non determinabile


@dataclass(slots=True)
class LicenseValidationResult:
    """Risultato validazione license dal SaaS.

    Attributes:
        status: stato license (VALID, INVALID, REVOKED, EXPIRED, ecc.)
        email: email del titolare license
        license_key_hash: SHA256(license_key) per riferimento sicuro nei log
        tenant_id: opaque tenant ID nel SaaS (per usage tracking)
        expires_at: ISO datetime scadenza license
        plan: tier abbonamento (starter, pro, enterprise)
        validated_at: timestamp UTC della validazione
        cache_ttl_seconds: TTL cache locale (default 24h)
        error_message: solo se INVALID/REVOKED/EXPIRED
    """

    status: LicenseStatus
    email: str = ""
    license_key_hash: str = ""
    tenant_id: str = ""
    expires_at: str = ""
    plan: str = ""
    validated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cache_ttl_seconds: int = 86400  # 24h default
    error_message: str = ""

    @property
    def is_valid(self) -> bool:
        """True se license utilizzabile per chiamate LLM."""
        return self.status == LicenseStatus.VALID

    def to_dict(self) -> dict:
        """Serializza a dict per response JSON."""
        return {
            "status": self.status.value,
            "email": self.email,
            "license_key_hash": self.license_key_hash,
            "tenant_id": self.tenant_id,
            "expires_at": self.expires_at,
            "plan": self.plan,
            "validated_at": self.validated_at,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "error_message": self.error_message,
            "is_valid": self.is_valid,
        }
