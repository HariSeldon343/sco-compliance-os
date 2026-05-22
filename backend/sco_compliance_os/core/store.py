"""SQLite store async via SQLAlchemy 2.0.

Schema:
- conversations(id, title, created_at, updated_at)
- messages(id, conversation_id FK, role, content TEXT,
           ask_user_question_json TEXT NULL,
           tool_calls_json TEXT NULL,
           created_at)

Pattern Conv. 48 SINGLE SOURCE OF TRUTH BACKEND: ask_user_question_json e
tool_calls_json persistiti per sopravvivere al cambio chat / refresh / reload.
Pattern Conv. 47 SINGLE SOURCE OF TRUTH per version costanti applicato qui via
init_schema() con migrazioni idempotenti ALTER TABLE ADD COLUMN IF NOT EXISTS.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    select,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from sco_compliance_os.core.logging_setup import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base ORM SQLAlchemy 2.0 declarative."""


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utc_now() -> datetime:
    return datetime.utcnow()


class Conversation(Base):
    """Conversation = thread di messaggi tra utente e agente."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    title: Mapped[str] = mapped_column(String(200), default="Nuova conversazione")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    """Message in una Conversation.

    ask_user_question_json e tool_calls_json sono TEXT JSON serialized:
    pattern Conv. 48 per stato widget post-streaming persistito lato backend.
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(20))  # user | assistant | tool
    content: Mapped[str] = mapped_column(Text, default="")
    ask_user_question_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Store:
    """Wrapper async per operazioni CRUD su conversations + messages."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._url = f"sqlite+aiosqlite:///{db_path}"
        self._engine: AsyncEngine = create_async_engine(self._url, echo=False, future=True)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )

    async def init_schema(self) -> None:
        """Crea schema se non esiste + migrazioni idempotenti.

        Le ALTER TABLE seguono pattern Conv. 48 per aggiungere colonne JSONB-like
        a tabelle esistenti senza distruggere dati. SQLite non supporta
        IF NOT EXISTS su ADD COLUMN nativamente, quindi try/except del fallimento.
        """
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Migrazioni idempotenti — pattern già adottato in sco-agent-local
            await self._safe_add_column(conn, "messages", "ask_user_question_json", "TEXT")
            await self._safe_add_column(conn, "messages", "tool_calls_json", "TEXT")
        logger.info("store.schema.initialized", url=self._url)

    @staticmethod
    async def _safe_add_column(conn: Any, table: str, column: str, sql_type: str) -> None:
        try:
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
        except Exception:  # noqa: BLE001 — duplicate column è atteso
            pass

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Context manager di sessione async."""
        async with self._session_factory() as sess:
            yield sess

    # ----- Conversations -----
    async def create_conversation(self, title: str = "Nuova conversazione") -> Conversation:
        """Crea nuova conversation con titolo opzionale."""
        async with self.session() as sess:
            conv = Conversation(title=title)
            sess.add(conv)
            await sess.commit()
            await sess.refresh(conv)
            return conv

    async def list_conversations(self, limit: int = 50) -> list[Conversation]:
        """Lista conversation ordinate per updated_at desc."""
        async with self.session() as sess:
            stmt = select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

    async def get_conversation(self, conv_id: str) -> Conversation | None:
        async with self.session() as sess:
            return await sess.get(Conversation, conv_id)

    # ----- Messages -----
    async def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        ask_user_question: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> Message:
        """Appende messaggio alla conversation.

        ask_user_question / tool_calls serializzati JSON-string. Pattern Conv. 48.
        """
        async with self.session() as sess:
            msg = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                ask_user_question_json=(
                    json.dumps(ask_user_question, ensure_ascii=False)
                    if ask_user_question is not None
                    else None
                ),
                tool_calls_json=(
                    json.dumps(tool_calls, ensure_ascii=False)
                    if tool_calls is not None
                    else None
                ),
            )
            sess.add(msg)
            await sess.commit()
            await sess.refresh(msg)
            return msg

    async def list_messages(self, conversation_id: str) -> list[Message]:
        async with self.session() as sess:
            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            result = await sess.execute(stmt)
            return list(result.scalars().all())

    async def close(self) -> None:
        await self._engine.dispose()


# Singleton helper (per FastAPI dependency)
_store: Store | None = None


def get_store(db_path: Path) -> Store:
    """Ritorna istanza Store singleton, creandola se necessario."""
    global _store
    if _store is None:
        _store = Store(db_path)
    return _store
