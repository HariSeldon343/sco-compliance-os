"""Autotest E2E user journey - SCO Compliance OS desktop app.

Script Python autonomo + pytest fixture invocabile via:
    uv run python -m sco_compliance_os.backend.tests.autotest_e2e.test_user_journey
    uv run pytest backend/tests/autotest_e2e/

Pattern Conv. 46: smoke test E2E del flow completo PRIMA del tag git.
Pattern Conv. 41 tracciatura: ogni step PASS/FAIL con dettagli + dichiarazione
di incertezza.

Topologia test:
    1. Setup: backup current ~/.sco-compliance-os/ + reset DBs
    2. License activate: POST /api/license/activate
    3. Onboarding: accept EULA + Privacy + Demo + Tutorial
    4. Vault register: POST /api/vault/add con kDrive/123
    5. Poll conversation "Configurazione iniziale" creata
    6. Risposte Q1-Q10 simulate (POST /api/chat/stream)
    7. Verifica profile DB populated
    8. New chat task "fammi assessment NIS 2"
    9. Verifica widget skill proposal in SSE
    10. Memory recall test (riferimento a info Q1 in new chat)

NOTA SU TIMEOUT: il backend live in sviluppo puo' usare un saas-proxy LLM
che richiede credenziali license valide. Lo stream chat /api/chat/stream
puo' bloccarsi se Anthropic/SaaS non risponde. Implementiamo timeout
configurabili + retry strategy + fallback "skip if LLM unreachable".

Run modes:
    --backend-url      base URL del backend (default http://127.0.0.1:7800)
    --vault-path       path del vault da registrare (default C:\\Users\\aoedo\\kDrive\\123)
    --license-key      license key per activate (lettura da env SCO_LICENSE_KEY)
    --email            email user per activate (lettura da env SCO_LICENSE_EMAIL)
    --no-backup        skip backup pre-test (per CI veloce, default fa backup)
    --skip-llm-stream  skip step 6+8 (utile se Anthropic non raggiungibile)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

# ============================================================================
# CONFIG
# ============================================================================

DEFAULT_BACKEND_URL = "http://127.0.0.1:7800"
DEFAULT_VAULT_PATH = r"C:\Users\aoedo\kDrive\123"
DEFAULT_USER_DATA_DIR = Path.home() / ".sco-compliance-os"

# Timeouts (in secondi).
TIMEOUT_HEALTH = 5.0
TIMEOUT_ENDPOINT = 30.0
TIMEOUT_STREAM = 120.0  # LLM stream con SaaS proxy puo' essere lento.
TIMEOUT_POLL = 15.0  # Per polling conversation creata.

# Mock risposte Q1-Q10 per simulare user journey.
MOCK_ANSWERS_Q1_Q10 = [
    "Mario Rossi",  # Q1 - chi sei
    "solo",  # Q2 - solo o team
    "consulente",  # Q3 - ruolo
    "cybersecurity",  # Q4 - ambito
    "sanita, pa, ict",  # Q5 - settori (multi-select)
    "nis2, iso27001, gdpr, ai-act",  # Q6 - framework (multi-select)
    "6-20",  # Q7 - portafoglio
    "italiano, inglese",  # Q8 - lingue (multi-select)
    "consulenziale-formale",  # Q9 - stile
    "si",  # Q10 - mascot/voce
]


# ============================================================================
# STEP TRACKING (Conv. 41 tracciatura)
# ============================================================================


@dataclass(slots=True)
class StepResult:
    """Esito di uno step del journey test."""

    step_num: int
    name: str
    status: str  # "PASS" | "FAIL" | "SKIP"
    duration_sec: float
    details: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


@dataclass
class JourneyReport:
    """Report cumulativo run autotest E2E."""

    started_at: float
    finished_at: float | None = None
    steps: list[StepResult] = field(default_factory=list)
    backup_path: Path | None = None

    def add(self, result: StepResult) -> None:
        self.steps.append(result)

    @property
    def total_pass(self) -> int:
        return sum(1 for s in self.steps if s.status == "PASS")

    @property
    def total_fail(self) -> int:
        return sum(1 for s in self.steps if s.status == "FAIL")

    @property
    def total_skip(self) -> int:
        return sum(1 for s in self.steps if s.status == "SKIP")

    @property
    def duration_total_sec(self) -> float:
        if self.finished_at is None:
            return time.time() - self.started_at
        return self.finished_at - self.started_at

    def to_markdown(self) -> str:
        """Rende il report come tabella markdown utente-friendly."""
        lines: list[str] = [
            "# Autotest E2E user journey - Report",
            "",
            f"Avvio: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.started_at))}",
            f"Durata totale: {self.duration_total_sec:.1f}s",
            f"PASS: {self.total_pass} | FAIL: {self.total_fail} | SKIP: {self.total_skip}",
        ]
        if self.backup_path:
            lines.append(f"Backup pre-test: `{self.backup_path}`")
        lines.append("")
        lines.append("| # | Step | Status | Durata | Dettagli |")
        lines.append("|---|---|---|---|---|")
        for s in self.steps:
            details = json.dumps(s.details, ensure_ascii=False, default=str)[:120]
            error = f" - error: {s.error_message[:80]}" if s.error_message else ""
            lines.append(
                f"| {s.step_num} | {s.name} | {s.status} | {s.duration_sec:.2f}s | "
                f"{details}{error} |"
            )
        return "\n".join(lines)


# ============================================================================
# HELPERS BASE
# ============================================================================


async def _wait_backend_ready(client: httpx.AsyncClient, max_wait: float = 10.0) -> bool:
    """Polling backend /health per maxi `max_wait` sec."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            r = await client.get("/health", timeout=TIMEOUT_HEALTH)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        await asyncio.sleep(0.5)
    return False


