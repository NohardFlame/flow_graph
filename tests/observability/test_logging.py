"""Structured logging: expected keys in log records; correlation_id propagation."""

import logging

import pytest

from app.config.logging import STRUCTURED_KEYS, get_logger, log_structured


class TestStructuredLogKeys:
    """Structured log record contains expected keys."""

    def test_structured_log_record_contains_expected_keys(self, caplog):
        """Logging with log_structured attaches only allowed keys to the record."""
        caplog.set_level(logging.INFO)
        logger = get_logger("test.module")
        log_structured(
            logger,
            logging.INFO,
            "test event",
            event="run_completed",
            module="test.module",
            run_id="r1",
            document_id="d1",
            step="complete_run",
            elapsed_ms=100,
            # Keys not in STRUCTURED_KEYS should be dropped
            unknown_key="ignored",
        )
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        assert getattr(record, "event", None) == "run_completed"
        assert getattr(record, "component", None) == "test.module"
        assert getattr(record, "run_id", None) == "r1"
        assert getattr(record, "document_id", None) == "d1"
        assert getattr(record, "step", None) == "complete_run"
        assert getattr(record, "elapsed_ms", None) == 100
        assert not hasattr(record, "unknown_key") or getattr(record, "unknown_key", None) is None

    def test_structured_keys_include_required_names(self):
        """STRUCTURED_KEYS includes event, module (mapped to component in records), run_id, step, correlation_id."""
        assert "event" in STRUCTURED_KEYS
        assert "module" in STRUCTURED_KEYS
        assert "run_id" in STRUCTURED_KEYS
        assert "step" in STRUCTURED_KEYS
        assert "correlation_id" in STRUCTURED_KEYS
        assert "document_id" in STRUCTURED_KEYS
        assert "elapsed_ms" in STRUCTURED_KEYS


class TestCorrelationIdPropagation:
    """Correlation id can be passed and logged in worker context."""

    def test_correlation_id_in_job_payload_roundtrip(self):
        """RunJobPayload accepts correlation_id; to_dict includes it."""
        from app.workers.schemas import RunJobPayload

        payload = RunJobPayload.from_dict({"run_id": "r1", "correlation_id": "req-123"})
        assert payload.correlation_id == "req-123"
        d = payload.to_dict()
        assert d.get("correlation_id") == "req-123"

    def test_correlation_id_optional_in_payload(self):
        """Payload without correlation_id has None."""
        from app.workers.schemas import RunJobPayload

        payload = RunJobPayload.from_dict({"run_id": "r1"})
        assert payload.correlation_id is None
