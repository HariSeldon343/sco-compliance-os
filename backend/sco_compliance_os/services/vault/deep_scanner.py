"""Deep scan profondo del vault per auto-trigger os-setup.

v0.8.1 fix bug Antonio segnalato (Sessione cantiere v0.8.1):
auto-trigger os-setup partiva ma:
    1. Si fermava dopo PRIMA domanda
    2. NON faceva scansione profonda vault PRIMA
    3. NON chiedeva "chi sei nel team"

Questo modulo introduce ``deep_scan_vault()`` che produce un ``DeepScanReport``
ricco di metrics + summary markdown leggibile per l'utente in chat, da posizionare
PRIMA delle 10 domande del nuovo os-setup.

Metrics raccolti (pattern Conv. 35 RESEARCH-BEFORE-ACT: scan reale filesystem,
mai mock):

    - Conteggio file per estensione: .md / .pdf / .docx / .xlsx / .txt / altre
    - Per file .md: parse frontmatter + distribuzione entity_type / ambito_canonico
      / status / tags (riusa parser tipizzato vault SCO)
    - Sigle ricorrenti: regex ``\\b[A-Z]{2,6}\\b`` con cap soglia frequenza
    - Clienti citati: folder ``Business/<area>/clienti/*`` (nomi dirs)
    - Lingue rilevate: heuristic da prime 500 char body di sample md files
    - Framework dominanti: count occurrence stringhe ("ISO 27001", "NIS 2", "GDPR",
      "ISO 9001", "AI Act", "ISO 42001", "ISO 14001", "D.Lgs. 81", "D.Lgs. 138",
      "Accreditamento sanitario", "MDR", "GDP", "ISO 22301", "ISO 20000-1",
      "L. 90", "ISO 27017", "ISO 27018", "D.Lgs. 231", "ISO 9001:2015",
      "ITIL", "Codice PI", "DM 2/9/2021")

Pattern Conv. 41 tracciatura: ogni scan logga vault_root + duration + counts.
Pattern Conv. 46 SMOKE PRIMA DEL TAG: cap file scanned a 5000, cap sample md
read a 200, in modo che il deep scan non degradi su vault molto grandi.

Output ``DeepScanReport`` dataclass + helper ``to_markdown_summary()`` per
render leggibile dal chat agent.
"""

from __future__ import annotations

import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from sco_compliance_os.core.logging_setup import get_logger

from .parser import parse_vault_file

# v0.10.0 fix: era stdlib logging.getLogger ma le chiamate logger.info(...,
# kwarg=val) seguono lo stile structlog. Mismatch API causava TypeError
# "Logger._log() got an unexpected keyword argument 'vault_path'" al fine scan.
# Pattern Conv. 44 lesson 1: niente catch generic mascherante; pattern Conv. 45
# lesson 2: stessa API ovunque per evitare confusione.
logger = get_logger(__name__)


# ----- Costanti di scan -----

# Cap difensivi (Conv. 46 enforcement): il deep scan deve essere fast (~1-3s
# su vault standard, < 10s su vault molto grandi).
_MAX_FILES_SCANNED = 5000
_MAX_MD_PARSED = 500
_MAX_SAMPLE_MD_FOR_LANG = 30
_MAX_SAMPLE_MD_FOR_SIGLE = 60
_LANG_SAMPLE_CHARS = 500
_MAX_CLIENTI_LIST = 20
_MAX_SIGLE_LIST = 25
_MIN_SIGLA_FREQ = 3

# Cartelle da escludere dalla scansione (allineato a scanner.py).
_SKIP_DIRS = frozenset(
    {
        ".git",
        ".obsidian",
        ".claude",
        "node_modules",
        "_template-originale",
        "__pycache__",
        ".venv",
        "_archivio",
        "_archived",
    }
)

_SKIP_PREFIXES = ("_archivio", "_archived", ".")

# Estensioni rilevanti per il counting.
_EXTENSIONS_OF_INTEREST = frozenset(
    {
        ".md",
        ".pdf",
        ".docx",
        ".xlsx",
        ".pptx",
        ".txt",
        ".csv",
        ".json",
        ".yaml",
        ".yml",
    }
)