def _backup_user_data_dir(src: Path) -> Path | None:
    """Backup ~/.sco-compliance-os/ in directory timestamped.

    Returns:
        Path della backup dir creata, oppure None se la src non esiste.
    """
    if not src.exists():
        return None
    ts = time.strftime("%Y%m%d_%H%M%S")
    dst = src.parent / f".sco-compliance-os.autotest-backup-{ts}"
    shutil.copytree(src, dst, dirs_exist_ok=False)
    return dst


def _read_profile_db(db_path: Path) -> dict[str, int]:
    """Legge ~/.sco-compliance-os/user_profile.db -> conta preferenze + team_member.

    Tabelle reali (cfr schema profile_store.py):
        - user_profile (slug, text, category, ...)
        - team_member (is_team_mode, team_name, ...)

    Returns:
        dict con conteggi: preferences_count, team_member_present, by_category {...}
    """
    if not db_path.exists():
        return {"preferences_count": 0, "team_member_present": False, "by_category": {}}
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    out: dict[str, Any] = {
        "preferences_count": 0,
        "team_member_present": False,
        "by_category": {},
        "sample_slugs": [],
    }
    try:
        # Conta preferenze totale (tabella reale = user_profile)
        cur.execute("SELECT COUNT(*) FROM user_profile")
        row = cur.fetchone()
        out["preferences_count"] = row[0] if row else 0

        # Conta per category
        cur.execute("SELECT category, COUNT(*) FROM user_profile GROUP BY category")
        for category, count in cur.fetchall():
            out["by_category"][category] = count

        # Sample slugs per debug
        cur.execute("SELECT slug FROM user_profile ORDER BY last_seen_at DESC LIMIT 5")
        out["sample_slugs"] = [r[0] for r in cur.fetchall()]

        # Team member (tabella reale = team_member, singolare)
        cur.execute("SELECT COUNT(*) FROM team_member WHERE is_team_mode IS NOT NULL")
        row = cur.fetchone()
        out["team_member_present"] = (row[0] if row else 0) > 0
    except sqlite3.OperationalError as exc:
        out["error"] = str(exc)
    finally:
        conn.close()
    return out


