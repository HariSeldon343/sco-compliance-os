"""Decision engine del Subconscious tick loop.

Architettura (clean-room replica OpenHuman, da docs pubbliche):

- Input: :class:`SubconsciousContext` = snapshot leggero del contesto agente
  (ultimi chunks 5 min + hot topics + active triggers).
- Reasoner: Claude Haiku 4.5 (modello fast, low cost) con system prompt strict
  JSON output.
- Output: :class:`DecisionOutcome` con enum :class:`Decision` (SKIP|ACT|ESCALATE)
  + rationale + proposed_action opzionale.

Vincoli OpenHuman (replica fedele):
1. **Two-models split**: ACT = azione locale read-only safe (es. summarize,
   re-index). ESCALATE = task profondo che richiede approvazione utente
   (NON eseguito automaticamente in v0.2.0).
2. **Cost-aware**: se il contesto e' vuoto (no recent chunks, no triggers,
   no hot topics), short-circuit a SKIP senza chiamata LLM.
3. **Rate limit**: max 1 deep LLM call per tick (no chaining auto).
4. **Privacy default OFF**: Subconscious enabled solo via opt-in esplicito
   (vedi config.py ``subconscious_enabled``).

Note v0.2.0:
- Le azioni ACT in v0.2.0 sono solo **proposte** registrate in activity log.
  Nessuna scrittura automatica su DB / vault / file in v0.2.0. Antonio
  approva via UI futuro (Wave 5+).
- ESCALATE produce ``proposed_action`` strutturato che il futuro UI mostra
  come "task suggerito da approvare".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

from sco_compliance_os.config import get_settings

logger = structlog.get_logger(__name__)


class Decision(StrEnum):
    """Esito decisionale del subconscious tick.

    Valori:
    - SKIP: contesto irrilevante, nessuna azione necessaria.
    - ACT: azione locale read-only safe proposta (registrata in activity log).
    - ESCALATE: serve reasoning profondo, propone task all'utente.
    """

    SKIP = "SKIP"
    ACT = "ACT"
    ESCALATE = "ESCALATE"


@dataclass(slots=True)
class SubconsciousContext:
    """Snapshot leggero del contesto agente al momento del tick.

    Tutti i campi hanno default vuoto: se tutti i campi sono vuoti,
    il decision engine short-circuit a SKIP senza chiamata LLM (cost-aware).
    """

    recent_chunks: list[dict[str, Any]] = field(default_factory=list)
    """Ultimi N chunks ingestiti nei 5 minuti precedenti (id + snippet + source)."""

    hot_topics: list[dict[str, Any]] = field(default_factory=list)
    """Top 10 chunks per hotness score (decay temporale)."""

    active_triggers: list[dict[str, Any]] = field(default_factory=list)
    """Triggers pending da connettori (Gmail/GCal/GDrive webhook o polling)."""

    def is_empty(self) -> bool:
        """True se nessun input significativo (short-circuit SKIP)."""
        return not (self.recent_chunks or self.hot_topics or self.active_triggers)

    def summary_for_prompt(self) -> str:
        """Compone snippet markdown sintetico per il system prompt.

        Limita ai primi 5 elementi per lista per tenere bassi i token di input.
        """
        parts: list[str] = []
        if self.recent_chunks:
            parts.append("## Recent chunks (last 5 min)")
            for c in self.recent_chunks[:5]:
                snippet = str(c.get("snippet", ""))[:200]
                parts.append(f"- [{c.get('source_type', '?')}] {snippet}")
        if self.hot_topics:
            parts.append("\n## Hot topics")
            for h in self.hot_topics[:5]:
                title = str(h.get("title", ""))[:80]
                parts.append(f"- {title} (hotness={h.get('hotness', 0):.2f})")
        if self.active_triggers:
            parts.append("\n## Active triggers")
            for t in self.active_triggers[:5]:
                kind = t.get("event_type", "?")
                conn = t.get("connector", "?")
                if kind == "deadline":
                    title = str(t.get("title", "?"))[:80]
                    days = t.get("days_remaining", "?")
                    due = t.get("due_date", "?")
                    parts.append(f"- [scadenza] {title} — tra {days} giorni (il {due})")
                else:
                    parts.append(f"- {conn}/{kind}")
        return "\n".join(parts) or "(empty context)"


@dataclass(slots=True)
class DecisionOutcome:
    """Esito strutturato di un tick subconscious."""

    decision: Decision
    rationale: str
    proposed_action: dict[str, Any] | None = None
    used_llm: bool = False
    """True se il LLM e' stato chiamato (False per short-circuit SKIP)."""


