import tempfile
from pathlib import Path

import pytest

from sco_compliance_os.services.chat import skill_proposer as sp
from sco_compliance_os.services.skills.loader import SkillMeta


@pytest.fixture(autouse=True)
def reset_pending_state():
    sp._pending_skill_options.clear()
    yield
    sp._pending_skill_options.clear()


def _make_skill(name: str, description: str) -> SkillMeta:
    temp_dir = Path(tempfile.gettempdir())

    return SkillMeta(
        name=name,
        description=description,
        scope="legacy",
        path=temp_dir / name,
        frontmatter={"name": name, "description": description},
    )


def test_propose_skills_returns_ordered_matches():
    skills = [
        _make_skill("report-licenze", "Genera report dettagliati sulle licenze"),
        _make_skill("analisi-rischio", "Analizza indicatori di rischio"),
        _make_skill("manuale-hr", "Supporto documentazione risorse umane"),
    ]
    message = "Mi serve un report licenze e un'analisi del rischio aggiornata"

    result = sp.propose_skills(message, skills, top_k=2)

    assert [skill.name for skill in result] == ["report-licenze", "analisi-rischio"]


def test_propose_skills_ignores_low_scores():
    skills = [
        _make_skill("backup", "Esegue backup completo dei dati sensibili"),
    ]
    # Solo un token in comune -> score inferiore a min_score default (2)
    message = "Serve un controllo rapido"

    assert sp.propose_skills(message, skills) == []


def test_propose_skills_empty_input_returns_empty():
    skills = [_make_skill("qualunque", "Descrizione generica")]

    assert sp.propose_skills("   ", skills) == []


@pytest.mark.asyncio
async def test_pending_set_get_clear():
    await sp.set_pending("conv-1", ["Skill A", "Skill B"])
    assert await sp.get_pending("conv-1") == ["Skill A", "Skill B"]

    await sp.clear_pending("conv-1")
    assert await sp.get_pending("conv-1") is None


@pytest.mark.asyncio
async def test_pending_entries_expire(monkeypatch):
    base_time = 1000.0

    monkeypatch.setattr(sp.time, "monotonic", lambda: base_time)
    await sp.set_pending("conv-2", ["Skill X"])

    monkeypatch.setattr(sp.time, "monotonic", lambda: base_time + sp._PENDING_TTL_SECONDS + 1)
    assert await sp.get_pending("conv-2") is None
