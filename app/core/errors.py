"""Base exception hierarchy for the application.

External adapters must translate vendor/library exceptions into these
internal error types. Handlers and tests can catch by type.
"""


class DomainError(Exception):
    """Base for all domain and application errors."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class ConfigError(DomainError):
    """Invalid or missing configuration."""


class ValidationError(DomainError):
    """Validation failure (e.g. input or schema)."""


class RetryableExternalError(DomainError):
    """External call failed in a way that may succeed on retry."""


class PermanentExternalError(DomainError):
    """External call failed in a way that retries will not fix."""


class ParsingError(DomainError):
    """Document or content parsing failed."""


class ExtractionError(DomainError):
    """LLM or extraction step failed."""


class NormalizationError(DomainError):
    """Normalization or canonical key derivation failed."""