# Framework normativi tracciati (ordinati per priorita visualizzazione output).
# Pattern multi-token con varianti tipografiche tipiche in italiano professionale.
_FRAMEWORK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("NIS 2", re.compile(r"\b(?:NIS\s*2|NIS2|D\.Lgs\.\s*138[/-]2024)\b", re.IGNORECASE)),
    ("ISO 27001", re.compile(r"\bISO[/\s]*(?:IEC[/\s]*)?27001\b", re.IGNORECASE)),
    (
        "GDPR",
        re.compile(r"\bGDPR|Reg(?:olamento)?\.?\s*(?:UE|EU)?\s*2016[/\-]679\b", re.IGNORECASE),
    ),
    (
        "AI Act",
        re.compile(r"\bAI\s*Act|Reg(?:olamento)?\.?\s*(?:UE|EU)?\s*2024[/\-]1689\b", re.IGNORECASE),
    ),
    ("ISO 42001", re.compile(r"\bISO[/\s]*(?:IEC[/\s]*)?42001\b", re.IGNORECASE)),
    ("ISO 9001", re.compile(r"\bISO[/\s]*9001(?!\d)\b", re.IGNORECASE)),
    ("D.Lgs. 81/2008", re.compile(r"\bD\.Lgs\.\s*81[/-]2008\b", re.IGNORECASE)),
    ("ISO 14001", re.compile(r"\bISO[/\s]*14001\b", re.IGNORECASE)),
    (
        "Accreditamento sanitario",
        re.compile(r"\baccreditament[oi]\s+(?:istituzional[ei]|sanitar[ie])\b", re.IGNORECASE),
    ),
    ("ISO 22301", re.compile(r"\bISO[/\s]*22301\b", re.IGNORECASE)),
    ("ISO 20000-1", re.compile(r"\bISO[/\s]*(?:IEC[/\s]*)?20000[\s\-]*1\b", re.IGNORECASE)),
    ("L. 90/2024", re.compile(r"\bL(?:egge)?\.?\s*90[/-]2024\b", re.IGNORECASE)),
    ("ISO 27017", re.compile(r"\bISO[/\s]*(?:IEC[/\s]*)?27017\b", re.IGNORECASE)),
    ("ISO 27018", re.compile(r"\bISO[/\s]*(?:IEC[/\s]*)?27018\b", re.IGNORECASE)),
    ("D.Lgs. 231/2001", re.compile(r"\bD\.Lgs\.\s*231[/-]2001\b", re.IGNORECASE)),
    (
        "MDR",
        re.compile(r"\b(?:MDR|Reg(?:olamento)?\.?\s*(?:UE|EU)?\s*2017[/\-]745)\b", re.IGNORECASE),
    ),
    ("GDP", re.compile(r"\bGDP\b(?:\s+\d{4})?", re.IGNORECASE)),
    (
        "Codice PI",
        re.compile(
            r"\bCodice\s+(?:di\s+)?prevenzione\s+incendi|D\.M\.\s*3[/-]8[/-]2015\b", re.IGNORECASE
        ),
    ),
    ("ITIL", re.compile(r"\bITIL(?:\s*v?[34])?\b", re.IGNORECASE)),
]


# Pattern sigle (regex Conv. 38 enforcement: glossario canonico).
_SIGLA_PATTERN = re.compile(r"\b([A-Z]{2,6})\b")

# Pattern detection lingue (heuristic word frequency).
_ITALIAN_TOKENS = frozenset(
    {
        "il",
        "la",
        "le",
        "lo",
        "gli",
        "un",
        "una",
        "di",
        "del",
        "della",
        "che",
        "con",
        "per",
        "non",
        "sono",
        "essere",
        "questo",
        "questa",
        "perche",
        "perché",
        "anche",
        "come",
        "quando",
        "dove",
        "dopo",
        "delle",
        "negli",
        "nella",
        "molto",
        "quindi",
        "infatti",
    }
)
_ENGLISH_TOKENS = frozenset(
    {
        "the",
        "and",
        "or",
        "but",
        "with",
        "from",
        "this",
        "that",
        "which",
        "where",
        "when",
        "what",
        "have",
        "has",
        "been",
        "being",
        "because",
        "however",
        "therefore",
        "while",
        "whereas",
        "moreover",
        "furthermore",
    }
)


# ----- Dataclass risultato -----


