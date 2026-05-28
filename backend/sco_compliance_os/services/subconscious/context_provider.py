"""Context provider per il Subconscious tick loop.

Costruisce un :class:`~sco_compliance_os.services.subconscious.decision_engine.SubconsciousContext`
popolato con tre dimensioni:

- recent_chunks: ultimi chunk ingestiti nella finestra temporale recente.
- hot_topics: top chunk per hotness (decay temporale stile OpenHuman).
- active_triggers: scadenze imminenti rilevate nei vault registrati.

Eventuali errori vengono loggati come warning e producono fallback vuoti in modo
da non impedire l'esecuzione del tick loop.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sco_compliance_os.config import get_settings
from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.memory.hotness import get_top_hot_chunks
from sco_compliance_os.services.memory.store import get_chunk, query_recent
from sco_compliance_os.services.subconscious.decision_engine import SubconsciousContext
from sco_compliance_os.services.vault.parser import parse_vault_file

logger = get_logger(__name__)


_RECENT_WINDOW_MINUTES = 5
_RECENT_LIMIT = 20
_HOT_TOPICS_LIMIT = 10
_DEADLINE_WINDOW_DAYS = 30


async def build_context() -> SubconsciousContext:
    """Ritorna un contesto popolato per il Subconscious tick loop."""

    recent_chunks = await _load_recent_chunks(
        limit=_RECENT_LIMIT, window_minutes=_RECENT_WINDOW_MINUTES
    )
    hot_topics = await _load_hot_topics(limit=_HOT_TOPICS_LIMIT)
    active_triggers = await _load_deadline_triggers(window_days=_DEADLINE_WINDOW_DAYS)

    return SubconsciousContext(
        recent_chunks=recent_chunks,
        hot_topics=hot_topics,
        active_triggers=active_triggers,
    )


async def _load_recent_chunks(*, limit: int, window_minutes: int) -> list[dict[str, Any]]:
    """Recupera e serializza gli ultimi chunk dalla memoria locale."""

    now = datetime.now(UTC)
    threshold = now - timedelta(minutes=window_minutes)

    chunks = await query_recent(limit=limit)
    selected: list[dict[str, Any]] = []
    fallback: list[dict[str, Any]] = []

    for chunk in chunks:
        created_at = _parse_datetime(chunk.created_at)
        chunk_dict = {
            "chunk_id": chunk.id,
            "source_type": chunk.source_type,
            "source_id": chunk.source_id,
            "source_path": chunk.source_path,
            "created_at": chunk.created_at,
            "heading_path": list(chunk.heading_path),
            "snippet": chunk.content_md.strip()[:320],
        }
        fallback.append(chunk_dict)
        if created_at is not None and created_at >= threshold:
            selected.append(chunk_dict)

    if not selected:
        selected = fallback[: min(5, len(fallback))]

    return selected


async def _load_hot_topics(*, limit: int) -> list[dict[str, Any]]:
    """Recupera i top chunk per hotness con metadati utili al prompt."""

    snapshots = await get_top_hot_chunks(n=limit)
    results: list[dict[str, Any]] = []

    for snap in snapshots:
        chunk = await get_chunk(snap.chunk_id)
        if chunk is None:
            continue
        title = chunk.heading_path[-1] if chunk.heading_path else Path(chunk.source_path).stem
        results.append(
            {
                "chunk_id": chunk.id,
                "title": title,
                "hotness": round(snap.hotness, 3),
                "last_accessed": snap.last_accessed,
                "access_count": snap.access_count,
                "source_type": chunk.source_type,
                "snippet": chunk.content_md.strip()[:280],
            }
        )

    return results


async def _load_deadline_triggers(*, window_days: int) -> list[dict[str, Any]]:
    """Scansiona i vault registrati per trovare scadenze imminenti."""

    settings = get_settings()
    registry_path = settings.vault_registry_path

    triggers = await asyncio.to_thread(
        _scan_deadlines_from_registry,
        registry_path,
        window_days,
    )

    return triggers


def _scan_deadlines_from_registry(registry_path: Path, window_days: int) -> list[dict[str, Any]]:
    """Versione sincrona dello scan da eseguire in thread pool."""

    entries = _load_registry_entries(registry_path)
    if not entries:
        return []

    today = date.today()
    results: list[DeadlineTrigger] = []

    for entry in entries:
        vault_path_str = str(entry.get("path", "")).strip()
        if not vault_path_str:
            continue
        vault_path = Path(vault_path_str)
        if not vault_path.exists():
            logger.warning(
                "subconscious.deadlines.vault_missing",
                vault=vault_path_str,
            )
            continue

        entities_dir = vault_path / "wiki" / "entities"
        if not entities_dir.exists():
            logger.warning(
                "subconscious.deadlines.entities_missing",
                vault=vault_path_str,
            )
            continue

        for file_path in entities_dir.glob("*.md"):
            trigger = _build_deadline_trigger(
                file_path=file_path,
                registry_entry=entry,
                today=today,
                window_days=window_days,
            )
            if trigger is not None:
                results.append(trigger)

    results.sort(key=lambda item: item.due_date)
    return [trigger.as_dict() for trigger in results]


def _load_registry_entries(registry_path: Path) -> list[dict[str, Any]]:
    """Carica la lista di vault registrati dal JSON utente."""

    if not registry_path.exists():
        return []

    try:
        raw = registry_path.read_text(encoding="utf-8")
        data = json.loads(raw) or []
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "subconscious.deadlines.registry_read_failed",
            path=str(registry_path),
            error=str(exc),
        )
        return []

    if not isinstance(data, list):
        logger.warning(
            "subconscious.deadlines.registry_invalid",
            path=str(registry_path),
            type=type(data).__name__,
        )
        return []

    return [entry for entry in data if isinstance(entry, dict)]


@dataclass(slots=True)
class DeadlineTrigger:
    """Dato strutturato per una scadenza imminente."""

    slug: str
    title: str
    due_date: date
    days_remaining: int
    data_tipo: str | None
    vault_id: str | None
    vault_path: str
    parent_entity: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": "deadline",
            "connector": "vault",
            "slug": self.slug,
            "title": self.title,
            "due_date": self.due_date.isoformat(),
            "days_remaining": self.days_remaining,
            "data_tipo": self.data_tipo,
            "parent_entity": self.parent_entity,
            "vault_id": self.vault_id,
            "vault_path": self.vault_path,
        }


def _build_deadline_trigger(
    *,
    file_path: Path,
    registry_entry: dict[str, Any],
    today: date,
    window_days: int,
) -> DeadlineTrigger | None:
    """Restituisce trigger per il file se soddisfa i criteri."""

    try:
        document = parse_vault_file(file_path)
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "subconscious.deadlines.parse_failed",
            path=str(file_path),
            error=str(exc),
        )
        return None

    if document.entity_type != "scadenza":
        return None

    frontmatter = document.raw_frontmatter or {}
    due_date_raw = frontmatter.get("data_riferimento")
    due_date = _parse_date(due_date_raw)
    if due_date is None:
        return None

    days_remaining = (due_date - today).days
    if days_remaining < 0 or days_remaining > window_days:
        return None

    title = document.title or file_path.stem
    return DeadlineTrigger(
        slug=file_path.stem,
        title=title,
        due_date=due_date,
        days_remaining=days_remaining,
        data_tipo=str(frontmatter.get("data_tipo")) if frontmatter.get("data_tipo") else None,
        vault_id=str(registry_entry.get("id")) if registry_entry.get("id") else None,
        vault_path=str(registry_entry.get("path", "")),
        parent_entity=document.parent_entity or None,
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None

    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        pass

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    logger.warning("subconscious.deadlines.unparseable_date", value=text)
    return None


__all__ = ["build_context"]
