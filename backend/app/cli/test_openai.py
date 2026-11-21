"""Safe, real OpenAI connectivity smoke test.

Run with: python -m app.cli.test_openai
Prints only non-secret status fields. The API key is never read from argv,
printed, logged or included in the result.
"""

from __future__ import annotations

import sys

from app.agents.services.llm_service import LlmError, LlmService
from app.core.config import settings


def main() -> int:
    if not settings.OPENAI_API_KEY:
        print("OpenAI connectivity: NOT CONFIGURED (OPENAI_API_KEY is empty)")
        return 2

    print(f"OpenAI connectivity check using model {settings.OPENAI_MODEL}…")
    try:
        result = LlmService().test_connection()
    except LlmError as exc:
        # Category and fixed message only; no provider response body or key material.
        print(f"OpenAI connectivity: FAILED ({exc.category}: {exc.message})")
        return 1

    print(
        "OpenAI connectivity: OK "
        f"(model={result['model']}, attempts={result['attempts']}, duration_ms={result['duration_ms']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