@dataclass
class DeepScanReport:
    """Snapshot ricco del vault per skill os-setup.

    Tutti i campi sono valori scalari o liste di scalari/dict semplici per
    essere serializzabili JSON-friendly (utili come context runtime delle skill).
    """

    vault_path: str
    vault_name: str

    # Conteggi base
    total_files: int = 0
    files_by_extension: dict[str, int] = field(default_factory=dict)
    md_files_parsed: int = 0
    files_scanned_capped: bool = False  # True se cap _MAX_FILES_SCANNED toccato

    # Distribuzione tipizzata vault SCO (parsing frontmatter md)
    entity_type_distribution: dict[str, int] = field(default_factory=dict)
    ambito_canonico_distribution: dict[str, int] = field(default_factory=dict)
    status_distribution: dict[str, int] = field(default_factory=dict)
    tags_top: list[tuple[str, int]] = field(default_factory=list)

    # Sigle ricorrenti
    sigle_top: list[tuple[str, int]] = field(default_factory=list)

    # Clienti citati (folder Business/*/clienti/*)
    clienti_citati: list[str] = field(default_factory=list)
    clienti_count: int = 0

    # Lingue rilevate (es. {"it": 0.85, "en": 0.10, "other": 0.05})
    languages_detected: dict[str, float] = field(default_factory=dict)

    # Framework normativi dominanti
    framework_occurrences: list[tuple[str, int]] = field(default_factory=list)

    # Performance / tracciatura
    scan_duration_sec: float = 0.0
    has_claude_md: bool = False
    has_wiki: bool = False
    has_raw: bool = False
    has_business: bool = False
    has_giornaliero: bool = False

    # Summary markdown human-readable (popolato da to_markdown_summary)
    markdown_summary: str = ""


# ----- Helpers di scan -----


def _should_skip_dir(dir_name: str) -> bool:
    """Decide se saltare una directory in walk (allineato a scanner.py)."""
    if dir_name in _SKIP_DIRS:
        return True
    return any(dir_name.startswith(prefix) for prefix in _SKIP_PREFIXES)


def _walk_vault_capped(vault_root: Path) -> tuple[list[Path], bool]:
    """Walk con cap _MAX_FILES_SCANNED. Pure-function.

    Returns:
        (lista path file di interesse, flag se cap toccato)
    """
    if not vault_root.exists() or not vault_root.is_dir():
        return [], False

    found: list[Path] = []
    capped = False
    stack: list[Path] = [vault_root]

    while stack:
        if len(found) >= _MAX_FILES_SCANNED:
            capped = True
            break
        current = stack.pop()
        try:
            for entry in current.iterdir():
                if entry.is_dir():
                    if _should_skip_dir(entry.name):
                        continue
                    stack.append(entry)
                elif entry.is_file():
                    if entry.suffix.lower() in _EXTENSIONS_OF_INTEREST:
                        found.append(entry)
                        if len(found) >= _MAX_FILES_SCANNED:
                            capped = True
                            break
        except (PermissionError, OSError) as exc:
            logger.warning("deep_scan walk error in %s: %s", current, exc)
            continue

    return found, capped


def _count_extensions(paths: list[Path]) -> dict[str, int]:
    """Conta file per estensione (lowercase, senza punto)."""
    counter: Counter[str] = Counter()
    for p in paths:
        ext = p.suffix.lower().lstrip(".")
        if ext:
            counter[ext] += 1
    return dict(counter.most_common())


def _detect_clienti(vault_root: Path) -> list[str]:
    """Estrae nomi cartelle clienti da Business/*/clienti/*.

    Pattern Conv. 41 traceability: ritorna lista ordinata alfabeticamente,
    capped a _MAX_CLIENTI_LIST per output compatto.
    """
    business_dir = vault_root / "Business"
    if not business_dir.is_dir():
        return []

    clienti: set[str] = set()
    try:
        for area_dir in business_dir.iterdir():
            if not area_dir.is_dir():
                continue
            if _should_skip_dir(area_dir.name):
                continue
            clienti_subdir = area_dir / "clienti"
            if not clienti_subdir.is_dir():
                continue
            try:
                for cliente_dir in clienti_subdir.iterdir():
                    if cliente_dir.is_dir() and not _should_skip_dir(cliente_dir.name):
                        clienti.add(cliente_dir.name)
            except (PermissionError, OSError) as exc:
                logger.warning("deep_scan clienti walk error in %s: %s", clienti_subdir, exc)
    except (PermissionError, OSError) as exc:
        logger.warning("deep_scan business walk error in %s: %s", business_dir, exc)

    sorted_list = sorted(clienti)
    return sorted_list[:_MAX_CLIENTI_LIST]


