"""Subscriber del bus eventi per auto-trigger skill su vault registrato.

Pattern Conv. 41 tracciatura: ogni invocazione loggata con event_type +
payload size + skill outcomes.

Flusso DEV-OPTIMIZER-AUTO v1.0.0 con branching decisione su struttura SCO:
    POST /api/vault/add OK
        |
        v
    event_bus.publish('vault.registered', payload)
        |
        v
    handle_vault_registered(payload)  [questo modulo]
        |
        |--> store.create_conversation("Configurazione iniziale del vault <nome>")
        |--> inspect_missing_components(vault_root)  [scaffolder.py]
        |--> execute_skill('os-setup', vault_root, context)        [SEMPRE]
        |
        |--> SE is_sco_structure=True (vault gia completo SCO):
        |      STOP — solo profilazione utente, niente ottimizzazione
        |
        |--> SE is_sco_structure=False (vault esistente da ottimizzare):
        |      execute_skill('os-ottimizzatore', vault_root, context+vault_inspect)
        |      con context payload vault_inspect={is_sco_structure, missing_dirs}
        |      che la skill legge per proporre completamento all'utente
        |
        v
    Conversation visibile in sidebar Recents come "system-generated".

Pattern Conv. 47 single source of truth: la conversation system-generated e' una
normalissima Conversation in DB, lo stato widget vive nei messages persistiti.
Il campo del payload e' ``is_sco_structure`` (terminologia SCO proprietaria).
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
from sco_compliance_os.services.vault.scaffolder import inspect_missing_components

logger = get_logger(__name__)


# Event types pubblicati dal sistema.
EVENT_VAULT_REGISTERED = "vault.registered"
EVENT_VAULT_REGISTERED_POST_SETUP = "vault.registered_post_setup"


async def _scan_vault_structure(vault_root: Path) -> dict[str, Any]:
    """Snapshot lightweight della struttura vault per context di os-ottimizzatore.

    Ritorna dict con i campi che la skill leggera' dal context runtime:
    presenza CLAUDE.md, presenza 9 cartelle canoniche, conteggio md_files +
    classificazione mancanti auto-create vs opt-in (DEV-OPTIMIZER-AUTO v1.0.0).

    Pattern: pure-function, no IO se non listdir + exists/is_dir. No walk
    profondo (>10000 file degraderebbe l'audit, vedi SKILL os-ottimizzatore
    sezione "Budget").

    Pattern Conv. 35: la struttura SCO canonica e' fonte autoritativa
    ``inspect_missing_components()`` in ``scaffolder.py``.
    """
    if not vault_root.exists() or not vault_root.is_dir():
        return {
            "vault_exists": False,
            "vault_root": str(vault_root),
        }

    # Riusa fonte autoritativa unica struttura SCO (scaffolder.py).
    # Pattern Conv. 47 single source of truth: no duplicazione liste cartelle.
    inspect = inspect_missing_components(vault_root)

    has_agents_md = (vault_root / "AGENTS.md").exists()

    # Conteggio md_files: cap a 5000 file per evitare walk eccessivo (Conv. 46
    # smoke test concern). Se il vault e' piu' grande, si segnala come ">5000".
    md_count = 0
    capped = False
    for _ in vault_root.rglob("*.md"):
        md_count += 1
        if md_count > 5000:
            capped = True
            break

    # folder_status come dict per backward compat con skill os-ottimizzatore.
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

    return {
        "vault_exists": True,
        "vault_root": str(vault_root),
        "has_claude_md": inspect["has_claude_md"],
        "has_agents_md": has_agents_md,
        "has_log_dir": inspect["has_log_dir"],
        "folders_present": folder_status,
        "md_files_count": md_count,
        "md_count_capped_at_5000": capped,
        # DEV-OPTIMIZER-AUTO v1.0.0: payload per os-ottimizzatore branch decisione.
        "vault_inspect": {
            "is_sco_structure": inspect["is_sco_structure"],
            "missing_folders": inspect["missing_folders"],
            "missing_auto": inspect["missing_auto"],
            "missing_opt_in": inspect["missing_opt_in"],
            "present_folders": inspect["present_folders"],
        },
        "is_sco_structure_detected": inspect["is_sco_structure"],
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
            - "is_sco_structure": bool
    """
    vault_id = str(payload.get("vault_id", ""))
    vault_path_str = str(payload.get("vault_path", ""))
    vault_name = str(payload.get("vault_name", "Vault"))
    is_new = bool(payload.get("is_new", True))

    logger.info(
        "auto_trigger.invoked",
        vault_id=vault_id,
        vault_path=vault_path_str,
        vault_name=vault_name,
        is_new=is_new,
    )

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
    # Pattern Conv. 47: anche re-add (is_new=False) genera nuova conversation
    # cosi' l'utente vede chiaramente che le skill sono ri-eseguite, idempotenti.
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
        "auto_trigger.conversation_created",
        vault_id=vault_id,
        conv_id=conv_id,
        title=title,
        is_new_vault=is_new,
    )

    # 2. Scan vault structure per context runtime.
    structure_snapshot = await _scan_vault_structure(vault_root)

    # Conv. 47 single source of truth: nome campo univoco.
    # Pattern DEV-OPTIMIZER-AUTO v1.0.0: usa il valore DETECTED dal filesystem
    # invece del payload (single source of truth = filesystem stato attuale,
    # NON snapshot del momento di POST /api/vault/add che potrebbe essere stale).
    is_sco_structure = bool(
        structure_snapshot.get(
            "is_sco_structure_detected",
            payload.get("is_sco_structure", False),
        )
    )
    base_context: dict[str, Any] = {
        "vault_id": vault_id,
        "vault_path": str(vault_root),
        "vault_name": vault_name,
        "is_sco_structure": is_sco_structure,
        "conversation_id": conv_id,
        **structure_snapshot,
    }

    logger.info(
        "auto_trigger.branch_decision",
        vault_id=vault_id,
        conv_id=conv_id,
        is_sco_structure=is_sco_structure,
        will_run_ottimizzatore=not is_sco_structure,
    )

    # 3. Esegui os-setup con persistenza assistant text alla chiusura.
    setup_chunks: list[str] = []

    async def _setup_event_capture(event: AgentEvent) -> None:
        if event.kind == "text_delta":
            setup_chunks.append(event.data.get("text", ""))

    logger.info(
        "auto_trigger.skill_executing",
        skill_name="os-setup",
        vault_id=vault_id,
        conv_id=conv_id,
    )
    setup_result = await execute_skill(
        "os-setup",
        vault_root=vault_root,
        context=base_context,
        on_event=_setup_event_capture,
    )
    logger.info(
        "auto_trigger.skill_executed",
        name="os-setup",
        vault_id=vault_id,
        conv_id=conv_id,
        success=setup_result.success,
        events_count=setup_result.events_count,
        text_length=len(setup_result.assistant_text or ""),
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

    # 5. Branch decisione DEV-OPTIMIZER-AUTO v1.0.0:
    # - is_sco_structure=True (vault gia completo): NIENTE os-ottimizzatore.
    #   Il vault e' gia in struttura SCO, non c'e' nulla da ottimizzare.
    #   Solo profilo utente (os-setup) e via.
    # - is_sco_structure=False (vault esistente da ottimizzare): SI os-ottimizzatore.
    #   La skill leggera' ``vault_inspect`` dal context runtime e proporra'
    #   completamento all'utente (con branch auto-confirm vs interactive).
    if is_sco_structure:
        logger.info(
            "auto_trigger.ottimizzatore_skipped",
            vault_id=vault_id,
            conv_id=conv_id,
            reason="vault_already_sco_complete",
        )
        logger.info(
            "skills.auto_trigger.completed",
            vault_id=vault_id,
            conv_id=conv_id,
            setup_success=setup_result.success,
            ottimizzatore_success=None,
            ottimizzatore_skipped=True,
        )
        return

    # 6. Esegui os-ottimizzatore nello stesso conv_id (solo se vault da ottimizzare).
    ottimizzatore_chunks: list[str] = []

    async def _ottimizzatore_event_capture(event: AgentEvent) -> None:
        if event.kind == "text_delta":
            ottimizzatore_chunks.append(event.data.get("text", ""))

    logger.info(
        "auto_trigger.skill_executing",
        skill_name="os-ottimizzatore",
        vault_id=vault_id,
        conv_id=conv_id,
        vault_inspect=base_context.get("vault_inspect"),
    )
    ottimizzatore_result = await execute_skill(
        "os-ottimizzatore",
        vault_root=vault_root,
        context=base_context,
        on_event=_ottimizzatore_event_capture,
    )
    logger.info(
        "auto_trigger.skill_executed",
        name="os-ottimizzatore",
        vault_id=vault_id,
        conv_id=conv_id,
        success=ottimizzatore_result.success,
        events_count=ottimizzatore_result.events_count,
        text_length=len(ottimizzatore_result.assistant_text or ""),
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
                        "vault_inspect": base_context.get("vault_inspect"),
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
