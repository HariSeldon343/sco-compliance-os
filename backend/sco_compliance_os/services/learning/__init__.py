"""Learning subsystem — apprendimento progressivo profilo utente.

Architettura clean-room ispirata al pattern OpenHuman user_profile.rs (no copia
codice, solo idea): 20 regex patterns Italian-first + English equivalent
applicati post-turn su messaggi utente, cap 5 preferenze per turn, dedupe by
slug, persistenza SQLite separata da Memory Tree.

Pubblica:
- user_profile: extract_preferences() + Preference dataclass + ProfileCategory enum
- profile_store: upsert/list/delete/pin operations
- profile_renderer: render_profile_markdown() per system prompt injection
"""

from sco_compliance_os.services.learning.profile_renderer import (
    render_profile_markdown,
)
from sco_compliance_os.services.learning.profile_store import (
    delete_preference,
    init_schema,
    list_preferences,
    pin_preference,
    unpin_preference,
    upsert_preference,
)
from sco_compliance_os.services.learning.user_profile import (
    Preference,
    ProfileCategory,
    extract_preferences,
)

__all__ = [
    "Preference",
    "ProfileCategory",
    "delete_preference",
    "extract_preferences",
    "init_schema",
    "list_preferences",
    "pin_preference",
    "render_profile_markdown",
    "unpin_preference",
    "upsert_preference",
]
