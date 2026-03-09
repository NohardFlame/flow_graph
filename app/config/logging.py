"""Structured logging baseline.

Consistent field names for all log events:
- event, module, document_id, run_id, chunk_id, job_id, attempt, elapsed_ms

No free-form print debugging in library code. Use structured loggers
that accept these fields as keyword arguments.
"""

import logging
from typing import Any

# Standard keys for structured log events (use as kwargs when logging).
STRUCTURED_KEYS = frozenset({
    "event",
    "module",
    "document_id",
    "run_id",
    "chunk_id",
    "job_id",
    "step",
    "attempt",
    "provider",
    "model",
    "elapsed_ms",
    "correlation_id",
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


def _filter_structured(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return only keys that are in STRUCTURED_KEYS; drop the rest.
    Renames 'module' to 'component' in extra to avoid overwriting LogRecord.module.
    """
    out = {k: v for k, v in kwargs.items() if k in STRUCTURED_KEYS and v is not None}
    if "module" in out:
        out["component"] = out.pop("module")
    return out


def log_structured(
    logger: logging.Logger,
    level: int,
    message: str,
    **kwargs: Any,
) -> None:
    """Log with structured extra. Only STRUCTURED_KEYS are included in the log record."""
    extra = _filter_structured(kwargs)
    if extra:
        logger.log(level, message, extra=extra)
    else:
        logger.log(level, message)
