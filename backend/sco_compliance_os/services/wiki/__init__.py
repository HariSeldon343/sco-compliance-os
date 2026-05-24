"""Servizi wiki vault SCO.

Espone funzioni per listare e leggere file markdown in:
    <vault_root>/wiki/sources/
    <vault_root>/wiki/entities/
    <vault_root>/wiki/concepts/
    <vault_root>/wiki/synthesis/
    <vault_root>/wiki/glossari/

Riusa il parser tipizzato esistente sco_compliance_os.services.vault.parser
(Conv. 47 enforcement: single source of truth dello schema frontmatter).
"""

from sco_compliance_os.services.wiki.parser import (
    WIKI_CATEGORIES,
    WikiCategoryError,
    WikiNotFoundError,
    get_wiki_file,
    list_wiki_files,
    parse_wiki_file,
    wiki_stats,
)

__all__ = [
    "WIKI_CATEGORIES",
    "WikiCategoryError",
    "WikiNotFoundError",
    "get_wiki_file",
    "list_wiki_files",
    "parse_wiki_file",
    "wiki_stats",
]
