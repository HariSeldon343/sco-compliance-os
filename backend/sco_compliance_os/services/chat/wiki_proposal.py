"""Hook post-message: proposta ingest wiki per allegati / link / search results.

Detecta tre fonti di candidati per ingestion strutturata nel wiki:

    1. Allegati file alla chat (.pdf, .docx, .txt, .md, .yaml, .json, .xlsx)
    2. URL link a fonti istituzionali (eur-lex, normattiva, gazzetta, iso, agid,
       agenas, acn, garante, enisa, aifa, ema, snlg-iss, ecc.)
    3. Risultati di web_search tool eseguiti dall'agente (lista hits con url +
       title + snippet)

Classifica ogni candidato verso una delle 6 destinazioni wiki SCO:

    - sources         (deposito raw + scheda di sintesi)
    - entities        (atto-normativo / standard / autorita / linea-guida /
                       metodologia / autore-prassi / soggetto-obbligato / scadenza)
    - concepts        (concetto trasversale cross-cliente, audit risk-based,
                       consenso informato, giustificazione esposizioni mediche)
    - synthesis       (mapping cross-framework: ISO 27001 ↔ NIS 2 Art. 21,
                       confronto requisiti, sintesi cross-standard)
    - glossari        (sigla nuova non glossata, espansione canonica da aggiungere)
    - memory_tree     (chunk generico per cui non si riesce a classificare meglio,
                       fallback)

Genera WikiIngestProposal con destinazione suggerita + slug normalizzato +
frontmatter draft + body summary. La proposta vive solo finchè l'utente non
la conferma o scarta (no persistenza qui — quella avviene a confirm tramite
endpoint REST in api/wiki_routes.py).

Pattern SCO "no hallucination": il classificatore è interamente rule-based
(regex su path + URL + content). Niente LLM dentro al detection layer per
evitare overhead e indeterminismo. Il frontmatter draft popola SOLO i campi
deducibili dalla fonte: entity_type / ambito_canonico si propongono solo se
detectati con confidence alta, altrimenti restano vuoti (l'utente li compila
nel widget WikiIngestProposalCard).

Pattern Conv. 47 single source of truth:
    - WIKI_CATEGORIES dichiarato in services/wiki/parser.py — non duplicato qui.
    - WikiDestination è alias che include WIKI_CATEGORIES + "memory_tree".
    - ENTITY_TYPES / AMBITO_CANONICO da services/vault/parser.py — riusati.

Pattern Conv. 41 tracciatura: ogni analyze_message_for_wiki_ingest logga decisioni
di classificazione (path -> destinazione, score, candidati alternative).

Pattern Conv. 35 verifica fonti: il classificatore privilegia fonti istituzionali
(domain whitelist) sopra fonti generiche (web-clip).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.vault.parser import (
    AMBITO_CANONICO,
    ENTITY_TYPES,
)
from sco_compliance_os.services.wiki.parser import WIKI_CATEGORIES

# v0.13.2 hotfix: questo modulo usa structlog kwargs (proposal_id=..., url=...)
# che sono incompatibili con stdlib `logging.Logger`. Migrato a structlog wrapper
# via `get_logger()` per coerenza con il resto del backend.
logger = get_logger(__name__)


# ----------------------------------------------------------------------------
# COSTANTI — single source of truth (Conv. 47)
# ----------------------------------------------------------------------------

# Destinazione = 5 categorie wiki + 1 fallback memory_tree.
# Type alias literale per autocompletamento + validazione runtime.
WikiDestination = Literal[
    "sources",
    "entities",
    "concepts",
    "synthesis",
    "glossari",
    "memory_tree",
]

# Set utility per verifica runtime (non bloccante, solo logging).
_VALID_DESTINATIONS: frozenset[str] = frozenset(WIKI_CATEGORIES) | {"memory_tree"}

# Domain whitelist fonti istituzionali (Conv. 35 enforcement).
# Quando un URL appartiene a uno di questi domain, alza il confidence score
# del classificatore verso "sources" o "entities".
INSTITUTIONAL_DOMAINS: frozenset[str] = frozenset(
    {
        # UE
        "eur-lex.europa.eu",
        "europa.eu",
        "ec.europa.eu",
        "enisa.europa.eu",
        "ema.europa.eu",
        "edpb.europa.eu",
        # Italia normativa
        "normattiva.it",
        "gazzettaufficiale.it",
        "governo.it",
        # Italia authority
        "agid.gov.it",
        "acn.gov.it",
        "agenas.gov.it",
        "garanteprivacy.it",
        "aifa.gov.it",
        "iss.it",
        "snlg-iss.it",
        "anac.it",
        "consip.it",
        "inps.it",
        "inail.it",
        # Standard
        "iso.org",
        "iec.ch",
        "uni.com",
        "store.uni.com",
        "cen.eu",
        # Internazionali
        "nist.gov",
        "csrc.nist.gov",
        "oecd.org",
        "who.int",
    }
)

# Mapping euristico content keyword -> ambito_canonico canonico.
# Usato per inferire ambito_canonico quando il body o il filename contiene
# pattern chiari. Conservativo: ambiguità -> nessuna proposta (campo vuoto).
_AMBITO_KEYWORD_MAP: dict[str, frozenset[str]] = {
    "cybersicurezza": frozenset(
        {"nis 2", "nis2", "iso 27001", "iso/iec 27001", "csirt", "acn", "cybersicurezza"}
    ),
    "governance-ai": frozenset({"ai act", "iso 42001", "ai system", "intelligenza artificiale"}),
    "privacy-protezione-dati": frozenset(
        {"gdpr", "privacy", "dpia", "trattamento dati personali", "garante privacy"}
    ),
    "accreditamento-sanitario": frozenset(
        {"accreditamento", "irccs", "asl", "drg", "ospedale", "sanitario"}
    ),
    "dispositivi-medici": frozenset({"mdr", "ivdr", "dispositivo medico", "ce marking medical"}),
    "radioprotezione": frozenset(
        {"radioprotezione", "esposizione medica", "irradiazione", "d.lgs. 101/2020"}
    ),
    "sicurezza-lavoro": frozenset({"81/2008", "rspp", "dvr", "duvri", "asr", "salute e sicurezza"}),
    "farmacovigilanza": frozenset(
        {"farmacovigilanza", "gdp", "good distribution practice", "mah", "ema"}
    ),
    "service-management-ict": frozenset(
        {"iso 20000", "itil", "service management", "service level agreement"}
    ),
    "appalti-pubblici": frozenset({"appalti", "36/2023", "rup", "consip", "mepa", "anac", "gara"}),
    "prevenzione-incendi": frozenset(
        {"prevenzione incendi", "uni 9795", "en 54", "decreto controlli", "codice pi"}
    ),
    "compliance-231": frozenset({"231/2001", "modello organizzativo", "odv", "reati presupposto"}),
    "qualita-sgq": frozenset({"iso 9001", "sgq", "sistema qualita", "qualita"}),
    "gestione-ambientale": frozenset({"iso 14001", "emas", "152/2006", "testo unico ambiente"}),
    "sicurezza-alimentare": frozenset(
        {"haccp", "852/2004", "sicurezza alimentare", "igiene alimenti"}
    ),
    "responsabilita-sociale": frozenset({"sa 8000", "responsabilita sociale", "iso 26000"}),
}

# Regex per riferimenti normativi italiani / europei.
# Match es: "D.Lgs. 138/2024", "Reg. UE 2024/1689", "ISO/IEC 27001:2022",
# "L. 90/2024", "DM 1/9/2021", "DPR 151/2011", "Art. 24 D.Lgs. 138/2024".
_NORMATIVE_REGEXES: list[tuple[str, re.Pattern[str]]] = [
    (
        "decreto-legislativo",
        re.compile(r"\bD\.?\s?Lgs\.?\s*\d+\s*/\s*\d{4}", re.IGNORECASE),
    ),
    (
        "legge-statale",
        re.compile(r"\b(?:L\.|Legge)\s*\d+\s*/\s*\d{4}", re.IGNORECASE),
    ),
    (
        "regolamento-ue",
        re.compile(r"\bReg\.?\s*UE\s*\d{4}\s*/\s*\d+", re.IGNORECASE),
    ),
    (
        "direttiva-ue",
        re.compile(r"\bDir\.?\s*(?:UE\s*)?\d{4}\s*/\s*\d+", re.IGNORECASE),
    ),
    (
        "iso-iec",
        re.compile(r"\bISO(?:/IEC)?\s*\d{4,5}(?:[-:]\d+)?(?::\d{4})?", re.IGNORECASE),
    ),
    (
        "dpr",
        re.compile(r"\bDPR\s*\d+\s*/\s*\d{4}", re.IGNORECASE),
    ),
    (
        "dm",
        re.compile(r"\bDM\s*\d{1,3}\s*/\s*\d{1,2}\s*/\s*\d{4}", re.IGNORECASE),
    ),
]

# Acronym detector: sequenze 2-6 lettere maiuscole (con isolatori di word).
# Esclude false-positive in URL (filtrati a monte) o in code block (Markdown
# fence tracking è fuori scope qui — assumiamo content pulito).
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,6}\b")

# Mapping mime / extension utile per classificazione attachment.
_DOC_EXTENSIONS_NORMATIVE: frozenset[str] = frozenset({".pdf", ".docx"})
_DOC_EXTENSIONS_TEXTUAL: frozenset[str] = frozenset({".md", ".txt"})
_DOC_EXTENSIONS_STRUCTURED: frozenset[str] = frozenset({".json", ".yaml", ".yml", ".xlsx"})

# Slug normalizzazione: lowercase + dash + max 80 char.
_SLUG_MAX_LEN = 80
_SLUG_SAFE_RE = re.compile(r"[^a-z0-9\-]+")


# ----------------------------------------------------------------------------
# DATACLASSES — proposal model
# ----------------------------------------------------------------------------


@dataclass(slots=True)
class WikiIngestSlot:
    """Un singolo candidato per ingest wiki (allegato, URL o search result)."""

    source_type: Literal["attachment", "url", "search_result"]
    title: str
    # Identificatore: per attachment = path filesystem; per URL = url completa;
    # per search_result = url + index nella lista.
    identifier: str
    # Sommario testuale 1-2 paragrafi del contenuto (per body excerpt).
    summary: str = ""
    # Suggested destination (rule-based classifier).
    suggested_destination: WikiDestination = "memory_tree"
    # Suggested slug normalizzato (lowercase-dash, max 80 char).
    suggested_slug: str = ""
    # Suggested frontmatter draft (campi pre-popolati da heuristics).
    suggested_frontmatter: dict[str, Any] = field(default_factory=dict)
    # Confidence score 0.0-1.0: alto = classification con evidenza forte.
    confidence: float = 0.5
    # Razionale leggibile della classificazione (per UI + log Conv. 41).
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "title": self.title,
            "identifier": self.identifier,
            "summary": self.summary,
            "suggested_destination": self.suggested_destination,
            "suggested_slug": self.suggested_slug,
            "suggested_frontmatter": self.suggested_frontmatter,
            "confidence": round(self.confidence, 3),
            "rationale": self.rationale,
        }


@dataclass(slots=True)
class WikiIngestProposal:
    """Proposta complessiva per un messaggio assistant.

    Aggrega N WikiIngestSlot (uno per candidato detectato) + metadata di tracking
    (proposal_id idempotente, conversation_id, message_id, timestamp).
    """

    proposal_id: str
    conversation_id: str
    message_id: str
    created_at: str  # ISO 8601 UTC
    slots: list[WikiIngestSlot] = field(default_factory=list)
    # Flag complessivo: True se almeno uno slot ha confidence >= 0.6.
    has_strong_candidate: bool = False

    @property
    def is_empty(self) -> bool:
        """True se nessun candidato detectato (no proposal da mostrare)."""
        return len(self.slots) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "created_at": self.created_at,
            "slots": [s.to_dict() for s in self.slots],
            "has_strong_candidate": self.has_strong_candidate,
        }


# ----------------------------------------------------------------------------
# UTILITY — slug, hash, URL extraction
# ----------------------------------------------------------------------------


def generate_slug_suggestion(title: str, *, max_len: int = _SLUG_MAX_LEN) -> str:
    """Normalizza un titolo in slug compatibile wiki SCO.

    Pattern: lowercase, accenti rimossi grezzamente, spazi -> dash,
    caratteri non [a-z0-9-] eliminati, dash consecutivi compressi, troncato a
    max_len (80 default, allineato a Conv. 43 SMART FILE INJECTION).

    Esempi:
        "D.Lgs. 138/2024 (NIS 2)" -> "d-lgs-138-2024-nis-2"
        "ISO/IEC 27001:2022" -> "iso-iec-27001-2022"
        "Direttiva UE 2022/2555" -> "direttiva-ue-2022-2555"
    """
    if not title:
        return "untitled"
    # Lowercase + sostituzione caratteri accentati italiani comuni.
    cleaned = title.lower()
    for src, dst in [
        ("à", "a"),
        ("è", "e"),
        ("é", "e"),
        ("ì", "i"),
        ("ò", "o"),
        ("ù", "u"),
        ("ç", "c"),
        ("ñ", "n"),
    ]:
        cleaned = cleaned.replace(src, dst)
    # Replace separatori comuni con dash.
    cleaned = re.sub(r"[\s/\\._:,\(\)]+", "-", cleaned)
    # Rimuovi tutto fuori vocabolario slug.
    cleaned = _SLUG_SAFE_RE.sub("", cleaned)
    # Comprimi dash consecutivi + strip dash di bordo.
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip("-")
    return cleaned or "untitled"


def build_proposal_id(conversation_id: str, message_id: str) -> str:
    """Genera proposal_id deterministico (sha256 sui 2 input, 16 hex char)."""
    seed = f"{conversation_id}::{message_id}".encode()
    return hashlib.sha256(seed).hexdigest()[:16]


def extract_urls_from_text(text: str) -> list[str]:
    """Estrae URL http/https dal testo (regex, no dependency aggiuntive).

    Pattern conservativo: match URL ben formati con scheme + host. Esclude
    URL fra parentesi markdown (es. `[label](url)`) tramite trimming finale.
    """
    if not text:
        return []
    # Pattern URL ragionevolmente strict: protocol + dominio + path opzionale.
    url_re = re.compile(
        r"https?://[^\s<>\"'\)\]]+",
        re.IGNORECASE,
    )
    matches = url_re.findall(text)
    # De-duplica preservando l'ordine di prima occorrenza.
    seen: set[str] = set()
    out: list[str] = []
    for u in matches:
        # Rimuovi punteggiatura finale comune (., , ; :).
        cleaned = u.rstrip(".,;:")
        if cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return out


def detect_normative_refs(text: str) -> list[tuple[str, str]]:
    """Detecta riferimenti normativi nel testo.

    Returns:
        Lista tuple (entity_subtype_hint, match_text). Es:
            [("decreto-legislativo", "D.Lgs. 138/2024"),
             ("iso-iec", "ISO/IEC 27001:2022")]
    """
    out: list[tuple[str, str]] = []
    if not text:
        return out
    for subtype_hint, pattern in _NORMATIVE_REGEXES:
        for match in pattern.finditer(text):
            out.append((subtype_hint, match.group(0).strip()))
    return out


def detect_acronyms(text: str) -> list[str]:
    """Detecta sigle/acronimi nel testo (2-6 lettere maiuscole, dedup ordinato).

    Non filtra contro glossario esistente (responsabilita downstream). Utile
    per popolare suggested_frontmatter quando destinazione = "glossari".
    """
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in _ACRONYM_RE.findall(text):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _infer_ambito_canonico(content: str) -> tuple[str | None, float]:
    """Inferisce ambito_canonico da keyword match nel content.

    Returns:
        Tupla (ambito | None, confidence 0.0-1.0). None se nessun keyword match.
        Confidence = numero match keyword / 3 (capped a 1.0).
    """
    if not content:
        return None, 0.0
    text_lower = content.lower()
    best_ambito: str | None = None
    best_score = 0
    for ambito, keywords in _AMBITO_KEYWORD_MAP.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_ambito = ambito
    if best_ambito is None or best_score == 0:
        return None, 0.0
    if best_ambito not in AMBITO_CANONICO:
        # Defensive: vocabolario chiuso (caso impossibile dato hard-coded dict
        # ma protegge da typo futuro).
        logger.warning(
            "wiki_proposal._infer_ambito_canonico: ambito %r fuori vocabolario", best_ambito
        )
        return None, 0.0
    return best_ambito, min(1.0, best_score / 3.0)


# ----------------------------------------------------------------------------
# CLASSIFICATORI — rule-based, per tipo di candidato
# ----------------------------------------------------------------------------


def classify_url_to_destination(
    url: str, surrounding_text: str = ""
) -> tuple[WikiDestination, float, str]:
    """Classifica URL -> destinazione wiki + confidence + rationale.

    Logica:
        1. Domain check vs INSTITUTIONAL_DOMAINS:
           - eur-lex / normattiva / gazzetta -> "entities" (atto normativo)
           - iso.org / uni.com -> "entities" (standard)
           - agid / acn / garante -> "entities" (autorità) o "sources"
           - altre istituzionali -> "sources"
        2. Non istituzionale -> "sources" o "memory_tree" come fallback.
        3. Confidence: alto (0.8+) per istituzionale, medio (0.5) per altro.
    """
    if not url:
        return "memory_tree", 0.1, "URL vuoto"

    try:
        parsed = urlparse(url)
        domain = (parsed.netloc or "").lower()
        # Strip leading "www."
        if domain.startswith("www."):
            domain = domain[4:]
    except Exception as exc:
        logger.warning("classify_url_to_destination: URL parse error %s: %s", url, exc)
        return "memory_tree", 0.1, f"URL non parsabile: {url}"

    if not domain:
        return "memory_tree", 0.1, "Dominio non estraibile da URL"

    # Match esatto contro whitelist.
    if domain in INSTITUTIONAL_DOMAINS:
        # Heuristica: domain normativo -> entities, altri istituzionali -> sources.
        if domain in {
            "eur-lex.europa.eu",
            "normattiva.it",
            "gazzettaufficiale.it",
        }:
            return (
                "entities",
                0.85,
                f"URL su dominio normativo istituzionale ({domain}) -> entity atto normativo",
            )
        if domain in {"iso.org", "iec.ch", "uni.com", "store.uni.com", "cen.eu"}:
            return (
                "entities",
                0.85,
                f"URL su dominio standard tecnico ({domain}) -> entity standard",
            )
        return (
            "sources",
            0.75,
            f"URL su dominio istituzionale ({domain}) -> scheda source con citazione",
        )

    # Fallback non istituzionale: classifica come source (web-clip) con confidence
    # medio. L'utente puo' rimanere o spostare a memory_tree manualmente.
    return (
        "sources",
        0.45,
        f"URL non istituzionale ({domain}) -> source web-clip (confidence medio)",
    )


def classify_attachment_to_destination(
    file_path: str, mime_type: str = "", content_preview: str = ""
) -> tuple[WikiDestination, float, str]:
    """Classifica allegato file -> destinazione wiki + confidence + rationale.

    Logica:
        1. Estensione + path heuristics:
           - .pdf / .docx con keyword normativo -> "entities" (atto / standard)
           - .pdf / .docx senza keyword chiaro -> "sources"
           - .md con frontmatter wiki-shape -> "sources" (riallineamento)
           - .txt / .md generici -> "sources"
           - .json / .yaml strutturati -> "sources" (data file)
           - .xlsx -> "sources" (dataset)
        2. Confidence basato su match keyword normativo nel content_preview
           (se disponibile).
    """
    if not file_path:
        return "memory_tree", 0.1, "Path attachment vuoto"

    path_obj = Path(file_path)
    ext = path_obj.suffix.lower()
    filename = path_obj.name.lower()

    # Heuristica filename normativo (chiavi tipiche).
    filename_normative_hints = (
        "d-lgs",
        "d.lgs",
        "dlgs",
        "decreto",
        "legge",
        "regolamento",
        "reg-ue",
        "regue",
        "direttiva",
        "iso-iec",
        "iso-",
        "uni-",
        "dpr",
        "dpcm",
        "dm-",
        "circolare",
        "linee-guida",
        "linee-guida-",
    )
    is_normative_filename = any(hint in filename for hint in filename_normative_hints)

    # Keyword normativo nel content preview (case-insensitive).
    normative_refs = detect_normative_refs(content_preview)
    has_normative_in_content = len(normative_refs) > 0

    if ext in _DOC_EXTENSIONS_NORMATIVE:
        if is_normative_filename or has_normative_in_content:
            return (
                "entities",
                0.8,
                f"Allegato {ext} con pattern normativo (filename={is_normative_filename}, content={has_normative_in_content}) -> entity",
            )
        return (
            "sources",
            0.6,
            f"Allegato {ext} generico -> scheda source con frontmatter standard B",
        )

    if ext in _DOC_EXTENSIONS_TEXTUAL:
        return (
            "sources",
            0.55,
            f"Allegato testuale {ext} -> source con summary",
        )

    if ext in _DOC_EXTENSIONS_STRUCTURED:
        return (
            "sources",
            0.5,
            f"Allegato strutturato {ext} (dataset/config) -> source",
        )

    # Estensione non supportata: memory_tree fallback (l'utente puo' comunque
    # chiedere di indicizzarlo come chunk generico).
    return (
        "memory_tree",
        0.3,
        f"Estensione {ext or '<none>'} non riconosciuta -> chunk memory_tree fallback",
    )


def classify_search_result_to_destination(
    title: str, url: str, snippet: str = ""
) -> tuple[WikiDestination, float, str]:
    """Classifica un singolo hit search_result -> destinazione wiki.

    Delega a classify_url_to_destination per il dominio, ma aggiusta il
    confidence al ribasso (snippet non e' il contenuto reale, va comunque
    fetchato per scheda source).
    """
    dest, conf, rationale = classify_url_to_destination(url, snippet)
    # Penalty 0.1 perche' lo snippet e' parziale.
    return dest, max(0.1, conf - 0.1), f"Search result: {rationale}"


# ----------------------------------------------------------------------------
# FRONTMATTER DRAFT BUILDER
# ----------------------------------------------------------------------------


def propose_frontmatter_draft(
    destination: WikiDestination,
    title: str,
    content: str = "",
    *,
    source_url: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Costruisce frontmatter draft per la destinazione + content disponibile.

    I campi tipizzati (entity_type, entity_subtype, ambito_canonico) sono
    popolati SOLO se inferibili con alta confidence. Altrimenti restano None /
    stringa vuota, e l'utente li compila nel widget.

    Pattern Conv. 11 enforcement: niente popolazione cautelativa di campi
    di vocabolario chiuso senza evidenza inequivocabile.
    """
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    base: dict[str, Any] = {
        "title": title,
        "status": "draft",
        "last_reviewed": today,
        "tags": [],
    }

    # Inferenza ambito_canonico (vale per tutte le destinazioni).
    ambito, ambito_conf = _infer_ambito_canonico(content + " " + title)
    if ambito is not None and ambito_conf >= 0.3:
        base["ambito_canonico"] = ambito

    if destination == "sources":
        # Schema standard B Ondata 4 (provenance metadata).
        base["type"] = "source"
        base["data_import_vault"] = today
        if source_url:
            base["fonte_primaria"] = source_url
        if file_path:
            base["fonte_primaria"] = f"[[raw/{Path(file_path).name}]]"
        base["entity_collegata"] = ""  # placeholder, utente compila
        base["ente_emittente"] = ""
        base["data_pubblicazione"] = None
        base["parser"] = "auto-detect"
        base["hash_md5"] = ""  # popolato a confirm tempo
        base["dimensione_byte"] = 0
        base["pagine"] = None

    elif destination == "entities":
        base["type"] = "entity"
        # Tentativo inferenza entity_type dal pattern normativo nel content.
        refs = detect_normative_refs((content or "") + " " + (title or ""))
        if refs:
            subtype_hint = refs[0][0]
            # Mappa subtype hint -> entity_type top-level.
            if subtype_hint in {
                "decreto-legislativo",
                "legge-statale",
                "regolamento-ue",
                "direttiva-ue",
                "dpr",
                "dm",
            }:
                base["entity_type"] = "atto-normativo"
                base["entity_subtype"] = subtype_hint
            elif subtype_hint == "iso-iec":
                base["entity_type"] = "standard-tecnico"
                base["entity_subtype"] = "iso-iec"
        # Defensive validation contro ENTITY_TYPES (Conv. 47).
        et = base.get("entity_type")
        if et is not None and et not in ENTITY_TYPES:
            logger.warning(
                "propose_frontmatter_draft: entity_type %r fuori vocabolario, rimuovo", et
            )
            base.pop("entity_type", None)
            base.pop("entity_subtype", None)

    elif destination == "concepts":
        base["type"] = "concept"
        # Concept non ha entity_type. Solo ambito + tags.

    elif destination == "synthesis":
        base["type"] = "synthesis"
        base["domini_applicabili"] = []  # placeholder, utente compila per mapping
        base["confidence"] = "medio"  # default Ondata 1 evoluzione vault

    elif destination == "glossari":
        base["type"] = "glossario"
        # Detect sigle nel content per pre-popolare la lista.
        acronyms = detect_acronyms(content + " " + title)
        if acronyms:
            base["sigle_detected"] = acronyms[:10]  # cap 10 per UI

    else:  # memory_tree
        base["type"] = "chunk"
        # Memory tree usa schema chunk diverso, qui solo metadata minima.

    return base


