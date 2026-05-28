"""Estrazione preferenze utente da messaggi chat via regex patterns.

Architettura clean-room ispirata al pattern OpenHuman user_profile.rs (no copia
codice GPL): 20 regex Italian-first + English equivalent applicati su sentence
boundaries, normalizzazione slug kebab-case, dedupe by slug, cap 5 preferenze
per turn ordinate per confidence DESC.

Pattern Conv. 35 (verifica fonti + esempi): ogni regex documentato con almeno
2 esempi italiani + 2 inglesi nel docstring per validazione semantica.
Pattern Conv. 41 (tracciatura): logger.info per ogni extraction con count.

Esempio uso:
    >>> from sco_compliance_os.services.learning import extract_preferences
    >>> prefs = extract_preferences(
    ...     "Il mio nome e Antonio. Preferisco risposte in italiano."
    ... )
    >>> for p in prefs:
    ...     print(p.category, p.slug, p.text)
    ProfileCategory.identity name-antonio Il mio nome e Antonio
    ProfileCategory.preference preferisco-risposte-in-italiano Preferisco risposte in italiano
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from sco_compliance_os.core.logging_setup import get_logger

logger = get_logger(__name__)


class ProfileCategory(StrEnum):
    """Categoria di preferenza utente estratta.

    - identity: chi e l'utente (nome, ruolo, professione, organizzazione)
    - preference: cosa preferisce (stile, formato, tono, lingua)
    - aversion: cosa NON vuole (esclusioni, divieti)
    - fact: fatto contestuale stabile (timezone, lingua nativa, paese)
    - stack: stack tecnico in uso (tool, framework, OS, editor)
    """

    identity = "identity"
    preference = "preference"
    aversion = "aversion"
    fact = "fact"
    stack = "stack"


@dataclass
class Preference:
    """Preferenza utente estratta da un messaggio chat.

    Attributes:
        text: testo originale della sentence (max 240 char, troncato).
        slug: identificativo kebab-case derivato dal match regex + parole chiave.
        category: ProfileCategory enum di appartenenza.
        confidence: 0.0-1.0, peso del pattern (preferenze identita > generiche).
        extracted_at: timestamp UTC dell'estrazione.
        source_turn_id: ID turno chat (conversation+message) opzionale per audit.
    """

    text: str
    slug: str
    category: ProfileCategory
    confidence: float = 0.7
    extracted_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source_turn_id: str | None = None


# ----- Pattern registry: 20 regex Italian-first + English -----

# Ogni pattern e una tupla:
#   (regex_compiled, category, confidence, slug_prefix)
# La regex DEVE catturare nel gruppo 1 il "valore" o "specificita" della
# preferenza (es. nel match "preferisco risposte in italiano" il gruppo 1
# cattura "risposte in italiano"). Se la regex non ha gruppi, slug = slug_prefix.

# Esempi e razionale per ogni regex sono documentati inline nei commenti
# (Conv. 35 enforcement: minimo 2 IT + 2 EN per ogni pattern).


def _ci(pattern: str) -> re.Pattern[str]:
    """Helper: compila regex case-insensitive + dotall False (per sentence-level)."""
    return re.compile(pattern, re.IGNORECASE)


PATTERNS: list[tuple[re.Pattern[str], ProfileCategory, float, str]] = [
    # 1. Identita: nome
    # IT: "Il mio nome e Mario", "Mi chiamo Antonio"
    # EN: "My name is John", "I am called Sarah"
    (
        _ci(
            r"(?:il mio nome\s+(?:e|è)|mi chiamo|my name is|i am called|i'm called)\s+([\w\s'-]{2,60})"
        ),
        ProfileCategory.identity,
        0.95,
        "name",
    ),
    # 2. Identita: ruolo / professione
    # IT: "Lavoro come consulente", "Sono un ingegnere"
    # EN: "I work as a developer", "I am a doctor"
    (
        _ci(
            r"(?:lavoro come|sono un[oa]?|faccio il|i work as|i am an?|i'm an?)\s+([\w\s'-]{3,80})"
        ),
        ProfileCategory.identity,
        0.85,
        "role",
    ),
    # 3. Identita: organizzazione / azienda
    # IT: "La mia azienda e SCO Consulting", "Lavoro per Fortibyte"
    # EN: "My company is Acme", "I work for Google"
    (
        _ci(
            r"(?:la mia azienda\s+(?:e|è)|lavoro per|my company is|i work for|i work at)\s+([\w\s\.,'-]{2,80})"
        ),
        ProfileCategory.identity,
        0.85,
        "organization",
    ),
    # 4. Preferenza esplicita generica
    # IT: "Preferisco il formato breve", "Mi piace la sintesi puntuale"
    # EN: "I prefer concise answers", "I like markdown"
    (
        _ci(
            r"(?:preferisco|mi piace|prediligo|i prefer|i like|i'd like)\s+([\w\s'\.\-àèéìòù]{3,150})"
        ),
        ProfileCategory.preference,
        0.75,
        "preferisco",
    ),
    # 5. Aversion esplicita
    # IT: "Non voglio bullet list", "Odio le emoji decorative"
    # EN: "I don't want long intros", "I hate filler"
    (
        _ci(
            r"(?:non voglio|non mi piace|odio|detesto|i don'?t want|i don'?t like|i hate)\s+([\w\s'\.\-àèéìòù]{3,150})"
        ),
        ProfileCategory.aversion,
        0.85,
        "non-voglio",
    ),
    # 6. Regola permanente ("da adesso in poi", "sempre")
    # IT: "Sempre rispondi in italiano", "D'ora in poi usa virgolette dritte"
    # EN: "Always respond in English", "From now on use markdown"
    (
        _ci(
            r"(?:sempre|d'?ora in poi|da (?:adesso|ora) in poi|always|from now on)[\s,:]+([\w\s'\.\-àèéìòù]{3,150})"
        ),
        ProfileCategory.preference,
        0.90,
        "regola-sempre",
    ),
    # 7. Divieto permanente ("mai")
    # IT: "Mai usare caporali", "Mai introduzioni lunghe"
    # EN: "Never use bullet points", "Never start with greetings"
    (
        _ci(r"(?:mai\s+(?:usare\s+|fare\s+)?|never\s+(?:use\s+|do\s+)?)([\w\s'\.\-àèéìòù]{3,150})"),
        ProfileCategory.aversion,
        0.90,
        "regola-mai",
    ),
    # 8. Fact: timezone / fuso orario
    # IT: "Il mio fuso orario e Europe/Rome", "Sono in Italia"
    # EN: "My timezone is UTC+1", "I'm in PST"
    (
        _ci(
            r"(?:il mio fuso orario\s+(?:e|è)|sono in|my timezone is|i'?m in)\s+([\w/+\-:\s]{2,40})"
        ),
        ProfileCategory.fact,
        0.80,
        "timezone",
    ),
    # 9. Fact: lingua preferita / nativa
    # IT: "La mia lingua e italiano", "Parlo italiano"
    # EN: "My language is English", "I speak French"
    (
        _ci(r"(?:la mia lingua\s+(?:e|è)|parlo|my language is|i speak)\s+([\w\s,'-]{2,60})"),
        ProfileCategory.fact,
        0.85,
        "language",
    ),
    # 10. Stack: tecnologie usate
    # IT: "Il mio stack e Python e FastAPI", "Uso TypeScript e React"
    # EN: "My stack is Node and Express", "I use Rust and Tauri"
    (
        _ci(
            r"(?:il mio stack\s+(?:e|è)|uso|utilizzo|my stack is|i use|i'?m using)\s+([\w\s,'\.+\-#]{3,150})"
        ),
        ProfileCategory.stack,
        0.80,
        "stack",
    ),
    # 11. Stack: editor / IDE
    # IT: "Il mio editor e VSCode", "Lavoro con Cursor"
    # EN: "My editor is Vim", "I work with IntelliJ"
    (
        _ci(
            r"(?:il mio editor\s+(?:e|è)|lavoro con|my editor is|i work with)\s+([\w\s,'\.+\-#]{2,60})"
        ),
        ProfileCategory.stack,
        0.75,
        "editor",
    ),
    # 12. Stack: sistema operativo
    # IT: "Il mio OS e Windows 11", "Uso macOS"
    # EN: "My OS is Linux", "I'm on Ubuntu"
    (
        _ci(
            r"(?:il mio (?:os|sistema operativo)\s+(?:e|è)|my os is|i'?m on)\s+([\w\s,'\.+\-#]{2,40})"
        ),
        ProfileCategory.stack,
        0.80,
        "os",
    ),
    # 13. Preferenza tono / registro comunicativo
    # IT: "Voglio un tono formale", "Preferisco uno stile diretto"
    # EN: "I want a casual tone", "Use a formal style"
    (
        _ci(
            r"(?:voglio un tono|preferisco uno stile|use a\s+\w+\s+tone|i want a\s+\w+\s+tone)\s+([\w\s'\.\-àèéìòù]{3,80})"
        ),
        ProfileCategory.preference,
        0.80,
        "tono",
    ),
    # 14. Preferenza formato risposta
    # IT: "Rispondi in markdown", "Voglio risposte brevi"
    # EN: "Answer in JSON", "I want short answers"
    (
        _ci(
            r"(?:rispondi in|voglio risposte|answer in|i want\s+\w+\s+answers?|reply in)\s+([\w\s,'\.\-àèéìòù]{3,80})"
        ),
        ProfileCategory.preference,
        0.80,
        "formato",
    ),
    # 15. Preferenza lunghezza
    # IT: "Sii conciso", "Sii dettagliato"
    # EN: "Be concise", "Be verbose"
    (
        _ci(
            r"\b(?:sii|be)\s+(conciso|breve|dettagliato|verboso|sintetico|prolisso|concise|verbose|brief|detailed|terse)\b"
        ),
        ProfileCategory.preference,
        0.75,
        "lunghezza",
    ),
    # 16. Fact: paese / regione
    # IT: "Abito in Italia", "Vivo a Roma"
    # EN: "I live in Spain", "I'm based in Berlin"
    (
        _ci(r"(?:abito (?:in|a)|vivo (?:in|a)|i live in|i'?m based in)\s+([\w\s,'-]{2,60})"),
        ProfileCategory.fact,
        0.80,
        "location",
    ),
    # 17. Preferenza esempi / casi pratici
    # IT: "Voglio esempi concreti", "Dammi casi reali"
    # EN: "I want real examples", "Give me concrete cases"
    (
        _ci(
            r"(?:voglio esempi|dammi (?:esempi|casi)|i want\s+\w*\s*examples?|give me\s+\w*\s*(?:examples?|cases?))\s*([\w\s'\.\-àèéìòù]{0,100})"
        ),
        ProfileCategory.preference,
        0.70,
        "esempi",
    ),
    # 18. Identita: titolo professionale strutturato
    # IT: "Il mio ruolo e Lead Auditor", "Il mio titolo e CTO"
    # EN: "My role is Architect", "My title is Director"
    (
        _ci(
            r"(?:il mio (?:ruolo|titolo)\s+(?:e|è)|my (?:role|title) is)\s+([\w\s,'\.\-àèéìòù]{2,80})"
        ),
        ProfileCategory.identity,
        0.90,
        "title",
    ),
    # 19. Stack: repository / progetto principale
    # IT: "Il mio progetto principale e sco-compliance-os", "Sviluppo Compliance Copilot"
    # EN: "My main project is acme-api", "I'm building Foo"
    (
        _ci(
            r"(?:il mio progetto principale\s+(?:e|è)|sviluppo|my main project is|i'?m building)\s+([\w\s,'\.\-#+]{2,80})"
        ),
        ProfileCategory.stack,
        0.75,
        "project",
    ),
    # 20. Preferenza referenze / citazioni
    # IT: "Cita le fonti", "Includi riferimenti normativi puntuali"
    # EN: "Cite sources", "Include references"
    (
        _ci(
            r"\b(?:cita (?:le )?fonti|includi (?:riferimenti|citazioni)|cite (?:the )?sources?|include references?)\b([\w\s'\.\-àèéìòù]{0,100})"
        ),
        ProfileCategory.preference,
        0.80,
        "citazioni",
    ),
]


# ----- Normalizzazione slug -----


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_DASH_DEDUP_RE = re.compile(r"-+")


def _slugify(text: str, max_len: int = 80) -> str:
    """Normalizza una stringa in kebab-case ASCII slug.

    Pipeline: NFKD unicode -> ASCII -> lower -> non-alnum a dash -> trim dash
    -> truncate max_len -> trim dash residuo.

    Esempio:
        >>> _slugify("Risposte in Italiano!")
        'risposte-in-italiano'
        >>> _slugify("ISO/IEC 27001:2022")
        'iso-iec-27001-2022'
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lower = ascii_text.lower().strip()
    dashed = _NON_ALNUM_RE.sub("-", lower)
    dedup = _DASH_DEDUP_RE.sub("-", dashed).strip("-")
    if len(dedup) > max_len:
        dedup = dedup[:max_len].rstrip("-")
    return dedup


