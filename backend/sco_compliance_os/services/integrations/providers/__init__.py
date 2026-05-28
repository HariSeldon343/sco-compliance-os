"""
sco_compliance_os.services.integrations.providers
=================================================

Wrapper SDK Google API per i provider Gmail, Google Calendar, Google Drive.
Ogni modulo è isolato dal flow OAuth (gestito da ``..oauth``) e si limita
a wrappare le API REST del provider in funzioni asincrone tipizzate.

Pattern: ogni modulo provider riceve un ``access_token`` valido ottenuto
da ``oauth.get_valid_access_token(provider, tenant_id)`` (che orchestria
auto-refresh trasparente al chiamante).

Architettura layer:

    api/integrations_routes.py
        │
        ▼ richiama
    services/integrations/oauth.py (start/complete/refresh, keyring)
        │
        ▼ access_token valido
    services/integrations/providers/{gmail,gcal,gdrive}.py (REST wrappers)
        │
        ▼ HTTP
    Google API REST endpoints
"""

from __future__ import annotations

__all__ = ["gcal", "gdrive", "gmail"]
