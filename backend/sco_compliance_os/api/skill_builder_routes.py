"""Router /api/skills/builder — costruzione skill personalizzate via wizard chat
oppure modalita' advanced (system prompt + frontmatter editor).

Goal v0.8.1 Antonio: "chiunque puo' costruire un sottoagente specializzato — o
con poche domande in chat (wizard semplice) o con la stessa potenza con cui
costruisce le proprie skill un esperto di Claude (advanced)".

Endpoint:
- POST   /api/skills/builder/wizard        crea skill da spec wizard semplice
- GET    /api/skills/builder/templates     5 template starter (auditor / consulente /
                                           analista / scrittore / ricercatore)
- POST   /api/skills/builder/from-template fork template + customizations
- PATCH  /api/skills/{slug}                edit skill esistente (solo scope=user)
- DELETE /api/skills/{slug}                rimuove skill (solo scope=user)

Pattern Conv. 47 single source of truth: SKILL.md su filesystem,
nessun cache DB. Discovery re-run via loader.discover_skills() ad ogni call.
Pattern Conv. 48: stato widget AskUserQuestion (wizard step) vive lato frontend,
qui solo input finale strutturato.
Pattern Conv. 41 tracciatura: log structured ogni operazione write/delete.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.skills.loader import get_skill

logger = get_logger(__name__)

router = APIRouter(prefix="/api/skills/builder", tags=["skills-builder"])

# Sub-router per PATCH/DELETE su /api/skills/{slug} (no prefix builder)
router_skills_crud = APIRouter(prefix="/api/skills", tags=["skills-builder"])


# ----- Vocabolari chiusi -----

AgentTypeLiteral = Literal["auditor", "consulente", "analista", "scrittore", "ricercatore", "altro"]
AmbitoLiteral = Literal[
    "cybersecurity",
    "compliance-sanitaria",
    "qualita",
    "sicurezza-lavoro",
    "multi-dominio",
]
ToneLiteral = Literal["consulenziale-formale", "neutro-tecnico", "divulgativo"]

# Vocabolario chiuso tools (Conv. 34 spot check vocabolario coerente skill loader)
ALLOWED_TOOLS: set[str] = {
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Glob",
    "Grep",
    "WebSearch",
    "WebFetch",
    "Task",
    "TodoWrite",
}

# Slug kebab-case strict (no spazi, no maiuscole, no caratteri speciali)
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")


# ----- Schemi Pydantic -----


class WizardSkillRequest(BaseModel):
    """Input wizard semplice (chat ask question 7 step)."""

    name: str = Field(..., min_length=2, max_length=64, description="Nome leggibile.")
    slug: str | None = Field(
        default=None,
        description="Slug kebab-case (auto-derivato da name se omesso).",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=400,
        description="Cosa fa l'agente (auto-trigger semantica per il loader).",
    )
    agent_type: AgentTypeLiteral = Field(default="altro")
    ambiti: list[AmbitoLiteral] = Field(
        default_factory=list,
        description="Ambiti applicabili (multi-select).",
    )
    tools_whitelist: list[str] = Field(
        default_factory=list,
        description="Tool ammessi dalla skill (sottoinsieme di ALLOWED_TOOLS).",
    )
    tone: ToneLiteral = Field(default="consulenziale-formale")
    example_question: str | None = Field(
        default=None,
        max_length=500,
        description="Esempio domanda che l'agente deve gestire bene.",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Override system prompt (advanced mode). Se None, generato da template.",
    )
    scope: Literal["user", "project"] = Field(default="user")

    @field_validator("tools_whitelist")
    @classmethod
    def _validate_tools(cls, v: list[str]) -> list[str]:
        invalid = [t for t in v if t not in ALLOWED_TOOLS]
        if invalid:
            raise ValueError(f"Tool non ammessi: {invalid}. Vocabolario: {sorted(ALLOWED_TOOLS)}")
        return v


class SkillTemplate(BaseModel):
    """Template starter per fork."""

    id: str
    title: str
    description: str
    agent_type: AgentTypeLiteral
    suggested_ambito: AmbitoLiteral
    suggested_tools: list[str]
    suggested_tone: ToneLiteral
    system_prompt_template: str


class FromTemplateRequest(BaseModel):
    """Fork template + customizations."""

    template_id: str = Field(..., description="ID del template (es. 'auditor-iso').")
    customizations: WizardSkillRequest = Field(
        ..., description="Spec sovrascrittiva su base template."
    )


class SkillPatchRequest(BaseModel):
    """Partial update skill esistente (solo scope=user)."""

    description: str | None = None
    system_prompt: str | None = None
    tools_whitelist: list[str] | None = None
    tone: ToneLiteral | None = None
    ambiti: list[AmbitoLiteral] | None = None

    @field_validator("tools_whitelist")
    @classmethod
    def _validate_tools(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        invalid = [t for t in v if t not in ALLOWED_TOOLS]
        if invalid:
            raise ValueError(f"Tool non ammessi: {invalid}. Vocabolario: {sorted(ALLOWED_TOOLS)}")
        return v


class SkillBuilderResponse(BaseModel):
    """Risposta a wizard / from-template / patch."""

    slug: str
    name: str
    scope: str
    skill_md_path: str
    created: bool = False
    updated: bool = False


# ----- Catalogo template starter -----

_TEMPLATES: list[SkillTemplate] = [
    SkillTemplate(
        id="auditor-iso",
        title="Auditor ISO",
        description=(
            "Lead auditor di parte terza ISO/IEC 27001, 9001, 14001 e affini. "
            "Conduce audit, formula NC/SM/OSS, prepara PVV e PDV con stile CSQA."
        ),
        agent_type="auditor",
        suggested_ambito="qualita",
        suggested_tools=["Read", "Grep", "Glob", "WebSearch"],
        suggested_tone="consulenziale-formale",
        system_prompt_template=(
            "Sei un Lead Auditor ISO senior. Conduci audit ISO 27001 / 9001 / 14001 "
            "secondo ISO 19011. Formuli rilievi NC/SM/OSS puntuali, con riferimento "
            "all'articolato della norma. Stile sobrio, lessico tecnico esatto, "
            "distingui sempre fatto da ipotesi. Per ogni risposta cita il punto "
            "della norma applicabile."
        ),
    ),
    SkillTemplate(
        id="consulente-compliance",
        title="Consulente compliance",
        description=(
            "Consulente normativo per gap analysis, piani di adeguamento, policy "
            "e procedure su NIS 2, GDPR, AI Act, ISO 42001."
        ),
        agent_type="consulente",
        suggested_ambito="cybersecurity",
        suggested_tools=["Read", "Write", "Grep", "WebSearch", "WebFetch"],
        suggested_tone="consulenziale-formale",
        system_prompt_template=(
            "Sei consulente compliance senior specializzato in NIS 2, GDPR, AI Act, "
            "ISO 42001. Conduci gap analysis, redigi policy e procedure, prepari "
            "piani di adeguamento. Stile diretto, semplice, chiaro, immediato "
            "(regola del consulente normativo 14/05). Riferimenti normativi puntuali con 'al punto', "
            "'al paragrafo', mai segno paragrafo. Distingui sempre fatto da ipotesi."
        ),
    ),
    SkillTemplate(
        id="analista-dati",
        title="Analista dati",
        description=(
            "Analista per estrazione, classificazione e sintesi di dataset, "
            "evidenze e tabelle. Produce sintesi gerarchiche."
        ),
        agent_type="analista",
        suggested_ambito="multi-dominio",
        suggested_tools=["Read", "Grep", "Glob", "Bash"],
        suggested_tone="neutro-tecnico",
        system_prompt_template=(
            "Sei un analista dati. Per ogni dataset estrai pattern, classifichi le "
            "evidenze, produci sintesi gerarchiche L0/L1/L2 in stile pattern Karpathy "
            "Memory Tree. Stile sobrio, niente filler, niente em-dash decorativo."
        ),
    ),
    SkillTemplate(
        id="scrittore-tecnico",
        title="Scrittore tecnico",
        description=(
            "Redattore di procedure, manuali, atti formali in italiano professionale "
            "stile CSQA. Applica humanizer + placeholder italiano professionale."
        ),
        agent_type="scrittore",
        suggested_ambito="qualita",
        suggested_tools=["Read", "Write", "Edit"],
        suggested_tone="consulenziale-formale",
        system_prompt_template=(
            "Sei redattore tecnico in italiano professionale. Applichi le regole "
            "tipografiche permanenti (umanizzatore, virgolette dritte, 'al punto', "
            "font uniforme, placeholder ____________________). Per documenti "
            "normativi attivi la variante /disaiizzatore-testi-tecnici-normativi. Niente em-dash "
            "decorativo, niente rule of three."
        ),
    ),
    SkillTemplate(
        id="ricercatore",
        title="Ricercatore",
        description=(
            "Ricercatore di fonti normative e tecniche. Verifica fonti vault + "
            "WebSearch istituzionali (EUR-Lex, Normattiva, GU, AGID, ACN). "
            "Convenzione 35 enforcement."
        ),
        agent_type="ricercatore",
        suggested_ambito="multi-dominio",
        suggested_tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
        suggested_tone="neutro-tecnico",
        system_prompt_template=(
            "Sei un ricercatore di fonti normative. Per ogni domanda sostanziale "
            "verifica prima il vault wiki interno, poi (se necessario) WebSearch su "
            "fonti istituzionali (EUR-Lex, Normattiva, GU, AGID, ACN, AGENAS, "
            "Garante). Mai a memoria. Cita sempre la fonte con link diretto."
        ),
    ),
]


# ----- Helper -----


def _slugify(name: str) -> str:
    """Deriva slug kebab-case da name (lowercase, dash, max 64 char)."""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:64]


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Slug '{slug}' non valido. Deve essere kebab-case "
                "(lowercase, dash, 3-64 char, no caratteri speciali)."
            ),
        )


def _user_skills_dir(settings: Settings) -> Path:
    """Directory scope=user dove vivono le skill create dall'utente."""
    return settings.data_dir / "skills"


