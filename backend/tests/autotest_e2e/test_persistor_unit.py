"""Unit test isolato per setup_answer_persistor.

Test deterministico in-memory: niente backend live, niente network.
Verifica che simulando 10 risposte Q1-Q10 si popolino correttamente
user_profile + team_member nel DB temp.

Run: uv run python tests/autotest_e2e/test_persistor_unit.py
"""

from __future__ import annotations

import asyncio
import sqlite3
import sys
import tempfile
from pathlib import Path

# Schema DDL copiato da profile_store.py (single source of truth schema).
SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL DEFAULT 'local',
    slug TEXT NOT NULL,
    text TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN
        ('identity','preference','aversion','fact','stack')),
    confidence REAL NOT NULL DEFAULT 0.7,
    first_extracted_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    seen_count INTEGER NOT NULL DEFAULT 1,
    pinned INTEGER NOT NULL DEFAULT 0,
    source_turn_id TEXT NULL,
    UNIQUE (tenant_id, slug)
);
CREATE TABLE IF NOT EXISTS team_member (
    tenant_id TEXT PRIMARY KEY,
    is_team_mode INTEGER NOT NULL DEFAULT 0,
    team_name TEXT NULL,
    team_member_role TEXT NULL,
    member_full_name TEXT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


async def main() -> int:
    """Run test in TempDir + verifica DB persistito."""
    import aiosqlite

    from sco_compliance_os.services.learning.setup_answer_persistor import (
        persist_setup_answer,
    )

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test_user_profile.db"

        # Init schema
        async with aiosqlite.connect(str(db_path)) as c:
            await c.executescript(SCHEMA_DDL)
            await c.commit()

        # Mock answers Q1-Q10 (mirror autotest E2E MOCK_ANSWERS_Q1_Q10)
        mock_answers: list[tuple[str, int]] = [
            ("Mario Rossi", 1),
            ("team", 2),
            ("consulente", 3),
            ("cybersecurity", 4),
            ("sanita, pa, ict", 5),
            ("nis2, iso27001, gdpr, ai-act", 6),
            ("6-20", 7),
            ("italiano, inglese", 8),
            ("consulenziale-formale", 9),
            ("si", 10),
        ]

        print("=== Test: persist_setup_answer Q1..Q10 ===")
        print()
        passed = 0
        failed = 0
        for msg, step in mock_answers:
            result = await persist_setup_answer(
                user_message=msg,
                active_skill_step=step,
                db_path=db_path,
                conversation_id="test-conv",
                message_id=f"msg-{step}",
            )
            status = "OK" if result["persisted"] else "FAIL"
            if result["persisted"]:
                passed += 1
            else:
                failed += 1
            extra = ""
            if result["team_member_updated"]:
                extra = " [team_member updated]"
            print(
                f"  Step {step:>2} '{msg[:30]:<30}' -> {status} "
                f"slug={result['preference_slug']}{extra}"
            )

        print()
        print(f"Risultato: {passed} persisted, {failed} failed")

        # Verifica DB
        print("\n=== DB user_profile dump ===")
        conn = sqlite3.connect(str(db_path))
        rows = list(
            conn.execute(
                "SELECT slug, category, confidence, text FROM user_profile ORDER BY slug"
            ).fetchall()
        )
        print(f"Tot righe user_profile: {len(rows)}")
        for r in rows:
            print(f"  {r[0]} ({r[1]}, conf={r[2]:.2f}) -> {r[3]}")

        # Verifica team_member
        print("\n=== DB team_member dump ===")
        rows_tm = list(conn.execute("SELECT * FROM team_member").fetchall())
        print(f"Tot righe team_member: {len(rows_tm)}")
        for r in rows_tm:
            print(f"  {r}")

        conn.close()

        # Assert finali
        success = passed == len(mock_answers) and failed == 0 and len(rows) == len(mock_answers)
        if success:
            print("\n[OK] Test PASS - tutte le 10 risposte persistite correttamente.")
            return 0
        print(
            "\n[KO] Test FAIL - persistenza incompleta: "
            f"expected={len(mock_answers)}, got={len(rows)}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
