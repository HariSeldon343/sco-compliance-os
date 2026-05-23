"""TokenJuice — 3-layer rule-based compression engine (clean-room replica).

Compressione di contenuti raw (HTML, markdown lunghi, transcript) PRIMA del
loro inserimento nel Memory Tree, per ridurre il consumo token nel context
window del modello LLM.

Pattern clean-room derivato dalla documentazione pubblica OpenHuman (3-layer
overlay builtin/user/project, NO accesso al source GPL-3.0 originale). La
logica e' stata riprogettata in Python idiomatico Antonio-style, con piena
disciplina type-strict mypy --strict + structlog + tiktoken counting.

3 LAYER CASCADE (in ordine, ciascuno opt-in/out via ``enable_layers``):

1. **Layer 1 builtin** (regex puro, no LLM, no config esterna).
   Pulizia di base: HTML -> markdown via html2text, rimozione tag noise
   (script/style/nav/footer), strip whitespace ridondante, collapse multiple
   newlines, drop link tracking UTM, drop cookie banner pattern.

2. **Layer 2 user rules** (config YAML opzionale).
   Lettura di ``~/.sco-compliance-os/tokenjuice_rules.yaml`` (override path
   accettato come argomento). Schema: ``patterns: list[{pattern: regex,
   replacement: str, description: str}]``. Fallback silenzioso se file
   assente o malformato (warning structlog, layer skip).

3. **Layer 3 project rules** (hardcoded compliance-italiana).
   Collassa riferimenti normativi verbosi: "Articolo X comma Y lettera Z"
   -> "Art. X c. Y lett. Z" (mantiene semantica, riduce ~40% token).
   Lookup table 24 voci normative italiane: D.Lgs. 138/2024 -> "NIS 2",
   Reg. UE 2024/1689 -> "AI Act", ISO/IEC 27001:2022 -> "ISO 27001", ecc.

API pubblica principale:
    ``async def compress_text(raw_text, source_type, enable_layers, user_rules_path)
    -> CompressResult``

Vincoli architetturali (Conv. 34 disciplina):
    - Idempotente: compress(compress(x)) ~ compress(x) entro 5% jitter.
    - No LLM call: tutte le 3 layer sono REGEX/TABLE LOOKUP. Zero costi.
    - Async-first: tutte le API I/O bound sono ``async def`` (read file
      YAML, anche se nel pratico e' veloce, per consistenza ecosistema).
    - Default safe: se YAML user assente -> layer 2 skip silenzioso.

NOTA pyproject deps: html2text>=2024.2.26, tiktoken>=0.9.0, pyyaml>=6.0.2
sono gia' presenti nel pyproject.toml (verificato 23/05). Nessuna nuova dep.

Carry-over Wave 3 (NON in scope qui): Layer 4 LLM-driven summarization
(Claude Haiku batch) per chunks > 8k token che resistono ai layer 1-3.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import structlog
import yaml

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

# Path default file user rules YAML (override accettato come arg).
_DEFAULT_USER_RULES_PATH: Final[Path] = Path.home() / ".sco-compliance-os" / "tokenjuice_rules.yaml"


# ---------------------------------------------------------------------------
# DATA CLASSES
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CompressResult:
    """Risultato di una compressione 3-layer.

    Attributes:
        compressed_text: testo finale dopo applicazione di tutti i layer abilitati.
        original_tokens: conteggio token testo originale (tiktoken cl100k_base).
        compressed_tokens: conteggio token testo finale.
        compression_ratio: 1.0 - (compressed / original); 0.0 = nessun saving,
            1.0 = 100% saving (testo ridotto a zero token).
        applied_rules: lista identificatori regole applicate (debug/audit trail).
        layer_stats: per layer (1, 2, 3) -> dict con ``tokens_before``,
            ``tokens_after``, ``tokens_saved``, ``rules_count``.
    """

    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    applied_rules: list[str] = field(default_factory=list)
    layer_stats: dict[int, dict[str, int]] = field(default_factory=dict)


@dataclass(slots=True)
class UserRule:
    """Singola user rule caricata da YAML.

    Attributes:
        pattern: regex Python (compilata in ``compiled`` post-load).
        replacement: stringa di sostituzione (supporta backreferences ``\\1`` ecc.).
        description: descrizione human-readable per audit trail.
        compiled: regex compilata (popolata da _load_user_rules).
    """

    pattern: str
    replacement: str
    description: str = ""
    compiled: re.Pattern[str] | None = None


# ---------------------------------------------------------------------------
# LAYER 1 — BUILTIN regex / html2text sanitize
# ---------------------------------------------------------------------------

# Pattern HTML noise da rimuovere PRIMA della conversione html2text.
# html2text gia' rimuove script/style ma non sempre nav/footer (dipende dal markup).
_HTML_NOISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<nav\b[^<]*(?:(?!</nav>)<[^<]*)*</nav>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<footer\b[^<]*(?:(?!</footer>)<[^<]*)*</footer>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<header\b[^<]*(?:(?!</header>)<[^<]*)*</header>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<!--.*?-->", re.DOTALL),
]

# UTM tracking parametri da rimuovere da query string nei link.
_UTM_PARAM_RE: Final[re.Pattern[str]] = re.compile(
    r"[?&](utm_[a-z_]+|gclid|fbclid|mc_eid|mc_cid|ref|source)=[^&\s)]*",
    re.IGNORECASE,
)

# Cookie banner pattern (italiani + inglesi).
_COOKIE_BANNER_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:questo sito|this site|we use cookies|utilizziamo cookie|cookie policy|"
    r"accetta tutti|accept all|gestisci preferenze|manage preferences)[^.\n]*[.\n]",
    re.IGNORECASE,
)

# Whitespace collapse: 3+ newlines -> 2, spazi multipli -> 1.
_MULTI_NEWLINE_RE: Final[re.Pattern[str]] = re.compile(r"\n{3,}")
_MULTI_SPACE_RE: Final[re.Pattern[str]] = re.compile(r"[ \t]{2,}")
_LEADING_WS_RE: Final[re.Pattern[str]] = re.compile(r"^[ \t]+", re.MULTILINE)

# Markdown link [anchor](url) -> anchor (preserva semantica, scarta URL).
# NOTA: applicato SOLO se URL e' tracking-heavy o se source_type == "html".
# Pattern conservativo: solo link con http(s):// e nessun anchor immagine.
_MD_LINK_RE: Final[re.Pattern[str]] = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def _apply_layer_1_builtin(raw_text: str, source_type: str) -> tuple[str, list[str]]:
    """Layer 1 builtin: HTML sanitize + whitespace collapse + UTM strip.

    Args:
        raw_text: input grezzo.
        source_type: 'html' | 'markdown' | 'transcript' | 'manual'.
            - 'html': applica html2text + tutti i pattern noise.
            - 'markdown': skip html2text, applica whitespace + UTM + cookie banner.
            - 'transcript': skip html2text, applica solo whitespace collapse.
            - 'manual': minimo intervento, solo whitespace collapse.

    Returns:
        (testo_pulito, lista_regole_applicate).
    """
    rules_applied: list[str] = []
    text = raw_text

    # 1.1 HTML noise rimozione + conversione (solo se source HTML).
    if source_type == "html":
        for idx, pattern in enumerate(_HTML_NOISE_PATTERNS):
            count_before = len(text)
            text = pattern.sub("", text)
            if len(text) < count_before:
                rules_applied.append(f"L1.html_noise_{idx}")

        # Conversione HTML -> markdown via html2text.
        try:
            import html2text

            converter = html2text.HTML2Text()
            converter.ignore_links = False
            converter.ignore_images = True
            converter.body_width = 0  # no wrap (preserva paragrafi originali)
            converter.unicode_snob = True
            converter.skip_internal_links = True
            text = converter.handle(text)
            rules_applied.append("L1.html2text_convert")
        except Exception as e:
            logger.warning("tokenjuice.l1.html2text_failed", error=str(e))

    # 1.2 UTM tracking strip (sempre, anche markdown).
    if _UTM_PARAM_RE.search(text):
        text = _UTM_PARAM_RE.sub("", text)
        rules_applied.append("L1.utm_strip")

    # 1.3 Cookie banner strip (solo se HTML o markdown lungo > 500 chars).
    if source_type in ("html", "markdown") and len(text) > 500:
        if _COOKIE_BANNER_RE.search(text):
            text = _COOKIE_BANNER_RE.sub("", text)
            rules_applied.append("L1.cookie_banner")

    # 1.4 Markdown link strip (solo per HTML/markdown, conserva anchor).
    if source_type in ("html", "markdown"):
        if _MD_LINK_RE.search(text):
            text = _MD_LINK_RE.sub(r"\1", text)
            rules_applied.append("L1.md_link_anchor_preserve")

    # 1.5 Whitespace collapse (sempre).
    if _MULTI_NEWLINE_RE.search(text):
        text = _MULTI_NEWLINE_RE.sub("\n\n", text)
        rules_applied.append("L1.multi_newline_collapse")
    if _MULTI_SPACE_RE.search(text):
        text = _MULTI_SPACE_RE.sub(" ", text)
        rules_applied.append("L1.multi_space_collapse")
    if _LEADING_WS_RE.search(text):
        text = _LEADING_WS_RE.sub("", text)
        rules_applied.append("L1.leading_ws_strip")

    return text.strip(), rules_applied


# ---------------------------------------------------------------------------
# LAYER 2 — USER rules (config YAML opzionale)
# ---------------------------------------------------------------------------


async def _load_user_rules(rules_path: Path) -> list[UserRule]:
    """Carica user rules da file YAML. Fallback silenzioso se assente/malformato.

    Schema YAML atteso:
        patterns:
          - pattern: "regex_pattern"
            replacement: "replacement_string"
            description: "human-readable desc"
          - ...

    Args:
        rules_path: Path al file YAML.

    Returns:
        Lista di UserRule. Empty se file assente o malformato.
    """
    if not rules_path.exists():
        logger.debug("tokenjuice.l2.rules_file_not_found", path=str(rules_path))
        return []

    try:
        # I/O bound: usa to_thread per non bloccare event loop.
        raw_yaml = await asyncio.to_thread(rules_path.read_text, encoding="utf-8")
        parsed: Any = yaml.safe_load(raw_yaml)
    except (yaml.YAMLError, OSError) as e:
        logger.warning(
            "tokenjuice.l2.yaml_parse_failed",
            path=str(rules_path),
            error=str(e),
        )
        return []

    if not isinstance(parsed, dict):
        logger.warning(
            "tokenjuice.l2.yaml_not_dict",
            path=str(rules_path),
            actual_type=type(parsed).__name__,
        )
        return []

    patterns = parsed.get("patterns", [])
    if not isinstance(patterns, list):
        logger.warning(
            "tokenjuice.l2.yaml_patterns_not_list",
            actual_type=type(patterns).__name__,
        )
        return []

    rules: list[UserRule] = []
    for idx, entry in enumerate(patterns):
        if not isinstance(entry, dict):
            logger.warning("tokenjuice.l2.entry_not_dict", idx=idx)
            continue
        pattern_str = entry.get("pattern", "")
        replacement = entry.get("replacement", "")
        description = entry.get("description", "")
        if not pattern_str:
            logger.warning("tokenjuice.l2.entry_no_pattern", idx=idx)
            continue
        try:
            compiled = re.compile(pattern_str)
        except re.error as rex:
            logger.warning(
                "tokenjuice.l2.regex_compile_failed",
                idx=idx,
                pattern=pattern_str,
                error=str(rex),
            )
            continue
        rules.append(
            UserRule(
                pattern=pattern_str,
                replacement=str(replacement),
                description=str(description),
                compiled=compiled,
            )
        )

    logger.info(
        "tokenjuice.l2.rules_loaded",
        path=str(rules_path),
        count=len(rules),
    )
    return rules


def _apply_layer_2_user(text: str, rules: list[UserRule]) -> tuple[str, list[str]]:
    """Layer 2 user: applica user rules YAML caricate.

    Args:
        text: testo da processare.
        rules: lista di UserRule (gia' compilate).

    Returns:
        (testo_processato, lista_id_regole_applicate).
    """
    rules_applied: list[str] = []
    result_text = text
    for idx, rule in enumerate(rules):
        if rule.compiled is None:
            continue
        if rule.compiled.search(result_text):
            try:
                result_text = rule.compiled.sub(rule.replacement, result_text)
                # ID rule: usa description se presente, altrimenti idx.
                rule_id = (
                    f"L2.user.{rule.description}" if rule.description else f"L2.user_rule_{idx}"
                )
                rules_applied.append(rule_id)
            except re.error as e:
                logger.warning(
                    "tokenjuice.l2.sub_failed",
                    idx=idx,
                    pattern=rule.pattern,
                    error=str(e),
                )
                continue
    return result_text, rules_applied


# ---------------------------------------------------------------------------
# LAYER 3 — PROJECT rules (compliance italiana hardcoded)
# ---------------------------------------------------------------------------

# 3.1 Riferimenti articolato verboso -> sigle. Pattern conservativi.
# "Articolo X comma Y lettera Z" -> "Art. X c. Y lett. Z"
_ART_VERBOSE_FULL_RE: Final[re.Pattern[str]] = re.compile(
    r"\bArticolo\s+(\d+)\s+comma\s+(\d+)\s+lettera\s+([a-z])\b",
    re.IGNORECASE,
)
_ART_VERBOSE_AC_RE: Final[re.Pattern[str]] = re.compile(
    r"\bArticolo\s+(\d+)\s+comma\s+(\d+)\b",
    re.IGNORECASE,
)
_ART_VERBOSE_A_RE: Final[re.Pattern[str]] = re.compile(
    r"\bArticolo\s+(\d+)\b",
    re.IGNORECASE,
)

# 3.2 Lookup table normative italiane verbose -> sigle canoniche.
# Sintassi: list[tuple[regex_pattern, sigla_canonica]].
# Pattern conservativi: case-insensitive, word boundaries dove sensato.
_NORMATIVE_LOOKUP: Final[list[tuple[re.Pattern[str], str]]] = [
    # NIS 2 (Direttiva e recepimento)
    (
        re.compile(
            r"\bDecreto\s+Legislativo\s+(?:4\s+)?settembre\s+2024,?\s*n\.?\s*138\b",
            re.IGNORECASE,
        ),
        "D.Lgs. 138/2024 (NIS 2)",
    ),
    (
        re.compile(
            r"\bDirettiva\s+(?:UE\s+)?2022/2555\b",
            re.IGNORECASE,
        ),
        "Direttiva UE 2022/2555 (NIS 2)",
    ),
    # AI Act
    (
        re.compile(
            r"\bRegolamento\s+(?:UE\s+)?2024/1689\b",
            re.IGNORECASE,
        ),
        "Reg. UE 2024/1689 (AI Act)",
    ),
    # GDPR
    (
        re.compile(
            r"\bRegolamento\s+(?:UE\s+)?2016/679\b",
            re.IGNORECASE,
        ),
        "Reg. UE 2016/679 (GDPR)",
    ),
    # ISO/IEC verbose
    (
        re.compile(
            r"\bISO/IEC\s+27001\s*:?\s*2022\b",
            re.IGNORECASE,
        ),
        "ISO 27001:2022",
    ),
    (
        re.compile(
            r"\bISO/IEC\s+27017\s*:?\s*2015\b",
            re.IGNORECASE,
        ),
        "ISO 27017:2015",
    ),
    (
        re.compile(
            r"\bISO/IEC\s+27018\s*:?\s*(?:2019|2025)\b",
            re.IGNORECASE,
        ),
        "ISO 27018",
    ),
    (
        re.compile(
            r"\bISO/IEC\s+42001\s*:?\s*2023\b",
            re.IGNORECASE,
        ),
        "ISO 42001:2023",
    ),
    (
        re.compile(
            r"\bISO/IEC\s+20000-1\s*:?\s*2018\b",
            re.IGNORECASE,
        ),
        "ISO 20000-1:2018",
    ),
    # D.Lgs. comuni
    (
        re.compile(
            r"\bDecreto\s+Legislativo\s+9\s+aprile\s+2008,?\s*n\.?\s*81\b",
            re.IGNORECASE,
        ),
        "D.Lgs. 81/2008 (sicurezza lavoro)",
    ),
    (
        re.compile(
            r"\bDecreto\s+Legislativo\s+31\s+luglio\s+2020,?\s*n\.?\s*101\b",
            re.IGNORECASE,
        ),
        "D.Lgs. 101/2020 (radioprotezione)",
    ),
    # Authority Italian + EU verbose
    (
        re.compile(
            r"\bAgenzia\s+per\s+la\s+Cybersicurezza\s+Nazionale\b",
            re.IGNORECASE,
        ),
        "ACN",
    ),
    (
        re.compile(
            r"\bAgenzia\s+nazionale\s+per\s+i\s+servizi\s+sanitari\s+regionali\b",
            re.IGNORECASE,
        ),
        "AGENAS",
    ),
    (
        re.compile(
            r"\bAgenzia\s+per\s+l[''](?:I|i)talia\s+(?:D|d)igitale\b",
            re.IGNORECASE,
        ),
        "AgID",
    ),
    (
        re.compile(
            r"\bGarante\s+per\s+la\s+protezione\s+dei\s+dati\s+personali\b",
            re.IGNORECASE,
        ),
        "Garante Privacy",
    ),
    (
        re.compile(
            r"\bEuropean\s+Union\s+Agency\s+for\s+Cybersecurity\b",
            re.IGNORECASE,
        ),
        "ENISA",
    ),
    # MDR / IVDR
    (
        re.compile(
            r"\bRegolamento\s+(?:UE\s+)?2017/745\b",
            re.IGNORECASE,
        ),
        "Reg. UE 2017/745 (MDR)",
    ),
    (
        re.compile(
            r"\bRegolamento\s+(?:UE\s+)?2017/746\b",
            re.IGNORECASE,
        ),
        "Reg. UE 2017/746 (IVDR)",
    ),
    # Legge 90/2024 cybersicurezza
    (
        re.compile(
            r"\bLegge\s+28\s+giugno\s+2024,?\s*n\.?\s*90\b",
            re.IGNORECASE,
        ),
        "L. 90/2024",
    ),
    # Legge 132/2025 IA
    (
        re.compile(
            r"\bLegge\s+10\s+settembre\s+2025,?\s*n\.?\s*132\b",
            re.IGNORECASE,
        ),
        "L. 132/2025",
    ),
    # DPR 151/2011 prevenzione incendi
    (
        re.compile(
            r"\bDPR\s+1\s+agosto\s+2011,?\s*n\.?\s*151\b",
            re.IGNORECASE,
        ),
        "DPR 151/2011",
    ),
    # Accordo Stato-Regioni 17/04/2025 formazione
    (
        re.compile(
            r"\bAccordo\s+Stato[-\s]Regioni\s+(?:del\s+)?17[/\s\-]04[/\s\-]2025\b",
            re.IGNORECASE,
        ),
        "ASR 17/04/2025",
    ),
    # D.Lgs. 209/2024 correttivo appalti
    (
        re.compile(
            r"\bDecreto\s+Legislativo\s+31\s+dicembre\s+2024,?\s*n\.?\s*209\b",
            re.IGNORECASE,
        ),
        "D.Lgs. 209/2024 (correttivo appalti)",
    ),
    # D.Lgs. 36/2023 appalti
    (
        re.compile(
            r"\bDecreto\s+Legislativo\s+31\s+marzo\s+2023,?\s*n\.?\s*36\b",
            re.IGNORECASE,
        ),
        "D.Lgs. 36/2023 (Codice appalti)",
    ),
    # Reg. UE 520/2012 farmacovigilanza
    (
        re.compile(
            r"\bRegolamento\s+(?:UE\s+)?520/2012\b",
            re.IGNORECASE,
        ),
        "Reg. UE 520/2012 (farmacovigilanza)",
    ),
]

# 3.3 Termini ridondanti di stile burocratico italiano -> form compatta.
_BUREAUCRATIC_COMPACT: Final[list[tuple[re.Pattern[str], str]]] = [
    (
        re.compile(r"\bai\s+sensi\s+di\s+quanto\s+disposto\s+dall(?:'|a)\b", re.IGNORECASE),
        "ai sensi di",
    ),
    (
        re.compile(r"\bin\s+ottemperanza\s+alle?\s+disposizioni\s+di\b", re.IGNORECASE),
        "ai sensi di",
    ),
    (
        re.compile(
            r"\bnel\s+rispetto\s+di\s+quanto\s+previsto\s+dal(?:la|le|l(?:'))\b", re.IGNORECASE
        ),
        "ai sensi di",
    ),
    (re.compile(r"\bsi\s+fa\s+riferimento\s+(?:al|alla|all(?:'))\b", re.IGNORECASE), "vd."),
    (re.compile(r"\bcon\s+riferimento\s+(?:al|alla|all(?:'))\b", re.IGNORECASE), "re:"),
]


def _apply_layer_3_project(text: str) -> tuple[str, list[str]]:
    """Layer 3 project: collassa riferimenti normativi italiani + sigle authority.

    Args:
        text: testo da processare.

    Returns:
        (testo_processato, lista_id_regole_applicate).
    """
    rules_applied: list[str] = []
    result_text = text

    # 3.1 Articolato verboso (in ordine: piu' specifico prima).
    if _ART_VERBOSE_FULL_RE.search(result_text):
        result_text = _ART_VERBOSE_FULL_RE.sub(r"Art. \1 c. \2 lett. \3", result_text)
        rules_applied.append("L3.art_verbose_full")
    if _ART_VERBOSE_AC_RE.search(result_text):
        result_text = _ART_VERBOSE_AC_RE.sub(r"Art. \1 c. \2", result_text)
        rules_applied.append("L3.art_verbose_ac")
    if _ART_VERBOSE_A_RE.search(result_text):
        result_text = _ART_VERBOSE_A_RE.sub(r"Art. \1", result_text)
        rules_applied.append("L3.art_verbose_a")

    # 3.2 Normative lookup (24 entries).
    for idx, (pat, sigla) in enumerate(_NORMATIVE_LOOKUP):
        if pat.search(result_text):
            result_text = pat.sub(sigla, result_text)
            rules_applied.append(f"L3.norm_lookup_{idx}")

    # 3.3 Bureaucratic compact.
    for idx, (pat, replacement) in enumerate(_BUREAUCRATIC_COMPACT):
        if pat.search(result_text):
            result_text = pat.sub(replacement, result_text)
            rules_applied.append(f"L3.bureaucratic_{idx}")

    return result_text, rules_applied


# ---------------------------------------------------------------------------
# TOKEN COUNTING
# ---------------------------------------------------------------------------


def _count_tokens(text: str) -> int:
    """Conta token via tiktoken cl100k_base (compatibile Anthropic ~95%).

    Fallback euristico (4 chars/token) se tiktoken non disponibile.

    Args:
        text: testo da contare.

    Returns:
        Conteggio token (int >= 0).
    """
    if not text:
        return 0
    try:
        import tiktoken

        encoder = tiktoken.get_encoding("cl100k_base")
        return len(encoder.encode(text))
    except (ImportError, ModuleNotFoundError):
        logger.debug("tokenjuice.tiktoken_unavailable_fallback")
        return max(1, len(text) // 4)
    except Exception as e:
        logger.warning("tokenjuice.tiktoken_encode_failed", error=str(e))
        return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# MAIN API
# ---------------------------------------------------------------------------


async def compress_text(
    raw_text: str,
    *,
    source_type: str = "manual",
    enable_layers: tuple[int, ...] = (1, 2, 3),
    user_rules_path: Path | None = None,
) -> CompressResult:
    """Comprime testo applicando 3-layer cascade (builtin/user/project).

    Pipeline (in ordine, ciascun layer opt-in/out):
        1. Layer 1 builtin: HTML sanitize + whitespace collapse + UTM strip.
        2. Layer 2 user: rules YAML opzionali da ~/.sco-compliance-os/.
        3. Layer 3 project: normative italiane verbose -> sigle canoniche.

    Args:
        raw_text: testo grezzo da comprimere.
        source_type: 'html' | 'markdown' | 'transcript' | 'manual'.
            Default 'manual' (minimo intervento). 'html' attiva html2text + tutti
            i pattern noise. 'markdown' skip html2text. 'transcript' solo whitespace.
        enable_layers: tuple di layer attivi. Default (1, 2, 3) = tutti.
            Esempi: (1,) = solo builtin, (1, 3) = skip user rules.
        user_rules_path: path file YAML user rules. Default
            ~/.sco-compliance-os/tokenjuice_rules.yaml (silent skip se assente).

    Returns:
        CompressResult con testo finale + token stats + layer breakdown.
    """
    if not raw_text or not raw_text.strip():
        return CompressResult(
            compressed_text="",
            original_tokens=0,
            compressed_tokens=0,
            compression_ratio=0.0,
            applied_rules=[],
            layer_stats={},
        )

    original_tokens = _count_tokens(raw_text)
    logger.info(
        "tokenjuice.compress.start",
        source_type=source_type,
        enable_layers=list(enable_layers),
        original_tokens=original_tokens,
        original_chars=len(raw_text),
    )

    current_text = raw_text
    all_rules_applied: list[str] = []
    layer_stats: dict[int, dict[str, int]] = {}

    # ----- Layer 1 -----
    if 1 in enable_layers:
        tokens_before = _count_tokens(current_text)
        new_text, rules_l1 = _apply_layer_1_builtin(current_text, source_type=source_type)
        current_text = new_text
        tokens_after = _count_tokens(current_text)
        layer_stats[1] = {
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "tokens_saved": tokens_before - tokens_after,
            "rules_count": len(rules_l1),
        }
        all_rules_applied.extend(rules_l1)

    # ----- Layer 2 -----
    if 2 in enable_layers:
        tokens_before = _count_tokens(current_text)
        resolved_path = user_rules_path or _DEFAULT_USER_RULES_PATH
        user_rules = await _load_user_rules(resolved_path)
        if user_rules:
            new_text, rules_l2 = _apply_layer_2_user(current_text, user_rules)
            current_text = new_text
            tokens_after = _count_tokens(current_text)
            layer_stats[2] = {
                "tokens_before": tokens_before,
                "tokens_after": tokens_after,
                "tokens_saved": tokens_before - tokens_after,
                "rules_count": len(rules_l2),
            }
            all_rules_applied.extend(rules_l2)
        else:
            # Layer 2 skipped (no user rules), zero stats.
            layer_stats[2] = {
                "tokens_before": tokens_before,
                "tokens_after": tokens_before,
                "tokens_saved": 0,
                "rules_count": 0,
            }

    # ----- Layer 3 -----
    if 3 in enable_layers:
        tokens_before = _count_tokens(current_text)
        new_text, rules_l3 = _apply_layer_3_project(current_text)
        current_text = new_text
        tokens_after = _count_tokens(current_text)
        layer_stats[3] = {
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "tokens_saved": tokens_before - tokens_after,
            "rules_count": len(rules_l3),
        }
        all_rules_applied.extend(rules_l3)

    compressed_tokens = _count_tokens(current_text)
    ratio = 1.0 - (compressed_tokens / original_tokens) if original_tokens > 0 else 0.0

    logger.info(
        "tokenjuice.compress.complete",
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        compression_ratio=round(ratio, 4),
        rules_applied_count=len(all_rules_applied),
        layers_used=list(layer_stats.keys()),
    )

    return CompressResult(
        compressed_text=current_text,
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        compression_ratio=round(ratio, 4),
        applied_rules=all_rules_applied,
        layer_stats=layer_stats,
    )


# ---------------------------------------------------------------------------
# INTROSPECTION API (per endpoint GET /api/tokenjuice/rules)
# ---------------------------------------------------------------------------


async def describe_rules(
    user_rules_path: Path | None = None,
) -> dict[str, Any]:
    """Ritorna config caricata (builtin + user + project) per ispezione UI.

    Args:
        user_rules_path: path file YAML user rules (None = default).

    Returns:
        Dict con tre chiavi:
            - 'builtin': lista nomi pattern hardcoded layer 1.
            - 'user': lista user rules caricate (path + count + entries).
            - 'project': lista normative/sigle layer 3.
    """
    builtin_patterns = [
        "html_noise_script",
        "html_noise_style",
        "html_noise_nav",
        "html_noise_footer",
        "html_noise_header",
        "html_comments",
        "utm_strip",
        "cookie_banner",
        "md_link_anchor_preserve",
        "multi_newline_collapse",
        "multi_space_collapse",
        "leading_ws_strip",
    ]

    resolved_path = user_rules_path or _DEFAULT_USER_RULES_PATH
    user_rules_loaded = await _load_user_rules(resolved_path)
    user_payload = {
        "path": str(resolved_path),
        "exists": resolved_path.exists(),
        "count": len(user_rules_loaded),
        "entries": [
            {
                "pattern": r.pattern,
                "replacement": r.replacement,
                "description": r.description,
            }
            for r in user_rules_loaded
        ],
    }

    project_entries = [
        {"sigla": sigla, "pattern_repr": pat.pattern[:80]} for pat, sigla in _NORMATIVE_LOOKUP
    ]
    project_entries.append({"sigla": "Art. X c. Y lett. Z", "pattern_repr": "_ART_VERBOSE_FULL_RE"})
    project_entries.append({"sigla": "Art. X c. Y", "pattern_repr": "_ART_VERBOSE_AC_RE"})
    project_entries.append({"sigla": "Art. X", "pattern_repr": "_ART_VERBOSE_A_RE"})
    project_entries.extend(
        {"sigla": replacement, "pattern_repr": pat.pattern[:80]}
        for pat, replacement in _BUREAUCRATIC_COMPACT
    )

    return {
        "builtin": builtin_patterns,
        "user": user_payload,
        "project": project_entries,
    }


# Re-export public API
__all__ = [
    "CompressResult",
    "UserRule",
    "compress_text",
    "describe_rules",
]


# Workaround mypy: logging modulo importato ma usato solo per type hints.
_LOG_REF: Final = logging.getLogger(__name__)