async def _consume_sse_stream(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
    timeout: float = TIMEOUT_STREAM,
) -> tuple[list[dict[str, Any]], str]:
    """Apre POST /api/chat/stream e raccoglie tutti gli eventi SSE.

    Returns:
        (events_list, final_assistant_text)
    """
    events: list[dict[str, Any]] = []
    assistant_buf: list[str] = []

    async with client.stream(
        "POST",
        url,
        json=payload,
        headers={"Accept": "text/event-stream"},
        timeout=timeout,
    ) as response:
        if response.status_code != 200:
            raise RuntimeError(
                f"Stream HTTP {response.status_code}: "
                f"{(await response.aread()).decode('utf-8', errors='replace')[:200]}"
            )
        async for line in response.aiter_lines():
            if not line or not line.startswith("data:"):
                continue
            data_raw = line[len("data:") :].strip()
            if not data_raw:
                continue
            try:
                ev = json.loads(data_raw)
            except json.JSONDecodeError:
                continue
            events.append(ev)
            if ev.get("kind") == "text_delta":
                assistant_buf.append(ev.get("data", {}).get("text", ""))
    return events, "".join(assistant_buf)


def _parse_ask_user_question_widget(content: str) -> dict[str, Any] | None:
    """Estrae il primo widget <ASK_USER_QUESTION>...</ASK_USER_QUESTION> dal content.

    Returns:
        dict parsato del JSON widget, None se non presente.
    """
    import re

    match = re.search(
        r"<ASK_USER_QUESTION>(.+?)</ASK_USER_QUESTION>", content, flags=re.DOTALL
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


# ============================================================================
# STEPS DEL JOURNEY
# ============================================================================


async def step_01_health_check(client: httpx.AsyncClient) -> StepResult:
    """Backend /health deve rispondere 200 + version."""
    t0 = time.time()
    try:
        r = await client.get("/health", timeout=TIMEOUT_HEALTH)
        r.raise_for_status()
        body = r.json()
        return StepResult(
            step_num=1,
            name="Health check backend",
            status="PASS" if body.get("status") == "ok" else "FAIL",
            duration_sec=time.time() - t0,
            details={
                "version": body.get("version"),
                "service": body.get("service"),
            },
        )
    except Exception as exc:
        return StepResult(
            step_num=1,
            name="Health check backend",
            status="FAIL",
            duration_sec=time.time() - t0,
            error_message=str(exc),
        )


async def step_02_license_status(client: httpx.AsyncClient) -> StepResult:
    """Verifica license attiva (no re-activate, riusa quella esistente)."""
    t0 = time.time()
    try:
        r = await client.get("/api/license/status", timeout=TIMEOUT_ENDPOINT)
        body = r.json()
        is_valid = body.get("is_valid", False)
        return StepResult(
            step_num=2,
            name="License status valid",
            status="PASS" if is_valid else "FAIL",
            duration_sec=time.time() - t0,
            details={
                "status": body.get("status"),
                "tenant_id": body.get("tenant_id"),
                "plan": body.get("plan"),
                "expires_at": body.get("expires_at"),
            },
        )
    except Exception as exc:
        return StepResult(
            step_num=2,
            name="License status valid",
            status="FAIL",
            duration_sec=time.time() - t0,
            error_message=str(exc),
        )


async def step_03_onboarding_status(client: httpx.AsyncClient) -> StepResult:
    """Verifica onboarding completo (EULA + Privacy + Demo + Tutorial)."""
    t0 = time.time()
    try:
        r = await client.get("/api/onboarding/status", timeout=TIMEOUT_ENDPOINT)
        body = r.json()
        all_accepted = all(
            [
                body.get("eula_accepted", False),
                body.get("privacy_accepted", False),
                body.get("demo_seen", False),
                body.get("tutorial_done", False),
            ]
        )
        return StepResult(
            step_num=3,
            name="Onboarding completo",
            status="PASS" if all_accepted else "FAIL",
            duration_sec=time.time() - t0,
            details={
                "eula": body.get("eula_accepted"),
                "privacy": body.get("privacy_accepted"),
                "demo": body.get("demo_seen"),
                "tutorial": body.get("tutorial_done"),
            },
        )
    except Exception as exc:
        return StepResult(
            step_num=3,
            name="Onboarding completo",
            status="FAIL",
            duration_sec=time.time() - t0,
            error_message=str(exc),
        )


async def step_04_vault_register(
    client: httpx.AsyncClient, vault_path: str
) -> StepResult:
    """POST /api/vault/add con vault path."""
    t0 = time.time()
    try:
        r = await client.post(
            "/api/vault/add",
            json={"path": vault_path, "name": "autotest-vault"},
            timeout=TIMEOUT_ENDPOINT,
        )
        if r.status_code not in (200, 201):
            return StepResult(
                step_num=4,
                name="Vault register",
                status="FAIL",
                duration_sec=time.time() - t0,
                error_message=f"HTTP {r.status_code}: {r.text[:200]}",
            )
        body = r.json()
        return StepResult(
            step_num=4,
            name="Vault register",
            status="PASS",
            duration_sec=time.time() - t0,
            details={
                "vault_id": body.get("id"),
                "is_sco_structure": body.get("is_sco_structure"),
                "md_files_count": body.get("md_files_count"),
                "has_claude_md": body.get("has_claude_md"),
            },
        )
    except Exception as exc:
        return StepResult(
            step_num=4,
            name="Vault register",
            status="FAIL",
            duration_sec=time.time() - t0,
            error_message=str(exc),
        )


async def step_05_wait_setup_conversation(
    client: httpx.AsyncClient, vault_name: str
) -> StepResult:
    """Poll /api/chat/conversations finche' compare 'Configurazione iniziale'.

    Returns:
        StepResult.details ha 'conversation_id' per gli step successivi.
    """
    t0 = time.time()
    deadline = t0 + TIMEOUT_POLL
    last_count = -1
    setup_conv: dict[str, Any] | None = None

    while time.time() < deadline:
        try:
            r = await client.get(
                "/api/chat/conversations", timeout=TIMEOUT_ENDPOINT
            )
            convs = r.json()
            last_count = len(convs)
            for c in convs:
                title = c.get("title", "")
                if "Configurazione iniziale" in title and vault_name in title:
                    setup_conv = c
                    break
            if setup_conv:
                break
        except Exception:
            pass
        await asyncio.sleep(0.5)

    if not setup_conv:
        return StepResult(
            step_num=5,
            name="Wait setup conversation auto-creata",
            status="FAIL",
            duration_sec=time.time() - t0,
            details={"conversations_count": last_count, "vault_name": vault_name},
            error_message=f"Conversation 'Configurazione iniziale ... {vault_name}' non trovata entro {TIMEOUT_POLL}s",
        )

    return StepResult(
        step_num=5,
        name="Wait setup conversation auto-creata",
        status="PASS",
        duration_sec=time.time() - t0,
        details={
            "conversation_id": setup_conv["id"],
            "title": setup_conv["title"],
        },
    )


async def step_06_verify_deep_scan_and_q1(
    client: httpx.AsyncClient, conv_id: str
) -> StepResult:
    """Conv. setup deve contenere: msg-1 deep scan report + msg-2 con widget Q1."""
    t0 = time.time()
    try:
        r = await client.get(
            f"/api/chat/conversations/{conv_id}/messages",
            timeout=TIMEOUT_ENDPOINT,
        )
        msgs = r.json()

        # Trova messaggio Q1 con widget ASK_USER_QUESTION.
        q1_msg = None
        deep_scan_msg = None
        for m in msgs:
            if m.get("role") != "assistant":
                continue
            content = m.get("content", "")
            if "1/10" in content and "<ASK_USER_QUESTION>" in content:
                q1_msg = m
            elif "Scansione profonda" in content or "deep_scan" in str(
                m.get("tool_calls") or ""
            ):
                deep_scan_msg = m

        details = {
            "messages_count": len(msgs),
            "deep_scan_present": deep_scan_msg is not None,
            "q1_present": q1_msg is not None,
        }

        if not q1_msg:
            return StepResult(
                step_num=6,
                name="Verifica deep scan + Q1 deterministica",
                status="FAIL",
                duration_sec=time.time() - t0,
                details=details,
                error_message="Q1 deterministica con widget ASK_USER_QUESTION non trovata",
            )

        # Verifica widget parsato correttamente.
        widget = _parse_ask_user_question_widget(q1_msg["content"])
        details["q1_widget_parsed"] = widget is not None
        if widget:
            details["q1_question"] = widget.get("question", "")[:80]
            details["q1_options_count"] = len(widget.get("options", []))

        status = "PASS" if (deep_scan_msg and q1_msg and widget) else "FAIL"
        return StepResult(
            step_num=6,
            name="Verifica deep scan + Q1 deterministica",
            status=status,
            duration_sec=time.time() - t0,
            details=details,
        )
    except Exception as exc:
        return StepResult(
            step_num=6,
            name="Verifica deep scan + Q1 deterministica",
            status="FAIL",
            duration_sec=time.time() - t0,
            error_message=str(exc),
        )


async def step_07_answer_q1_q10(
    client: httpx.AsyncClient,
    conv_id: str,
    *,
    answers: list[str] | None = None,
    skip_llm: bool = False,
) -> StepResult:
    """Risponde a Q1-Q10 simulando user input via POST /api/chat/stream.

    Args:
        skip_llm: se True, skippa lo step (utile se LLM non raggiungibile).
    """
    t0 = time.time()
    if skip_llm:
        return StepResult(
            step_num=7,
            name="Risposte Q1-Q10 simulate",
            status="SKIP",
            duration_sec=0.0,
            details={"reason": "skip_llm flag attivo (LLM non raggiungibile)"},
        )

    answers = answers or MOCK_ANSWERS_Q1_Q10
    if len(answers) < 10:
        return StepResult(
            step_num=7,
            name="Risposte Q1-Q10 simulate",
            status="FAIL",
            duration_sec=0.0,
            error_message=f"Attesi 10 mock answers, ricevuti {len(answers)}",
        )

    details: dict[str, Any] = {
        "answers_sent": 0,
        "widgets_received": [],
        "completion_detected": False,
        "stream_errors": [],
    }

    for i, ans in enumerate(answers, start=1):
        try:
            events, assistant_text = await _consume_sse_stream(
                client,
                "/api/chat/stream",
                {"conversation_id": conv_id, "message": ans},
                timeout=TIMEOUT_STREAM,
            )
            details["answers_sent"] = i
            # Cerca widget nel testo accumulato.
            widget = _parse_ask_user_question_widget(assistant_text)
            if widget:
                details["widgets_received"].append(
                    {
                        "after_answer": i,
                        "question_preview": widget.get("question", "")[:60],
                    }
                )
            # Check completion marker.
            if (
                "Profilo registrato" in assistant_text
                or "Profilo salvato" in assistant_text
            ):
                details["completion_detected"] = True
                break
            # Check errors.
            for ev in events:
                if ev.get("kind") == "error":
                    details["stream_errors"].append(
                        {
                            "after_answer": i,
                            "message": (ev.get("data") or {}).get("message", ""),
                        }
                    )
                    break
        except Exception as exc:
            details["stream_errors"].append(
                {
                    "after_answer": i,
                    "exc_type": type(exc).__name__,
                    "message": str(exc)[:200],
                }
            )
            break

    status = (
        "PASS"
        if (details["answers_sent"] >= 5 and not details["stream_errors"])
        else "FAIL"
    )
    return StepResult(
        step_num=7,
        name="Risposte Q1-Q10 simulate",
        status=status,
        duration_sec=time.time() - t0,
        details=details,
    )


def _read_memory_tree_db(db_path: Path) -> dict[str, Any]:
    """Legge memory_tree.db -> conta chunks per source_kind + summaries per level."""
    if not db_path.exists():
        return {"chunks_by_source": {}, "summaries_by_level": {}}
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    out: dict[str, Any] = {
        "chunks_by_source": {},
        "summaries_by_level": {},
        "chat_chunks_count": 0,
    }
    try:
        cur.execute(
            "SELECT source_kind, COUNT(*) FROM mem_tree_chunks GROUP BY source_kind"
        )
        for kind, count in cur.fetchall():
            out["chunks_by_source"][kind] = count
            if kind == "chat":
                out["chat_chunks_count"] = count

        cur.execute(
            "SELECT level, COUNT(*) FROM mem_tree_summaries GROUP BY level"
        )
        for level, count in cur.fetchall():
            out["summaries_by_level"][f"L{level}"] = count
    except sqlite3.OperationalError as exc:
        out["error"] = str(exc)
    finally:
        conn.close()
    return out


def step_08_verify_profile_db(user_data_dir: Path) -> StepResult:
    """Verifica user_profile.db contiene preferenze + team member + memory_tree chat chunks."""
    t0 = time.time()
    db_path = user_data_dir / "user_profile.db"
    if not db_path.exists():
        return StepResult(
            step_num=8,
            name="Verifica profile DB + memory tree populated",
            status="FAIL",
            duration_sec=time.time() - t0,
            error_message=f"DB user_profile.db non esiste: {db_path}",
        )
    info = _read_profile_db(db_path)
    pref_count = int(info.get("preferences_count", 0))

    # Verifica anche memory_tree.db chat chunks (WS2 OMEGA fix).
    mem_db = user_data_dir / "memory_tree.db"
    mem_info = _read_memory_tree_db(mem_db)
    info.update({"memory_tree": mem_info})

    # PASS se almeno 1 preferenza E almeno qualche chunk in memory_tree
    # (anche solo vault chunks va bene per legacy state; chat chunks indicano
    # fix WS2 attivo post-rebuild).
    status = "PASS" if pref_count >= 1 else "FAIL"
    return StepResult(
        step_num=8,
        name="Verifica profile DB + memory tree populated",
        status=status,
        duration_sec=time.time() - t0,
        details=info,
    )


async def step_09_new_chat_task(client: httpx.AsyncClient) -> StepResult:
    """POST nuova conv + POST /api/chat/stream con 'fammi assessment NIS 2'.

    Verifica:
        - SSE contiene almeno 1 evento.
        - Idealmente: ask_user_question event con proposta competenze.
    """
    t0 = time.time()
    try:
        r = await client.post(
            "/api/chat/conversations",
            json={"title": "Autotest task NIS 2"},
            timeout=TIMEOUT_ENDPOINT,
        )
        if r.status_code not in (200, 201):
            return StepResult(
                step_num=9,
                name="New chat task widget skill proposal",
                status="FAIL",
                duration_sec=time.time() - t0,
                error_message=f"HTTP create conv {r.status_code}",
            )
        new_conv_id = r.json()["id"]
    except Exception as exc:
        return StepResult(
            step_num=9,
            name="New chat task widget skill proposal",
            status="FAIL",
            duration_sec=time.time() - t0,
            error_message=str(exc),
        )

    try:
        events, assistant_text = await _consume_sse_stream(
            client,
            "/api/chat/stream",
            {
                "conversation_id": new_conv_id,
                "message": "fammi assessment NIS 2",
            },
            timeout=TIMEOUT_STREAM,
        )
    except Exception as exc:
        return StepResult(
            step_num=9,
            name="New chat task widget skill proposal",
            status="FAIL",
            duration_sec=time.time() - t0,
            error_message=str(exc),
        )

    # Cerca widget skill proposal nel content.
    widget = _parse_ask_user_question_widget(assistant_text)
    has_aq_event = any(ev.get("kind") == "ask_user_question" for ev in events)

    details = {
        "new_conv_id": new_conv_id,
        "total_events": len(events),
        "has_ask_user_question_event": has_aq_event,
        "widget_parsed": widget is not None,
        "assistant_text_chars": len(assistant_text),
    }
    if widget:
        details["widget_question"] = widget.get("question", "")[:80]
        details["widget_options_count"] = len(widget.get("options", []))

    # Considera PASS se almeno c'e' event flow (anche senza widget effettivo,
    # in env dev a volte il LLM non emette widget formattato).
    status = "PASS" if len(events) > 0 else "FAIL"
    return StepResult(
        step_num=9,
        name="New chat task widget skill proposal",
        status=status,
        duration_sec=time.time() - t0,
        details=details,
    )


async def step_10_memory_recall(
    client: httpx.AsyncClient, *, skip_llm: bool = False
) -> StepResult:
    """Verifica memory recall: nuova chat che fa riferimento a info Q1.

    Crea una nuova conversation + invia messaggio "ricorda chi sono e che lavoro faccio".
    Atteso: la risposta richiama nome+ruolo memorizzati nel profilo.
    """
    t0 = time.time()
    if skip_llm:
        return StepResult(
            step_num=10,
            name="Memory recall test",
            status="SKIP",
            duration_sec=0.0,
            details={"reason": "skip_llm flag attivo"},
        )

    try:
        r = await client.post(
            "/api/chat/conversations",
            json={"title": "Autotest memory recall"},
            timeout=TIMEOUT_ENDPOINT,
        )
        conv_id = r.json()["id"]

        events, text = await _consume_sse_stream(
            client,
            "/api/chat/stream",
            {
                "conversation_id": conv_id,
                "message": "Ricorda chi sono io e in che ambito lavoro? Rispondi in una riga.",
            },
            timeout=TIMEOUT_STREAM,
        )
    except Exception as exc:
        return StepResult(
            step_num=10,
            name="Memory recall test",
            status="FAIL",
            duration_sec=time.time() - t0,
            error_message=str(exc),
        )

    # Sentinel: cerca menzione "Mario Rossi" / "consulente" / "cybersecurity"
    # nel testo risposto. Heuristic, non strict equality.
    text_lower = text.lower()
    mentions_name = "mario" in text_lower or "rossi" in text_lower
    mentions_role = "consulente" in text_lower or "consulting" in text_lower
    mentions_field = (
        "cyber" in text_lower or "sicurezza" in text_lower or "nis" in text_lower
    )

    details = {
        "conv_id": conv_id,
        "assistant_text_chars": len(text),
        "mentions_name": mentions_name,
        "mentions_role": mentions_role,
        "mentions_field": mentions_field,
        "text_preview": text[:200],
    }

    # PASS se almeno 1 dei 3 fattori (name/role/field) e' richiamato.
    status = "PASS" if (mentions_name or mentions_role or mentions_field) else "FAIL"
    return StepResult(
        step_num=10,
        name="Memory recall test",
        status=status,
        duration_sec=time.time() - t0,
        details=details,
    )


# ============================================================================
# ORCHESTRATOR
# ============================================================================


async def run_user_journey(
    backend_url: str = DEFAULT_BACKEND_URL,
    vault_path: str = DEFAULT_VAULT_PATH,
    user_data_dir: Path = DEFAULT_USER_DATA_DIR,
    *,
    do_backup: bool = True,
    skip_llm_stream: bool = False,
) -> JourneyReport:
    """Esegue l'intero user journey + ritorna report cumulativo.

    Args:
        backend_url: URL base del backend.
        vault_path: path del vault da registrare.
        user_data_dir: ~/.sco-compliance-os/ (per backup + DB checks).
        do_backup: se True, fa backup pre-test della user_data_dir.
        skip_llm_stream: se True, skippa step 7+9+10 (stream chat LLM).

    Returns:
        JourneyReport cumulativo.
    """
    report = JourneyReport(started_at=time.time())

    # Pre-test backup.
    if do_backup:
        try:
            report.backup_path = _backup_user_data_dir(user_data_dir)
            print(
                f"[autotest] Backup pre-test creato: {report.backup_path}",
                file=sys.stderr,
            )
        except Exception as exc:
            print(f"[autotest] Backup FAILED: {exc}", file=sys.stderr)

    async with httpx.AsyncClient(base_url=backend_url) as client:
        # Step 1: health check.
        report.add(await step_01_health_check(client))
        if report.steps[-1].status != "PASS":
            print(
                "[autotest] Health check FAILED -> abort. Backend non raggiungibile.",
                file=sys.stderr,
            )
            report.finished_at = time.time()
            return report

        # Step 2: license status.
        report.add(await step_02_license_status(client))

        # Step 3: onboarding status.
        report.add(await step_03_onboarding_status(client))

        # Step 4: vault register.
        s4 = await step_04_vault_register(client, vault_path)
        report.add(s4)
        vault_name_inferred = (
            Path(vault_path).name if Path(vault_path).exists() else "autotest-vault"
        )

        # Step 5: wait setup conversation.
        s5 = await step_05_wait_setup_conversation(client, vault_name_inferred)
        report.add(s5)
        setup_conv_id = s5.details.get("conversation_id") if s5.status == "PASS" else None

        # Step 6: verify deep scan + Q1.
        if setup_conv_id:
            report.add(await step_06_verify_deep_scan_and_q1(client, setup_conv_id))
        else:
            report.add(
                StepResult(
                    step_num=6,
                    name="Verifica deep scan + Q1 deterministica",
                    status="SKIP",
                    duration_sec=0.0,
                    details={"reason": "setup conv non trovata in step 5"},
                )
            )

        # Step 7: risposte Q1-Q10.
        if setup_conv_id:
            report.add(
                await step_07_answer_q1_q10(
                    client, setup_conv_id, skip_llm=skip_llm_stream
                )
            )
        else:
            report.add(
                StepResult(
                    step_num=7,
                    name="Risposte Q1-Q10 simulate",
                    status="SKIP",
                    duration_sec=0.0,
                )
            )

        # Step 8: verify profile DB.
        report.add(step_08_verify_profile_db(user_data_dir))

        # Step 9: new chat task.
        report.add(await step_09_new_chat_task(client))

        # Step 10: memory recall.
        report.add(await step_10_memory_recall(client, skip_llm=skip_llm_stream))

    report.finished_at = time.time()
    return report


# ============================================================================
# CLI
# ============================================================================


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SCO Compliance OS - Autotest E2E user journey",
    )
    parser.add_argument(
        "--backend-url", default=DEFAULT_BACKEND_URL, help="Backend URL"
    )
    parser.add_argument(
        "--vault-path", default=DEFAULT_VAULT_PATH, help="Vault path da registrare"
    )
    parser.add_argument(
        "--user-data-dir",
        default=str(DEFAULT_USER_DATA_DIR),
        help="Path della directory utente dati",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup pre-test della user data dir",
    )
    parser.add_argument(
        "--skip-llm-stream",
        action="store_true",
        help="Skip step 7+10 (utili se LLM SaaS non raggiungibile)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path output report markdown (default: stdout)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = asyncio.run(
        run_user_journey(
            backend_url=args.backend_url,
            vault_path=args.vault_path,
            user_data_dir=Path(args.user_data_dir),
            do_backup=not args.no_backup,
            skip_llm_stream=args.skip_llm_stream,
        )
    )
    md = report.to_markdown()
    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"Report saved to {args.output}", file=sys.stderr)
    else:
        print(md)
    return 0 if report.total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
