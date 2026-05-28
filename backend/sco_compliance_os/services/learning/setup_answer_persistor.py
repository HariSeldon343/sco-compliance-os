"""Persistence dei risposte ai widget os-setup come Preferences strutturate.

Pattern Conv. 41 tracciatura + Conv. 47 single source of truth backend:
le risposte alle 10 domande del widget os-setup (Q1-Q10) vivono come Preference
strutturate nel DB profile (`user_profile.db`), accessibili via
`GET /api/profile` e iniettate nel system prompt LLM via `chat_routes.py`.

Pattern Conv. 35 RESEARCH-BEFORE-ACT: usiamo mapping deterministico
(answer_value -> slug + text + category + confidence) invece di affidarci
ai 20 regex italian-first di `user_profile.py` che NON matchano single-token
answers come "Mario Rossi" o "consulente" da soli.

Gap risolto (Workstream 1 OMEGA, 25/05/2026):
    Prima:  Q1 "Mario Rossi" -> extract_preferences() NO match (manca "mi chiamo")
            -> user_profile.db resta vuoto
    Dopo:   detect_setup_answer_for_question("1/10", "Mario Rossi") -> Preference
            identity / name-mario-rossi confidence 0.95 -> upsert_preference()
            -> user_profile.db popolato strutturato

Pattern di uso:
    1. `chat_routes.py` rileva conversation con `active_skill == "os-setup"`
       e `active_skill_step` >= 1.
    2. Quando l'utente risponde con un user message, il finally block del SSE
       stream chiama `persist_setup_answer(conv_id, step, user_message)`.
    3. Il modulo classifica la risposta secondo lo step (1/10 -> identity,
       2/10 -> team_member, ecc.) e fa upsert nel profile + team_member store.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.learning.profile_store import (
    upsert_preference,
    upsert_team_member,
)
from sco_compliance_os.services.learning.user_profile import (
    Preference,
    ProfileCategory,
)

logger = get_logger(__name__)


# ============================================================================
# MAPPING DETERMINISTICO step os-setup -> (slug_prefix, category, confidence)
# ============================================================================

# Step os-setup canonici (1/10 ... 10/10).
SETUP_STEPS = (
    "1/10",  # Chi sei -> identity name
    "2/10",  # Solo o team -> team_member
    "3/10",  # Ruolo -> identity role
    "4/10",  # Ambito -> stack work-domain
    "5/10",  # Settori -> stack sectors (multi-select)
    "6/10",  # Framework -> stack frameworks (multi-select)
    "7/10",  # Portafoglio -> fact portfolio-size
    "8/10",  # Lingue -> fact languages (multi-select)
    "9/10",  # Stile -> preference style
    "10/10",  # Mascot/voce -> preference ui-extras
)


# Slug strutturati + category + confidence per ogni step.
# Pattern Karpathy "schema is the product": il mapping vive in CLAUDE.md vault
# come single source of truth, qui replica fedele.
STEP_TO_PROFILE: dict[str, tuple[str, ProfileCategory, float]] = {
    "1/10": ("name", ProfileCategory.identity, 0.95),
    "2/10": ("modalita-lavoro", ProfileCategory.identity, 0.90),
    "3/10": ("role", ProfileCategory.identity, 0.90),
    "4/10": ("ambito-principale", ProfileCategory.stack, 0.90),
    "5/10": ("settori-clienti", ProfileCategory.stack, 0.85),
    "6/10": ("framework-normativi", ProfileCategory.stack, 0.90),
    "7/10": ("portafoglio-clienti", ProfileCategory.fact, 0.85),
    "8/10": ("lingue-lavoro", ProfileCategory.fact, 0.85),
    "9/10": ("stile-documenti", ProfileCategory.preference, 0.90),
    "10/10": ("mascot-voce", ProfileCategory.preference, 0.80),
}


# Vocabolari chiusi per valori canonici (option `value` widget SKILL.md).
RUOLO_LABELS = {
    "consulente": "Consulente libero professionista o consulenza esterna",
    "auditor": "Lead Auditor (OdC, ente accreditato)",
    "direzione": "Direzione / Management",
    "dpo": "Data Protection Officer",
    "rspp": "RSPP / ASPP",
    "altro": "Ruolo altro non standardizzato",
}

AMBITO_LABELS = {
    "cybersecurity": "Cybersecurity (NIS 2, ISO 27001, Legge 90, ACN)",
    "compliance-sanitaria": "Compliance sanitaria (accreditamento, ISO 9001 sanita, MDR)",
    "qualita": "Qualita SGQ (ISO 9001 manifatturiero o servizi)",
    "sicurezza-lavoro": "Sicurezza lavoro (D.Lgs. 81/2008)",
    "privacy": "Privacy / GDPR (Garante, DPIA, AI Act)",
    "multi-ambito": "Multi-ambito cross-dominio integrato",
}

STILE_LABELS = {
    "consulenziale-formale": "Tono consulenziale formale (italiano professionale, virgolette dritte)",
    "neutro-tecnico": "Neutro tecnico (terminologia ISO/normativa standard)",
    "divulgativo": "Divulgativo (accessibile a non addetti ai lavori)",
}

MASCOT_LABELS = {
    "si": "Mascot animato + voce attivi",
    "solo-voce": "Solo voce sintetica, niente mascot",
    "solo-mascot": "Solo mascot animato, niente voce",
    "no": "Interfaccia chat standard senza animazioni o audio",
}


# ============================================================================
# SLUG NORMALIZZATION
# ============================================================================

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_DASH_DEDUP_RE = re.compile(r"-+")


def _slugify(text: str, max_len: int = 80) -> str:
    """Normalizza in kebab-case ASCII (clone di user_profile._slugify)."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lower = ascii_text.lower().strip()
    dashed = _NON_ALNUM_RE.sub("-", lower)
    dedup = _DASH_DEDUP_RE.sub("-", dashed).strip("-")
    if len(dedup) > max_len:
        dedup = dedup[:max_len].rstrip("-")
    return dedup


