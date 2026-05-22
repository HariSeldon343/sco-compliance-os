# Aggiungere un nuovo connettore — guida contributor

Guida per aggiungere un nuovo connettore al sistema `@sco/integrations`. Pattern stabile: si segue lo schema definito da `BaseConnector` (vedi `backend/sco_compliance_os/services/integrations/base.py`).

## Prerequisiti

1. **OAuth App registrata sul provider**: hai un `client_id` + `client_secret` rilasciato dal provider (es. Google Cloud Console, Slack App Directory, GitHub Developer Settings).
2. **Redirect URI configurata**: tipicamente `http://localhost:7777/api/integrations/callback` per l'app desktop locale (porta backend sidecar).
3. **Scopes minimi identificati**: studia le docs ufficiali del provider e scegli il **set minimo** di scopes per le feature che vuoi supportare. Pattern: principle of least privilege.
4. **Docs ufficiali lette** (Conv. 35 RESEARCH-BEFORE-ACT): NON inventare endpoint OAuth. Cita link docs nel modulo Python.

## Checklist creazione nuovo connector

```
[ ] 1. Provider OAuth app registrata + scopes scelti documentati
[ ] 2. File nuovo: backend/sco_compliance_os/services/integrations/<provider>_connector.py
[ ] 3. Classe eredita da BaseConnector e dichiara tutti i ClassVar (slug, name, category, oauth_provider, scopes_required, auth_url_template, token_url)
[ ] 4. Decorata con @connector per auto-registration nel registry
[ ] 5. Implementa start_oauth_flow() con urlencode parametri standard OAuth 2.0
[ ] 6. Implementa handle_callback() con scambio code → token (TODO Wave 2: httpx reale, ora STUB)
[ ] 7. Implementa refresh_token_if_needed() con gestione is_expired() + missing refresh_token
[ ] 8. Implementa fetch_data() con paginazione + parsing payload (TODO Wave 2)
[ ] 9. Implementa disconnect() con revoke endpoint (se il provider lo espone)
[ ] 10. Error handling: catch errori HTTP e wrap in OAuthError con code semantico
[ ] 11. Test stub: aggiungere unit test in backend/tests/services/integrations/test_<provider>.py
[ ] 12. Aggiornare README.md "Roadmap connettori" — spostare riga in "Wave attuale"
[ ] 13. Aggiornare types.ts se serve nuovo OAuthProvider literal type
[ ] 14. Documentare scopes_required scelti come commento in cima al file
[ ] 15. CI verde + smoke test E2E (Conv. 46 enforcement)
```

## Template skeleton (copy-paste)

```python
"""
<provider>_connector.py — Connector OAuth per <Provider>.

Provider: <Provider>
Scopes:
    - ``<scope1>`` — <descrizione>
    - ``<scope2>`` — <descrizione>

Docs ufficiali (Pattern Conv. 35 RESEARCH-BEFORE-ACT):
    - <Provider> OAuth flow: <URL docs>
    - <Provider> API endpoint principale: <URL docs>

Wave <N> status: STUB.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from .base import BaseConnector, MemoryChunk, OAuthError, OAuthTokens
from .registry import connector

logger = logging.getLogger(__name__)


@connector
class <Provider>Connector(BaseConnector):
    """Connector <Provider> via OAuth 2.0."""

    slug = "<provider_slug>"
    name = "<Provider Display Name>"
    category = "<categoria>"  # email | calendar | storage | code | ...
    oauth_provider = "<provider_key>"
    scopes_required = ["<scope1>", "<scope2>"]
    auth_url_template = "<URL authorize endpoint>"
    token_url = "<URL token endpoint>"
    supports_pkce = False  # True se il provider supporta PKCE

    async def start_oauth_flow(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes_required),
            "state": state,
        }
        return f"{self.auth_url_template}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str) -> OAuthTokens:
        # TODO Wave 2: httpx.AsyncClient.post(token_url, ...)
        raise NotImplementedError("STUB — implementare scambio code → token")

    async def refresh_token_if_needed(self, tokens: OAuthTokens) -> OAuthTokens:
        if not tokens.is_expired():
            return tokens
        raise NotImplementedError("STUB — implementare refresh")

    async def fetch_data(
        self, tokens: OAuthTokens, since: datetime | None = None
    ) -> list[MemoryChunk]:
        # TODO Wave 2: chiamata API provider + parsing
        return []

    async def disconnect(self, tokens: OAuthTokens) -> None:
        # TODO Wave 2: revoke token su provider
        return None
```

## Vincoli di sicurezza

- **MAI** hard-codare `client_id` o `client_secret` nel codice. Le credenziali vivono in env variables o config locale fuori dal repo.
- **MAI** loggare access_token / refresh_token (anche parziali). Solo metadata (provider, user_id, expires_at, scopes).
- **SEMPRE** validare il parametro `state` in `handle_callback()` contro quello generato in `start_oauth_flow()`.
- **SEMPRE** usare HTTPS per redirect_uri in produzione. `http://localhost:*` ammesso solo in dev locale.

## Riferimenti

- `base.py` — contratto astratto
- `registry.py` — auto-registration via `@connector`
- `token_store.py` — storage cifrato keyring
- `scheduler.py` — fetch loop
- `docs/adr/0003-integrations-architecture.md` — razionale architetturale