def _build_skill_md(spec: WizardSkillRequest, resolved_slug: str) -> str:
    """Genera SKILL.md (frontmatter agentskills.io standard + body)."""
    frontmatter: dict[str, Any] = {
        "name": resolved_slug,
        "description": spec.description,
        "auto_trigger": None,
        "language": "it",
        "version": "1.0.0",
        "budget_tokens": 8000,
    }

    if spec.tools_whitelist:
        frontmatter["allowed_tools"] = spec.tools_whitelist
    if spec.ambiti:
        frontmatter["ambiti"] = spec.ambiti
    if spec.agent_type:
        frontmatter["agent_type"] = spec.agent_type
    if spec.tone:
        frontmatter["tone"] = spec.tone

    fm_yaml = yaml.safe_dump(
        frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False
    )

    # Body: usa system_prompt override se presente, altrimenti template dal tone
    if spec.system_prompt:
        body_main = spec.system_prompt
    else:
        body_main = _default_body_from_tone(spec)

    example_block = ""
    if spec.example_question:
        example_block = f"\n## Esempio domanda gestita bene\n\n> {spec.example_question}\n"

    return f"---\n{fm_yaml}---\n\n# {spec.name}\n\n{body_main}\n{example_block}"


def _default_body_from_tone(spec: WizardSkillRequest) -> str:
    """System prompt default derivato da tone + agent_type."""
    tone_map = {
        "consulenziale-formale": (
            "Tono consulenziale formale: lessico tecnico esatto, frasi corte, "
            "regole tipografiche permanenti (humanizer + virgolette dritte + "
            "'al punto' + font uniforme + placeholder italiano professionale). "
            "Distingui sempre fatto da ipotesi."
        ),
        "neutro-tecnico": (
            "Tono neutro tecnico: sobrio, sintetico, senza filler. "
            "Niente em-dash decorativo, niente rule of three, niente AI vocabulary."
        ),
        "divulgativo": (
            "Tono divulgativo: linguaggio semplice, chiaro, immediato "
            "(regola del consulente normativo 14/05). Comprensibile a un bambino senza essere "
            "infantile. Esempi concreti."
        ),
    }
    type_map = {
        "auditor": "Sei un auditor.",
        "consulente": "Sei un consulente.",
        "analista": "Sei un analista.",
        "scrittore": "Sei un redattore.",
        "ricercatore": "Sei un ricercatore.",
        "altro": "Sei un agente specializzato.",
    }
    return (
        f"{type_map[spec.agent_type]} {spec.description}\n\n## Come scrivi\n\n{tone_map[spec.tone]}"
    )