def _parse_step_from_skill_step(active_skill_step: int | None) -> str | None:
    """Converti active_skill_step (int) in step string canonico '1/10'..'10/10'.

    Logica: active_skill_step e' incrementato in chat_routes.py finally block.
    Step 0 = appena settato all'auto-trigger (Q1 emessa). Quando l'utente
    risponde a Q1, active_skill_step = 1 (incrementato dal finally block PRIMA
    di salvare assistant_text, ma DOPO append messaggio user). Quindi la
    risposta corrente all'utente N-esima corrisponde a step = N.

    Mapping conservativo:
        step 1 -> "1/10" (risposta a Q1)
        step 2 -> "2/10" (risposta a Q2)
        ...
        step 10 -> "10/10"
    """
    if active_skill_step is None:
        return None
    if 1 <= active_skill_step <= 10:
        return f"{active_skill_step}/10"
    return None


# ============================================================================
# DETECT + BUILD PREFERENCE
# ============================================================================


def _build_preference(
    step_key: str,
    user_answer: str,
    *,
    turn_id: str | None = None,
) -> Preference | None:
    """Costruisce una Preference strutturata per uno step os-setup.

    Args:
        step_key: chiave step '1/10' .. '10/10'.
        user_answer: testo risposta utente (free text o option `value`).
        turn_id: opzionale audit trail.

    Returns:
        Preference pronta per upsert, None se step non riconosciuto o answer vuoto.
    """
    if step_key not in STEP_TO_PROFILE:
        return None
    cleaned = (user_answer or "").strip()
    if not cleaned:
        return None

    slug_prefix, category, confidence = STEP_TO_PROFILE[step_key]
    slug_body = _slugify(cleaned, max_len=60)
    slug = f"{slug_prefix}-{slug_body}" if slug_body else slug_prefix
    slug = slug.strip("-")[:80]
    if not slug:
        return None

    # Costruisci testo human-readable arricchito con label.
    text = _build_text_with_label(step_key, cleaned)

    return Preference(
        text=text,
        slug=slug,
        category=category,
        confidence=confidence,
        extracted_at=datetime.now(UTC),
        source_turn_id=turn_id,
    )


def _build_text_with_label(step_key: str, value: str) -> str:
    """Genera testo human-readable arricchito per la preferenza."""
    value_lower = value.lower().strip()
    if step_key == "1/10":
        return f"Si chiama {value.strip()}"
    if step_key == "2/10":
        if "team" in value_lower:
            return "Lavora in team"
        return "Singolo professionista, vault personale"
    if step_key == "3/10":
        label = RUOLO_LABELS.get(value_lower, value.strip())
        return f"Ruolo principale: {label}"
    if step_key == "4/10":
        label = AMBITO_LABELS.get(value_lower, value.strip())
        return f"Ambito di lavoro: {label}"
    if step_key == "5/10":
        # Multi-select: split su virgola.
        items = [s.strip() for s in value.split(",") if s.strip()]
        return f"Settori clienti prevalenti: {', '.join(items)}"
    if step_key == "6/10":
        items = [s.strip() for s in value.split(",") if s.strip()]
        return f"Framework normativi usati: {', '.join(items)}"
    if step_key == "7/10":
        return f"Portafoglio clienti attivi: {value.strip()}"
    if step_key == "8/10":
        items = [s.strip() for s in value.split(",") if s.strip()]
        return f"Lingue di lavoro: {', '.join(items)}"
    if step_key == "9/10":
        label = STILE_LABELS.get(value_lower, value.strip())
        return f"Stile preferito documenti: {label}"
    if step_key == "10/10":
        label = MASCOT_LABELS.get(value_lower, value.strip())
        return f"Preferenza UI: {label}"
    return value.strip()


