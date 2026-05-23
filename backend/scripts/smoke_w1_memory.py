"""Smoke test E2E Wave 1 OpenHuman replica W1-MEMORY (subagent).

Pipeline:
    1. Setup DB di test temporaneo (no overwrite ~/.sco-compliance-os/).
    2. Apply migration 0002 + init memory_chunks schema.
    3. Inject 50 chunks fake (mix di pattern normativi italiani).
    4. fast_score_sync su tutti i chunks.
    5. record_access su 10 chunks (per popolare hotness).
    6. promote_to_l1 con buffer di chunks > 6000 token.
    7. TreeBuilder.build_source_tree("test") + verifica.
    8. get_top_hot_chunks + verifica ordering.

Esecuzione: cd backend && uv run python scripts/smoke_w1_memory.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend package in path (pyproject install handles this normally)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import structlog  # noqa: E402

from sco_compliance_os.core.migrations import apply_migrations  # noqa: E402
from sco_compliance_os.services.memory.chunker import Chunk  # noqa: E402
from sco_compliance_os.services.memory.store import (  # noqa: E402
    bulk_insert,
    count_chunks,
    init_schema,
    query_by_source,
)
from sco_compliance_os.services.memory.openhuman_scorer import (  # noqa: E402
    fast_score_sync,
    fast_score_batch,
)
from sco_compliance_os.services.memory.hotness import (  # noqa: E402
    get_top_hot_chunks,
    record_access,
)
from sco_compliance_os.services.memory.cascade import (  # noqa: E402
    promote_to_l1,
    should_seal_l0,
)
from sco_compliance_os.services.memory.tree_builder import TreeBuilder  # noqa: E402

logger = structlog.get_logger(__name__)


def _fake_chunk(idx: int, source: str = "test") -> Chunk:
    """Crea un chunk fake con contenuto markdown ricco di pattern normativi."""
    sample_contents = [
        (
            "## Sezione NIS 2 — Notifica incidente\n\n"
            "Ai sensi del D.Lgs. 138/2024 (recepimento Direttiva UE 2022/2555 NIS 2), "
            "il soggetto essenziale deve notificare l'incidente significativo entro "
            "24 ore ad ACN tramite CSIRT-Italia. Il riferimento normativo "
            "è all'articolo 25, comma 4, lettera a) del D.Lgs. citato.\n"
        ),
        (
            "## Standard ISO/IEC 27001:2022\n\n"
            "L'organizzazione deve implementare un SGSI conforme a ISO/IEC 27001:2022. "
            "I controlli Annex A si articolano in 93 controlli distinti. "
            "Riferimenti incrociati a ISO/IEC 27002:2022 per la guidance attuativa.\n"
        ),
        (
            "## GDPR + AI Act compliance\n\n"
            "Il trattamento dati personali deve rispettare GDPR Reg. UE 2016/679. "
            "Per sistemi IA ad alto rischio si applica AI Act Reg. UE 2024/1689. "
            "Il Garante Privacy vigila sui titolari del trattamento.\n"
        ),
        (
            "## Audit interno ISO 9001\n\n"
            "L'audit interno è programmato annualmente. Non conformità (NC) rilevate "
            "vengono classificate come maggiori (NC_E) o minori (NC_I) secondo "
            "la procedura interna. Eventuali Spunti di Miglioramento (SM) sono "
            "tracciati nel registro audit.\n"
        ),
        (
            "## Accreditamento sanitario Sicilia\n\n"
            "Riferimento al D.A. 741/2020 della Regione Sicilia per accreditamento "
            "istituzionale strutture sanitarie. AGENAS coordina a livello nazionale. "
            "Il Manuale MAO-SRO descrive i requisiti operativi.\n"
        ),
    ]
    content = sample_contents[idx % len(sample_contents)]
    # Aggiungi padding casuale per variare token_count
    content += f"\n\n_Chunk idx={idx}_\n" + ("Lorem ipsum dolor sit amet. " * (5 + idx % 20))
    return Chunk(
        id=str(uuid.uuid4()),
        source_path=f"test/fake_doc_{idx}.md",
        parent_chunk_id=None,
        heading_path=[f"# Doc {idx}", "## Sezione"],
        content_md=content,
        token_count=len(content) // 4,
        source_type="manual",
        source_id=source,
        provenance={"smoke_test": True, "idx": idx},
        created_at=datetime.now(timezone.utc).isoformat(),
    )


async def main() -> int:
    """Smoke test E2E. Ritorna 0 se PASS, !=0 se FAIL."""
    structlog.configure(
        processors=[
            structlog.dev.ConsoleRenderer(colors=False),
        ],
    )

    # 1. Setup DB temporaneo
    tmp_dir = Path(tempfile.mkdtemp(prefix="sco-smoke-w1-"))
    test_db = tmp_dir / "memory_tree.db"
    print(f"\n=== SMOKE W1-MEMORY ===\nDB temporaneo: {test_db}\n")

    # 2. Apply schema (memory_chunks) + migration 0002 (summaries, scores, ...)
    print("[1/8] Init schema memory_chunks...")
    await init_schema(db_path=test_db)
    print("      OK")

    print("[2/8] Apply migration 0002 (summaries, scores, entity_index, jobs)...")
    mig_result = await apply_migrations(db_path=test_db)
    applied = mig_result.get("applied", [])
    errors = mig_result.get("errors", [])
    if errors:
        print(f"      FAIL: errors={errors}")
        return 2
    print(f"      OK applied={applied}")

    # 3. Inject 50 chunks fake
    print("[3/8] Inject 50 chunks fake...")
    fake_chunks = [_fake_chunk(i, source="test") for i in range(50)]
    inserted = await bulk_insert(fake_chunks, db_path=test_db)
    total = await count_chunks(db_path=test_db)
    print(f"      OK inserted={inserted}, total_in_db={total}")
    if inserted != 50:
        print(f"      FAIL: expected 50, got {inserted}")
        return 3

    # 4. fast_score_sync su tutti
    print("[4/8] fast_score_sync on 50 chunks...")
    scores = fast_score_batch(fake_chunks)
    high_scores = [s for s in scores if s.fast_score > 0.4]
    print(f"      OK scored={len(scores)}, high_score(>0.4)={len(high_scores)}")
    if not scores or scores[0].fast_score == 0:
        print(f"      FAIL: top score is 0, expected non-zero norm matches")
        return 4
    print(f"      Top 3 scores: {[(s.chunk_id[:8], round(s.fast_score, 3), s.norm_matches, s.authority_matches) for s in scores[:3]]}")

    # 5. record_access su 10 chunks per popolare hotness
    print("[5/8] record_access on 10 chunks (popolare hotness)...")
    for c in fake_chunks[:10]:
        await record_access(c.id, db_path=test_db)
    top_hot = await get_top_hot_chunks(n=15, db_path=test_db)
    print(f"      OK top_hot_count={len(top_hot)}")
    if len(top_hot) < 10:
        print(f"      FAIL: expected >=10 hotness rows, got {len(top_hot)}")
        return 5
    print(f"      Top 3 hot: {[(s.chunk_id[:8], round(s.hotness, 3), s.access_count) for s in top_hot[:3]]}")

    # 6. promote_to_l1 con buffer chunks (forza seal)
    print("[6/8] promote_to_l1 (force seal con tutti i 50 chunks)...")
    # Forza il seal: con 50 chunks andiamo sicuramente sopra 6000 token
    should_seal, reason = should_seal_l0(fake_chunks)
    print(f"      should_seal={should_seal}, reason={reason}")
    if not should_seal:
        print(f"      FAIL: expected seal=True con 50 chunks, ma reason={reason}")
        return 6
    promo_result = await promote_to_l1(
        fake_chunks,
        source="test",
        topic="cybersicurezza",
        day=datetime.now(timezone.utc).date().isoformat(),
        db_path=test_db,
    )
    summary_id = promo_result.get("summary_id")
    print(f"      OK summary_id={summary_id}, token_count={promo_result.get('token_count')}, chunk_count={promo_result.get('chunk_count')}")
    if not summary_id:
        print(f"      FAIL: summary_id empty")
        return 6

    # 7. TreeBuilder.build_source_tree("test") + verifica
    print("[7/8] TreeBuilder.build_source_tree(test)...")
    builder = TreeBuilder(db_path=test_db)
    tree_result = await builder.build_source_tree("test")
    print(f"      OK nodes={len(tree_result.nodes)}, roots={len(tree_result.roots)}, "
          f"L0={tree_result.l0_count}, L1={tree_result.l1_count}, L2={tree_result.l2_count}, "
          f"compression={tree_result.compression_ratio}x")
    if tree_result.l0_count != 50:
        print(f"      FAIL: expected 50 L0, got {tree_result.l0_count}")
        return 7
    if tree_result.l1_count < 1:
        print(f"      FAIL: expected >=1 L1, got {tree_result.l1_count}")
        return 7

    # 7b. Verifica build_topic_tree
    print("[7b/8] TreeBuilder.build_topic_tree(cybersicurezza)...")
    topic_result = await builder.build_topic_tree("cybersicurezza")
    print(f"      OK L1={topic_result.l1_count}, L2={topic_result.l2_count}")
    if topic_result.l1_count < 1:
        print(f"      FAIL: expected >=1 L1 in topic tree")
        return 7

    # 7c. Verifica build_global_tree
    print("[7c/8] TreeBuilder.build_global_tree()...")
    global_result = await builder.build_global_tree()
    print(f"      OK nodes={len(global_result.nodes)}")

    # 8. list_summaries_by_filter (endpoint backing)
    print("[8/8] TreeBuilder.list_summaries_by_filter(level=1)...")
    l1_list = await builder.list_summaries_by_filter(level=1, limit=20)
    print(f"      OK L1 found via filter: {len(l1_list)}")
    if not l1_list:
        print(f"      FAIL: expected >=1 L1 via filter")
        return 8

    print("\n=== SMOKE W1-MEMORY: PASS ===")
    print(f"DB temporaneo restato in: {test_db}")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except Exception as e:
        print(f"\nFATAL: {e}")
        import traceback

        traceback.print_exc()
        exit_code = 99
    sys.exit(exit_code)