def _write_skill(spec: WizardSkillRequest, settings: Settings) -> SkillBuilderResponse:
    """Materializza skill su filesystem in scope=user (data_dir/skills/<slug>/SKILL.md).

    Project scope (vault_root/.claude/skills/) richiede vault attivo gia' registrato:
    in v0.8.1 supportiamo solo user scope, project resta per ondata successiva.
    """
    if spec.scope == "project":
        raise HTTPException(
            status_code=400,
            detail=(
                "Scope 'project' non ancora supportato in v0.8.1 (richiede vault "
                "attivo + sync). Usa scope='user'."
            ),
        )

    slug = spec.slug or _slugify(spec.name)
    _validate_slug(slug)

    # Check duplicate name (User + Project + Legacy)
    existing = get_skill(slug)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Skill '{slug}' esiste gia' in scope='{existing.scope}'. "
                "Scegli un nome diverso o usa PATCH per editare."
            ),
        )

    skills_dir = _user_skills_dir(settings)
    skills_dir.mkdir(parents=True, exist_ok=True)
    skill_dir = skills_dir / slug
    skill_dir.mkdir(parents=True, exist_ok=False)

    skill_md = skill_dir / "SKILL.md"
    md_content = _build_skill_md(spec, slug)
    skill_md.write_text(md_content, encoding="utf-8")

    logger.info(
        "skill_builder.wizard.created",
        slug=slug,
        scope="user",
        agent_type=spec.agent_type,
        tools_count=len(spec.tools_whitelist),
        path=str(skill_md),
    )

    return SkillBuilderResponse(
        slug=slug,
        name=spec.name,
        scope="user",
        skill_md_path=str(skill_md),
        created=True,
    )


