"""Fake LLM adapter for tests. Stateful: configurable response sequence and errors."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.adapters.llm.response_parser import parse_extraction_response
from app.domain.extraction_models import ExtractionResult, RepairResult
from app.domain.parse_models import ExtractionChunk


class FakeLLMAdapter:
    """Stateful fake implementing LLMClientProtocol. Use for tests without live API.

    - extraction_responses: sequence of str (valid JSON) or Exception. Each
      extract_actions call consumes the next; str is parsed and returned as
      ExtractionResult; Exception is raised.
    - repair_responses: sequence of RepairResult. Each repair_json call consumes
      the next.
    - default_metadata: optional dict to override provider, model, etc. on results.
    """

    def __init__(
        self,
        extraction_responses: Sequence[str | BaseException] = (),
        repair_responses: Sequence[RepairResult] = (),
        *,
        default_metadata: dict[str, Any] | None = None,
    ) -> None:
        self._extraction_queue: list[str | BaseException] = list(extraction_responses)
        self._repair_queue: list[RepairResult] = list(repair_responses)
        self._default_metadata = default_metadata or {}
        self._extract_call_count = 0
        self._repair_call_count = 0

    def extract_actions(self, chunk: ExtractionChunk, prompt_cfg: Any) -> ExtractionResult:
        self._extract_call_count += 1
        if not self._extraction_queue:
            raise RuntimeError("FakeLLMAdapter: no more extraction responses configured")
        item = self._extraction_queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        schema_version = _get_str(prompt_cfg, "schema_version", "v1")
        prompt_version = _get_str(prompt_cfg, "prompt_version", "v1")
        drafts = parse_extraction_response(item, schema_version)
        meta = {
            "provider": "fake",
            "model": "fake",
            "prompt_version": prompt_version,
            "schema_version": schema_version,
            "cache_hit": False,
            "retry_count": 0,
            "latency_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": None,
            "warnings": (),
            "fallback_used": False,
        }
        meta.update(self._default_metadata)
        return ExtractionResult(
            drafts=tuple(drafts),
            provider=meta["provider"],
            model=meta["model"],
            prompt_version=meta["prompt_version"],
            schema_version=meta["schema_version"],
            cache_hit=meta["cache_hit"],
            retry_count=meta["retry_count"],
            latency_ms=meta["latency_ms"],
            input_tokens=meta["input_tokens"],
            output_tokens=meta["output_tokens"],
            estimated_cost_usd=meta["estimated_cost_usd"],
            warnings=tuple(meta["warnings"]) if isinstance(meta["warnings"], (list, tuple)) else meta["warnings"],
            fallback_used=meta["fallback_used"],
            structured_output_used=meta.get("structured_output_used", False),
            schema_fallback_used=meta.get("schema_fallback_used", False),
        )

    def repair_json(self, raw_output: str, schema_cfg: Any) -> RepairResult:
        self._repair_call_count += 1
        if not self._repair_queue:
            return RepairResult(repaired_json=raw_output, success=False, drafts=None)
        return self._repair_queue.pop(0)

    @property
    def extract_call_count(self) -> int:
        return self._extract_call_count

    @property
    def repair_call_count(self) -> int:
        return self._repair_call_count


def _get_str(cfg: Any, key: str, default: str) -> str:
    if isinstance(cfg, dict) and key in cfg and isinstance(cfg[key], str):
        return cfg[key]
    return default
