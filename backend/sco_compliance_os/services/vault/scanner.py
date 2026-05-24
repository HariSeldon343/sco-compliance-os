"""Scanner ricorsivo del vault SCO.

Pattern walk filesystem + skip cartelle dot-prefixed e archivi + index in
SQLite separato ~/.sco-compliance-os/vault_index.db.

Schema vault_documents (idempotente):
    path TEXT PK,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    title TEXT,
    entity_type TEXT,
    entity_subtype TEXT,
    ambito_canonico TEXT,
    domini_applicabili TEXT,  -- JSON array
    relationships TEXT,        -- JSON array
    applica_entity TEXT,       -- JSON array
    pertinenza_in_verifica TEXT, -- JSON array
    fornitore_di TEXT,         -- JSON array
    tags TEXT,                 -- JSON array
    last_reviewed TEXT,
    parent_entity TEXT,
    last_indexed TEXT NOT NULL

Indici per query veloci cross-cliente (vedi query.py).
Pattern Conv. 35 RESEARCH-BEFORE-ACT: scan reale filesystem, mai mock.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from .parser import VaultDocument, parse_vault_file

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path.home() / ".sco-compliance-os" / "vault_index.db"

# Cartelle da escludere dalla scansione.
_SKIP_DIRS = frozenset(
    {
        ".git",
        ".obsidian",
        ".claude",
        "node_modules",
        "_template-originale",
        "__pycache__",
        ".venv",
    }
)

# Pattern archivio (prefix-based).
_SKIP_PREFIXES = ("_archivio", "_archived", ".")

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vault_documents (
    path TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    title TEXT NOT NULL DEFAULT '',
    entity_type TEXT,
    entity_subtype TEXT,
    ambito_canonico TEXT,
    domini_applicabili TEXT NOT NULL DEFAULT '[]',
    relationships TEXT NOT NULL DEFAULT '[]',
    applica_entity TEXT NOT NULL DEFAULT '[]',
    pertinenza_in_verifica TEXT NOT NULL DEFAULT '[]',
    fornitore_di TEXT NOT NULL DEFAULT '[]',
    tags TEXT NOT NULL DEFAULT '[]',
    last_reviewed TEXT NOT NULL DEFAULT '',
    parent_entity TEXT NOT NULL DEFAULT '',
    last_indexed TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vault_type ON vault_documents(type);
CREATE INDEX IF NOT EXISTS idx_vault_entity_type ON vault_documents(entity_type);
CREATE INDEX IF NOT EXISTS idx_vault_ambito ON vault_documents(ambito_canonico);
CREATE INDEX IF NOT EXISTS idx_vault_status ON vault_documents(status);
"""


def default_db_path() -> Path:
    """Path canonico del vault index DB."""
    return _DEFAULT_DB_PATH


async def init_schema(db_path: Path | None = None) -> None:
    """Inizializza schema idempotente."""
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.executescript(_SCHEMA_SQL)
        await db.commit()
    logger.info("Vault index schema inizializzato: %s", path)


def _should_skip(dir_name: str) -> bool:
    """Decide se saltare una directory in walk."""
    if dir_name in _SKIP_DIRS:
        return True
    return any(dir_name.startswith(prefix) for prefix in _SKIP_PREFIXES)


def walk_vault(vault_root: Path) -> AsyncIterator[Path]:
    """Generatore async di .md file nel vault, skip archivi e dot-dirs."""

    async def _walk() -> AsyncIterator[Path]:
        if not vault_root.exists() or not vault_root.is_dir():
            logger.error("Vault root non esiste o non è directory: %s", vault_root)
            return

        stack: list[Path] = [vault_root]
        while stack:
            current = stack.pop()
            try:
                for entry in current.iterdir():
                    if entry.is_dir():
                        if _should_skip(entry.name):
                            continue
                        stack.append(entry)
                    elif entry.is_file() and entry.suffix.lower() == ".md":
                        yield entry
            except (PermissionError, OSError) as exc:
                logger.warning("Walk error in %s: %s", current, exc)
                continue

    return _walk()


def _doc_to_row(doc: VaultDocument) -> tuple:
    """Serializza VaultDocument in tupla per INSERT."""
    now = datetime.now(UTC).isoformat()
    return (
        doc.path,
        doc.type,
        doc.status,
        doc.title,
        doc.entity_type,
        doc.entity_subtype,
        doc.ambito_canonico,
        json.dumps(doc.domini_applicabili, ensure_ascii=False),
        json.dumps([asdict(r) for r in doc.relationships], ensure_ascii=False),
        json.dumps([asdict(a) for a in doc.applica_entity], ensure_ascii=False),
        json.dumps([asdict(p) for p in doc.pertinenza_in_verifica], ensure_ascii=False),
        json.dumps([asdict(f) for f in doc.fornitore_di], ensure_ascii=False),
        json.dumps(doc.tags, ensure_ascii=False),
        doc.last_reviewed,
        doc.parent_entity,
        now,
    )


async def index_document(doc: VaultDocument, db_path: Path | None = None) -> None:
    """Inserisce o sostituisce un VaultDocument nell'index."""
    path = db_path or default_db_path()
    async with aiosqlite.connect(path) as db:
        await db.execute(
            """INSERT OR REPLACE INTO vault_documents
            (path, type, status, title, entity_type, entity_subtype, ambito_canonico,
             domini_applicabili, relationships, applica_entity, pertinenza_in_verifica,
             fornitore_di, tags, last_reviewed, parent_entity, last_indexed)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            _doc_to_row(doc),
        )
        await db.commit()


async def scan_vault(
    vault_root: Path,
    db_path: Path | None = None,
) -> tuple[int, int]:
    """Scansiona ricorsivamente vault_root e popola l'index.

    Returns:
        (n_files_processati, n_files_indicizzati_con_successo)
    """
    await init_schema(db_path)
    walker = walk_vault(vault_root)
    processed = 0
    indexed = 0

    async for md_file in walker:
        processed += 1
        try:
            doc = parse_vault_file(md_file)
            if doc.type == "unknown" and not doc.entity_type:
                # Skip file senza segnali SCO (es. README sparsi).
                continue
            await index_document(doc, db_path=db_path)
            indexed += 1
        except Exception as exc:
            logger.error("Errore indexing %s: %s", md_file, exc)
            continue

    logger.info(
        "scan_vault complete: vault_root=%s processed=%d indexed=%d",
        vault_root,
        processed,
        indexed,
    )
    return processed, indexed


async def count_documents(db_path: Path | None = None) -> int:
    """Conta documenti indicizzati."""
    path = db_path or default_db_path()
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT COUNT(*) FROM vault_documents") as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0
