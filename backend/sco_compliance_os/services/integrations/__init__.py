"""
sco_compliance_os.services.integrations
========================================

Package del backend SCO Compliance OS dedicato al sistema di connettori
OAuth verso provider esterni (Gmail, Google Calendar, Google Drive, Slack,
GitHub, e roadmap di 50+ connettori).

Architettura:

- ``base.BaseConnector``: classe astratta (ABC) che definisce il contratto
  comune di tutti i connettori.
- ``registry.ConnectorRegistry``: singleton di discovery / lookup.
- ``token_store``: storage cifrato dei token OAuth via OS keyring.
- ``scheduler``: loop di fetch periodico (default 20 min).
- ``gmail_connector``, ``slack_connector``, etc.: implementazioni concrete.

Convenzioni:

- Pattern SCO "single source of truth": i token vivono solo nel
  keyring OS, mai duplicati in DB o filesystem plaintext.
- Pattern Conv. 35 RESEARCH-BEFORE-ACT: ogni connector cita le docs
  ufficiali OAuth del provider come reference nel modulo.

Versione: 0.1.0 (Wave 1 — scaffolding 5 connettori stub).
"""

__version__ = "0.1.0"

__all__ = [
    "__version__",
]