_SYSTEM_PROMPT = """\
Sei il subconscious di Antonio Silvestro Amodeo, consulente compliance senior.
Lavori in background ogni 5 minuti analizzando lo stato del suo assistente.

Il tuo compito: decidere se intervenire. Tre opzioni esclusive.

SKIP — niente di rilevante in questo momento. Default sano. Costa zero.
ACT — esiste un'azione locale safe (es. consolidare un riassunto, indicizzare
      un chunk, aggiornare un'entity wiki). Read-only / write-locale-derivate
      soltanto. Niente scrittura su vault clienti, mail, calendari.
ESCALATE — il contesto richiede ragionamento profondo o decisione umana.
           Proponi un task strutturato che Antonio approvera' nell'interfaccia.

OUTPUT FORMAT (JSON puro, NIENTE markdown, NIENTE prosa):
{
  "decision": "SKIP" | "ACT" | "ESCALATE",
  "rationale": "una riga concisa in italiano",
  "proposed_action": null | {
    "kind": "summarize" | "index" | "review_chunk" | "draft_reply" | ...,
    "target_id": "id-opaco-dell-oggetto",
    "summary": "una riga sul cosa fare"
  }
}

Regole:
- Se il contesto e' chiaramente irrilevante o ripetitivo -> SKIP.
- Privilegia SKIP. Antonio preferisce un subconscious silenzioso a uno rumoroso.
- Se fra gli active triggers c'e' una scadenza (deadline) imminente, valuta ESCALATE
  per proporre un promemoria: proposed_action.kind="reminder", summary con titolo
  scadenza + giorni rimanenti. Le scadenze sono il segnale piu' importante.
- ESCALATE solo quando un'azione discrezionale e' richiesta.
- Niente prosa fuori dal JSON.
"""


class DecisionEngine:
    """Decision engine LLM-backed (Claude Haiku 4.5) con short-circuit cost-aware."""

    def __init__(
        self,
        *,
        anthropic_client: Any | None = None,
        model_id: str | None = None,
    ) -> None:
        """
        Args:
            anthropic_client: client gia' istanziato (testing). Se None,
                viene creato al primo decide() usando le settings runtime.
            model_id: override modello (default ``settings.model_fast``).
        """
        self._client = anthropic_client
        self._model_id = model_id

    async def decide(self, context: SubconsciousContext) -> DecisionOutcome:
        """Esegue la decision tree sul contesto fornito.

        Short-circuit: se context.is_empty() -> SKIP senza chiamata LLM.

        Returns:
            DecisionOutcome con decision + rationale + eventuale proposed_action.
            ``used_llm=False`` se short-circuit, True altrimenti.
        """
        if context.is_empty():
            logger.debug("subconscious.decide.short_circuit", reason="empty_context")
            return DecisionOutcome(
                decision=Decision.SKIP,
                rationale="empty_context",
                proposed_action=None,
                used_llm=False,
            )

        try:
            outcome = await self._llm_decide(context)
            return outcome
        except Exception as e:
            logger.warning(
                "subconscious.decide.llm_failure",
                error=str(e),
                error_type=type(e).__name__,
            )
            return DecisionOutcome(
                decision=Decision.SKIP,
                rationale=f"llm_error_fallback: {type(e).__name__}",
                proposed_action=None,
                used_llm=True,
            )

    async def _llm_decide(self, context: SubconsciousContext) -> DecisionOutcome:
        """Chiamata effettiva al modello Claude Haiku 4.5."""
        client = await self._ensure_client()
        model_id = self._model_id or get_settings().model_fast
        user_msg = (
            "Analizza il contesto seguente e produci la decisione JSON.\n\n"
            + context.summary_for_prompt()
        )

        logger.info("subconscious.decide.llm_call", model=model_id)
        # SDK Anthropic supporta sia client async sia sync; usiamo async se disponibile.
        msg = await client.messages.create(
            model=model_id,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        raw_text = self._extract_text(msg)
        parsed = self._parse_json(raw_text)
        decision = self._coerce_decision(parsed.get("decision"))
        rationale = str(parsed.get("rationale", ""))[:500] or "(empty rationale)"
        proposed_action = parsed.get("proposed_action")
        if proposed_action is not None and not isinstance(proposed_action, dict):
            proposed_action = None

        return DecisionOutcome(
            decision=decision,
            rationale=rationale,
            proposed_action=proposed_action,
            used_llm=True,
        )

    async def _ensure_client(self) -> Any:
        """Lazy init Anthropic client. Usa SaaS proxy SCO se license_key presente."""
        if self._client is not None:
            return self._client
        # Lazy import evita import-time cost a livello pacchetto
        from anthropic import AsyncAnthropic

        settings = get_settings()
        api_key_secret = (
            settings.license_key
            if settings.license_key.get_secret_value()
            else settings.anthropic_api_key
        )
        api_key = api_key_secret.get_secret_value() or "missing-key"
        base_url = settings.sco_saas_base_url if settings.license_key.get_secret_value() else None
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncAnthropic(**kwargs)
        return self._client

    @staticmethod
    def _extract_text(msg: Any) -> str:
        """Estrae il primo blocco testuale dalla response Anthropic."""
        try:
            content = msg.content
            if not content:
                return ""
            first = content[0]
            if hasattr(first, "text"):
                return str(first.text)
            if isinstance(first, dict):
                return str(first.get("text", ""))
        except Exception:
            return ""
        return ""

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """Parsing tollerante: estrae il primo blocco { ... } e prova json.loads."""
        if not raw:
            return {}
        text = raw.strip()
        # Strip eventuali code fence markdown
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            parsed: dict[str, Any] = json.loads(text[start : end + 1])
            return parsed
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _coerce_decision(value: Any) -> Decision:
        """Normalizza il valore decisione (tollerante a case / stringhe extra)."""
        if not value:
            return Decision.SKIP
        v = str(value).strip().upper()
        if v in {Decision.SKIP.value, Decision.ACT.value, Decision.ESCALATE.value}:
            return Decision(v)
        return Decision.SKIP
