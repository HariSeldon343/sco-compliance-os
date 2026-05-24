"""Subscriber del bus eventi per auto-trigger skill su vault registrato.

Pattern Conv. 41 tracciatura: ogni invocazione loggata con event_type +
payload size + skill outcomes.

Flusso:
    POST /api/vault/add OK
        |
        v
    event_bus.publish('vault.registered', payload)
        |
        v
    handle_vault_registered(payload)  [questo modulo]
        |
        |--> store.create_conversation("Configurazione iniziale del vault <nome>")
        |--> execute_skill('os-setup', vault_root, context, on_event=persist_assistant_chunks)
        |--> execute_skill('os-ottimizzatore', vault_root, context, on_event=persist_assistant_chunks)
        |
        v
    Conversation visibile in sidebar Recents come "system-generated".

Pattern Conv. 47 single source of truth: la conversation system-generated e' una
normalissima Conversation in DB, lo stato widget vive nei messages persistiti.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sco_compliance_os.config import get_settings
from sco_compliance_os.core.agent_sdk_runner import AgentEvent
from sco_compliance_os.core.events import EventBus
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.core.store import get_store
from sco_compliance_os.services.skills.runner import execute_skill

logger = get_logger(__name__)


# Event types pubblicati dal sistema.
EVENT_VAULT_REGISTERED = "vault.registered"
EVENT_VAULT_REGISTERED_POST_SETUP = "vault.registered_post_setup"


async def _scan_vault_structure(vault_root: Path) -> dict[str, Any]:
    """Snapshot lightweight della struttura vault per context di os-ottimizzatore.

    Ritorna dict con i campi che la skill leggera' dal context runtime:
    presenza CLAUDE.md, presenza 9 cartelle canoniche, conteggio md_files.

    Pattern: pure-function, no IO se non listdir + exists/is_dir. No walk
    profondo (>10000 file degraderebbe l'audit, vedi SKILL os-ottimizzatore
    sezione "Budget").
    """
    if not vault_root.exists() or not vault_root.is_dir():
        return {
            "vault_exists": False,
            "vault_root": str(vault_root),
        }

    canonical_folders = [
        "Contesto",
        "Business",
        "Giornaliero",
        "Libreria",
        "Skill",
        "Progetti",
        "Team",
        "raw",
        "wiki",
    ]
    folder_status = {f: (vault_root / f).is_dir() for f in canonical_folders}

    has_claude_md = (vault_root / "CLAUDE.md").exists()
    has_agents_md = (vault_root / "AGENTS.md").exists()
    has_log_dir = (vault_root / "log").is_dir()

    # Conteggio md_files: cap a 5000 file per evitare walk eccessivo (Conv. 46
    # smoke test concern). Se il vault e' piu' grande, si segnala come ">5000".
    md_count = 0
    capped = False
    for _ in vault_root.rglob("*.md"):
        md_count += 1
        if md_count > 5000:
            capped = True
            break

    return {
        "vault_exists": True,
        "vault_root": str(vault_root),
        "has_claude_md": has_claude_md,
        "has_agents_md": has_agents_md,
        "has_log_dir": has_log_dir,
        "folders_present": folder_status,
        "md_files_count": md_count,
        "md_count_capped_at_5000": capped,
    }


async def handle_vault_registered(payload: dict[str, Any]) -> None:
    """Handler subscriber per evento ``vault.registered``.

    Esegue in sequenza:
    1. Crea una conversation system-generated con titolo descrittivo.
    2. Esegue os-setup forwardando text_delta come assistant message buffer.
    3. Emette evento ``vault.registered_post_setup`` con conv_id.
    4. Esegue os-ottimizzatore nello stesso flusso.

    Args:
        payload: dict con almeno chiavi:
            - "vault_id": str
            - "vault_path": str (path assoluto)
            - "vault_name": str
            - "is_karpathy": bool
    """
    vault_id = str(payload.get("vault_id", ""))
    vault_path_str = str(payload.get("vault_path", ""))
    vault_name = str(payload.get("vault_name", "Vault"))

    if not vault_path_str:
        logger.warning(
            "skills.auto_trigger.vault_registered.missing_path",
            payload_keys=list(payload.keys()),
        )
        return

    vault_root = Path(vault_path_str)

    settings = get_settings()
    store = get_store(settings.memory_tree_db_path)

    # 1. Crea conversation system-generated.
    title = f"Configurazione iniziale del vault {vault_name}"
    try:
        conversation = await store.create_conversation(title=title)
    except Exception as exc:
        logger.exception(
            "skills.auto_trigger.create_conversation_failed",
            vault_id=vault_id,
            error=str(exc),
        )
        return

    conv_id = conversation.id
    logger.info(
        "skills.auto_trigger.conversation_created",
        vault_id=vault_id,
        conv_id=conv_id,
        title=title,
    )

    # 2. Scan vault structure per context runtime.
    structure_snapshot = await _scan_vault_structure(vault_root)

    base_context: dict[str, Any] = {
        "vault_id": vault_id,
        "vault_path": str(vault_root),
        "vault_name": vault_name,
        "is_karpathy": bool(payload.get("is_karpathy", False)),
        "conversation_id": conv_id,
        **structure_snapshot,
    }

    # 3. Esegui os-setup con persistenza assistant text alla chiusura.
    setup_chunks: list[str] = []

    async def _setup_event_capture(event: AgentEvent) -> None:
        if event.kind == "text_delta":
            setup_chunks.append(event.data.get("text", ""))

    setup_result = await execute_skill(
        "os-setup",
        vault_root=vault_root,
        context=base_context,
        on_event=_setup_event_capture,
    )

    setup_text = setup_result.assistant_text or "".join(setup_chunks)
    if setup_text:
        try:
            await store.append_message(
                conversation_id=conv_id,
                role="assistant",
                content=setup_text,
                tool_calls=[
                    {
                        "kind": "skill_invocation",
                        "skill_name": setup_result.skill_name,
                        "success": setup_result.success,
                        "events_count": setup_result.events_count,
                    }
                ],
            )
        except Exception as exc:
            logger.exception(
                "skills.auto_trigger.os_setup_persist_failed",
                conv_id=conv_id,
                error=str(exc),
            )

    if not setup_result.success:
        logger.warning(
            "skills.auto_trigger.os_setup_failed",
            conv_id=conv_id,
            error=setup_result.error_message,
        )
        # Non interrompiamo: anche se os-setup fallisce, vogliamo eseguire
        # os-ottimizzatore (audit struttura e' indipendente dal profilo).

    # 4. Emit evento post-setup (per future skill che vogliano subscribe).
    bus = EventBus.instance()
    await bus.publish(
        EVENT_VAULT_REGISTERED_POST_SETUP,
        {
            "vault_id": vault_id,
            "vault_path": str(vault_root),
            "vault_name": vault_name,
            "conv_id": conv_id,
            "setup_success": setup_result.success,
        },
    )

    # 5. Esegui os-ottimizzatore nello stesso conv_id.
    ottimizzatore_chunks: list[str] = []

    async def _ottimizzatore_event_capture(event: AgentEvent) -> None:
        if event.kind == "text_delta":
            ottimizzatore_chunks.append(event.data.get("text", ""))

    ottimizzatore_result = await execute_skill(
        "os-ottimizzatore",
        vault_root=vault_root,
        context=base_context,
        on_event=_ottimizzatore_event_capture,
    )

    ottimizzatore_text = (
        ottimizzatore_result.assistant_text or "".join(ottimizzatore_chunks)
    )
    if ottimizzatore_text:
        try:
            await store.append_message(
                conversation_id=conv_id,
                role="assistant",
                content=ottimizzatore_text,
                tool_calls=[
                    {
                        "kind": "skill_invocation",
                        "skill_name": ottimizzatore_result.skill_name,
                        "success": ottimizzatore_result.success,
                        "events_count": ottimizzatore_result.events_count,
                    }
                ],
            )
        except Exception as exc:
            logger.exception(
                "skills.auto_trigger.os_ottimizzatore_persist_failed",
                conv_id=conv_id,
                error=str(exc),
            )

    logger.info(
        "skills.auto_trigger.completed",
        vault_id=vault_id,
        conv_id=conv_id,
        setup_success=setup_result.success,
        ottimizzatore_success=ottimizzatore_result.success,
    )


def register_default_subscribers() -> None:
    """Registra i subscriber default sul bus singleton.

    Idempotente: re-registrazione dello stesso handler aggiungerebbe duplicato,
    quindi controlliamo presenza prima.
    """
    bus = EventBus.instance()
    existing = bus._subscribers.get(EVENT_VAULT_REGISTERED, [])  # noqa: SLF001
    if handle_vault_registered in existing:
        logger.debug("skills.auto_trigger.already_registered")
        return
    bus.subscribe(EVENT_VAULT_REGISTERED, handle_vault_registered)
    logger.info(
        "skills.auto_trigger.registered_subscriber",
        event_type=EVENT_VAULT_REGISTERED,
    )
