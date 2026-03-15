"""LiteLLM adapter: completion, exception mapping, parse, optional repair."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.adapters.llm.extraction_schema import (
    EXTRACTION_JSON_SCHEMA,
    EXTRACTION_SCHEMA_NAME,
)
from app.adapters.llm.prompt_builder import build_extraction_messages
from app.adapters.llm.response_parser import parse_extraction_response
from app.config.logging import get_logger, log_structured
from app.config.settings import LiteLLMSettings
from app.core.errors import (
    ExtractionError,
    PermanentExternalError,
    RetryableExternalError,
    ValidationError,
)
from app.domain.extraction_models import ExtractionResult, RepairResult
from app.domain.parse_models import ExtractionChunk

_LOG = get_logger(__name__)

# response_format for LiteLLM structured output (JSON Schema)
_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": EXTRACTION_SCHEMA_NAME,
        "schema": EXTRACTION_JSON_SCHEMA,
    },
    "strict": True,
}


def _map_litellm_exception(e: BaseException) -> BaseException:
    """Map LiteLLM/provider exceptions to domain errors. No vendor types leak."""
    err_type = type(e).__name__
    msg = str(e)
    if err_type in ("Timeout", "APITimeoutError", "TimeoutError"):
        return RetryableExternalError(f"Timeout: {msg}")
    if err_type in ("RateLimitError", "RateLimitException"):
        return RetryableExternalError(f"Rate limit: {msg}")
    if err_type in ("ServiceUnavailableError", "APIConnectionError", "InternalServerError"):
        return RetryableExternalError(f"Transient: {msg}")
    if err_type in ("AuthenticationError", "AuthenticationException"):
        return PermanentExternalError(f"Auth: {msg}")
    if err_type in ("BadRequestError", "InvalidRequestError"):
        return PermanentExternalError(f"Bad request: {msg}")
    if err_type in ("ContextWindowExceededError",):
        return PermanentExternalError(f"Context window: {msg}")
    return ExtractionError(f"LLM call failed: {msg}")


def _get_content(response: Any) -> str:
    """Extract assistant message content from LiteLLM response."""
    try:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        msg = getattr(choices[0], "message", None)
        if msg is None:
            return ""
        content = getattr(msg, "content", None)
        return content if isinstance(content, str) else ""
    except Exception:
        return ""


def _get_usage(response: Any) -> tuple[int | None, int | None]:
    """Extract (input_tokens, output_tokens) from response.usage."""
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None, None
        in_t = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None)
        out_t = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None)
        return in_t, out_t
    except Exception:
        return None, None


def _get_status_code(response: Any) -> int | None:
    """Extract HTTP status code from LiteLLM response when available."""
    try:
        code = getattr(response, "status_code", None)
        if isinstance(code, int):
            return code
        hidden = getattr(response, "_hidden_params", None)
        if isinstance(hidden, dict):
            raw = hidden.get("response_obj") or hidden.get("raw_response")
            code = getattr(raw, "status_code", None) if raw is not None else None
            if isinstance(code, int):
                return code
        return None
    except Exception:
        return None


class LiteLLMAdapter:
    """LLM gateway using LiteLLM. Implements LLMClientProtocol."""

    def __init__(self, settings: LiteLLMSettings) -> None:
        self._settings = settings

    def extract_actions(self, chunk: ExtractionChunk, prompt_cfg: Any) -> ExtractionResult:
        """Build prompt, call completion, parse response. Retry/repair handled inside."""
        from litellm import completion
        from litellm.exceptions import (
            APIConnectionError,
            AuthenticationError,
            BadRequestError,
            RateLimitError,
            ServiceUnavailableError,
            Timeout,
        )

        prompt_version = _str_from_cfg(prompt_cfg, "prompt_version", "v1")
        schema_version = _str_from_cfg(prompt_cfg, "schema_version", "v1")
        norm_hint = _str_from_cfg(prompt_cfg, "normalization_hint", None) or None
        messages = build_extraction_messages(
            chunk, prompt_version, schema_version, normalization_hint=norm_hint
        )
        model = self._settings.model
        fallback = self._settings.fallback_model
        max_retries = self._settings.max_retries
        timeout = self._settings.request_timeout or 120
        timeout = max(60, int(timeout))
        repair_max = self._settings.repair_max_attempts
        use_temperature = 1.0 if "gemini-3" in (model or "").lower() else 0.3

        retryable_exceptions = (Timeout, RateLimitError, ServiceUnavailableError, APIConnectionError)
        permanent_exceptions = (AuthenticationError, BadRequestError)

        last_err: BaseException | None = None
        retry_count = 0
        fallback_used = False

        for attempt in range(max_retries + 1):
            try:
                start = time.perf_counter()
                structured_output_used = False
                schema_fallback_used = False
                response = None
                try:
                    attempt_label = "retry %s" % (attempt + 1) if attempt > 0 else "attempt 1"
                    log_structured(
                        _LOG,
                        logging.INFO,
                        "LLM provider call %s (structured_output=True)" % attempt_label,
                        provider="litellm",
                        model=model,
                        event="llm_provider_call",
                    )
                    response = completion(
                        model=model,
                        messages=messages,
                        temperature=use_temperature,
                        timeout=float(timeout),
                        num_retries=0,
                        api_key=self._settings.api_key or None,
                        api_base=self._settings.base_url,
                        response_format=_RESPONSE_FORMAT,
                    )
                    structured_output_used = True
                except BadRequestError:
                    log_structured(
                        _LOG,
                        logging.INFO,
                        "Structured output not supported by provider, falling back to JSON mode",
                        provider="litellm",
                        model=model,
                        event="extraction_schema_fallback",
                    )
                    schema_fallback_used = True
                    log_structured(
                        _LOG,
                        logging.INFO,
                        "LLM provider call (schema_fallback, structured_output=False)",
                        provider="litellm",
                        model=model,
                        event="llm_provider_call",
                    )
                    response = completion(
                        model=model,
                        messages=messages,
                        temperature=use_temperature,
                        timeout=float(timeout),
                        num_retries=0,
                        api_key=self._settings.api_key or None,
                        api_base=self._settings.base_url,
                    )

                elapsed_ms = int((time.perf_counter() - start) * 1000)
                content = _get_content(response)
                in_t, out_t = _get_usage(response)
                response_model = getattr(response, "model", None) or model
                status_code = _get_status_code(response)
                if status_code is None:
                    status_code = 200  # success path implies HTTP 200

                drafts, repaired_response = _parse_or_repair(
                    self, content, schema_version, prompt_cfg, repair_max
                )

                return ExtractionResult(
                    drafts=tuple(drafts),
                    provider="litellm",
                    model=response_model,
                    prompt_version=prompt_version,
                    schema_version=schema_version,
                    cache_hit=False,
                    retry_count=retry_count,
                    latency_ms=elapsed_ms,
                    input_tokens=in_t,
                    output_tokens=out_t,
                    estimated_cost_usd=None,
                    warnings=(),
                    fallback_used=fallback_used,
                    structured_output_used=structured_output_used,
                    schema_fallback_used=schema_fallback_used,
                    raw_response=content,
                    repaired_response=repaired_response,
                    status_code=status_code,
                )
            except ValidationError as e:
                raise ExtractionError(f"Extraction validation failed: {e}") from e
            except permanent_exceptions as e:
                raise _map_litellm_exception(e)
            except retryable_exceptions as e:
                last_err = e
                retry_count += 1
                if attempt >= max_retries and fallback and not fallback_used:
                    model = fallback
                    fallback_used = True
                    retry_count = 0
                    continue
                if attempt >= max_retries:
                    raise _map_litellm_exception(e)
            except Exception as e:
                if isinstance(e, (ValidationError, ExtractionError)):
                    raise
                raise _map_litellm_exception(e)

        if last_err is not None:
            raise _map_litellm_exception(last_err)
        raise ExtractionError("extract_actions: unexpected")

    def repair_json(self, raw_output: str, schema_cfg: Any) -> RepairResult:
        """One short repair call: fix invalid JSON to match schema."""
        import litellm
        from litellm import completion

        schema_version = _str_from_cfg(schema_cfg, "schema_version", "v1")
        repair_prompt = (
            f"Fix the following JSON so it is a valid JSON array of objects. "
            f"Each object may only have string fields: verb, primary_object, primary_actor, "
            f"input_state, output_state, action_label, suggested_actor_canonical, "
            f"suggested_object_canonical, suggested_verb_canonical, suggested_state_canonical. "
            f"Return only the corrected JSON, no explanation.\n\n{raw_output}"
        )
        try:
            repair_timeout = self._settings.request_timeout or 120
            repair_timeout = max(60, int(repair_timeout))
            response = completion(
                model=self._settings.model,
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0,
                timeout=float(repair_timeout),
                num_retries=0,
                api_key=self._settings.api_key or None,
                api_base=self._settings.base_url,
            )
            content = _get_content(response)
            if not content.strip():
                return RepairResult(repaired_json=raw_output, success=False, drafts=None)
            drafts = parse_extraction_response(content, schema_version)
            return RepairResult(repaired_json=content, success=True, drafts=tuple(drafts))
        except Exception:
            return RepairResult(repaired_json=raw_output, success=False, drafts=None)


def _str_from_cfg(cfg: Any, key: str, default: str) -> str:
    if isinstance(cfg, dict) and key in cfg and isinstance(cfg[key], str):
        return cfg[key]
    return default


def _parse_or_repair(
    adapter: LiteLLMAdapter,
    content: str,
    schema_version: str,
    prompt_cfg: Any,
    repair_max: int,
) -> tuple[list, str | None]:
    """Parse content; on ValidationError try repair once. Returns (drafts, repaired_json or None)."""
    try:
        drafts = parse_extraction_response(content, schema_version)
        return drafts, None
    except ValidationError:
        if repair_max <= 0:
            raise
        repair = adapter.repair_json(content, {"schema_version": schema_version})
        if repair.success and repair.drafts is not None:
            return list(repair.drafts), repair.repaired_json
        raise