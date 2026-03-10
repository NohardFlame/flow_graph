"""Retry and repair policy for extraction: classify errors, cap retries and repair attempts."""

import time
from typing import Any, Protocol

from app.core.errors import RetryableExternalError
from app.domain.extraction_models import ExtractionResult
from app.domain.parse_models import ExtractionChunk

# Seconds to wait before retrying after a rate limit or other retryable error
RETRY_BACKOFF_SECONDS = 15


def is_retryable(err: BaseException) -> bool:
    """Return True if the error is transient and retry may succeed.

    Retry: timeouts, 429, transient upstream (mapped to RetryableExternalError by adapter).
    Do not retry: auth, bad request, content policy (PermanentExternalError, ExtractionError).
    """
    return isinstance(err, RetryableExternalError)


class ExtractActionsProtocol(Protocol):
    def extract_actions(self, chunk: ExtractionChunk, prompt_cfg: Any) -> ExtractionResult: ...


def extract_with_retry(
    adapter: ExtractActionsProtocol,
    chunk: ExtractionChunk,
    prompt_cfg: Any,
    max_retries: int,
) -> ExtractionResult:
    """Call adapter.extract_actions with retries on RetryableExternalError.

    Returns the first successful result. Raises after max_retries retryable
    failures or on first non-retryable error. Result's retry_count is not
    updated by this helper (adapter may set it).
    """
    last_err: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return adapter.extract_actions(chunk, prompt_cfg)
        except BaseException as e:
            last_err = e
            if not is_retryable(e):
                raise
            if attempt < max_retries:
                time.sleep(RETRY_BACKOFF_SECONDS)
    if last_err is not None:
        raise last_err
    raise RuntimeError("extract_with_retry: unexpected")
