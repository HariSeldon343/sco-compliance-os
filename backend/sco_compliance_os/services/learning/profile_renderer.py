"""Renderer markdown del profilo utente per injection in system prompt.

Genera markdown strutturato a 5 sezioni (Identita / Preferenze / Aversioni /
Fatti / Stack tecnico), con cap totale 2000 caratteri. Se sforato, prioritizza
le sezioni con piu pinned + piu seen_count (gia ordinate da list_preferences()).

Pattern Conv. 41 tracciatura: count totale + char totali loggati.
Pattern Conv. 48 SINGLE SOURCE OF TRUTH: input deve essere lista gia fetched
dal profile_store, NON ri-fetcha dal DB qui (separation of concerns).
"""

from __future__ import annotations

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.learning.user_profile import (
    Preference,
    ProfileCategory,
)

logger = get_logger(__name__)


_MAX_TOTAL_CHARS = 2000
_SECTION_TITLES: dict[ProfileCategory, str] = {
    ProfileCategory.identity: "Identita",
    ProfileCategory.preference: "Preferenze",
    ProfileCategory.aversion: "Aversioni",
    ProfileCategory.fact: "Fatti",
    ProfileCategory.stack: "Stack tecnico",
}

# Ordine di sezioni nel markdown output (identita prima, stack ultimo)
_SECTION_ORDER: list[ProfileCategory] = [
    ProfileCategory.identity,
    ProfileCategory.preference,
    ProfileCategory.aversion,
    ProfileCategory.fact,
    ProfileCategory.stack,
]


def _group_by_category(
    preferences: list[Preference],
) -> dict[ProfileCategory, list[Preference]]:
    """Raggruppa preferenze per categoria preservando ordine input.

    L'ordine input riflette gia priority (pinned DESC, seen_count DESC) dal
    profile_store, quindi NON ri-ordinare qui — pattern SCO single
    source of truth per ranking.
    """
    grouped: dict[ProfileCategory, list[Preference]] = {cat: [] for cat in _SECTION_ORDER}
    for pref in preferences:
        grouped[pref.category].append(pref)
    return grouped


def _render_section(
    category: ProfileCategory,
    items: list[Preference],
    *,
    available_chars: int,
) -> tuple[str, int]:
    """Renderizza una singola sezione markdown rispettando budget caratteri.

    Args:
        category: ProfileCategory della sezione.
        items: lista preferenze gia filtered + ordinate.
        available_chars: budget caratteri residuo per questa sezione.

    Returns:
        (markdown_section, chars_consumed).
    """
    if not items or available_chars <= 0:
        return "", 0

    title = _SECTION_TITLES[category]
    header = f"### {title}\n"
    if len(header) > available_chars:
        return "", 0

    lines: list[str] = [header]
    consumed = len(header)

    for pref in items:
        # Marker pinned per visibilita modello (preferenza esplicita utente)
        line = f"- {pref.text}\n"
        if consumed + len(line) > available_chars:
            # Trunca se ultima riga + nota "+N altre" se ci sono altre
            remaining = len(items) - (lines.__len__() - 1)
            if remaining > 0:
                ellipsis = f"- ... e altre {remaining} preferenze in archivio\n"
                if consumed + len(ellipsis) <= available_chars:
                    lines.append(ellipsis)
                    consumed += len(ellipsis)
            break
        lines.append(line)
        consumed += len(line)

    return "".join(lines), consumed


def render_profile_markdown(
    preferences: list[Preference],
    *,
    max_chars: int = _MAX_TOTAL_CHARS,
) -> str:
    """Renderizza profilo utente come markdown per system prompt injection.

    Output strutturato a 5 sezioni (Identita / Preferenze / Aversioni / Fatti /
    Stack tecnico), cap totale `max_chars` (default 2000). Se sforato, prima
    sezione drop e la sezione viene marcata "+N altre preferenze in archivio".

    Args:
        preferences: lista Preference gia fetched + ordinata per display priority.
            Pattern Conv. 48: il caller deve aver chiamato list_preferences()
            prima di passare a questa funzione. Niente DB fetch qui.
        max_chars: budget totale caratteri output (default 2000).

    Returns:
        Stringa markdown pronta per prepend a system prompt LLM. Vuota se
        input vuoto o se non c'e budget sufficiente per il titolo.

    Esempio:
        >>> from sco_compliance_os.services.learning import Preference, ProfileCategory
        >>> prefs = [
        ...     Preference(text="Antonio Amodeo", slug="name-antonio",
        ...                category=ProfileCategory.identity, confidence=0.95),
        ...     Preference(text="Preferisco italiano", slug="preferisco-italiano",
        ...                category=ProfileCategory.preference, confidence=0.85),
        ... ]
        >>> md = render_profile_markdown(prefs)
        >>> "## Profilo utente" in md
        True
        >>> "Antonio Amodeo" in md
        True
    """
    if not preferences:
        return ""

    top_header = "## Profilo utente\n\n"
    if len(top_header) > max_chars:
        return ""

    parts: list[str] = [top_header]
    consumed = len(top_header)

    grouped = _group_by_category(preferences)

    for category in _SECTION_ORDER:
        items = grouped.get(category, [])
        if not items:
            continue
        available = max_chars - consumed
        # Separatore newline tra sezioni (skip per la prima)
        sep = "\n" if len(parts) > 1 else ""
        if available <= len(sep) + 10:
            break
        section_md, section_chars = _render_section(
            category,
            items,
            available_chars=available - len(sep),
        )
        if section_md:
            parts.append(sep + section_md)
            consumed += len(sep) + section_chars

    output = "".join(parts).rstrip() + "\n"

    logger.info(
        "learning.profile.rendered",
        preferences_count=len(preferences),
        output_chars=len(output),
        max_chars=max_chars,
        truncated=consumed >= max_chars - 50,
    )
    return output
