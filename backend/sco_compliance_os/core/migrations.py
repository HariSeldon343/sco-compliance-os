"""Migration runner per Memory Tree DB (idempotente).

Pattern: legge i file .sql in `backend/migrations/` ordinati per nome,
li esegue tutti via aiosqlite.executescript(). Tutte le DDL devono essere
idempotenti (IF NOT EXISTS) per consentire rerun sicuri.

Conv. 44 lesson 3 PyInstaller: i file .sql vengono inclusi nel bundle via
data files config nello .spec. Path resolution prova:
    1. Path resolved relativo a __file__ (dev/test).
    2. Path resolved relativo a sys._MEIPASS (PyInstaller bundle).
    3. Fallback: skip migration con warning se directory non trovata.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import aiosqlite
import structlog

logger = structlog.get_logger(__name__)


def _resolve_migrations_dir() -> Path | None:
    """Trova la directory delle migrations cross-environment.

    Returns:
        Path alla directory, o None se non trovata.
    """
    # Path 1: dev locale, backend/migrations/ relativo a core/migrations.py
    here = Path(__file__).resolve()
    candidate1 = here.parent.parent.parent / "migrations"
    if candidate1.exists() and candidate1.is_dir():
        return candidate1

    # Path 2: PyInstaller bundle (sys._MEIPASS)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate2 = Path(meipass) / "migrations"
        if candidate2.exists() and candidate2.is_dir():
            return candidate2

    # Path 3: cwd fallback
    candidate3 = Path.cwd() / "migrations"
    if candidate3.exists() and candidate3.is_dir():
        return candidate3

    return None


async def apply_migrations(db_path: Optional[Path] = None) -> dict[str, int | list[str]]:
    """Applica tutte le migration .sql trovate in ordine alfabetico.

    Args:
        db_path: path al DB SQLite. Se None, usa il default del Memory Tree
            (~/.sco-compliance-os/memory_tree.db).

    Returns:
        dict con campi: applied (list di nomi file), skipped (list), errors (list).
    """
    from sco_compliance_os.services.memory.store import default_db_path

    target_db = db_path or default_db_path()
    target_db.parent.mkdir(parents=True, exist_ok=True)

    migrations_dir = _resolve_migrations_dir()
    if not migrations_dir:
        logger.warning(
            "migrations.dir_not_found",
            note="no migrations directory found, skipping",
        )
        return {"applied": [], "skipped": [], "errors": []}

    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        logger.info("migrations.no_files", dir=str(migrations_dir))
        return {"applied": [], "skipped": [], "errors": []}

    applied: list[str] = []
    errors: list[str] = []

    async with aiosqlite.connect(target_db) as db:
        for sql_file in sql_files:
            try:
                sql_text = sql_file.read_text(encoding="utf-8")
                await db.executescript(sql_text)
                await db.commit()
                applied.append(sql_file.name)
                logger.info(
                    "migrations.applied",
                    file=sql_file.name,
                    db=str(target_db),
                )
            except Exception as e:
                err_msg = f"{sql_file.name}: {e}"
                errors.append(err_msg)
                logger.error(
                    "migrations.error",
                    file=sql_file.name,
                    error=str(e),
                    exc_info=True,
                )

    logger.info(
        "migrations.complete",
        applied_count=len(applied),
        error_count=len(errors),
    )
    return {"applied": applied, "skipped": [], "errors": errors}
