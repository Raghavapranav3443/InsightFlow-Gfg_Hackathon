"""
core/logging.py
──────────────────────────────────────────────────────────────────────────────
Structured JSON logging via structlog.
All modules use: `import structlog; logger = structlog.get_logger()`
NEVER use print() for application logging.
"""
from __future__ import annotations

import logging
import sys

import structlog

from core.config import get_settings


def configure_logging() -> None:
    """
    Call once at app startup (in main.py lifespan).
    Sets up structlog with JSON output in production, pretty output in dev.
    """
    cfg = get_settings()
    log_level = getattr(logging, cfg.LOG_LEVEL, logging.INFO)

    # Standard library logging config (for libraries that use it)
    logging.basicConfig(
        stream=sys.stdout,
        level=log_level,
        format="%(message)s",
    )
    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if cfg.is_production:
        # JSON output — parseable by Datadog, Logtail, etc.
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Human-readable console output for dev
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