def _detect_languages(md_paths: list[Path]) -> dict[str, float]:
    """Heuristic detection lingua su sample di md files.

    Strategia: leggi i primi 500 char di un sample di md files, conta token
    italiani vs inglesi, normalizza a percentuali. Niente librerie esterne
    (es. langdetect) per evitare dipendenze aggiuntive nel bundle PyInstaller.
    """
    if not md_paths:
        return {}

    sample = md_paths[:_MAX_SAMPLE_MD_FOR_LANG]
    it_count = 0
    en_count = 0
    other_count = 0

    for md_path in sample:
        try:
            text = md_path.read_text(encoding="utf-8", errors="replace")[
                :_LANG_SAMPLE_CHARS
            ].lower()
        except (OSError, UnicodeDecodeError) as exc:
            logger.debug("deep_scan lang sample read error %s: %s", md_path, exc)
            continue
        # Strip markdown markup grossolano (frontmatter + simboli)
        text = re.sub(r"[#*`_\[\]()>|-]+", " ", text)
        tokens = re.findall(r"[a-zA-Zàèéìòù]+", text)
        if not tokens:
            continue
        it_hits = sum(1 for t in tokens if t in _ITALIAN_TOKENS)
        en_hits = sum(1 for t in tokens if t in _ENGLISH_TOKENS)
        if it_hits > en_hits and it_hits >= 2:
            it_count += 1
        elif en_hits > it_hits and en_hits >= 2:
            en_count += 1
        else:
            other_count += 1

    total = it_count + en_count + other_count
    if total == 0:
        return {}
    return {
        "it": round(it_count / total, 2),
        "en": round(en_count / total, 2),
        "other": round(other_count / total, 2),
    }


def _detect_sigle(md_paths: list[Path]) -> list[tuple[str, int]]:
    """Estrae sigle ricorrenti (Conv. 38 enforcement: glossario candidate).

    Strategia: scan body di un sample di md files, applica regex SIGLA_PATTERN,
    conta frequenza, filtra cap _MIN_SIGLA_FREQ + soglia _MAX_SIGLE_LIST.
    Esclude sigle inquinanti tipiche (sigle 1-letter, mesi, vocali).
    """
    if not md_paths:
        return []

    blacklist = frozenset(
        {
            "OK",
            "PDF",
            "URL",
            "API",
            "HTTP",
            "HTML",
            "XML",
            "JSON",
            "CEO",
            "CTO",
            "PM",
            "QA",
            "UI",
            "UX",
            "OS",
            "DB",
            "SQL",
            "TODO",
            "FIXME",
            "NA",
            "TBD",
            "ID",
            "GMT",
            "UTC",
            "PST",
        }
    )

    counter: Counter[str] = Counter()
    sample = md_paths[:_MAX_SAMPLE_MD_FOR_SIGLE]
    for md_path in sample:
        try:
            text = md_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError) as exc:
            logger.debug("deep_scan sigle read error %s: %s", md_path, exc)
            continue
        for match in _SIGLA_PATTERN.findall(text):
            if match in blacklist:
                continue
            counter[match] += 1

    filtered = [(s, c) for s, c in counter.most_common() if c >= _MIN_SIGLA_FREQ]
    return filtered[:_MAX_SIGLE_LIST]


def _detect_framework_occurrences(md_paths: list[Path]) -> list[tuple[str, int]]:
    """Conta occorrenze framework normativi nel body md.

    Sample size: tutti i file md fino al cap _MAX_MD_PARSED. Per ogni framework
    conta quanti file lo citano almeno una volta (no per-occurrence per evitare
    overweight di file lungo).

    Returns:
        Lista ordinata per count DESC, solo framework con count > 0.
    """
    if not md_paths:
        return []

    file_hits: Counter[str] = Counter()
    sample = md_paths[:_MAX_MD_PARSED]
    for md_path in sample:
        try:
            text = md_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError) as exc:
            logger.debug("deep_scan framework read error %s: %s", md_path, exc)
            continue
        for fw_name, pattern in _FRAMEWORK_PATTERNS:
            if pattern.search(text):
                file_hits[fw_name] += 1

    return [(fw, c) for fw, c in file_hits.most_common() if c > 0]