# ============================================================================
# PUBLIC API
# ============================================================================


async def persist_setup_answer(
    *,
    user_message: str,
    active_skill_step: int | None,
    conversation_id: str | None = None,
    message_id: str | None = None,
    tenant_id: str = "local",
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Persiste UNA risposta os-setup come Preference + eventuale team_member.

    Da chiamare ESCLUSIVAMENTE quando la conversation ha
    `active_skill == "os-setup"` (Conv. 47 single source of truth backend).

    Args:
        user_message: testo della risposta utente (free text o option value).
        active_skill_step: stato active_skill_step della conversation,
            DOPO l'append del messaggio user (incrementato in chat_routes
            finally block).
        conversation_id: ID conv per audit + turn_id.
        message_id: ID messaggio user.
        tenant_id: tenant ID (default 'local').
        db_path: override DB path (testing).

    Returns:
        dict con:
            - persisted: bool, True se almeno 1 elemento e' stato persistito.
            - step_key: "N/10" o None se step non valido.
            - preference_slug: slug della Preference persistita.
            - team_member_updated: bool, True se step 2/10 ha popolato team_member.
            - reason: stringa motivo skip se persisted=False.
    """
    out: dict[str, Any] = {
        "persisted": False,
        "step_key": None,
        "preference_slug": None,
        "team_member_updated": False,
        "reason": "",
    }

    if not user_message or not user_message.strip():
        out["reason"] = "empty_user_message"
        return out

    step_key = _parse_step_from_skill_step(active_skill_step)
    if step_key is None:
        out["reason"] = f"step_out_of_range:{active_skill_step}"
        return out
    out["step_key"] = step_key

    turn_id = f"{conversation_id}__{message_id}" if conversation_id and message_id else None

    # Costruisci Preference
    pref = _build_preference(step_key, user_message, turn_id=turn_id)
    if pref is None:
        out["reason"] = "preference_build_failed"
        return out

    # Persisti Preference
    try:
        await upsert_preference(pref, tenant_id=tenant_id, db_path=db_path)
        out["persisted"] = True
        out["preference_slug"] = pref.slug
        logger.info(
            "setup_answer_persistor.preference_upserted",
            step=step_key,
            slug=pref.slug,
            category=pref.category.value,
            turn_id=turn_id,
        )
    except Exception as exc:
        logger.exception(
            "setup_answer_persistor.upsert_preference_failed",
            step=step_key,
            slug=pref.slug,
            error=str(exc),
        )
        out["reason"] = f"upsert_preference_failed:{type(exc).__name__}"
        return out

    # Step 2/10: side-effect persisti team_member dedicato (Conv. 47 SSOT
    # per is_team_mode + team_name + team_member_role).
    if step_key == "2/10":
        try:
            answer_lower = user_message.strip().lower()
            is_team_mode = "team" in answer_lower and "solo" not in answer_lower
            await upsert_team_member(
                tenant_id=tenant_id,
                is_team_mode=is_team_mode,
                team_name=None,  # popolato dalla sotto-domanda se ci sara'
                team_member_role=None,
                member_full_name=None,
                db_path=db_path,
            )
            out["team_member_updated"] = True
            logger.info(
                "setup_answer_persistor.team_member_upserted",
                tenant_id=tenant_id,
                is_team_mode=is_team_mode,
            )
        except Exception as exc:
            logger.warning(
                "setup_answer_persistor.team_member_upsert_failed",
                error=str(exc),
            )

    return out


def is_setup_step_user_answer(
    *,
    active_skill: str | None,
    active_skill_step: int | None,
) -> bool:
    """Helper: ritorna True se la conv ha active_skill='os-setup' e step valido.

    Si usa in `chat_routes.py` per decidere se invocare `persist_setup_answer`
    nel finally block del SSE stream.
    """
    if active_skill != "os-setup":
        return False
    if active_skill_step is None:
        return False
    return 1 <= active_skill_step <= 10


__all__ = [
    "SETUP_STEPS",
    "STEP_TO_PROFILE",
    "is_setup_step_user_answer",
    "persist_setup_answer",
]
