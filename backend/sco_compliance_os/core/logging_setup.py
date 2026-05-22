"""Setup logging strutturato con structlog.

Output JSON in produzione, console rendering in dev.
Propaga request_id per correlation tracing.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

# ContextVar per propagare request_id tra middleware FastAPI e logger
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def configure_logging(log_level: str = "INFO", json_output: bool = False) -> None:
    """Configura structlog + logging stdlib.

    Args:
        log_level: livello logging (DEBUG, INFO, WARNING, ERROR).
        json_output: se True, output JSON line-by-line (produzione).
                     Se False, console renderer leggibile (dev).
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Logging stdlib base
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    # Processors structlog
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _inject_request_id,
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _inject_request_id(_logger: Any, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Inietta request_id corrente nel log event."""
    rid = _request_id_var.get()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def set_request_id(request_id: str | None = None) -> str:
    """Setta request_id corrente. Genera UUID4 se None."""
    rid = request_id or str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Wrapper getter logger structlog."""
    return structlog.get_logger(name)
