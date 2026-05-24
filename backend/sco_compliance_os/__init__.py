"""SCO Compliance OS — backend package.

App desktop AI assistant brandata SCO per consulenza compliance e normativa.
Pacchetto clean-room scritto da zero. Vedi LICENSE alla root del repo.

Hidden imports candidates per PyInstaller (Conv. 44 lesson 3 enforcement,
da dichiarare nel .spec quando si genererà il sidecar bundle):
- email_validator
- dns, dns.resolver
- idna
- anthropic._client
- claude_agent_sdk
- mcp
- sqlalchemy.dialects.sqlite.aiosqlite
"""

from __future__ import annotations

__version__ = "0.6.0"
__author__ = "Antonio Silvestro Amodeo"
__all__ = ["__author__", "__version__"]