# ----- Endpoint -----


@router.post("/wizard", response_model=SkillBuilderResponse)
async def create_via_wizard(
    payload: WizardSkillRequest,
    settings: Settings = Depends(get_settings),
) -> SkillBuilderResponse:
    """Crea skill da spec wizard semplice (chat ask question 7 step)."""
    return _write_skill(payload, settings)


@router.get("/templates", response_model=list[SkillTemplate])
async def list_templates() -> list[SkillTemplate]:
    """Lista template starter per fork (5 archetypi)."""
    return _TEMPLATES


@router.post("/from-template", response_model=SkillBuilderResponse)
async def create_from_template(
    payload: FromTemplateRequest,
    settings: Settings = Depends(get_settings),
) -> SkillBuilderResponse:
    """Fork template + customizations.

    Risolve template, applica system_prompt_template come default se l'utente
    non lo ha sovrascritto, poi delega a _write_skill.
    """
    template = next((t for t in _TEMPLATES if t.id == payload.template_id), None)
    if template is None:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{payload.template_id}' non trovato.",
        )

    spec = payload.customizations.model_copy()
    if not spec.system_prompt:
        spec.system_prompt = template.system_prompt_template
    if not spec.tools_whitelist:
        spec.tools_whitelist = list(template.suggested_tools)
    if not spec.ambiti:
        spec.ambiti = [template.suggested_ambito]

    return _write_skill(spec, settings)


@router_skills_crud.patch("/{slug}", response_model=SkillBuilderResponse)
async def patch_skill(
    slug: str,
    payload: SkillPatchRequest,
    settings: Settings = Depends(get_settings),
) -> SkillBuilderResponse:
    """Partial update skill esistente.

    Vincolo: solo scope=user (Legacy bundled + Project sono immutabili dal user).
    """
    _validate_slug(slug)
    existing = get_skill(slug)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Skill '{slug}' non trovata.")
    if existing.scope != "user":
        raise HTTPException(
            status_code=403,
            detail=(
                f"Skill '{slug}' scope='{existing.scope}' immutabile. "
                "Solo scope=user e' editabile dall'app."
            ),
        )

    # Re-read frontmatter + body per merge in-place
    raw = existing.skill_md_path.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
    if fm_match is None:
        raise HTTPException(status_code=500, detail="SKILL.md corrotto: no frontmatter.")
    frontmatter_dict: dict[str, Any] = yaml.safe_load(fm_match.group(1)) or {}
    body = fm_match.group(2)

    # Apply patch (only non-None fields)
    if payload.description is not None:
        frontmatter_dict["description"] = payload.description
    if payload.tools_whitelist is not None:
        frontmatter_dict["allowed_tools"] = payload.tools_whitelist
    if payload.tone is not None:
        frontmatter_dict["tone"] = payload.tone
    if payload.ambiti is not None:
        frontmatter_dict["ambiti"] = payload.ambiti
    if payload.system_prompt is not None:
        # Re-genera body con nuovo system prompt, preserva eventuale "Esempio domanda"
        example_match = re.search(
            r"\n## Esempio domanda gestita bene\n\n.*?(?=\n##|\Z)",
            body,
            re.DOTALL,
        )
        example_block = example_match.group(0) if example_match else ""
        body = f"# {frontmatter_dict.get('name', slug)}\n\n{payload.system_prompt}\n{example_block}"

    fm_yaml = yaml.safe_dump(
        frontmatter_dict,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    new_md = f"---\n{fm_yaml}---\n\n{body.lstrip()}"
    existing.skill_md_path.write_text(new_md, encoding="utf-8")

    logger.info("skill_builder.patch.updated", slug=slug, scope=existing.scope)
    return SkillBuilderResponse(
        slug=slug,
        name=str(frontmatter_dict.get("name", slug)),
        scope=existing.scope,
        skill_md_path=str(existing.skill_md_path),
        updated=True,
    )


@router_skills_crud.delete("/{slug}")
async def delete_skill(
    slug: str,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Rimuove skill (solo scope=user)."""
    _validate_slug(slug)
    existing = get_skill(slug)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Skill '{slug}' non trovata.")
    if existing.scope != "user":
        raise HTTPException(
            status_code=403,
            detail=(
                f"Skill '{slug}' scope='{existing.scope}' protetta. "
                "Solo scope=user puo' essere eliminato."
            ),
        )

    shutil.rmtree(existing.path)
    logger.info("skill_builder.delete.removed", slug=slug, path=str(existing.path))
    return {"slug": slug, "deleted": True}


# Helper exposed per debug/test: lista nomi template
def get_template_ids() -> list[str]:
    return [t.id for t in _TEMPLATES]
