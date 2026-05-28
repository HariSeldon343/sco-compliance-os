"""Skill discovery + frontmatter parsing.

Walk delle 3 scope (User > Project > Legacy bundled) con dedupe by skill name:
se la stessa skill esiste in scope diversi, vince la prima trovata (User > Project > Legacy).

Skill format minimo:
    skills/<skill_name>/SKILL.md
        ---
        name: os-setup
        description: "Profilazione utente al primo register vault..."
        scope: project          # auto-popolato a runtime, NON nel file
        auto_trigger: vault_registered
        language: it
        ---
        # SKILL body markdown...

Pattern Conv. 47: nessun cache in DB, discovery rerun on-demand.
Pattern Conv. 34: spot check obbligatorio post-multi-agent — applicato qui via
type hints stricte + frontmatter validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from sco_compliance_os.config import get_settings
from sco_compliance_os.core.logging_setup import get_logger

logger = get_logger(__name__)


# Per-turn injection cap del body skill markdown (anti-overflow context window).
SKILL_BODY_MAX_BYTES = 8 * 1024  # 8 KiB

# Regex frontmatter YAML standard agentskills.io: --- ... ---
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


SkillScope = Literal["user", "project", "legacy"]


@dataclass
class SkillMeta:
    """Metadata di una skill scoperta sul filesystem.

    Attributes:
        name: identificativo skill (slug kebab-case, deve essere unico).
        description: descrizione breve auto-trigger semantica.
        scope: scope di provenienza (user/project/legacy).
        path: path assoluto della cartella della skill.
        frontmatter: dict YAML parsed (include name + description + extra).
        body_md: markdown body lazy-loaded via load_body() per evitare
            IO eccessivo durante discovery batch.
    """

    name: str
    description: str
    scope: SkillScope
    path: Path
    frontmatter: dict[str, Any] = field(default_factory=dict)
    _body_md: str | None = field(default=None, init=False, repr=False)

    @property
    def skill_md_path(self) -> Path:
        """Path al file SKILL.md della skill."""
        return self.path / "SKILL.md"

    def load_body(self, max_bytes: int = SKILL_BODY_MAX_BYTES) -> str:
        """Carica il body markdown della skill (lazy + cap byte).

        Args:
            max_bytes: cap dimensione body. Se body supera, viene troncato con
                marker esplicito '... [SKILL body truncated]'.

        Returns:
            Markdown body string (eventualmente troncato).
        """
        if self._body_md is not None:
            return self._body_md
        try:
            raw = self.skill_md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning(
                "skill_loader.body_read_failed",
                path=str(self.skill_md_path),
                error=str(exc),
            )
            self._body_md = ""
            return ""

        match = _FRONTMATTER_RE.match(raw)
        body = match.group(2) if match else raw

        encoded = body.encode("utf-8")
        if len(encoded) > max_bytes:
            truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
            body = truncated + "\n\n... [SKILL body truncated]"
            logger.info(
                "skill_loader.body_truncated",
                skill_name=self.name,
                original_bytes=len(encoded),
                truncated_bytes=max_bytes,
            )
        self._body_md = body
        return body

    @property
    def auto_trigger(self) -> str | None:
        """Trigger evento se dichiarato in frontmatter (es. 'vault_registered')."""
        value = self.frontmatter.get("auto_trigger")
        return str(value) if value else None

    @property
    def language(self) -> str:
        """Lingua skill (default 'it' italian-first)."""
        return str(self.frontmatter.get("language", "it"))


def _parse_skill_md(skill_md_path: Path) -> tuple[dict[str, Any], str] | None:
    """Parsing frontmatter YAML + body di un SKILL.md.

    Returns:
        Tuple (frontmatter_dict, body_md) o None se parsing fallisce.
    """
    try:
        raw = skill_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning(
            "skill_loader.parse_read_failed",
            path=str(skill_md_path),
            error=str(exc),
        )
        return None

    match = _FRONTMATTER_RE.match(raw)
    if match is None:
        logger.warning(
            "skill_loader.parse_no_frontmatter",
            path=str(skill_md_path),
        )
        return None

    try:
        frontmatter_raw = match.group(1)
        body = match.group(2)
        frontmatter = yaml.safe_load(frontmatter_raw) or {}
        if not isinstance(frontmatter, dict):
            logger.warning(
                "skill_loader.parse_frontmatter_not_dict",
                path=str(skill_md_path),
                type=type(frontmatter).__name__,
            )
            return None
        return frontmatter, body
    except yaml.YAMLError as exc:
        logger.warning(
            "skill_loader.parse_yaml_error",
            path=str(skill_md_path),
            error=str(exc),
        )
        return None


def _scan_scope_dir(
    scope_dir: Path,
    scope: SkillScope,
) -> list[SkillMeta]:
    """Scansiona una directory scope e ritorna skill scoperte.

    Pattern di scan: una skill = una sottocartella con SKILL.md dentro.
    Sottocartelle senza SKILL.md sono ignorate (non considerate skill).
    """
    if not scope_dir.exists() or not scope_dir.is_dir():
        return []

    skills: list[SkillMeta] = []
    for child in scope_dir.iterdir():
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.exists():
            continue

        parsed = _parse_skill_md(skill_md)
        if parsed is None:
            continue
        frontmatter, _body = parsed

        name = str(frontmatter.get("name", "")).strip()
        description = str(frontmatter.get("description", "")).strip()
        if not name:
            logger.warning(
                "skill_loader.skip_missing_name",
                path=str(skill_md),
            )
            continue

        skills.append(
            SkillMeta(
                name=name,
                description=description,
                scope=scope,
                path=child,
                frontmatter=frontmatter,
            )
        )
    return skills


def _resolve_scope_dirs(vault_root: Path | None) -> list[tuple[Path, SkillScope]]:
    """Risolve i 3 scope dir in precedenza User > Project > Legacy.

    Args:
        vault_root: path vault attivo (per scope Project). Se None, Project scope
            viene saltato.

    Returns:
        Lista tuple (path, scope) in ordine di precedenza.
    """
    settings = get_settings()
    user_dir = settings.data_dir / "skills"

    # Legacy bundled: relative al modulo Python scaffold/templates/skills/
    # Path risolto via __file__ del modulo loader.
    legacy_dir = Path(__file__).resolve().parent.parent.parent / "scaffold" / "templates" / "skills"

    scopes: list[tuple[Path, SkillScope]] = [(user_dir, "user")]
    if vault_root is not None:
        project_dir = vault_root / ".claude" / "skills"
        scopes.append((project_dir, "project"))
    scopes.append((legacy_dir, "legacy"))
    return scopes


def discover_skills(vault_root: Path | None = None) -> list[SkillMeta]:
    """Discovery skill attraverso i 3 scope con dedupe by name.

    Args:
        vault_root: path vault attivo per scope Project. Se None, scope Project
            viene saltato e si usano solo User + Legacy.

    Returns:
        Lista SkillMeta dedup-ata (name unico), in ordine di precedenza
        scope (User vince su Project vince su Legacy).
    """
    scopes = _resolve_scope_dirs(vault_root)
    seen_names: set[str] = set()
    result: list[SkillMeta] = []
    for scope_dir, scope in scopes:
        scoped = _scan_scope_dir(scope_dir, scope)
        for skill in scoped:
            if skill.name in seen_names:
                logger.debug(
                    "skill_loader.dedupe_skip",
                    skill_name=skill.name,
                    skipped_scope=skill.scope,
                )
                continue
            seen_names.add(skill.name)
            result.append(skill)
    logger.info(
        "skill_loader.discover.completed",
        skills_count=len(result),
        vault_root=str(vault_root) if vault_root else None,
    )
    return result


def get_skill(name: str, vault_root: Path | None = None) -> SkillMeta | None:
    """Ritorna la SkillMeta con il dato name secondo precedenza scope.

    Args:
        name: nome skill (slug kebab-case).
        vault_root: path vault attivo per scope Project.

    Returns:
        SkillMeta se trovata, None altrimenti.
    """
    for skill in discover_skills(vault_root):
        if skill.name == name:
            return skill
    return None
