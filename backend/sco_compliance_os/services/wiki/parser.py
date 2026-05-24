"""Parser/lister wiki vault Karpathy.

Layer sottile sopra sco_compliance_os.services.vault.parser:
- list_wiki_files(): enumera categoria, ritorna metadata sintetica per UI lista
- get_wiki_file(): file singolo con body completo
- parse_wiki_file(): wrapper di alto livello, ritorna dict shape stabile
- wiki_stats(): conteggi per categoria

Conv. 47 enforcement: lo schema frontmatter NON è duplicato qui. Riusa
VaultDocument come single source of truth (services/vault/parser.py).

Conv. 35 enforcement: validazione contro vault reale Karpathy (le 5 cartelle
canoniche, slug from filename). Mai mockare lo schema.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sco_compliance_os.services.vault.parser import (
    VaultDocument,
    parse_vault_file,
)

logger = logging.getLogger(__name__)

# Cartelle wiki Karpathy canoniche (5 categorie + 1 metaflag glossari).
WIKI_CATEGORIES: frozenset[str] = frozenset(
    {"sources", "entities", "concepts", "synthesis", "glossari"}
)

# Cap default body excerpt per response lista (UI non scarica body interi).
_DEFAULT_BODY_EXCERPT_CHARS = 280

# Skip pattern: indici e _archived prefix-based.
_SKIP_FILENAMES = frozenset({"_index.md", "_index"})


class WikiCategoryError(ValueError):
    """Categoria wiki non valida (fuori vocabolario chiuso)."""


class WikiNotFoundError(FileNotFoundError):
    """File wiki non trovato nel vault."""


def _excerpt(body_md: str, max_chars: int = _DEFAULT_BODY_EXCERPT_CHARS) -> str:
    """Estrae primo paragrafo del body markdown, troncato a max_chars."""
    if not body_md:
        return ""
    # Rimuovi heading markdown e blocchi codice/quote, prendi primo paragrafo non vuoto.
    lines = body_md.splitlines()
    in_code = False
    paragraph_lines: list[str] = []
    for raw in lines:
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not line:
            if paragraph_lines:
                break
            continue
        if line.startswith("#") or line.startswith(">"):
            if paragraph_lines:
                break
            continue
        paragraph_lines.append(line)
    text = " ".join(paragraph_lines).strip()
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "..."
    return text


def _wiki_dir(vault_root: Path, category: str) -> Path:
    """Risolve path categoria wiki, valida vocabolario chiuso."""
    if category not in WIKI_CATEGORIES:
        raise WikiCategoryError(
            f"Categoria '{category}' fuori vocabolario chiuso "
            f"({sorted(WIKI_CATEGORIES)})"
        )
    return vault_root / "wiki" / category


def _slug_from_path(path: Path) -> str:
    """Estrae slug da filename senza estensione."""
    return path.stem


def _last_modified_iso(path: Path) -> str:
    """Mtime del file come ISO 8601 UTC."""
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=UTC).isoformat()
    except OSError as exc:
        logger.warning("stat failed for %s: %s", path, exc)
        return ""


def _coerce_str_list(values: object) -> list[str]:
    """Coerce qualsiasi sequenza in lista[str], skip None.

    Necessario perche' tag come `tags: [iso, 14001]` vengono parsati da PyYAML
    come [str, int, ...]. Pydantic response model accetta solo str: coerce qui.
    """
    if not isinstance(values, list):
        return []
    return [str(v) for v in values if v is not None]


def _doc_to_summary_dict(doc: VaultDocument, slug: str, last_modified: str) -> dict[str, Any]:
    """Serializza VaultDocument come dict per response lista (NO body interno).

    Mantiene i campi più usati dall'UI:
    slug, title, status, entity_type, entity_subtype, ambito_canonico,
    domini_applicabili, tags, last_reviewed, last_modified, body_excerpt.
    """
    return {
        "slug": slug,
        "title": doc.title or slug,
        "status": doc.status,
        "type": doc.type,
        "entity_type": doc.entity_type,
        "entity_subtype": doc.entity_subtype,
        "ambito_canonico": doc.ambito_canonico,
        "domini_applicabili": _coerce_str_list(doc.domini_applicabili),
        "parent_entity": doc.parent_entity,
        "tags": _coerce_str_list(doc.tags),
        "last_reviewed": doc.last_reviewed,
        "last_modified": last_modified,
        "body_excerpt": _excerpt(doc.body_md),
        "relationships_count": len(doc.relationships),
        "applica_entity_count": len(doc.applica_entity),
    }


def _doc_to_full_dict(doc: VaultDocument, slug: str, last_modified: str) -> dict[str, Any]:
    """Serializza VaultDocument completo per response singolo file (con body)."""
    return {
        "slug": slug,
        "path": doc.path,
        "type": doc.type,
        "title": doc.title or slug,
        "status": doc.status,
        "entity_type": doc.entity_type,
        "entity_subtype": doc.entity_subtype,
        "ambito_canonico": doc.ambito_canonico,
        "domini_applicabili": _coerce_str_list(doc.domini_applicabili),
        "parent_entity": doc.parent_entity,
        "tags": _coerce_str_list(doc.tags),
        "last_reviewed": doc.last_reviewed,
        "last_modified": last_modified,
        "frontmatter": doc.raw_frontmatter,
        "body_md": doc.body_md,
        "relationships": [asdict(r) for r in doc.relationships],
        "applica_entity": [asdict(a) for a in doc.applica_entity],
        "pertinenza_in_verifica": [asdict(p) for p in doc.pertinenza_in_verifica],
        "fornitore_di": [asdict(f) for f in doc.fornitore_di],
    }


def parse_wiki_file(path: Path) -> dict[str, Any]:
    """Parse file wiki e ritorna dict full (body incluso).

    Pattern Conv. 47 enforcement: delega a parse_vault_file esistente,
    NON duplica schema frontmatter.
    """
    doc = parse_vault_file(path)
    return _doc_to_full_dict(doc, _slug_from_path(path), _last_modified_iso(path))


def list_wiki_files(
    vault_root: Path,
    category: str,
    *,
    entity_type: str | None = None,
    ambito_canonico: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Lista file in <vault_root>/wiki/<category>/.

    Filtri opzionali query-string (frontmatter-based).
    Skip file _index.md per default (sono indici navigazione, non contenuti).

    Returns:
        dict: {
            category: str,
            total: int,
            limit: int,
            offset: int,
            items: list[dict] (summary, senza body completo)
        }
    """
    wiki_dir = _wiki_dir(vault_root, category)
    if not wiki_dir.exists() or not wiki_dir.is_dir():
        logger.info("wiki dir non esiste: %s (categoria vuota)", wiki_dir)
        return {
            "category": category,
            "total": 0,
            "limit": limit,
            "offset": offset,
            "items": [],
        }

    # Enumera .md non _index.
    md_files = sorted(
        (
            p
            for p in wiki_dir.glob("*.md")
            if p.is_file() and p.name not in _SKIP_FILENAMES
        ),
        key=lambda p: p.name.lower(),
    )

    results: list[dict[str, Any]] = []
    for md in md_files:
        try:
            doc = parse_vault_file(md)
        except Exception as exc:
            logger.warning("parse failed %s: %s", md, exc)
            continue

        # Filtri frontmatter (sempre vs none).
        if entity_type and doc.entity_type != entity_type:
            continue
        if ambito_canonico and doc.ambito_canonico != ambito_canonico:
            continue
        if status and doc.status != status:
            continue

        results.append(
            _doc_to_summary_dict(doc, _slug_from_path(md), _last_modified_iso(md))
        )

    total = len(results)
    paged = results[offset : offset + limit] if limit > 0 else results

    return {
        "category": category,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": paged,
    }


