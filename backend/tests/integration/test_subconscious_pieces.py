"""Test Subconscio v0.15.0: context_provider (radar scadenze) + action_executor.

Pattern conftest: fixture async `client` (esegue il lifespan -> schemi memory
inizializzati) + `temp_data_dir` (override data_dir + HOME). asyncio_mode=auto.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient

from sco_compliance_os.config import get_settings
from sco_compliance_os.services.subconscious.action_executor import (
    SAFE_ACTION_KINDS,
    execute_safe_action,
)
from sco_compliance_os.services.subconscious.decision_engine import Decision, DecisionOutcome

# ---------- action_executor: boundary enforcement (logica pura) ----------


@pytest.mark.asyncio
async def test_executor_refuses_when_disabled() -> None:
    """Subconscio spento -> nessuna esecuzione automatica."""
    outcome = DecisionOutcome(
        decision=Decision.ACT, rationale="x", proposed_action={"kind": "index"}, used_llm=True
    )
    result = await execute_safe_action(outcome, enabled=False)
    assert result.executed is False
    assert result.detail == "subconscious_disabled"


@pytest.mark.asyncio
async def test_executor_refuses_escalate() -> None:
    """ESCALATE resta SEMPRE una proposta, mai eseguita in auto."""
    outcome = DecisionOutcome(
        decision=Decision.ESCALATE,
        rationale="serve decisione umana",
        proposed_action={"kind": "index"},
        used_llm=True,
    )
    result = await execute_safe_action(outcome, enabled=True)
    assert result.executed is False
    assert result.detail == "not_act"


@pytest.mark.asyncio
async def test_executor_refuses_non_whitelisted_kind() -> None:
    """Un'azione fuori dalla whitelist NON viene eseguita (guard chiuso)."""
    outcome = DecisionOutcome(
        decision=Decision.ACT,
        rationale="azione pericolosa",
        proposed_action={"kind": "delete_client_files"},
        used_llm=True,
    )
    result = await execute_safe_action(outcome, enabled=True)
    assert result.executed is False
    assert result.detail == "not_whitelisted"
    assert "delete_client_files" not in SAFE_ACTION_KINDS


@pytest.mark.asyncio
async def test_executor_executes_whitelisted_index(client: AsyncClient) -> None:
    """Azione whitelisted 'index' eseguita (client fixture: schema memory pronto)."""
    outcome = DecisionOutcome(
        decision=Decision.ACT,
        rationale="reindex",
        proposed_action={"kind": "index"},
        used_llm=True,
    )
    result = await execute_safe_action(outcome, enabled=True)
    assert result.executed is True
    assert result.kind == "index"


# ---------- context_provider: radar scadenze ----------


@pytest.mark.asyncio
async def test_context_provider_picks_up_deadline(
    client: AsyncClient, temp_data_dir: Path, tmp_path: Path
) -> None:
    """Una scadenza entro 30 giorni in un vault registrato finisce in active_triggers."""
    # Vault fittizio con una entity scadenza imminente.
    vault = tmp_path / "vault-test"
    entities = vault / "wiki" / "entities"
    entities.mkdir(parents=True)
    due = (date.today() + timedelta(days=10)).isoformat()
    (entities / "scadenza-nis2.md").write_text(
        "---\n"
        "type: entity\n"
        "entity_type: scadenza\n"
        "title: Notifica incidente NIS2 (test)\n"
        f"data_riferimento: {due}\n"
        "data_tipo: assoluta\n"
        'parent_entity: "[[wiki/entities/d-lgs-138-2024]]"\n'
        "---\n\nCorpo scadenza di test.\n",
        encoding="utf-8",
    )

    # Registra il vault nel registry (lista di dict).
    settings = get_settings()
    settings.vault_registry_path.write_text(
        json.dumps([{"id": "v1", "path": str(vault)}]), encoding="utf-8"
    )

    from sco_compliance_os.services.subconscious.context_provider import build_context

    ctx = await build_context()

    deadlines = [t for t in ctx.active_triggers if t.get("event_type") == "deadline"]
    assert len(deadlines) >= 1, ctx.active_triggers
    assert any("NIS2" in str(t.get("title", "")) for t in deadlines)
    # Il contesto non e' vuoto -> il decision engine NON fa short-circuit a SKIP.
    assert ctx.is_empty() is False


@pytest.mark.asyncio
async def test_context_provider_ignores_far_deadline(
    client: AsyncClient, temp_data_dir: Path, tmp_path: Path
) -> None:
    """Una scadenza oltre la finestra (30 gg) NON entra nei trigger."""
    vault = tmp_path / "vault-far"
    entities = vault / "wiki" / "entities"
    entities.mkdir(parents=True)
    due = (date.today() + timedelta(days=120)).isoformat()
    (entities / "scadenza-lontana.md").write_text(
        "---\n"
        "type: entity\n"
        "entity_type: scadenza\n"
        "title: Scadenza lontana\n"
        f"data_riferimento: {due}\n"
        "data_tipo: assoluta\n"
        "---\n\nCorpo.\n",
        encoding="utf-8",
    )
    settings = get_settings()
    settings.vault_registry_path.write_text(
        json.dumps([{"id": "v1", "path": str(vault)}]), encoding="utf-8"
    )

    from sco_compliance_os.services.subconscious.context_provider import build_context

    ctx = await build_context()
    deadlines = [t for t in ctx.active_triggers if t.get("event_type") == "deadline"]
    assert deadlines == []
