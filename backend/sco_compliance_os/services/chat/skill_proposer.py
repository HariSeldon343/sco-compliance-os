from __future__ import annotations

import asyncio
import re
import time
from collections import OrderedDict
from collections.abc import Iterable

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.skills.loader import SkillMeta

logger = get_logger(__name__)

_STOPWORDS = {
    "a",
    "ad",
    "al",
    "alla",
    "alle",
    "allo",
    "che",
    "chi",
    "con",
    "da",
    "dal",
    "dalla",
    "dalle",
    "dallo",
    "de",
    "dei",
    "del",
    "della",
    "delle",
    "dello",
    "di",
    "e",
    "gli",
    "i",
    "il",
    "in",
    "la",
    "le",
    "lo",
    "ma",
    "mi",
    "nei",
    "nel",
    "nella",
    "nelle",
    "nello",
    "no",
    "non",
    "o",
    "per",
    "piu",
    "più",
    "quale",
    "quei",
    "quel",
    "quella",
    "quelle",
    "quello",
    "se",
    "si",
    "su",
    "sul",
    "sulla",
    "sulle",
    "sullo",
    "tra",
    "un",
    "una",
    "uno",
}

_WORD_RE = re.compile(r"[0-9A-Za-zàèéìòùÀÈÉÌÒÙ']+")
_PENDING_MAX = 1000
_PENDING_TTL_SECONDS = 600.0


class _PendingEntry:
    __slots__ = ("options", "timestamp")

    def __init__(self, options: list[str], timestamp: float) -> None:
        self.options = options
        self.timestamp = timestamp


_pending_skill_options: OrderedDict[str, _PendingEntry] = OrderedDict()
_pending_lock = asyncio.Lock()


def _tokenize(text: str) -> set[str]:
    tokens: set[str] = set()
    for match in _WORD_RE.finditer(text.lower()):
        word = match.group(0)
        word = word.strip("'")
        if not word or word in _STOPWORDS or len(word) <= 2:
            continue
        tokens.add(word)
    return tokens


def _score_match(query_tokens: set[str], candidates: Iterable[str]) -> int:
    score = 0
    for raw in candidates:
        tokens = _tokenize(raw)
        score += len(query_tokens & tokens)
    return score


def propose_skills(
    user_message: str,
    available_skills: list[SkillMeta],
    *,
    top_k: int = 3,
    min_score: int = 2,
) -> list[SkillMeta]:
    """Seleziona skill pertinenti rispetto al messaggio utente."""
    if not user_message.strip() or not available_skills:
        return []

    query_tokens = _tokenize(user_message)
    if not query_tokens:
        return []

    scored: list[tuple[int, SkillMeta]] = []
    for skill in available_skills:
        name_score = _score_match(query_tokens, [skill.name, skill.frontmatter.get("name", "")])
        desc_source = skill.description or skill.frontmatter.get("description", "")
        desc_score = _score_match(query_tokens, [desc_source])
        total = (name_score * 3) + desc_score
        if total >= min_score:
            scored.append((total, skill))

    if not scored:
        return []

    scored.sort(key=lambda item: (-item[0], item[1].name))
    top_items = scored[:top_k]
    return [skill for _score, skill in top_items]


async def get_pending(conv_id: str) -> list[str] | None:
    """Ritorna le opzioni pending per la conversation (se non scadute)."""
    async with _pending_lock:
        _prune_expired_locked()
        entry = _pending_skill_options.get(conv_id)
        if entry is None:
            return None
        return list(entry.options)


async def set_pending(conv_id: str, options: list[str]) -> None:
    if not options:
        return
    async with _pending_lock:
        _prune_expired_locked()
        timestamp = time.monotonic()
        _pending_skill_options[conv_id] = _PendingEntry(list(options), timestamp)
        while len(_pending_skill_options) > _PENDING_MAX:
            popped_conv_id, _ = _pending_skill_options.popitem(last=False)
            logger.debug("skill_proposer.pending_evicted", conversation_id=popped_conv_id)


async def clear_pending(conv_id: str) -> None:
    async with _pending_lock:
        if _pending_skill_options.pop(conv_id, None) is not None:
            logger.debug("skill_proposer.pending_cleared", conversation_id=conv_id)


def _prune_expired_locked() -> None:
    if not _pending_skill_options:
        return
    now = time.monotonic()
    expired_ids: list[str] = []
    for conv_id, entry in list(_pending_skill_options.items()):
        if now - entry.timestamp > _PENDING_TTL_SECONDS:
            expired_ids.append(conv_id)
    for conv_id in expired_ids:
        _pending_skill_options.pop(conv_id, None)
        logger.debug("skill_proposer.pending_expired", conversation_id=conv_id)


__all__ = [
    "clear_pending",
    "get_pending",
    "propose_skills",
    "set_pending",
]
