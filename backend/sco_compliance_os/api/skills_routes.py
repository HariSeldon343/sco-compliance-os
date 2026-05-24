"""Router /api/skills — discovery + manual trigger skill loader runtime.

Endpoint:
- GET /api/skills/list — lista skill discoverable (User > Project > Legacy)
- POST /api/skills/run — esegui skill su richiesta utente, opzionalmente
  inviando l'output in una conversation esistente.

Pattern Conv. 47 single source of truth: la lista skill NON e' cacheata in DB,
si rerun discovery filesystem ad ogni call.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sco_compliance_os.config import Settings, get_settings
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.core.store import get_store
from sco_compliance_os.services.skills.loader import (
    SkillMeta,
    discover_skills,
)
from sco_compliance_os.services.skills.runner import (
    execute_skill_stream,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/skills", tags=["skills"])


# ----- Schemi Pydantic -----


class SkillSummary(BaseModel):
    """Skill summary response per GET /list."""

    name: str
    description: str
    scope: str
    path: str
    auto_trigger: str | None = None
    language: str = "it"


class SkillRunRequest(BaseModel):
    """Richiesta esecuzione skill manuale."""

    name: str = Field(..., description="Nome skill da eseguire.")
    conversation_id: str | None = Field(
        default=None,
        description="ID conversation per persistere output. Se None, crea nuova conv.",
    )
    vault_path: str | None = Field(
        default=None,
        description="Path vault attivo per scope Project + context.",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Context runtime da iniettare nel system prompt.",
    )


# ----- Helper -----


def _skill_to_summary(skill: SkillMeta) -> SkillSummary:
    return SkillSummary(
        name=skill.name,
        description=skill.description,
        scope=skill.scope,
        path=str(skill.path),
        auto_trigger=skill.auto_trigger,
        language=skill.language,
    )


def _resolve_vault_root(vault_path: str | None) -> Path | None:
    if not vault_path:
        return None
    p = Path(vault_path).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"vault_path '{vault_path}' non esiste o non e' directory",
        )
    return p


# ----- Endpoint -----


@router.get("/list", response_model=list[SkillSummary])
async def list_skills(
    vault_path: str | None = None,
) -> list[SkillSummary]:
    """Lista skill discoverable.

    Args:
        vault_path: opzionale, path vault attivo per includere scope Project.
            Se omesso, ritorna solo skill User + Legacy.
    """
    vault_root = _resolve_vault_root(vault_path)
    skills = discover_skills(vault_root)
    return [_skill_to_summary(s) for s in skills]


@router.post("/run")
async def run_skill(
    payload: SkillRunRequest,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Esegue skill on-demand con streaming SSE.

    Behavior:
    - Se conversation_id e' fornito, persiste output assistant in essa.
    - Se conversation_id e' None, crea una nuova conversation con titolo
      "Skill <name>".
    """
    vault_root = _resolve_vault_root(payload.vault_path)
    store = get_store(settings.memory_tree_db_path)

    conv_id = payload.conversation_id
    if conv_id is None:
        conv = await store.create_conversation(title=f"Skill {payload.name}")
        conv_id = conv.id
    else:
        existing = await store.get_conversation(conv_id)
        if existing is None:
            raise HTTPException(
                status_code=404, detail=f"Conversation {conv_id} non trovata"
            )

    assert conv_id is not None  # post-check per type checker

    async def _event_stream() -> AsyncIterator[str]:
        """Yield SSE eventi della skill + persisti output finale."""
        assistant_buf: list[str] = []
        success = True
        events_count = 0

        try:
            async for ev in execute_skill_stream(
                payload.name,
                vault_root=vault_root,
                context=payload.context,
            ):
                events_count += 1
                if ev.kind == "text_delta":
                    assistant_buf.append(ev.data.get("text", ""))
                elif ev.kind == "error":
                    success = False
                event_payload = {"kind": ev.kind, "data": ev.data, "seq": ev.seq}
                yield f"data: {json.dumps(event_payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("skills.run.stream_error", error=str(exc))
            yield (
                "data: "
                + json.dumps({"kind": "error", "data": {"message": str(exc)}})
                + "\n\n"
            )
            success = False
        finally:
            text = "".join(assistant_buf)
            if text:
                try:
                    await store.append_message(
                        conversation_id=conv_id,
                        role="assistant",
                        content=text,
                        tool_calls=[
                            {
                                "kind": "skill_invocation",
                                "skill_name": payload.name,
                                "success": success,
                                "events_count": events_count,
                            }
                        ],
                    )
                except Exception as exc:
                    logger.exception(
                        "skills.run.persist_failed",
                        conv_id=conv_id,
                        error=str(exc),
                    )

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Conversation-Id": conv_id,
        },
    )
