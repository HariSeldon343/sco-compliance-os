"""Skill loader runtime + executor.

Discovery scope precedence: User > Project > Legacy bundled.
- User: ~/.sco-compliance-os/skills/*/SKILL.md (utente custom)
- Project: <vault_root>/.claude/skills/*/SKILL.md (vault-specifico)
- Legacy: bundled scaffold/templates/skills/*/SKILL.md (built-in)

Skill format: cartella per skill con SKILL.md (YAML frontmatter + Markdown body)
+ eventuali file di supporto (reference/, scripts/, ecc.). Compatibilità con
standard agentskills.io MIT (clean-room scratch, no copy GPL).

Pattern Conv. 47 single source of truth: skill vivono SOLO in filesystem,
mai cached in DB. Discovery rerun ad ogni execute_skill call (no cache).
"""

from sco_compliance_os.services.skills.auto_trigger import (
    EVENT_VAULT_REGISTERED,
    EVENT_VAULT_REGISTERED_POST_SETUP,
    handle_vault_registered,
    register_default_subscribers,
)
from sco_compliance_os.services.skills.loader import (
    SkillMeta,
    discover_skills,
    get_skill,
)
from sco_compliance_os.services.skills.runner import (
    SkillExecutionResult,
    execute_skill,
)

__all__ = [
    "EVENT_VAULT_REGISTERED",
    "EVENT_VAULT_REGISTERED_POST_SETUP",
    "SkillExecutionResult",
    "SkillMeta",
    "discover_skills",
    "execute_skill",
    "get_skill",
    "handle_vault_registered",
    "register_default_subscribers",
]
