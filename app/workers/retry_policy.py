"""Retry classification for run-level step failures. Do not mask: non-retryable propagate."""

from app.core.errors import (
    ConfigError,
    ExtractionError,
    NormalizationError,
    NotFoundError,
    ParsingError,
    PermanentExternalError,
    RetryableExternalError,
    StorageError,
    StorageNotFoundError,
    ValidationError,
)


def is_run_step_retryable(exc: BaseException) -> bool:
    """Return True if the step failure is transient and retry may succeed.

    Retry: RetryableExternalError, transient storage/network.
    Do not retry: PermanentExternalError, ValidationError, ConfigError,
    ParsingError (e.g. unsupported format), NormalizationError, NotFoundError.
    """
    if isinstance(exc, RetryableExternalError):
        return True
    if isinstance(exc, (ValidationError, ConfigError, PermanentExternalError)):
        return False
    if isinstance(exc, (ParsingError, NormalizationError, ExtractionError, NotFoundError)):
        return False
    if isinstance(exc, StorageNotFoundError):
        # Missing object is typically permanent for this run
        return False
    if isinstance(exc, StorageError):
        # Generic storage error: treat as retryable (transient availability)
        return True
    # ConnectionError, TimeoutError etc. from stdlib: retryable
    if type(exc).__name__ in ("ConnectionError", "TimeoutError", "OSError"):
        return True
    return False


def error_code_for_run(exc: BaseException) -> str:
    """Map exception to a short error code for run.error_code persistence."""
    if isinstance(exc, RetryableExternalError):
        return "retryable_external"
    if isinstance(exc, PermanentExternalError):
        return "permanent_external"
    if isinstance(exc, ValidationError):
        return "validation_error"
    if isinstance(exc, ConfigError):
        return "config_error"
    if isinstance(exc, ParsingError):
        return "parsing_error"
    if isinstance(exc, NormalizationError):
        return "normalization_error"
    if isinstance(exc, ExtractionError):
        return "extraction_error"
    if isinstance(exc, StorageNotFoundError):
        return "storage_not_found"
    if isinstance(exc, StorageError):
        return "storage_error"
    if isinstance(exc, NotFoundError):
        return "not_found"
    if isinstance(exc, ConnectionError):
        return "connection_error"
    if type(exc).__name__ == "TimeoutError":
        return "timeout"
    return "error"
