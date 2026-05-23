"""Debug E2E chat flow sco-compliance-os v0.1.0-alpha.7.

Subagent ALPHA verification script. NON modifica file di produzione.

Test:
1. Verifica state filesystem (active-license.json, DB)
2. Init schema DB se necessario
3. Crea fake active-license.json con license valida Antonio
4. Crea conversation via store.create_conversation()
5. Esegue agent_sdk_runner.stream() con un prompt breve
6. Stampa eventi SSE ricevuti

Esegui: cd backend && uv run python scripts/debug_chat_e2e.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Aggiungi backend root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sco_compliance_os.config import get_settings
from sco_compliance_os.core.store import get_store


async def main() -> None:
    print("=" * 60)
    print("DEBUG E2E CHAT FLOW — sco-compliance-os v0.1.0-alpha.7")
    print("=" * 60)

    settings = get_settings()
    print("\n[1] Settings caricati")
    print(f"    data_dir={settings.data_dir}")
    print(f"    backend_port={settings.backend_port}")
    print(f"    sco_saas_base_url={settings.sco_saas_base_url}")
    print(f"    model_default={settings.model_default}")

    # [2] Verifica active-license.json
    license_path = settings.data_dir / "active-license.json"
    print(f"\n[2] Active license check: {license_path}")
    if license_path.exists():
        data = json.loads(license_path.read_text(encoding="utf-8"))
        print(
            f"    EXISTS — email={data.get('email')} validated={data.get('validation_result', {}).get('is_valid')}"
        )
    else:
        print("    NON ESISTE — creo fake con license Antonio (per test)")
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        license_payload = {
            "email": "asamodeo@fortibyte.it",
            "license_key": "SCO-AF8EFB49-BEB2-43F6-ACCD-6E220FDCC930",
            "validation_result": {
                "status": "valid",
                "is_valid": True,
                "email": "asamodeo@fortibyte.it",
                "license_key_hash": "test-hash",
                "tenant_id": "f4917af5-9365-4c02-a8f6-8d1d19c3fc53",
                "expires_at": "2027-12-31T23:59:59.000Z",
                "plan": "enterprise",
                "validated_at": "2026-05-22T11:00:00+00:00",
                "cache_ttl_seconds": 86400,
                "error_message": "",
            },
            "activated_at": "2026-05-22T11:00:00+00:00",
        }
        license_path.write_text(json.dumps(license_payload, indent=2), encoding="utf-8")
        print("    CREATA fake active-license.json")

    # [3] Init schema DB
    store = get_store(settings.memory_tree_db_path)
    await store.init_schema()
    print(f"\n[3] DB schema init OK — path={settings.memory_tree_db_path}")

    # [4] Crea conversation
    conv = await store.create_conversation(title="DEBUG E2E ALPHA")
    print(f"\n[4] Conversation creata: id={conv.id}")

    # [5] Importa runner e itera stream
    print("\n[5] Import agent_sdk_runner + chiamata stream()...")
    try:
        from sco_compliance_os.core.agent_sdk_runner import build_runner

        runner = await build_runner(model_slug=settings.model_default)
        events_count = 0
        text_chunks: list[str] = []
        ev_kinds: dict[str, int] = {}

        print("\n    Prompt: 'Rispondi solo \"pong\" e basta.'")
        print("    Streaming events:")
        print("    " + "-" * 50)

        async for ev in runner.stream("Rispondi solo 'pong' e basta."):
            events_count += 1
            ev_kinds[ev.kind] = ev_kinds.get(ev.kind, 0) + 1
            if ev.kind == "text_delta":
                text = ev.data.get("text", "")
                text_chunks.append(text)
                print(f"    [{ev.seq}] text_delta: {text!r}")
            elif ev.kind == "tool_use":
                print(f"    [{ev.seq}] tool_use: {ev.data.get('tool_name')}")
            elif ev.kind == "error":
                print(f"    [{ev.seq}] ERROR: {ev.data}")
            elif ev.kind == "done":
                print(
                    f"    [{ev.seq}] DONE: stop_reason={ev.data.get('stop_reason')} usage={ev.data.get('usage')}"
                )
            elif ev.kind == "thinking":
                print(f"    [{ev.seq}] thinking: {ev.data.get('text', '')[:60]!r}...")

        print("    " + "-" * 50)
        full_text = "".join(text_chunks)
        print("\n[6] Risultato:")
        print(f"    Eventi totali: {events_count}")
        print(f"    Tipi eventi: {ev_kinds}")
        print(f"    Testo aggregato: {full_text!r}")
        print(f"    Testo lunghezza: {len(full_text)}")

        # Verdetto
        print("\n[7] VERDETTO:")
        if "pong" in full_text.lower():
            print("    PASS — agent SDK reale ha risposto correttamente")
        elif "stub" in full_text.lower() or "sto rispondendo" in full_text.lower():
            print("    FAIL — sta girando lo STUB OLD (testo hardcoded 'Ciao, sono lo stub...')")
            print("    --> Backend uvicorn ha caricato versione PRE-commit 6fd6c01")
        else:
            print(f"    UNEXPECTED — response inattesa: {full_text!r}")

    except Exception as exc:
        print(f"\n    EXCEPTION: {type(exc).__name__}: {exc}")
        import traceback

        traceback.print_exc()

    await store.close()
    print("\n[8] Cleanup OK\n")


if __name__ == "__main__":
    asyncio.run(main())
