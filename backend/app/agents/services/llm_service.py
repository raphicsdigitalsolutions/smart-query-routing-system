"""Official OpenAI SDK wrapper with structured output, bounded retries and redaction.

The OpenAI key comes from an optional per-call argument (used for personal BYOK
keys) or, when absent, from server settings. No key, prompt body, raw model
response or provider exception text is logged or returned to callers.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.agents.state import ConnectivityOutput
from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


class LlmError(Exception):
    """Sanitized provider or output failure with a stable category."""

    def __init__(self, category: str, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class LlmResult(Generic[T]):
    data: T
    metadata: dict[str, Any]


_ERROR_MESSAGES = {
    "not_configured": "AI provider is not configured on the server.",
    "invalid_api_key": "The AI provider rejected the configured credentials.",
    "insufficient_credits": "The AI provider account has insufficient credits.",
    "rate_limited": "The AI provider is rate limiting requests.",
    "network_error": "The AI provider could not be reached.",
    "timeout": "The AI provider request timed out.",
    "model_access": "The configured AI model is unavailable to this account.",
    "invalid_response": "The AI provider returned an invalid structured response.",
    "provider_error": "The AI provider request failed.",
}

_RETRYABLE = {"rate_limited", "network_error", "timeout", "invalid_response"}


def _status_code(category: str) -> int:
    if category == "rate_limited":
        return 429
    if category in {"network_error", "timeout"}:
        return 504
    return 502


def _error(category: str) -> LlmError:
    return LlmError(category, _ERROR_MESSAGES[category], status_code=_status_code(category))


class LlmService:
    """Small, injectable wrapper around the official SDK."""

    def __init__(
        self,
        client: Any | None = None,
        deadline: float | None = None,
        api_key: str | None = None,
    ) -> None:
        self._client = client
        self._deadline = deadline
        # A personal (BYOK) key takes precedence over settings.OPENAI_API_KEY.
        self._api_key = api_key

    def with_deadline(self, seconds: float) -> "LlmService":
        """Return a copy with a monotonic end-to-end workflow deadline."""
        return LlmService(
            client=self._client,
            deadline=time.monotonic() + seconds,
            api_key=self._api_key,
        )

    def remaining_seconds(self) -> float | None:
        if self._deadline is None:
            return None
        return self._deadline - time.monotonic()

    @property
    def client(self) -> Any:
        if self._client is None:
            api_key = (self._api_key or settings.OPENAI_API_KEY or "").strip()
            if not api_key:
                raise _error("not_configured")
            self._client = OpenAI(
                api_key=api_key,
                timeout=settings.OPENAI_TIMEOUT_SECONDS,
                # Retry policy is owned by AI_LLM_ATTEMPTS so the workflow deadline
                # cannot be exceeded by hidden SDK-level retries.
                max_retries=0,
            )
        return self._client

    @staticmethod
    def _truncate(value: str) -> str:
        max_chars = settings.AI_MAX_INPUT_TOKENS * 3
        if len(value) <= max_chars:
            return value
        return f"{value[:max_chars]}\n[truncated for safety]"

    @staticmethod
    def _map_provider_error(exc: Exception) -> LlmError:
        if isinstance(exc, AuthenticationError):
            return _error("invalid_api_key")
        if isinstance(exc, PermissionDeniedError):
            return _error("model_access")
        if isinstance(exc, RateLimitError):
            code = str(getattr(exc, "code", "") or "").lower()
            if "quota" in code or "credit" in code:
                return _error("insufficient_credits")
            return _error("rate_limited")
        if isinstance(exc, BadRequestError):
            code = str(getattr(exc, "code", "") or "").lower()
            if "model" in code or "access" in code:
                return _error("model_access")
            return _error("provider_error")
        if isinstance(exc, APITimeoutError):
            return _error("timeout")
        if isinstance(exc, APIConnectionError):
            return _error("network_error")
        if isinstance(exc, APIError):
            return _error("provider_error")
        return _error("provider_error")

    def _call_model(
        self,
        *,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        timeout: float,
    ) -> tuple[T, dict[str, Any]]:
        try:
            response = self.client.beta.chat.completions.parse(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self._truncate(user_prompt)},
                ],
                response_format=schema,
                max_completion_tokens=settings.AI_MAX_OUTPUT_TOKENS,
                timeout=timeout,
                store=False,
            )
        except Exception as exc:  # mapped to stable categories before escaping
            raise self._map_provider_error(exc) from None

        choices = getattr(response, "choices", None)
        if not choices:
            raise _error("invalid_response")
        message = choices[0].message
        raw = getattr(message, "parsed", None)
        if raw is None:
            content = getattr(message, "content", None)
            if not isinstance(content, str):
                raise _error("invalid_response")
            try:
                raw = json.loads(content)
            except json.JSONDecodeError:
                raise _error("invalid_response") from None

        try:
            if isinstance(raw, schema):
                validated = raw
            elif isinstance(raw, str):
                validated = schema.model_validate_json(raw)
            else:
                validated = schema.model_validate(raw)
        except (ValidationError, ValueError, TypeError):
            raise _error("invalid_response") from None

        usage = getattr(response, "usage", None)
        metadata = {
            "model": settings.OPENAI_MODEL,
            "input_chars": len(user_prompt),
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
        }
        return validated, metadata

    def generate_structured(
        self,
        *,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        api_key: str | None = None,
    ) -> LlmResult[T]:
        """Generate Pydantic-validated output with a small, fixed retry budget.

        ``api_key`` overrides the configured key for this call. An injected
        client is left untouched so deterministic tests keep working.
        """
        if api_key and self._client is None and api_key != self._api_key:
            scoped = LlmService(deadline=self._deadline, api_key=api_key.strip())
            return scoped.generate_structured(
                schema=schema,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                api_key=api_key,
            )
        started = time.perf_counter()
        last_error: LlmError | None = None
        metadata: dict[str, Any] = {}

        for attempt in range(1, settings.AI_LLM_ATTEMPTS + 1):
            remaining = self.remaining_seconds()
            if remaining is not None and remaining <= 0:
                raise _error("timeout")
            timeout = (
                min(settings.OPENAI_TIMEOUT_SECONDS, remaining)
                if remaining is not None
                else settings.OPENAI_TIMEOUT_SECONDS
            )
            try:
                validated, metadata = self._call_model(
                    schema=schema,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    timeout=timeout,
                )
                metadata["attempts"] = attempt
                metadata["duration_ms"] = int((time.perf_counter() - started) * 1000)
                return LlmResult(data=validated, metadata=metadata)
            except LlmError as exc:
                last_error = exc
                if exc.category not in _RETRYABLE or attempt == settings.AI_LLM_ATTEMPTS:
                    break

        assert last_error is not None
        raise last_error

    def test_connection(self, *, api_key: str | None = None) -> dict[str, Any]:
        """Perform a real, minimal request; never reports success without one."""
        result = self.generate_structured(
            schema=ConnectivityOutput,
            system_prompt="Return the configured connectivity status object.",
            user_prompt="Connectivity check.",
            api_key=api_key,
        )
        return {
            "connected": result.data.status == "ok",
            "model": result.metadata.get("model"),
            "attempts": result.metadata.get("attempts"),
            "duration_ms": result.metadata.get("duration_ms"),
        }


def get_llm_service(api_key: str | None = None) -> LlmService:
    """Build a service; a supplied personal key overrides server settings."""
    return LlmService(api_key=api_key)
