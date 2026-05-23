"""
registry.py — ConnectorRegistry singleton per discovery dei connettori.

Pattern: registro globale (singleton thread-safe) che mantiene la mappa
``{slug: BaseConnector class}``. Permette:

- Discovery dinamica lato API (``GET /api/integrations/list``).
- Lookup per slug (``GET /api/integrations/{slug}/start``).
- Filtering per categoria (UI: "mostra solo email connectors").

L'auto-registrazione avviene tramite il decorator ``@connector``:

    from .registry import connector
    from .base import BaseConnector

    @connector
    class GmailConnector(BaseConnector):
        slug = "gmail"
        ...

In alternativa si può registrare esplicitamente:

    ConnectorRegistry.register(GmailConnector)

Pattern Karpathy "single source of truth": il registry è l'unica fonte
autorevole della lista connettori. La UI legge da qui via API, non da
config files duplicati.
"""

from __future__ import annotations

import logging
from threading import RLock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseConnector

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """Registro singleton dei connettori OAuth disponibili.

    Thread-safe via RLock per supportare registrazione concorrente
    da moduli importati in parallelo.
    """

    _instance: ConnectorRegistry | None = None
    _lock = RLock()

    def __new__(cls) -> ConnectorRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._connectors = {}  # type: ignore[attr-defined]
            return cls._instance

    def __init__(self) -> None:
        # __init__ called multiple times on singleton: guard against re-init
        if not hasattr(self, "_connectors"):
            self._connectors: dict[str, type[BaseConnector]] = {}

    @classmethod
    def register(cls, connector_cls: type[BaseConnector]) -> type[BaseConnector]:
        """Registra una classe connector nel registry.

        Args:
            connector_cls: sottoclasse di ``BaseConnector`` con ``slug`` valido.

        Returns:
            La stessa classe (per supportare uso come decorator).

        Raises:
            ValueError: se il slug è vuoto o già registrato.
        """
        instance = cls()
        slug = getattr(connector_cls, "slug", "")
        if not slug:
            raise ValueError(f"{connector_cls.__name__}: class attribute 'slug' mancante.")
        with cls._lock:
            if slug in instance._connectors:
                logger.warning(
                    "connector slug already registered, overriding | slug=%s old=%s new=%s",
                    slug,
                    instance._connectors[slug].__name__,
                    connector_cls.__name__,
                )
            instance._connectors[slug] = connector_cls
            logger.info("connector registered | slug=%s class=%s", slug, connector_cls.__name__)
        return connector_cls

    @classmethod
    def get(cls, slug: str) -> type[BaseConnector] | None:
        """Ritorna la classe connector per uno slug, ``None`` se non esiste."""
        instance = cls()
        return instance._connectors.get(slug)

    @classmethod
    def list_all(cls) -> list[type[BaseConnector]]:
        """Ritorna tutte le classi connector registrate."""
        instance = cls()
        return list(instance._connectors.values())

    @classmethod
    def list_slugs(cls) -> list[str]:
        """Ritorna tutti gli slug registrati."""
        instance = cls()
        return list(instance._connectors.keys())

    @classmethod
    def get_by_category(cls, category: str) -> list[type[BaseConnector]]:
        """Ritorna connector filtrati per categoria.

        Args:
            category: una di ``ConnectorCategory`` (es. ``"email"``).
        """
        instance = cls()
        return [c for c in instance._connectors.values() if getattr(c, "category", "") == category]

    @classmethod
    def clear(cls) -> None:
        """Svuota il registry (utile per test). Non usare in produzione."""
        instance = cls()
        with cls._lock:
            instance._connectors.clear()


def connector(cls: type[BaseConnector]) -> type[BaseConnector]:
    """Decorator helper per registrare un connector.

    Usage:

        @connector
        class GmailConnector(BaseConnector):
            slug = "gmail"
            ...
    """
    return ConnectorRegistry.register(cls)
