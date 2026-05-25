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
from sco_compliance_os.services.vault.deep_scanner import deep_scan_vault
from sco_compliance_os.services.vault.scaffolder import (
    auto_organize_vault,
    inspect_missing_components,
)

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

    # v0.9.0 multi-turn skill flow: marca la conversation come skill-driven
    # cosi' il chat handler /api/chat/stream propaga il SKILL.md body al system
    # prompt nei turni successivi all'auto-trigger. Pattern Conv. 48 SSOT backend.
    try:
        await store.set_active_skill(conv_id, "os-setup", step=0)
        logger.info(
            "auto_trigger.active_skill_set",
            conv_id=conv_id,
            skill_name="os-setup",
        )
    except Exception as exc:
        logger.warning(
            "auto_trigger.set_active_skill_failed",
            conv_id=conv_id,
            error=str(exc),
        )

    # 2. Scan vault structure per context runtime.
    structure_snapshot = await _scan_vault_structure(vault_root)

    # 2-bis. DEEP SCAN PROFONDA v0.8.1 (cantiere DEV-OS-SETUP-DEEP-SCAN):
    # Esegui scan profonda PRIMA delle 10 domande os-setup. Il report markdown
    # leggibile viene appeso come messaggio assistant alla conversation, cosi'
    # l'utente vede subito lo stato del vault prima di rispondere alle domande.
    # Pattern Conv. 35 RESEARCH-BEFORE-ACT: niente domanda 1 senza analisi
    # reale del filesystem.
    deep_scan_report_dict: dict[str, Any] = {}
    deep_scan_markdown = ""
    try:
        deep_report = deep_scan_vault(vault_root, vault_name=vault_name)
        deep_scan_markdown = deep_report.markdown_summary
        # Serializza in dict JSON-friendly per context runtime skill.
        deep_scan_report_dict = {
            "total_files": deep_report.total_files,
            "files_by_extension": deep_report.files_by_extension,
            "md_files_parsed": deep_report.md_files_parsed,
            "files_scanned_capped": deep_report.files_scanned_capped,
            "entity_type_distribution": deep_report.entity_type_distribution,
            "ambito_canonico_distribution": deep_report.ambito_canonico_distribution,
            "status_distribution": deep_report.status_distribution,
            "tags_top": deep_report.tags_top,
            "sigle_top": deep_report.sigle_top,
            "clienti_citati": deep_report.clienti_citati,
            "clienti_count": deep_report.clienti_count,
            "languages_detected": deep_report.languages_detected,
            "framework_occurrences": deep_report.framework_occurrences,
            "scan_duration_sec": deep_report.scan_duration_sec,
            "has_claude_md": deep_report.has_claude_md,
            "has_wiki": deep_report.has_wiki,
            "has_raw": deep_report.has_raw,
            "has_business": deep_report.has_business,
            "has_giornaliero": deep_report.has_giornaliero,
        }
        logger.info(
            "auto_trigger.deep_scan_completed",
            vault_id=vault_id,
            conv_id=conv_id,
            total_files=deep_report.total_files,
            md_parsed=deep_report.md_files_parsed,
            clienti=deep_report.clienti_count,
            framework_top=len(deep_report.framework_occurrences),
            duration_sec=deep_report.scan_duration_sec,
        )
    except Exception as exc:
        # Pattern Conv. 44 lesson 1 CircuitBreaker: fallimento deep scan
        # non blocca il resto del flow os-setup. L'utente vede comunque
        # le domande, semplicemente senza pre-report.
        # v0.9.0: log exception type + 1ª riga traceback per diagnostica reale
        # invece di catch generic mascherante. Continua con DeepScanReport stub
        # parziale ricostruito (stat base disponibili anche senza scan profondo).
        import traceback as _tb

        tb_first_line = ""
        try:
            tb_lines = _tb.format_exception(type(exc), exc, exc.__traceback__)
            # prendi la prima riga del frame piu' vicino al crash
            for ln in reversed(tb_lines):
                if 'File "' in ln:
                    tb_first_line = ln.strip()
                    break
        except Exception:
            pass

        logger.exception(
            "auto_trigger.deep_scan_failed",
            vault_id=vault_id,
            conv_id=conv_id,
            exc_type=type(exc).__name__,
            error=str(exc),
            tb_first_line=tb_first_line,
        )

        # Ricostruisci stat base da snapshot esistente (best-effort fallback).
        base_total = int(structure_snapshot.get("md_files_count", 0) or 0)
        deep_scan_markdown = (
            f"## Scansione profonda del vault \"{vault_name}\"\n\n"
            f"La scansione profonda ha incontrato un problema tecnico: "
            f"`{type(exc).__name__}: {str(exc)[:160]}`.\n\n"
            f"Statistiche base dalla scansione preliminare: "
            f"{base_total} file markdown rilevati.\n\n"
            f"Procedo con le 10 domande di profilazione "
            f"(la scansione profonda non e' bloccante).\n\n---\n"
        )

    # Appendi il report deep scan come messaggio assistant ALLA conversation
    # PRIMA di invocare os-setup. Cosi' l'utente vede in chat:
    #   1. Report deep scan markdown ricco
    #   2. Domande 1..10 dell'os-setup (in messaggi successivi del bot)
    if deep_scan_markdown:
        try:
            await store.append_message(
                conversation_id=conv_id,
                role="assistant",
                content=deep_scan_markdown,
                tool_calls=[
                    {
                        "kind": "deep_scan_report",
                        "vault_id": vault_id,
                        "total_files": deep_scan_report_dict.get("total_files", 0),
                        "clienti_count": deep_scan_report_dict.get("clienti_count", 0),
                        "framework_count": len(
                            deep_scan_report_dict.get("framework_occurrences", [])
                        ),
                    }
                ],
            )
        except Exception as exc:
            logger.exception(
                "auto_trigger.deep_scan_persist_failed",
                conv_id=conv_id,
                error=str(exc),
            )

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
        "deep_scan_report": deep_scan_report_dict,
        **structure_snapshot,
    }

    logger.info(
        "auto_trigger.branch_decision",
        vault_id=vault_id,
        conv_id=conv_id,
        is_sco_structure=is_sco_structure,
        will_run_ottimizzatore=not is_sco_structure,
    )

    # v0.10.0 FIX DEFINITIVO: emit Q1 DETERMINISTICA invece di affidarsi al LLM.
    #
    # Bug v0.9.0: execute_skill('os-setup') chiamava il LLM via SaaS proxy,
    # ma o (a) il LLM non emetteva il widget formattato, o (b) lo stream
    # falliva silente, o (c) il LLM emetteva TUTTE le 10 domande in un colpo
    # (trim al primo widget mancava perche' il modello non emette il pattern
    # esatto `<ASK_USER_QUESTION>{json}</ASK_USER_QUESTION>` ma varianti).
    #
    # Soluzione v0.10.0: niente LLM al primo turno. Append direttamente un
    # messaggio assistant con presentazione + Q1 hard-coded (Conv. 48 SSOT
    # backend: il widget e' formattato esattamente come lo aspetta il parser
    # inline frontend `parseInlineWidgets.ts`). Q2-Q10 vengono generate dal
    # LLM nei turni successivi via `chat_routes.py`, che ora carica history
    # piena + prepende skill_body al system prompt finche' active_skill set.
    #
    # Pattern Conv. 35 RESEARCH-BEFORE-ACT applied: il primo turno e' un dato
    # certo (non un'ipotesi LLM). Anti-pattern del "vediamo cosa risponde il
    # modello" disciplinarmente eliminato.

    # Conta dei framework rilevati dal deep_scan per pre-popolare la lista
    # framework della domanda 6/10 (calcolato dopo per altri turni LLM-driven).
    _framework_top = deep_scan_report_dict.get("framework_occurrences", [])
    _detected_frameworks_names = [
        fw[0] if isinstance(fw, (list, tuple)) and fw else str(fw)
        for fw in _framework_top[:6]
    ]
    _detected_summary = (
        f"Nel vault ho gia rilevato: {', '.join(_detected_frameworks_names)}."
        if _detected_frameworks_names
        else ""
    )

    # Q1 deterministica: presentazione + widget "Come ti chiami?"
    q1_widget_json = (
        '{"question":"Come ti chiami? Indica nome e cognome.",'
        '"options":[{"value":"free_text",'
        '"label":"Scrivi nel campo qui sotto",'
        '"description":"Esempio: Mario Rossi"}]}'
    )
    setup_text = (
        f"Hai visto il report del vault. "
        f"{_detected_summary}\n\n"
        f"Per personalizzare l'agente ti faccio 10 domande veloci. "
        f"Una alla volta.\n\n"
        f"### 1/10 — Chi sei\n\n"
        f"<ASK_USER_QUESTION>{q1_widget_json}</ASK_USER_QUESTION>"
    )

    try:
        await store.append_message(
            conversation_id=conv_id,
            role="assistant",
            content=setup_text,
            tool_calls=[
                {
                    "kind": "skill_invocation",
                    "skill_name": "os-setup",
                    "success": True,
                    "deterministic_q1": True,
                    "step": "1/10",
                }
            ],
        )
        logger.info(
            "auto_trigger.q1_emitted_deterministic",
            conv_id=conv_id,
            vault_id=vault_id,
            content_len=len(setup_text),
            detected_frameworks_count=len(_detected_frameworks_names),
        )
    except Exception as exc:
        logger.exception(
            "skills.auto_trigger.q1_persist_failed",
            conv_id=conv_id,
            error=str(exc),
        )

    # NB v0.10.0: l'execute_skill('os-setup') NON viene piu' chiamato qui al
    # primo turno. La skill resta attiva (conversation.active_skill='os-setup')
    # e il chat_routes propaghera' il body SKILL.md al system prompt nei turni
    # successivi, dove il LLM gestira' Q2..Q10 + chiusura "Profilo registrato:".
    # Conv. 47 SSOT: una sola sorgente per la transizione di stato (chat handler).
    setup_result = type("SetupResultStub", (), {"success": True, "skill_name": "os-setup"})()

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

    # 5b. DEV-AUTO-SCAFFOLD v1.0.2: auto-organize vault PRIMA di os-ottimizzatore.
    # Antonio vuole che il sistema AUTO-COMPLETI la struttura SENZA chiedere
    # conferma per OGNI vault (vuoto o pieno). Riusa scaffolder.auto_organize_vault
    # in modalita auto_apply=True. Idempotente: chiamata ripetuta safe (skip su
    # file/cartelle gia presenti, backup pre-spostamento per file riclassificati).
    # Pattern Conv. 41 tracciatura + Conv. 44 lesson 1 CircuitBreaker:
    # errori non bloccano os-ottimizzatore successivo.
    auto_organize_summary_line = ""
    try:
        organize_result = auto_organize_vault(
            vault_root,
            vault_name=vault_name,
            auto_apply=True,
        )
        logger.info(
            "auto_trigger.auto_organize_completed",
            vault_id=vault_id,
            conv_id=conv_id,
            organized=organize_result.organized,
            directories_created=len(organize_result.directories_created),
            files_created=len(organize_result.files_created),
            files_moved=len(organize_result.files_moved),
            files_backed_up=len(organize_result.files_backed_up),
            errors=len(organize_result.errors),
        )
        # Snippet sintetico da appendere alla conversation come tracciatura
        # visibile all'utente (Conv. 41 traceability).
        if organize_result.organized:
            auto_organize_summary_line = (
                f"\n\n---\n\n**Auto-organize struttura SCO eseguito** "
                f"({len(organize_result.directories_created)} cartelle create, "
                f"{len(organize_result.files_created)} file template, "
                f"{len(organize_result.files_moved)} file riclassificati, "
                f"{len(organize_result.files_backed_up)} backup in "
                f"`_archivio_pre_v1.0.2/`)."
            )
    except Exception as exc:
        logger.exception(
            "auto_trigger.auto_organize_failed",
            vault_id=vault_id,
            conv_id=conv_id,
            error=str(exc),
        )
        organize_result = None

    # Aggiorna context per os-ottimizzatore con esito auto-organize, cosi'
    # la skill puo' riportare l'esito al posto di proporre interattivamente
    # il completamento (gia eseguito).
    if organize_result is not None:
        base_context["auto_organize_applied"] = True
        base_context["auto_organize_organized"] = organize_result.organized
        base_context["auto_organize_dirs_created"] = list(
            organize_result.directories_created
        )
        base_context["auto_organize_files_created"] = list(
            organize_result.files_created
        )
        base_context["auto_organize_files_moved"] = [
            {"src": s, "dest": d} for s, d in organize_result.files_moved
        ]
        base_context["auto_organize_files_backed_up"] = list(
            organize_result.files_backed_up
        )
        # Refresh vault_inspect post-organize: la struttura e' cambiata.
        try:
            fresh_inspect = inspect_missing_components(vault_root)
            base_context["vault_inspect"] = {
                "is_sco_structure": fresh_inspect["is_sco_structure"],
                "missing_folders": fresh_inspect["missing_folders"],
                "missing_auto": fresh_inspect["missing_auto"],
                "missing_opt_in": fresh_inspect["missing_opt_in"],
                "present_folders": fresh_inspect["present_folders"],
            }
        except Exception as exc:
            logger.warning(
                "auto_trigger.inspect_refresh_failed",
                vault_id=vault_id,
                error=str(exc),
            )

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
    # Conv. 41 traceability: appende il summary line dell'auto-organize al
    # messaggio assistant cosi' che l'utente veda in chat cosa e' stato fatto
    # in autonomia dal sistema (struttura SCO completata + file riclassificati).
    if auto_organize_summary_line:
        ottimizzatore_text = (ottimizzatore_text or "") + auto_organize_summary_line
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