# ----------------------------------------------------------------------------
# ENTRY POINT — analyze_message_for_wiki_ingest
# ----------------------------------------------------------------------------


def _build_summary(content: str, max_chars: int = 400) -> str:
    """Estrae sommario 1-2 paragrafi del content (primo blocco non vuoto)."""
    if not content:
        return ""
    # Split paragrafi (doppio newline).
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not paragraphs:
        return ""
    text = paragraphs[0]
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "..."
    return text


def analyze_message_for_wiki_ingest(
    *,
    conversation_id: str,
    message_id: str,
    message_content: str = "",
    attachments: list[dict[str, Any]] | None = None,
    search_results: list[dict[str, Any]] | None = None,
) -> WikiIngestProposal:
    """Analizza messaggio assistant + sue fonti -> WikiIngestProposal.

    Args:
        conversation_id: ID conversation (per proposal_id + tracking).
        message_id: ID messaggio assistant analizzato.
        message_content: testo del messaggio assistant (per URL detection +
            normative refs detection per inline citations).
        attachments: lista dict con almeno {path, mime_type, ...} per ogni
            allegato. Opzionale.
        search_results: lista dict con almeno {url, title, snippet, ...} per
            ogni search hit emesso da web_search tool. Opzionale.

    Returns:
        WikiIngestProposal con N slot (zero se nulla detectato). is_empty=True
        quando non ci sono candidati e l'UI puo' non mostrare il widget.

    Pattern Conv. 41: ogni decisione di classificazione e' loggata structured.
    """
    proposal_id = build_proposal_id(conversation_id, message_id)
    now_iso = datetime.now(UTC).isoformat()
    proposal = WikiIngestProposal(
        proposal_id=proposal_id,
        conversation_id=conversation_id,
        message_id=message_id,
        created_at=now_iso,
    )

    # 1. ALLEGATI -----------------------------------------------------------
    for att in attachments or []:
        path = att.get("path") or att.get("identifier") or ""
        if not path:
            continue
        mime = att.get("mime_type", "")
        content_preview = att.get("content_preview", "") or att.get("text_content", "")
        dest, conf, rationale = classify_attachment_to_destination(path, mime, content_preview)
        title = att.get("title") or Path(path).stem
        slug = generate_slug_suggestion(title)
        fm_draft = propose_frontmatter_draft(dest, title, content_preview, file_path=path)
        slot = WikiIngestSlot(
            source_type="attachment",
            title=title,
            identifier=path,
            summary=_build_summary(content_preview),
            suggested_destination=dest,
            suggested_slug=slug,
            suggested_frontmatter=fm_draft,
            confidence=conf,
            rationale=rationale,
        )
        proposal.slots.append(slot)
        logger.info(
            "wiki_proposal.attachment_classified",
            proposal_id=proposal_id,
            path=path,
            destination=dest,
            confidence=round(conf, 3),
        )

    # 2. URL nel content del messaggio -------------------------------------
    seen_urls: set[str] = set()
    for url in extract_urls_from_text(message_content):
        if url in seen_urls:
            continue
        seen_urls.add(url)
        dest, conf, rationale = classify_url_to_destination(url, message_content)
        # Solo URL istituzionali o con confidence >= 0.4 generano slot.
        # Filtro: evita di proporre ingest per ogni link generico nel messaggio.
        if conf < 0.4:
            continue
        # Title heuristica: ultimo segmento del path o domain.
        try:
            parsed = urlparse(url)
            path_segment = parsed.path.rstrip("/").split("/")[-1] if parsed.path else ""
            title = path_segment.replace("-", " ").replace("_", " ").strip() or parsed.netloc
        except Exception:
            title = url
        if not title:
            title = url
        slug = generate_slug_suggestion(title)
        fm_draft = propose_frontmatter_draft(dest, title, "", source_url=url)
        slot = WikiIngestSlot(
            source_type="url",
            title=title,
            identifier=url,
            summary=f"Link rilevato nel messaggio: {url}",
            suggested_destination=dest,
            suggested_slug=slug,
            suggested_frontmatter=fm_draft,
            confidence=conf,
            rationale=rationale,
        )
        proposal.slots.append(slot)
        logger.info(
            "wiki_proposal.url_classified",
            proposal_id=proposal_id,
            url=url,
            destination=dest,
            confidence=round(conf, 3),
        )

    # 3. Search results emessi da web_search tool --------------------------
    for hit in search_results or []:
        url = hit.get("url", "")
        title = hit.get("title") or hit.get("name") or ""
        snippet = hit.get("snippet") or hit.get("description") or ""
        if not url or not title:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        dest, conf, rationale = classify_search_result_to_destination(title, url, snippet)
        if conf < 0.3:
            continue
        slug = generate_slug_suggestion(title)
        fm_draft = propose_frontmatter_draft(dest, title, snippet, source_url=url)
        slot = WikiIngestSlot(
            source_type="search_result",
            title=title,
            identifier=url,
            summary=_build_summary(snippet),
            suggested_destination=dest,
            suggested_slug=slug,
            suggested_frontmatter=fm_draft,
            confidence=conf,
            rationale=rationale,
        )
        proposal.slots.append(slot)
        logger.info(
            "wiki_proposal.search_result_classified",
            proposal_id=proposal_id,
            url=url,
            destination=dest,
            confidence=round(conf, 3),
        )

    # Flag globale: almeno uno strong candidate (>= 0.6).
    proposal.has_strong_candidate = any(s.confidence >= 0.6 for s in proposal.slots)

    logger.info(
        "wiki_proposal.analyze_complete",
        proposal_id=proposal_id,
        conversation_id=conversation_id,
        message_id=message_id,
        total_slots=len(proposal.slots),
        has_strong=proposal.has_strong_candidate,
    )

    return proposal


__all__ = [
    "INSTITUTIONAL_DOMAINS",
    "WikiDestination",
    "WikiIngestProposal",
    "WikiIngestSlot",
    "analyze_message_for_wiki_ingest",
    "build_proposal_id",
    "classify_attachment_to_destination",
    "classify_search_result_to_destination",
    "classify_url_to_destination",
    "detect_acronyms",
    "detect_normative_refs",
    "extract_urls_from_text",
    "generate_slug_suggestion",
    "propose_frontmatter_draft",
]
