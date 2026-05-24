"""Parser markdown vault Karpathy con frontmatter YAML.

Estrae dimensioni tipizzate Ondate 2-3-4 (vault Antonio Amodeo, riferimento
autoritativo: C:\\Users\\aoedo\\Desktop\\Second Brain\\CLAUDE.md sezione INGEST):

    Dimensione 1: entity_type (7 valori chiusi)
    Dimensione 2: entity_subtype (sotto-tipo gerarchico)
    Dimensione 3: ambito_canonico (17 valori chiusi)
    Dimensione 4: relationships (array di 8 tipi chiusi: recepisce, attua,
                  abroga, modifica, supersedes, correlato-a, richiama, vigilato-da)
    Dimensione 5: applica_entity (edge cliente↔entity con 9 ruoli chiusi)
    Dimensione 6: scadenze (entity_type=scadenza con parent_entity)
    Dimensione 7: pertinenza_in_verifica (qualifiche ambigue strutturate)
    Dimensione 8: fornitore_di (edge cliente↔cliente asimmetrico)

Pattern Karpathy "no hallucination": il parser è strict sui vocabolari chiusi.
Valori fuori vocabolario sollevano warning ma vengono preservati in raw_frontmatter
(per non perdere dati durante migrazioni). Validazione separata in scanner.py.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Vocabolari chiusi Ondate 2-3-4 (riferimento: CLAUDE.md vault Amodeo).
ENTITY_TYPES = frozenset(
    {
        "atto-normativo",
        "standard-tecnico",
        "linea-guida",
        "autorita",
        "metodologia",
        "autore-prassi",
        "soggetto-obbligato",
        "scadenza",  # Dimensione 6 Ondata 3 — sub-tipo dedicato
    }
)

AMBITO_CANONICO = frozenset(
    {
        "cybersicurezza",
        "governance-ai",
        "privacy-protezione-dati",
        "accreditamento-sanitario",
        "dispositivi-medici",
        "radioprotezione",
        "sicurezza-lavoro",
        "farmacovigilanza",
        "service-management-ict",
        "appalti-pubblici",
        "prevenzione-incendi",
        "compliance-231",
        "qualita-sgq",
        "gestione-ambientale",
        "sicurezza-alimentare",
        "responsabilita-sociale",
        "multi-dominio",  # metaflag
    }
)

RELATIONSHIP_TYPES = frozenset(
    {
        "recepisce",
        "attua",
        "abroga",
        "modifica",
        "supersedes",
        "correlato-a",
        "richiama",
        "vigilato-da",
    }
)

EDGE_RUOLI = frozenset(
    {
        "soggetto-essenziale",
        "soggetto-importante",
        "destinatario-obblighi",
        "certificando",
        "fornitore-critico",
        "destinatario-vigilanza",
        "mah-farmacovigilanza",
        "provider-deployer-ai",
        "applica-volontario",
    }
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass(slots=True)
class AppliedEntity:
    """Edge cliente↔entity (Dimensione 5)."""

    entity: str  # wikilink target [[wiki/entities/<slug>]]
    ruolo: str  # vocabolario chiuso EDGE_RUOLI
    note: str = ""


@dataclass(slots=True)
class PertinenzaInVerifica:
    """Qualifica ambigua strutturata (Dimensione 7 Ondata 4)."""

    entity: str
    motivo: str
    profili_da_verificare: list[str] = field(default_factory=list)
    linea_cautelativa: str = ""
    data_ipotesi: str = ""
    promemoria_riapertura: str = ""


@dataclass(slots=True)
class FornitoreDi:
    """Edge cliente↔cliente asimmetrico (Dimensione 8 Ondata 4)."""

    cliente: str  # wikilink target
    tipo_servizio: str
    rilevanza_compliance: list[str] = field(default_factory=list)
    note: str = ""


@dataclass(slots=True)
class Relationship:
    """Relationship fra entity wiki (Dimensione 4 Ondata 3)."""

    tipo: str  # vocabolario chiuso RELATIONSHIP_TYPES
    target: str  # wikilink target
    note: str = ""


@dataclass(slots=True)
class VaultDocument:
    """Documento del vault Karpathy parsed.

    Copre sia entity wiki (wiki/entities/*.md) sia _index cliente
    (Business/*/clienti/*/_index.md), sia sources, concepts, synthesis.
    """

    path: str
    type: str  # 'entity'|'cliente'|'source'|'concept'|'synthesis'|'glossario'|'unknown'
    status: str = "active"
    title: str = ""
    raw_frontmatter: dict = field(default_factory=dict)
    body_md: str = ""

    # Dimensioni Ondata 2-3-4 (popolate solo se applicabili al tipo doc).
    entity_type: str | None = None
    entity_subtype: str | None = None
    ambito_canonico: str | None = None
    domini_applicabili: list[str] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    applica_entity: list[AppliedEntity] = field(default_factory=list)
    pertinenza_in_verifica: list[PertinenzaInVerifica] = field(default_factory=list)
    fornitore_di: list[FornitoreDi] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)
    last_reviewed: str = ""
    parent_entity: str = ""  # per entity_type=scadenza


def _parse_yaml_safe(yaml_text: str) -> dict:
    """Parsing YAML tollerante con fallback a naive parser su YAMLError.

    Strategia v0.4.0 (cantiere fix YAML invalido vault Karpathy):
    1. Tenta yaml.safe_load standard.
    2. Su YAMLError (chiave seguita da `- elem` inline, indentazione mista, etc):
       normalizza il testo (sposta `key: - elem` su 2 righe) e riprova.
    3. Su nuovo fallimento, fallback a _naive_yaml_parse (estrae solo chiavi top-level
       come stringhe; perde array nested ma non blocca il vault).

    Pattern Karpathy "vault intoccabile" (decisione Antonio 24/05/2026): il parser
    deve essere robusto a YAML imperfetto invece di richiedere fix manuali del vault.
    """
    try:
        import yaml  # type: ignore
    except (ImportError, ModuleNotFoundError):
        logger.warning("pyyaml non disponibile, fallback parser naive (limited)")
        return _naive_yaml_parse(yaml_text)

    try:
        return yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as first_err:
        # Tentativo 2: normalizza pattern `key: - elem` (lista inline malformata)
        # in `key:\n  - elem` (forma canonica YAML block-style).
        normalized = re.sub(
            r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):\s+-\s+(.+)$",
            r"\1\2:\n\1  - \3",
            yaml_text,
            flags=re.MULTILINE,
        )
        try:
            return yaml.safe_load(normalized) or {}
        except yaml.YAMLError as second_err:
            logger.warning(
                "YAML parse failed twice (first=%s, normalized=%s), fallback naive parser",
                first_err,
                second_err,
            )
            return _naive_yaml_parse(yaml_text)


def _naive_yaml_parse(text: str) -> dict:
    """Parser YAML fallback (chiave: valore semplice, no array nested)."""
    result: dict = {}
    for line in text.splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def _split_frontmatter(content: str) -> tuple[dict, str]:
    """Estrae frontmatter YAML + body dal contenuto markdown."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    return _parse_yaml_safe(match.group(1)), match.group(2)


def _classify_doc_type(path: Path, frontmatter: dict) -> str:
    """Classifica tipo documento da path + frontmatter type."""
    fm_type = str(frontmatter.get("type", "")).lower()
    if fm_type in {"entity", "cliente", "source", "concept", "synthesis", "glossario"}:
        return fm_type
    path_str = str(path).replace("\\", "/").lower()
    if "/wiki/entities/" in path_str:
        return "entity"
    if "/wiki/sources/" in path_str:
        return "source"
    if "/wiki/concepts/" in path_str:
        return "concept"
    if "/wiki/synthesis/" in path_str:
        return "synthesis"
    if "/wiki/glossari/" in path_str:
        return "glossario"
    if "/business/" in path_str and "/clienti/" in path_str and "_index" in path_str:
        return "cliente"
    return "unknown"


def _parse_relationships(raw: object) -> list[Relationship]:
    """Estrae lista relationships con validazione vocabolario."""
    if not isinstance(raw, list):
        return []
    out: list[Relationship] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        tipo = str(item.get("tipo", "")).strip()
        target = str(item.get("target", "")).strip()
        if not tipo or not target:
            continue
        if tipo not in RELATIONSHIP_TYPES:
            logger.warning("Relationship tipo fuori vocabolario: %r", tipo)
        out.append(Relationship(tipo=tipo, target=target, note=str(item.get("note", ""))))
    return out


def _parse_applica_entity(raw: object) -> list[AppliedEntity]:
    """Estrae edge applica_entity con validazione ruoli."""
    if not isinstance(raw, list):
        return []
    out: list[AppliedEntity] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        entity = str(item.get("entity", "")).strip()
        ruolo = str(item.get("ruolo", "")).strip()
        if not entity or not ruolo:
            continue
        if ruolo not in EDGE_RUOLI:
            logger.warning("Ruolo edge fuori vocabolario: %r", ruolo)
        out.append(AppliedEntity(entity=entity, ruolo=ruolo, note=str(item.get("note", ""))))
    return out


def _parse_pertinenza(raw: object) -> list[PertinenzaInVerifica]:
    """Estrae pertinenza_in_verifica (Dimensione 7 Ondata 4)."""
    if not isinstance(raw, list):
        return []
    out: list[PertinenzaInVerifica] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            PertinenzaInVerifica(
                entity=str(item.get("entity", "")).strip(),
                motivo=str(item.get("motivo", "")),
                profili_da_verificare=list(item.get("profili_da_verificare", []) or []),
                linea_cautelativa=str(item.get("linea_cautelativa", "")),
                data_ipotesi=str(item.get("data_ipotesi", "")),
                promemoria_riapertura=str(item.get("promemoria_riapertura", "")),
            )
        )
    return out


def _parse_fornitore_di(raw: object) -> list[FornitoreDi]:
    """Estrae fornitore_di (Dimensione 8 Ondata 4)."""
    if not isinstance(raw, list):
        return []
    out: list[FornitoreDi] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            FornitoreDi(
                cliente=str(item.get("cliente", "")).strip(),
                tipo_servizio=str(item.get("tipo_servizio", "")),
                rilevanza_compliance=list(item.get("rilevanza_compliance", []) or []),
                note=str(item.get("note", "")),
            )
        )
    return out


def parse_vault_file(path: Path) -> VaultDocument:
    """Parsa file markdown vault, ritorna VaultDocument tipizzato.

    Pattern Karpathy "no hallucination": se il file non esiste o è vuoto,
    ritorna VaultDocument minimo con status='deprecated' e log warning.
    """
    if not path.exists():
        logger.warning("parse_vault_file: file non esiste %s", path)
        return VaultDocument(path=str(path), type="unknown", status="deprecated")

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1", errors="replace")

    fm, body = _split_frontmatter(content)
    doc_type = _classify_doc_type(path, fm)

    entity_type = str(fm.get("entity_type", "")) or None
    if entity_type and entity_type not in ENTITY_TYPES:
        logger.warning("entity_type fuori vocabolario in %s: %r", path, entity_type)

    ambito = str(fm.get("ambito_canonico", "")) or None
    if ambito and ambito not in AMBITO_CANONICO:
        logger.warning("ambito_canonico fuori vocabolario in %s: %r", path, ambito)

    tags_raw = fm.get("tags", [])
    tags = list(tags_raw) if isinstance(tags_raw, list) else []

    return VaultDocument(
        path=str(path),
        type=doc_type,
        status=str(fm.get("status", "active")),
        title=str(fm.get("title", fm.get("cliente", path.stem))),
        raw_frontmatter=fm,
        body_md=body,
        entity_type=entity_type,
        entity_subtype=str(fm.get("entity_subtype", "")) or None,
        ambito_canonico=ambito,
        domini_applicabili=list(fm.get("domini_applicabili", []) or []),
        relationships=_parse_relationships(fm.get("relationships")),
        applica_entity=_parse_applica_entity(fm.get("applica_entity")),
        pertinenza_in_verifica=_parse_pertinenza(fm.get("pertinenza_in_verifica")),
        fornitore_di=_parse_fornitore_di(fm.get("fornitore_di")),
        tags=tags,
        last_reviewed=str(fm.get("last_reviewed", "")),
        parent_entity=str(fm.get("parent_entity", "")),
    )