def _scan_frontmatter_distributions(
    md_paths: list[Path],
) -> tuple[dict[str, int], dict[str, int], dict[str, int], list[tuple[str, int]], int]:
    """Parse frontmatter di sample md files + raccoglie distribuzioni.

    Returns:
        (entity_type_dist, ambito_canonico_dist, status_dist, tags_top, parsed_count)
    """
    entity_counter: Counter[str] = Counter()
    ambito_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    tags_counter: Counter[str] = Counter()
    parsed_count = 0

    sample = md_paths[:_MAX_MD_PARSED]
    for md_path in sample:
        try:
            doc = parse_vault_file(md_path)
        except Exception as exc:
            logger.debug("deep_scan parse error %s: %s", md_path, exc)
            continue
        parsed_count += 1
        if doc.entity_type:
            entity_counter[doc.entity_type] += 1
        if doc.ambito_canonico:
            ambito_counter[doc.ambito_canonico] += 1
        if doc.status:
            status_counter[doc.status] += 1
        for tag in doc.tags:
            if isinstance(tag, str) and tag.strip():
                tags_counter[tag.strip()] += 1

    tags_top = tags_counter.most_common(15)
    return (
        dict(entity_counter.most_common()),
        dict(ambito_counter.most_common()),
        dict(status_counter.most_common()),
        tags_top,
        parsed_count,
    )


# ----- API pubblica -----


def deep_scan_vault(
    vault_path: Path,
    *,
    vault_name: str | None = None,
) -> DeepScanReport:
    """Esegue scan profondo del vault e ritorna report ricco.

    Pattern Conv. 35 RESEARCH-BEFORE-ACT: scan reale filesystem, mai mock.
    Pattern Conv. 46 SMOKE PRIMA DEL TAG: cap su file e sample per garantire
    durata sub-10s anche su vault grandi (cap _MAX_FILES_SCANNED, sample
    parsing limitato a _MAX_MD_PARSED).

    Args:
        vault_path: path radice del vault (Path object).
        vault_name: nome friendly del vault (se None, usa nome cartella).

    Returns:
        DeepScanReport popolato con tutti i metrics + markdown_summary.
    """
    start_ts = time.monotonic()

    effective_name = vault_name or vault_path.name
    report = DeepScanReport(
        vault_path=str(vault_path),
        vault_name=effective_name,
    )

    if not vault_path.exists() or not vault_path.is_dir():
        logger.warning("deep_scan_vault: vault path inesistente %s", vault_path)
        report.markdown_summary = (
            f"Vault `{effective_name}` non trovato o non accessibile al path "
            f"`{vault_path}`. Verifica il percorso e riprova."
        )
        report.scan_duration_sec = round(time.monotonic() - start_ts, 3)
        return report

    # 1. Walk filesystem capped
    paths, capped = _walk_vault_capped(vault_path)
    report.total_files = len(paths)
    report.files_scanned_capped = capped

    # 2. Conteggi per estensione
    report.files_by_extension = _count_extensions(paths)

    # 3. Subset md files
    md_paths = [p for p in paths if p.suffix.lower() == ".md"]

    # 4. Distribuzioni frontmatter
    (
        report.entity_type_distribution,
        report.ambito_canonico_distribution,
        report.status_distribution,
        report.tags_top,
        report.md_files_parsed,
    ) = _scan_frontmatter_distributions(md_paths)

    # 5. Sigle ricorrenti
    report.sigle_top = _detect_sigle(md_paths)

    # 6. Clienti citati
    report.clienti_citati = _detect_clienti(vault_path)
    report.clienti_count = len(report.clienti_citati)

    # 7. Lingue rilevate
    report.languages_detected = _detect_languages(md_paths)

    # 8. Framework dominanti
    report.framework_occurrences = _detect_framework_occurrences(md_paths)

    # 9. Presenza cartelle/file chiave SCO three-layer
    report.has_claude_md = (vault_path / "CLAUDE.md").is_file()
    report.has_wiki = (vault_path / "wiki").is_dir()
    report.has_raw = (vault_path / "raw").is_dir()
    report.has_business = (vault_path / "Business").is_dir()
    report.has_giornaliero = (vault_path / "Giornaliero").is_dir()

    # 10. Performance
    report.scan_duration_sec = round(time.monotonic() - start_ts, 3)

    # 11. Markdown summary leggibile
    report.markdown_summary = to_markdown_summary(report)

    logger.info(
        "deep_scan_vault.completed",
        vault_path=str(vault_path),
        total_files=report.total_files,
        md_parsed=report.md_files_parsed,
        clienti=report.clienti_count,
        framework_top=len(report.framework_occurrences),
        duration_sec=report.scan_duration_sec,
        capped=capped,
    )

    return report


