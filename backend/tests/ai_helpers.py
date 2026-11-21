"""Deterministic fakes shared by Phase 6 agent and API tests."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from app.agents.services.llm_service import LlmService
from app.schemas.ai import AiAnalysisResponse


class FakeCompletions:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("Unexpected extra model call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(parsed=response))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20),
        )


class FakeOpenAIClient:
    def __init__(self, responses: list[Any]) -> None:
        self.completions = FakeCompletions(responses)
        self.beta = SimpleNamespace(
            chat=SimpleNamespace(completions=self.completions)
        )


def make_llm(responses: list[Any]) -> tuple[LlmService, FakeOpenAIClient]:
    client = FakeOpenAIClient(responses)
    return LlmService(client=client), client


def valid_classification() -> dict[str, Any]:
    return {
        "intent": "request_password_reset_help",
        "category": "account_access",
        "urgency": "normal",
        "language": "en",
        "entities": ["password"],
        "confidence": 0.82,
        "rationale": "The query asks about account access and password reset.",
    }


def valid_routing(department_id: int) -> dict[str, Any]:
    return {
        "department_id": department_id,
        "department_name": None,
        "staff_id": None,
        "staff_name": None,
        "confidence": 0.76,
        "reason": "Account access requests fit this department.",
    }


def valid_draft(body: str | None = None) -> dict[str, Any]:
    return {
        "body": body or (
            "Thanks for your message. A staff member will review your account access "
            "question and confirm the next step after checking the approved guidance."
        ),
        "language": "en",
        "confidence": 0.71,
        "source_ids": [],
        "needs_staff_review": True,
    }


def sample_analysis(ticket_id: int) -> AiAnalysisResponse:
    return AiAnalysisResponse(
        id=1,
        ticket_id=ticket_id,
        version=1,
        status="completed",
        is_current=True,
        classification=valid_classification(),
        priority_recommendation="normal",
        department_recommendation={
            "department_id": 1,
            "department_name": "Registry",
            "confidence": 0.76,
            "reason": "Account access requests fit this department.",
            "source": "model",
        },
        knowledge_sources=[],
        no_evidence=True,
        draft=valid_draft(),
        validation={"passed": True, "issues": [], "overall_confidence": 0.76},
        confidence=0.76,
        abstention_reason="No approved knowledge source matched this query.",
        execution_metadata=[],
        created_at=datetime.now(timezone.utc),
    )
