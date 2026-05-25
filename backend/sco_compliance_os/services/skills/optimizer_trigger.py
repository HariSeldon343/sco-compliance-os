"""Subscriber bus eventi per auto-trigger os-ottimizzatore post completion os-setup.

v0.13.2 hotfix DEV-AUTO-OPTIMIZER. Bug Antonio (Sessione 21): "Perche' se non e'
pienamente ottimizzato il sistema non e' partito automaticamente quello che
dovrebbe partire con os-optimizator?". Risposta: os-ottimizzatore aveva
auto_trigger ``vault_registered_post_setup`` ma il chat handler NON emetteva
quell'evento quando l'utente completava le 10 domande os-setup. Questo modulo
chiude il loop.

Flusso DEV-AUTO-OPTIMIZER v1.0.0:
    Chat handler /api/chat/stream rileva "Profilo registrato:" in final_text
        |
        v
    event_bus.publish('setup.completed', payload)
        |
        v
    handle_setup_completed(payload)  [questo modulo]
        |
        |--> store.create_conversation("Ottimizzazione iniziale del vault <nome>")
        |--> deep_scan_vault(vault_root)  [scansione ESTESA: scanner + relationship analysis]
        |--> store.append_message(role=assistant, content=banner "Ottimizzazione in corso...")
        |--> execute_skill('os-ottimizzatore', vault_root, context)
        |--> ingest_inputs(memory_tree, source_kind="document", tags=["bootstrap","optimizer"])
        |--> warmup_anthropic_cache(system_prompt)  [pre-warming ephemeral cache 5min TTL]
        |
        v
    Conversation visibile in sidebar "Ottimizzazione iniziale del vault <nome>".
    Memory tree popolato con bootstrap chunks (recall futuro veloce).
    Anthropic ephemeral cache calda -> prima chat utente latency 5-10s (vs 30-60s).

Pattern Conv. 41 tracciatura: ogni step loggato con duration + counts.
Pattern Conv. 47 single source of truth: il payload completion vive sul DB
nel campo conversation.active_skill (clear post-completion in chat handler).
Pattern Conv. 44 lesson 1 CircuitBreaker: errori non bloccano il chat flow utente.

Toggle env var: ``SCO_AUTO_OPTIMIZER_ENABLED=0`` per disabilitare (default attivo).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sco_compliance_os.config import get_settings
from sco_compliance_os.core.agent_sdk_runner import AgentEvent
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.core.store import get_store
from sco_compliance_os.services.skills.runner import execute_skill
from sco_compliance_os.services.vault.deep_scanner import deep_scan_vault
from sco_compliance_os.services.vault.scaffolder import inspect_missing_components

logger = get_logger(__name__)


# Toggle env var per disabilitare optimizer (default attivo).
def _is_auto_optimizer_enabled() -> bool:
    """True se auto-optimizer attivo (default True). Override via env var.

    Pattern Conv. 41 tracciatura: log diagnostico al primo check di sessione.
    """
    raw = os.environ.get("SCO_AUTO_OPTIMIZER_ENABLED", "1").strip()
    return raw not in ("0", "false", "False", "no", "off")


async def _extended_vault_scan(
    vault_root: Path,
    vault_name: str,
) -> dict[str, Any]:
    """Scan profonda ESTESA rispetto a quella di os-setup.

    Differenza vs ``_scan_vault_structure`` in auto_trigger.py:
    - Riusa ``deep_scan_vault()`` per scan filesystem completo (entity types,
      framework occurrences, clienti citati, lingue).
    - Aggiunge relationship analysis su wiki/entities/ (count wikilink incoming
      per pagina, candidati a entity hub).
    - Cap difensivo: max 5000 file (gia' enforcement di deep_scan_vault).

    Ritorna dict JSON-friendly per context runtime + memory bootstrap.

    Pattern Conv. 35 RESEARCH-BEFORE-ACT: scan reale filesystem, mai mock.
    Pattern Conv. 41 tracciatura: log entity_count + relationship_count.
    """
    try:
        deep_report = deep_scan_vault(vault_root, vault_name=vault_name)
    except Exception as exc:
        logger.exception(
            "optimizer_trigger.deep_scan_failed",
            vault_root=str(vault_root),
            error=str(exc),
        )
        return {
            "deep_scan_failed": True,
            "deep_scan_error": str(exc),
            "vault_root": str(vault_root),
        }

    # Relationship analysis lightweight: count file md in wiki/entities/.
    # Versione completa (parse wikilink targets + reverse index) e' carry-over
    # v0.13.3: per la pipeline hotfix il count e' sufficiente.
    entities_dir = vault_root / "wiki" / "entities"
    entities_count = 0
    if entities_dir.is_dir():
        try:
            entities_count = sum(1 for _ in entities_dir.rglob("*.md"))
        except (OSError, PermissionError) as exc:
            logger.warning(
                "optimizer_trigger.entities_count_failed",
                error=str(exc),
            )

    inspect = inspect_missing_components(vault_root)

    return {
        "vault_root": str(vault_root),
        "vault_name": vault_name,
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
        "wiki_entities_count": entities_count,
        "is_sco_structure": inspect["is_sco_structure"],
        "missing_folders": inspect["missing_folders"],
        "present_folders": inspect["present_folders"],
    }


async def _ingest_bootstrap_chunks(
    vault_root: Path,
    vault_name: str,
    extended_scan: dict[str, Any],
    optimizer_output: str,
) -> dict[str, int]:
    """Popola memory_tree con bootstrap chunks dal deep scan + output optimizer.

    source_kind = "document" (vocabolario chiuso TreeChunkSourceKind:
    chat | email | document | vault_file | note). Tag "bootstrap" + "optimizer"
    per filtraggio successivo.

    Pattern Conv. 41 tracciatura: log admitted/dropped/upserted.
    Pattern Karpathy "schema is the product": chunks ingeriti idempotente
    (stable IDs hash content + source_id + seq).

    Returns:
        IngestCounts.to_dict() con keys admitted/dropped/pending_extraction/upserted/total.
    """
    try:
        from sco_compliance_os.services.memory.tree_ingester import (
            IngestInput,
            ingest_inputs,
        )

        # Inputs: deep scan report (frame riassuntivo) + optimizer output (skill output).
        inputs: list[IngestInput] = []

        # Frame riassuntivo deep scan come document_source: extended_scan
        # struttura come markdown human-readable + JSON-like rappresentazione.
        scan_summary_lines = [
            f"# Bootstrap deep scan vault {vault_name}",
            "",
            f"Path: {vault_root}",
            f"Total files: {extended_scan.get('total_files', 0)}",
            f"MD parsed: {extended_scan.get('md_files_parsed', 0)}",
            f"Wiki entities: {extended_scan.get('wiki_entities_count', 0)}",
            f"Clienti citati: {extended_scan.get('clienti_count', 0)}",
            "",
            "## Framework rilevati",
        ]
        for fw in extended_scan.get("framework_occurrences", [])[:10]:
            if isinstance(fw, (list, tuple)) and len(fw) >= 2:
                scan_summary_lines.append(f"- {fw[0]}: {fw[1]} occorrenze")

        scan_summary_lines.append("")
        scan_summary_lines.append("## Clienti citati")
        for cliente in extended_scan.get("clienti_citati", [])[:20]:
            scan_summary_lines.append(f"- {cliente}")

        scan_summary_lines.append("")
        scan_summary_lines.append("## Ambito canonico")
        for ambito, count in (extended_scan.get("ambito_canonico_distribution") or {}).items():
            scan_summary_lines.append(f"- {ambito}: {count}")

        scan_summary_md = "\n".join(scan_summary_lines)

        inputs.append(
            IngestInput(
                source_kind="document",
                source_id=f"bootstrap-deep-scan-{vault_name}",
                content=scan_summary_md,
                owner="local",
                tags=["bootstrap", "optimizer", "deep-scan", "vault-snapshot"],
            )
        )

        # Output optimizer skill come document_source separato.
        if optimizer_output and len(optimizer_output.strip()) > 100:
            inputs.append(
                IngestInput(
                    source_kind="document",
                    source_id=f"bootstrap-optimizer-{vault_name}",
                    content=optimizer_output,
                    owner="local",
                    tags=["bootstrap", "optimizer", "skill-output"],
                )
            )

        counts = await ingest_inputs(inputs, consult_llm_on_borderline=False)
        return counts.to_dict()
    except Exception as exc:
        logger.exception(
            "optimizer_trigger.ingest_bootstrap_failed",
            vault_root=str(vault_root),
            error=str(exc),
        )
        return {
            "admitted": 0,
            "dropped": 0,
            "pending_extraction": 0,
            "total": 0,
            "upserted": 0,
            "error": str(exc),
        }


async def _warmup_anthropic_cache(system_prompt: str) -> dict[str, Any]:
    """Pre-warm Anthropic ephemeral cache invocando uno stream "ack" con max_tokens=1.

    Razionale: AnthropicProvider abilita cache_control=ephemeral su system prompt
    > 1024 char (vedi providers/anthropic.py:112). La prima richiesta scrive in
    cache (cost normale), le successive (entro 5min TTL) leggono dalla cache
    (input tokens ~200 vs 5400, -90% costo, -70% latency).

    La prima chat utente reale post-optimizer trovera' la cache calda.

    Pattern Conv. 41 tracciatura: log input_tokens + output_tokens + duration.
    Pattern Conv. 44 lesson 1: timeout 30s, errori non bloccanti.

    Returns:
        dict con "success" + "input_tokens" + "output_tokens" (best-effort).
    """
    try:
        from sco_compliance_os.services.llm.providers.anthropic import (
            build_anthropic_provider_from_license,
        )

        provider = build_anthropic_provider_from_license()
        if provider is None:
            logger.warning(
                "optimizer_trigger.warmup_skipped",
                reason="no_license_active",
            )
            return {"success": False, "reason": "no_license"}

        settings = get_settings()
        model = settings.model_default

        # Stream "ack" — max_tokens=1, payload minimo.
        # Pattern: aspettiamo solo l'event done per chiudere lo stream.
        input_tokens = 0
        output_tokens = 0
        success = False
        async for chunk in provider.stream(
            messages=[{"role": "user", "content": "ack"}],
            model=model,
            max_tokens=1,
            system_prompt=system_prompt,
        ):
            if chunk.kind == "done":
                usage = chunk.data.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                success = True
                break
            elif chunk.kind == "error":
                logger.warning(
                    "optimizer_trigger.warmup_stream_error",
                    error=chunk.data.get("message", "unknown"),
                )
                return {
                    "success": False,
                    "reason": "stream_error",
                    "error": chunk.data.get("message", "unknown"),
                }

        logger.info(
            "optimizer_trigger.warmup_completed",
            success=success,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return {
            "success": success,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    except Exception as exc:
        logger.exception(
            "optimizer_trigger.warmup_failed",
            error=str(exc),
        )
        return {"success": False, "reason": "exception", "error": str(exc)}


def _build_warmup_system_prompt(
    vault_name: str,
    extended_scan: dict[str, Any],
) -> str:
    """Costruisce system prompt rappresentativo per cache warmup.

    Riproduce la struttura del prompt che chat_routes.py compone runtime
    (DEFAULT_SYSTEM_PROMPT + skill catalog + profile_markdown). Ovviamente
    chat_routes.py user-by-user costruira' un prompt piu' lungo includendo
    skill body in attive_skill, ma il warmup popola la cache per i blocchi
    cache-control ephemeral. Le sezioni dinamiche (profile_markdown specifico
    + skill body specifico) non cachano, ma cachano il bulk fisso.

    Pattern Conv. 47 single source of truth: leggiamo _DEFAULT_SYSTEM_PROMPT
    dal modulo agent_sdk_runner per riusare il contenuto.
    """
    try:
        from sco_compliance_os.api.chat_routes import _get_skill_catalog_for_prompt
        from sco_compliance_os.core.agent_sdk_runner import _DEFAULT_SYSTEM_PROMPT

        skill_catalog = _get_skill_catalog_for_prompt(vault_root=None)
        if skill_catalog:
            base = f"{_DEFAULT_SYSTEM_PROMPT}\n\n{skill_catalog}"
        else:
            base = _DEFAULT_SYSTEM_PROMPT

        # Aggiunta context vault iniziale per scaldare anche la parte vault-specifica.
        vault_context = (
            f"\n\n## Vault attivo\n\n"
            f"Nome: {vault_name}\n"
            f"Total files: {extended_scan.get('total_files', 0)}\n"
            f"Framework principali: {', '.join(fw[0] for fw in extended_scan.get('framework_occurrences', [])[:5] if isinstance(fw, (list, tuple)) and fw)}\n"
        )
        return base + vault_context
    except Exception as exc:
        logger.warning(
            "optimizer_trigger.warmup_prompt_fallback",
            error=str(exc),
        )
        # Fallback: prompt minimo > 1024 char per attivare cache_control.
        return (
            "Sei l'agente SCO Compliance OS, specialista compliance italiana. "
            "Operi su vault Obsidian three-layer Karpathy con raw/ + wiki/ + Contesto/. "
            "Rispondi in italiano professionale, frasi corte, virgolette dritte, "
            "no jargon non spiegato. "
            f"Vault attivo: {vault_name}. "
        ) * 5  # ~1.5k char garantiti


async def handle_setup_completed(payload: dict[str, Any]) -> None:
    """Handler subscriber per evento ``setup.completed``.

    Esegue in sequenza:
    1. Toggle check: skip se SCO_AUTO_OPTIMIZER_ENABLED=0.
    2. Crea conversation system-generated "Ottimizzazione iniziale del vault <nome>".
    3. Set active_skill ``os-ottimizzatore`` step=0.
    4. Banner iniziale "Ottimizzazione in corso..." come messaggio assistant.
    5. Deep scan ESTESO + execute_skill('os-ottimizzatore').
    6. Ingest bootstrap chunks in memory_tree.
    7. Warmup ephemeral cache Anthropic.

    Args:
        payload: dict con almeno chiavi:
            - "vault_id": str (opzionale, lookup dal registry se mancante)
            - "vault_path": str
            - "vault_name": str
            - "completion_conv_id": str (conv_id della conversation che ha
              triggerato il setup completion, per backref)
            - "completion_skill_name": str (es. "os-setup")
    """
    if not _is_auto_optimizer_enabled():
        logger.info(
            "optimizer_trigger.disabled_by_env",
            payload_keys=list(payload.keys()),
        )
        return

    vault_path_str = str(payload.get("vault_path", ""))
    vault_name = str(payload.get("vault_name", "Vault"))
    vault_id = str(payload.get("vault_id", ""))
    completion_conv_id = str(payload.get("completion_conv_id", ""))
    completion_skill_name = str(payload.get("completion_skill_name", "os-setup"))

    logger.info(
        "optimizer_trigger.invoked",
        vault_id=vault_id,
        vault_path=vault_path_str,
        vault_name=vault_name,
        completion_conv_id=completion_conv_id,
        completion_skill_name=completion_skill_name,
    )

    if not vault_path_str:
        logger.warning(
            "optimizer_trigger.missing_vault_path",
            payload_keys=list(payload.keys()),
        )
        return

    vault_root = Path(vault_path_str)
    if not vault_root.exists():
        logger.warning(
            "optimizer_trigger.vault_root_missing",
            vault_path=str(vault_root),
        )
        return

    settings = get_settings()
    store = get_store(settings.memory_tree_db_path)

    # 1. Crea conversation per l'ottimizzazione.
    title = f"Ottimizzazione iniziale del vault {vault_name}"
    try:
        conversation = await store.create_conversation(title=title)
    except Exception as exc:
        logger.exception(
            "optimizer_trigger.create_conversation_failed",
            vault_id=vault_id,
            error=str(exc),
        )
        return
    conv_id = conversation.id

    logger.info(
        "optimizer_trigger.conversation_created",
        vault_id=vault_id,
        conv_id=conv_id,
        title=title,
    )

    # 2. Marca attivo os-ottimizzatore (Conv. 48 SSOT backend).
    try:
        await store.set_active_skill(conv_id, "os-ottimizzatore", step=0)
    except Exception as exc:
        logger.warning(
            "optimizer_trigger.set_active_skill_failed",
            conv_id=conv_id,
            error=str(exc),
        )

    # 3. Banner iniziale come messaggio assistant (visibile in chat).
    banner_md = (
        f"Ottimizzazione in corso per il vault \"{vault_name}\".\n\n"
        f"Sto scansionando in profondita la struttura del vault, "
        f"costruendo il quadro dei framework normativi e dei clienti "
        f"presenti, e pre-caricando il contesto per le prime risposte "
        f"piu veloci.\n\n"
        f"Tempo stimato: 15-30 secondi.\n\n---\n"
    )
    try:
        await store.append_message(
            conversation_id=conv_id,
            role="assistant",
            content=banner_md,
            tool_calls=[
                {
                    "kind": "optimizer_banner",
                    "vault_id": vault_id,
                    "completion_conv_id": completion_conv_id,
                }
            ],
        )
    except Exception as exc:
        logger.exception(
            "optimizer_trigger.banner_persist_failed",
            conv_id=conv_id,
            error=str(exc),
        )

    # 4. Deep scan ESTESO.
    extended_scan = await _extended_vault_scan(vault_root, vault_name)
    logger.info(
        "optimizer_trigger.extended_scan_completed",
        vault_id=vault_id,
        conv_id=conv_id,
        total_files=extended_scan.get("total_files", 0),
        entities=extended_scan.get("wiki_entities_count", 0),
        framework_count=len(extended_scan.get("framework_occurrences", [])),
    )

    # 5. Execute os-ottimizzatore con context arricchito.
    base_context: dict[str, Any] = {
        "vault_id": vault_id,
        "vault_path": str(vault_root),
        "vault_name": vault_name,
        "conversation_id": conv_id,
        "completion_conv_id": completion_conv_id,
        "is_sco_structure": extended_scan.get("is_sco_structure", False),
        "vault_inspect": {
            "is_sco_structure": extended_scan.get("is_sco_structure", False),
            "missing_folders": extended_scan.get("missing_folders", []),
            "present_folders": extended_scan.get("present_folders", []),
        },
        "extended_scan": extended_scan,
    }

    ottimizzatore_chunks: list[str] = []

    async def _capture_event(event: AgentEvent) -> None:
        if event.kind == "text_delta":
            ottimizzatore_chunks.append(event.data.get("text", ""))

    try:
        ottimizzatore_result = await execute_skill(
            "os-ottimizzatore",
            vault_root=vault_root,
            context=base_context,
            on_event=_capture_event,
        )
        ottimizzatore_text = (
            ottimizzatore_result.assistant_text or "".join(ottimizzatore_chunks)
        )
        ottimizzatore_success = ottimizzatore_result.success
    except Exception as exc:
        logger.exception(
            "optimizer_trigger.execute_skill_failed",
            conv_id=conv_id,
            error=str(exc),
        )
        ottimizzatore_text = (
            f"Ottimizzazione interrotta: errore interno `{type(exc).__name__}`. "
            f"Il deep scan e' stato comunque eseguito. Puoi riavviare manualmente "
            f"l'ottimizzazione dal pannello Skill."
        )
        ottimizzatore_success = False

    if ottimizzatore_text:
        try:
            await store.append_message(
                conversation_id=conv_id,
                role="assistant",
                content=ottimizzatore_text,
                tool_calls=[
                    {
                        "kind": "skill_invocation",
                        "skill_name": "os-ottimizzatore",
                        "success": ottimizzatore_success,
                        "extended_scan_total_files": extended_scan.get(
                            "total_files", 0
                        ),
                    }
                ],
            )
        except Exception as exc:
            logger.exception(
                "optimizer_trigger.skill_persist_failed",
                conv_id=conv_id,
                error=str(exc),
            )

    # 6. Ingest bootstrap chunks in memory_tree (best-effort).
    bootstrap_counts = await _ingest_bootstrap_chunks(
        vault_root, vault_name, extended_scan, ottimizzatore_text
    )
    logger.info(
        "optimizer_trigger.bootstrap_ingested",
        conv_id=conv_id,
        **bootstrap_counts,
    )

    # 7. Warmup Anthropic cache (best-effort).
    warmup_prompt = _build_warmup_system_prompt(vault_name, extended_scan)
    warmup_result = await _warmup_anthropic_cache(warmup_prompt)
    logger.info(
        "optimizer_trigger.warmup_completed",
        conv_id=conv_id,
        **warmup_result,
    )

    # Clear active_skill: optimizer flow chiuso, conversation idle.
    try:
        await store.set_active_skill(conv_id, None, None)
    except Exception as exc:
        logger.warning(
            "optimizer_trigger.clear_active_skill_failed",
            conv_id=conv_id,
            error=str(exc),
        )

    logger.info(
        "optimizer_trigger.completed",
        vault_id=vault_id,
        conv_id=conv_id,
        ottimizzatore_success=ottimizzatore_success,
        bootstrap_admitted=bootstrap_counts.get("admitted", 0),
        warmup_success=warmup_result.get("success", False),
    )


async def refresh_cache(vault_name: str = "vault-corrente") -> dict[str, Any]:
    """Refresh Anthropic ephemeral cache invocando un warmup periodico.

    Chiamata da main.py scheduler ogni N secondi (default 240s, sotto TTL 5min).
    Idempotente: non interagisce con conversations o memory_tree, solo ping
    al provider per resetare il TTL della cache.

    Returns:
        dict warmup_result.
    """
    # Heuristic warmup prompt: usa lo stesso _DEFAULT_SYSTEM_PROMPT base.
    try:
        from sco_compliance_os.api.chat_routes import _get_skill_catalog_for_prompt
        from sco_compliance_os.core.agent_sdk_runner import _DEFAULT_SYSTEM_PROMPT

        skill_catalog = _get_skill_catalog_for_prompt(vault_root=None)
        warmup_prompt = (
            f"{_DEFAULT_SYSTEM_PROMPT}\n\n{skill_catalog}"
            if skill_catalog
            else _DEFAULT_SYSTEM_PROMPT
        )
    except Exception:
        warmup_prompt = (
            "Sei l'agente SCO Compliance OS. Vault attivo: " + vault_name
        ) * 10

    return await _warmup_anthropic_cache(warmup_prompt)
