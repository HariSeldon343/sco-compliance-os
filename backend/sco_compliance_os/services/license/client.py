"""HTTP client per validazione license key verso SaaS sco-saas-claude.

Endpoint contract:
    POST https://sco-saas-claude.vercel.app/api/v1/license/validate
    Headers: Content-Type: application/json
    Body: {"email": "user@example.com", "license_key": "SCO-XXX-YYY-ZZZ"}

Response 200 (valid):
    {
        "status": "valid",
        "tenant_id": "tnt_abc123",
        "expires_at": "2027-01-01T00:00:00Z",
        "plan": "pro"
    }

Response 401 (invalid):
    {"status": "invalid", "error": "license_key not found"}

Response 403 (revoked):
    {"status": "revoked", "error": "license revoked by admin", "revoked_at": "..."}

Response 410 (expired):
    {"status": "expired", "error": "license expired", "expired_at": "..."}

Cache: result memorizzato in ~/.sco-compliance-os/license-cache.json con TTL 24h.
Se SaaS irraggiungibile + cache valida + < 24h → grace period, app continua.
Se SaaS irraggiungibile + cache scaduta → mostra LicenseInvalidScreen.

Pattern SCO "no hallucination": mai inventare validità. Se network down
e cache scaduta, status = NETWORK_ERROR esplicito (frontend mostra retry button).
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import httpx

from sco_compliance_os.services.license.models import (
    LicenseStatus,
    LicenseValidationResult,
)

logger = logging.getLogger(__name__)


DEFAULT_SAAS_BASE_URL = "https://sco-saas-claude.vercel.app"
DEFAULT_CACHE_TTL_SECONDS = 86400  # 24h
DEFAULT_TIMEOUT_SECONDS = 10.0


class LicenseValidationError(Exception):
    """Eccezione per errori validazione license."""

    def __init__(self, message: str, status: LicenseStatus = LicenseStatus.UNKNOWN):
        super().__init__(message)
        self.status = status


def _hash_license_key(license_key: str) -> str:
    """SHA256 hash della license key per logging sicuro."""
    return hashlib.sha256(license_key.encode("utf-8")).hexdigest()[:16]


def _cache_path() -> Path:
    """Path del file cache license."""
    return Path.home() / ".sco-compliance-os" / "license-cache.json"


class LicenseClient:
    """Client HTTP per validazione license verso SaaS sco-saas-claude."""

    def __init__(
        self,
        saas_base_url: str = DEFAULT_SAAS_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        self.saas_base_url = saas_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds

    async def validate(
        self,
        email: str,
        license_key: str,
        *,
        force_refresh: bool = False,
    ) -> LicenseValidationResult:
        """Valida license key verso SaaS + cache locale 24h.

        Args:
            email: email cliente.
            license_key: chiave license fornita dal cliente.
            force_refresh: se True, salta cache e chiama sempre il SaaS.

        Returns:
            LicenseValidationResult con status (VALID/INVALID/REVOKED/EXPIRED/NETWORK_ERROR).
        """
        license_hash = _hash_license_key(license_key)

        # Tenta cache prima (se non force_refresh)
        if not force_refresh:
            cached = self._read_cache(email, license_hash)
            if cached and self._is_cache_fresh(cached):
                logger.info(
                    "license.cache.hit | email=%s license_hash=%s status=%s",
                    email,
                    license_hash,
                    cached.status.value,
                )
                return cached

        # Chiama SaaS
        try:
            result = await self._call_saas(email, license_key, license_hash)
            self._write_cache(email, license_hash, result)
            return result
        except httpx.RequestError as exc:
            # Network error: prova fallback cache anche se scaduta (grace period)
            logger.warning(
                "license.saas.network_error | email=%s err=%s — trying cache fallback",
                email,
                exc,
            )
            cached = self._read_cache(email, license_hash)
            if cached and cached.is_valid:
                # Grace period: license era valida ultima volta, concediamo continuità
                logger.warning(
                    "license.grace_period | email=%s license_hash=%s",
                    email,
                    license_hash,
                )
                cached.status = LicenseStatus.NETWORK_ERROR
                cached.error_message = (
                    f"SaaS irraggiungibile ({exc}), uso cache valida (grace period)"
                )
                return cached
            return LicenseValidationResult(
                status=LicenseStatus.NETWORK_ERROR,
                email=email,
                license_key_hash=license_hash,
                error_message=f"SaaS irraggiungibile: {exc}",
            )

    async def _call_saas(
        self, email: str, license_key: str, license_hash: str
    ) -> LicenseValidationResult:
        """Chiama POST /api/v1/license/validate sul SaaS."""
        url = f"{self.saas_base_url}/api/v1/license/validate"
        payload = {"email": email, "license_key": license_key}

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "sco-compliance-os/0.1.0",
                },
            )

        # Parse response
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError):
            data = {}

        if response.status_code == 200 and data.get("status") == "valid":
            return LicenseValidationResult(
                status=LicenseStatus.VALID,
                email=email,
                license_key_hash=license_hash,
                tenant_id=str(data.get("tenant_id", "")),
                expires_at=str(data.get("expires_at", "")),
                plan=str(data.get("plan", "starter")),
                cache_ttl_seconds=self.cache_ttl_seconds,
            )
        elif response.status_code == 401:
            return LicenseValidationResult(
                status=LicenseStatus.INVALID,
                email=email,
                license_key_hash=license_hash,
                error_message=str(data.get("error", "License key non valida")),
            )
        elif response.status_code == 403:
            return LicenseValidationResult(
                status=LicenseStatus.REVOKED,
                email=email,
                license_key_hash=license_hash,
                error_message=str(data.get("error", "License revocata")),
            )
        elif response.status_code == 410:
            return LicenseValidationResult(
                status=LicenseStatus.EXPIRED,
                email=email,
                license_key_hash=license_hash,
                error_message=str(data.get("error", "License scaduta")),
            )
        else:
            return LicenseValidationResult(
                status=LicenseStatus.UNKNOWN,
                email=email,
                license_key_hash=license_hash,
                error_message=f"Risposta inattesa SaaS: HTTP {response.status_code}",
            )

    def _is_cache_fresh(self, cached: LicenseValidationResult) -> bool:
        """True se cache è entro TTL."""
        try:
            validated_at = datetime.fromisoformat(cached.validated_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        age = datetime.now(UTC) - validated_at
        return age < timedelta(seconds=cached.cache_ttl_seconds)

    def _read_cache(self, email: str, license_hash: str) -> LicenseValidationResult | None:
        """Legge cache JSON locale, ritorna result se exists per email+hash."""
        cache_file = _cache_path()
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            key = f"{email}:{license_hash}"
            entry = data.get(key)
            if not entry:
                return None
            return LicenseValidationResult(
                status=LicenseStatus(entry["status"]),
                email=entry["email"],
                license_key_hash=entry["license_key_hash"],
                tenant_id=entry.get("tenant_id", ""),
                expires_at=entry.get("expires_at", ""),
                plan=entry.get("plan", ""),
                validated_at=entry.get("validated_at", ""),
                cache_ttl_seconds=entry.get("cache_ttl_seconds", DEFAULT_CACHE_TTL_SECONDS),
                error_message=entry.get("error_message", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("license.cache.read_error | err=%s", exc)
            return None

    def _write_cache(self, email: str, license_hash: str, result: LicenseValidationResult) -> None:
        """Scrive result in cache JSON locale."""
        cache_file = _cache_path()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
        key = f"{email}:{license_hash}"
        data[key] = result.to_dict()
        cache_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


@lru_cache(maxsize=1)
def get_license_client() -> LicenseClient:
    """Singleton LicenseClient con settings da env."""
    import os

    saas_url = os.environ.get("SCO_SAAS_BASE_URL", DEFAULT_SAAS_BASE_URL)
    return LicenseClient(saas_base_url=saas_url)