def _split_sentences(text: str) -> list[str]:
    """Split testo in sentence usando boundary . ! ? newline.

    Mantiene punteggiatura nei segmenti per analisi successive (es. distinzione
    "preferisco X" vs "preferisco X?"). Filtra segmenti < 3 char (rumore).
    """
    if not text:
        return []
    # Split su .!?\n manteniamo separatori opzionali ma puliamo whitespace
    raw = re.split(r"[.!?\n]+", text)
    return [s.strip() for s in raw if s and len(s.strip()) >= 3]


def _truncate(text: str, max_len: int = 240) -> str:
    """Tronca testo preservando word boundary se possibile."""
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    last_space = cut.rfind(" ")
    if last_space > max_len * 0.7:
        return cut[:last_space].rstrip()
    return cut.rstrip()


# ----- API pubblica -----


def extract_preferences(
    message_text: str,
    *,
    source_turn_id: str | None = None,
    cap: int = 5,
) -> list[Preference]:
    """Estrae preferenze utente da un messaggio chat.

    Pipeline:
        1. Split testo in sentence (boundary . ! ? newline).
        2. Per ogni sentence, prova ogni regex pattern (case-insensitive).
        3. Costruisci Preference con slug normalizzato + confidence pattern.
        4. Dedupe by slug (mantieni quella con confidence maggiore).
        5. Sort confidence DESC, cap a `cap` preferenze (default 5).

    Args:
        message_text: testo grezzo del messaggio utente.
        source_turn_id: ID turno chat (es. "conv_<uuid>__msg_<uuid>") opzionale.
        cap: numero massimo preferenze restituite (default 5, raccomandato).

    Returns:
        Lista di Preference, ordinate per confidence DESC, max `cap` elementi.

    Esempio:
        >>> prefs = extract_preferences("Mi chiamo Antonio. Preferisco italiano.")
        >>> [p.category.value for p in prefs]
        ['identity', 'preference']
    """
    if not message_text or not message_text.strip():
        return []

    sentences = _split_sentences(message_text)
    if not sentences:
        return []

    candidates: list[Preference] = []
    now = datetime.now(UTC)

    for sentence in sentences:
        for regex, category, confidence, slug_prefix in PATTERNS:
            match = regex.search(sentence)
            if not match:
                continue
            # Cattura gruppo 1 se presente, altrimenti tutta la sentence
            captured = match.group(1).strip() if match.groups() and match.group(1) else ""
            if captured:
                slug_body = _slugify(captured, max_len=60)
                slug = f"{slug_prefix}-{slug_body}" if slug_body else slug_prefix
            else:
                slug = slug_prefix
            slug = slug.strip("-")[:80]
            if not slug:
                continue
            candidates.append(
                Preference(
                    text=_truncate(sentence),
                    slug=slug,
                    category=category,
                    confidence=confidence,
                    extracted_at=now,
                    source_turn_id=source_turn_id,
                )
            )

    if not candidates:
        logger.info(
            "learning.profile.extracted",
            count=0,
            message_len=len(message_text),
            source_turn_id=source_turn_id,
        )
        return []

    # Dedupe by slug: mantieni quella con confidence maggiore
    by_slug: dict[str, Preference] = {}
    for pref in candidates:
        existing = by_slug.get(pref.slug)
        if existing is None or pref.confidence > existing.confidence:
            by_slug[pref.slug] = pref

    deduped = list(by_slug.values())
    # Sort confidence DESC, tiebreak alfabetico slug
    deduped.sort(key=lambda p: (-p.confidence, p.slug))
    result = deduped[:cap]

    logger.info(
        "learning.profile.extracted",
        count=len(result),
        candidates=len(candidates),
        unique_slugs=len(deduped),
        message_len=len(message_text),
        source_turn_id=source_turn_id,
    )
    return result