_SLUG_SAFE_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def get_wiki_file(vault_root: Path, category: str, slug: str) -> dict[str, Any]:
    """Ritorna singolo file wiki con body completo.

    Raises:
        WikiCategoryError: categoria non valida.
        WikiNotFoundError: file non trovato.
        ValueError: slug con caratteri non sicuri (path traversal protection).
    """
    if not _SLUG_SAFE_RE.match(slug):
        raise ValueError(
            f"Slug '{slug}' contiene caratteri non ammessi (solo a-z, 0-9, ., _, -)"
        )

    wiki_dir = _wiki_dir(vault_root, category)
    md_path = wiki_dir / f"{slug}.md"

    # Resolve + verifica containment per path traversal.
    try:
        resolved = md_path.resolve()
        resolved_dir = wiki_dir.resolve()
        # Verify resolved path è sotto wiki_dir.
        resolved.relative_to(resolved_dir)
    except (ValueError, OSError) as exc:
        raise WikiNotFoundError(
            f"Path resolution fallita per {category}/{slug}: {exc}"
        ) from exc

    if not resolved.exists() or not resolved.is_file():
        raise WikiNotFoundError(f"Wiki file {category}/{slug}.md non trovato")

    return parse_wiki_file(resolved)


def wiki_stats(vault_root: Path) -> dict[str, Any]:
    """Conteggio file per categoria wiki.

    Returns:
        dict: {
            vault_path: str,
            wiki_dir_exists: bool,
            counts: { sources: int, entities: int, concepts: int, synthesis: int, glossari: int },
            total: int
        }
    """
    wiki_root = vault_root / "wiki"
    counts: dict[str, int] = {}
    for category in sorted(WIKI_CATEGORIES):
        cat_dir = wiki_root / category
        if not cat_dir.exists() or not cat_dir.is_dir():
            counts[category] = 0
            continue
        counts[category] = sum(
            1
            for p in cat_dir.glob("*.md")
            if p.is_file() and p.name not in _SKIP_FILENAMES
        )
    return {
        "vault_path": str(vault_root),
        "wiki_dir_exists": wiki_root.is_dir(),
        "counts": counts,
        "total": sum(counts.values()),
    }
