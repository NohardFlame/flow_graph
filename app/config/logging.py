"""Structured logging baseline.

Consistent field names for all log events:
- event, module, document_id, run_id, chunk_id, job_id, attempt, elapsed_ms

No free-form print debugging in library code. Use structured loggers
that accept these fields as keyword arguments.
"""

import logging
from typing import Any

# Standard keys for structured log events (use as kwargs when logging)
STRUCTURED_KEYS = frozenset({
    "event",
    "module",
    "document_id",
    "run_id",
    "chunk_id",
    "job_id",
    "attempt",
    "elapsed_ms",
})


def configure_logging(
    log_level: str = "INFO",
    **kwargs: Any,
) -> None:
    """Configure root logger with level. ObservabilitySettings can be passed later."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, **kwargs)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module name."""
    return logging.getLogger(name)
