"""Node 1: structured query classification."""

from __future__ import annotations

import time
from collections.abc import Callable

from app.agents.prompts.classification import (
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_USER_PROMPT,
)
from app.agents.services.llm_service import LlmError, LlmService
from app.agents.state import (
    AgentState,
    append_error,
    append_execution,
    ClassificationOutput,
)

ClassificationNode = Callable[[AgentState], AgentState]


def make_classification_node(llm: LlmService) -> ClassificationNode:
    def classification_node(state: AgentState) -> AgentState:
        started = time.perf_counter()
        user_prompt = CLASSIFICATION_USER_PROMPT.format(
            subject=state.get("subject", ""),
            description=state.get("query_text", ""),
            category=state.get("category") or "none",
            priority=state.get("priority") or "unknown",
            status=state.get("status") or "unknown",
        )
        try:
            result = llm.generate_structured(
                schema=ClassificationOutput,
                system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except LlmError as exc:
            return {
                **state,
                "errors": append_error(
                    state,
                    {"node": "classification", "code": exc.category, "message": exc.message},
                ),
                "abstention_reason": "Classification was unavailable; no reliable response could be prepared.",
                "execution": append_execution(
                    state,
                    {
                        "node": "classification",
                        "status": "failed",
                        "duration_ms": int((time.perf_counter() - started) * 1000),
                        "detail": exc.category,
                    },
                ),
            }

        data = result.data.model_dump()
        return {
            **state,
            "classification": data,
            "priority_recommendation": result.data.urgency,
            "confidence": result.data.confidence,
            "execution": append_execution(
                state,
                {
                    "node": "classification",
                    "status": "completed",
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "attempts": result.metadata.get("attempts"),
                    "model": result.metadata.get("model"),
                },
            ),
        }

    return classification_node
