"""Error classification: retryable, permanent, internal. Do not mask; assert real behavior."""

import pytest

from app.core.errors import InternalError, ParsingError, RetryableExternalError, ValidationError
from app.workers.retry_policy import error_code_for_run, is_run_step_retryable


class TestErrorClassification:
    """Known provider/timeout -> retryable; unsupported format -> permanent; unexpected -> internal."""

    def test_known_provider_timeout_is_retryable(self):
        e = RetryableExternalError("Timeout: request timed out")
        assert is_run_step_retryable(e) is True
        assert error_code_for_run(e) == "retryable_external"

    def test_unsupported_file_format_is_permanent(self):
        e = ParsingError("Unsupported format")
        assert is_run_step_retryable(e) is False
        assert error_code_for_run(e) == "parsing_error"

    def test_unexpected_bug_is_internal(self):
        e = InternalError("Unexpected state")
        assert is_run_step_retryable(e) is False
        assert error_code_for_run(e) == "internal_error"

    def test_generic_exception_maps_to_internal_error_code(self):
        e = ValueError("something wrong")
        assert is_run_step_retryable(e) is False
        assert error_code_for_run(e) == "internal_error"

    def test_validation_error_is_permanent(self):
        e = ValidationError("bad input")
        assert is_run_step_retryable(e) is False
        assert error_code_for_run(e) == "validation_error"
