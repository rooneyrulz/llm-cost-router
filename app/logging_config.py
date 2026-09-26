"""
Logging setup.

1. Structured (JSON) logs instead of formatted strings, so you can actually
   query/filter logs later (e.g. "show me every tool call that failed for
   request X") instead of grepping.
2. Two separate log destinations:
   - app.log        -> HTTP/system level events (request in/out, errors)
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

import structlog

LOG_DIR = "logs"
LOG_LEVEL = "INFO"

def _configure_stdlib_logging(log_dir: Path, log_level: str) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)

    app_handler = logging.handlers.RotatingFileHandler(
        log_dir / "router.log", maxBytes=5_000_000, backupCount=3
    )
    stdout_handler = logging.StreamHandler(sys.stdout)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers = [app_handler, stdout_handler]

def setup_logging() -> None:
    _configure_stdlib_logging(Path(LOG_DIR), LOG_LEVEL)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """App-level logger (requests, startup, top-level errors)."""
    return structlog.get_logger(name)

def bind_request_context(**kwargs) -> None:
    """Bind fields (request_id, symbol, agent_name, ...) to all subsequent
    log lines on this async task/thread until clear_request_context()."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_request_context() -> None:
    structlog.contextvars.clear_contextvars()