def to_markdown_summary(report: DeepScanReport) -> str:
    """Rendering markdown human-readable del DeepScanReport (500-1000 char).

    Output pattern Antonio:
        - Tono Amodeo italiano professionale (no AI vocabulary).
        - Linguaggio chiaro immediato (Conv. 14/05/2026): frasi corte.
        - Niente emoji decorativi (Conv. 03/05/2026).
        - Virgolette dritte (Conv. 03/05/2026).
        - Tabelle per dati strutturati invece di periodi lunghi.
    """
    lines: list[str] = []
    lines.append(f'## Scansione profonda del vault "{report.vault_name}"')
    lines.append("")

    # Riga apertura sintetica
    if report.files_scanned_capped:
        lines.append(
            f"Scansionati i primi {report.total_files} file (vault molto grande, "
            f"limite di sicurezza raggiunto). Durata: {report.scan_duration_sec}s."
        )
    else:
        lines.append(f"Scansionati {report.total_files} file in {report.scan_duration_sec}s.")
    lines.append("")

    # Tabella file per estensione (top 6)
    if report.files_by_extension:
        lines.append("### File per tipo")
        lines.append("")
        lines.append("| Tipo | Numero |")
        lines.append("|---|---|")
        for ext, count in list(report.files_by_extension.items())[:6]:
            lines.append(f"| .{ext} | {count} |")
        lines.append("")

    # Struttura SCO three-layer
    sco_status_lines: list[str] = []
    if report.has_claude_md:
        sco_status_lines.append("- CLAUDE.md presente")
    if report.has_wiki:
        sco_status_lines.append("- cartella `wiki/` presente")
    if report.has_raw:
        sco_status_lines.append("- cartella `raw/` presente")
    if report.has_business:
        sco_status_lines.append("- cartella `Business/` presente")
    if report.has_giornaliero:
        sco_status_lines.append("- cartella `Giornaliero/` presente")
    if sco_status_lines:
        lines.append("### Struttura SCO")
        lines.append("")
        lines.extend(sco_status_lines)
        lines.append("")

    # Distribuzione tipizzata (solo se >0 file parsed con metadati SCO)
    if report.md_files_parsed > 0 and (
        report.entity_type_distribution or report.ambito_canonico_distribution
    ):
        lines.append(f"### Metadati SCO ({report.md_files_parsed} file markdown analizzati)")
        lines.append("")
        if report.entity_type_distribution:
            top_ents = list(report.entity_type_distribution.items())[:5]
            ent_str = ", ".join(f"{k} ({v})" for k, v in top_ents)
            lines.append(f"- Tipi entity prevalenti: {ent_str}")
        if report.ambito_canonico_distribution:
            top_amb = list(report.ambito_canonico_distribution.items())[:5]
            amb_str = ", ".join(f"{k} ({v})" for k, v in top_amb)
            lines.append(f"- Ambiti canonici prevalenti: {amb_str}")
        lines.append("")

    # Clienti citati
    if report.clienti_citati:
        lines.append(f"### Clienti rilevati ({report.clienti_count})")
        lines.append("")
        sample = ", ".join(report.clienti_citati[:10])
        lines.append(sample)
        if report.clienti_count > 10:
            lines.append(f"...e altri {report.clienti_count - 10}.")
        lines.append("")

    # Framework dominanti
    if report.framework_occurrences:
        lines.append("### Framework normativi piu' citati")
        lines.append("")
        for fw, count in report.framework_occurrences[:8]:
            lines.append(f"- {fw}: {count} file")
        lines.append("")

    # Lingue
    if report.languages_detected:
        it_pct = int(report.languages_detected.get("it", 0) * 100)
        en_pct = int(report.languages_detected.get("en", 0) * 100)
        other_pct = int(report.languages_detected.get("other", 0) * 100)
        lines.append("### Lingue rilevate")
        lines.append("")
        lines.append(f"Italiano {it_pct}%, Inglese {en_pct}%, Altro {other_pct}%")
        lines.append("")

    # Sigle top (cruscotto candidate glossario Conv. 38)
    if report.sigle_top:
        lines.append("### Sigle ricorrenti (candidate glossario)")
        lines.append("")
        sample_sigle = ", ".join(f"{s} ({c})" for s, c in report.sigle_top[:12])
        lines.append(sample_sigle)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("Ora ti faccio 10 domande veloci per personalizzare l'agente. Una alla volta.")

    return "\n".join(lines)


__all__ = [
    "DeepScanReport",
    "deep_scan_vault",
    "to_markdown_summary",
]
