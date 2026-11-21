"""Deterministic Phase 6 agent tests with mocked LLM responses."""

from __future__ import annotations

import pytest

from app.agents.graph import run_workflow
from app.agents.nodes.knowledge_research import make_knowledge_node
from app.agents.nodes.response_drafting import make_drafting_node
from app.agents.nodes.routing import make_routing_node
from app.agents.nodes.validation import validation_node
from app.agents.services.llm_service import LlmError, LlmService
from app.agents.state import ClassificationOutput
from app.agents.tools.knowledge_search import (
    InMemoryKnowledgeRepository,
    KnowledgePassage,
)
from app.agents.tools.privacy import sanitize_ticket_text
from app.core.config import settings
from tests.ai_helpers import (
    make_llm,
    valid_classification,
    valid_draft,
    valid_routing,
)


def _base_state(department_id: int) -> dict:
    return {
        "ticket_id": 1,
        "subject": "Password reset question",
        "query_text": "How do I reset my password for the student portal?",
        "category": "account_access",
        "priority": "normal",
        "department_id": department_id,
        "department_name": "Registry",
        "status": "new",
        "student_context": {"context_kind": "minimal_ticket_metadata"},
        "knowledge": [],
        "errors": [],
        "warnings": [],
        "execution": [],
    }


def test_classification_output_validation_rejects_invalid_structured_response():
    llm, client = make_llm([{"intent": "too short"}, {"intent": "also short"}])
    with pytest.raises(LlmError) as caught:
        llm.generate_structured(
            schema=ClassificationOutput,
            system_prompt="classify",
            user_prompt="ticket text",
        )
    assert caught.value.category == "invalid_response"
    assert len(client.completions.calls) == settings.AI_LLM_ATTEMPTS


def test_classification_retries_then_accepts_valid_response():
    llm, client = make_llm([{"intent": "bad"}, valid_classification()])
    result = llm.generate_structured(
        schema=ClassificationOutput,
        system_prompt="classify",
        user_prompt="ticket text",
    )
    assert result.data.urgency == "normal"
    assert result.metadata["attempts"] == 2
    assert len(client.completions.calls) == 2


def test_workflow_deadline_prevents_provider_calls_when_expired():
    llm, client = make_llm([valid_classification()])
    expired = llm.with_deadline(-1.0)
    with pytest.raises(LlmError) as caught:
        expired.generate_structured(
            schema=ClassificationOutput,
            system_prompt="classify",
            user_prompt="ticket text",
        )
    assert caught.value.category == "timeout"
    assert client.completions.calls == []


def test_provider_exception_is_redacted():
    secret_marker = "sk-test-secret-marker"
    llm, _ = make_llm([RuntimeError(secret_marker)])
    with pytest.raises(LlmError) as caught:
        llm.generate_structured(
            schema=ClassificationOutput,
            system_prompt="classify",
            user_prompt="ticket text",
        )
    assert caught.value.category == "provider_error"
    assert secret_marker not in str(caught.value)


def test_ticket_text_is_redacted_before_prompting():
    redacted = sanitize_ticket_text(
        "Contact ada@university.edu or +1 555 123 4567. "
        "password=sk-test-secret-1234567890 reference 12345678"
    )
    assert "ada@university.edu" not in redacted
    assert "555 123 4567" not in redacted
    assert "sk-test-secret-1234567890" not in redacted
    assert "12345678" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED]" in redacted or "[REDACTED_TOKEN]" in redacted
    assert "[REDACTED_NUMBER]" in redacted


def test_routing_falls_back_when_model_recommends_unknown_ids(db_session, users, departments):
    llm, _ = make_llm(
        [
            {
                "department_id": 999999,
                "department_name": "Unknown Department",
                "staff_id": 999999,
                "staff_name": "Unknown Staff",
                "confidence": 0.99,
                "reason": "This department does not exist.",
            }
        ]
    )
    state = _base_state(departments["registry"].id)
    node = make_routing_node(llm, db_session, users["admin"])
    result = node(state)

    recommendation = result["department_recommendation"]
    assert recommendation["department_id"] == departments["registry"].id
    assert recommendation["source"] == "validated_fallback"
    assert result["staff_recommendation"] is None
    assert any(warning["code"] == "validated_fallback" for warning in result["warnings"])


def test_knowledge_retrieval_and_abstention():
    document = KnowledgePassage(
        source_id="TEST-FAQ-1",
        title="Approved test guidance",
        excerpt="Approved test guidance for account access and password reset.",
        tags=["password", "reset"],
    )
    repository = InMemoryKnowledgeRepository([document])
    matches = repository.search("How do I reset my password?")
    assert matches
    assert matches[0]["source_id"] == "TEST-FAQ-1"

    empty = InMemoryKnowledgeRepository([])
    result = make_knowledge_node(empty)(_base_state(1))
    assert result["no_evidence"] is True
    assert result["knowledge"] == []
    assert "No approved knowledge source" in result["abstention_reason"]


def test_draft_source_references_are_filtered_against_evidence():
    proposed = valid_draft()
    proposed["source_ids"] = ["TEST-FAQ-1", "not-a-source"]
    llm, _ = make_llm([proposed])
    result = make_drafting_node(llm)(
        {
            **_base_state(1),
            "classification": valid_classification(),
            "no_evidence": False,
            "knowledge": [
                {
                    "source_id": "TEST-FAQ-1",
                    "title": "Approved test guidance",
                    "excerpt": "Approved test text.",
                    "relevance_score": 0.4,
                }
            ],
        }
    )
    draft = result["draft"]
    assert draft["body"]
    assert "TEST-FAQ-1" in draft["source_ids"]
    assert "not-a-source" not in draft["source_ids"]
    assert "[TEST-FAQ-1]" in draft["body"]
    assert "[not-a-source]" not in draft["body"]


def test_validation_requires_uncertainty_when_no_evidence_exists():
    state = {
        **_base_state(1),
        "classification": valid_classification(),
        "department_recommendation": {"department_id": 1, "confidence": 0.7},
        "no_evidence": True,
        "knowledge": [],
        "draft": valid_draft("Here is the exact university password policy you must follow."),
    }
    failed = validation_node(state)
    assert failed["validation"]["passed"] is False
    assert any("uncertainty" in issue for issue in failed["validation"]["issues"])

    abstaining = {**state, "draft": valid_draft()}
    passed = validation_node(abstaining)
    assert passed["validation"]["passed"] is True


def test_validation_requires_inline_citations_when_evidence_exists():
    evidence = [
        {
            "source_id": "TEST-FAQ-1",
            "title": "Approved test guidance",
            "excerpt": "Approved test text.",
            "relevance_score": 0.5,
        }
    ]
    state = {
        **_base_state(1),
        "classification": valid_classification(),
        "department_recommendation": {"department_id": 1, "confidence": 0.7},
        "no_evidence": False,
        "knowledge": evidence,
        "draft": {**valid_draft(), "source_ids": ["TEST-FAQ-1"]},
    }
    failed = validation_node(state)
    assert failed["validation"]["passed"] is False
    assert any("does not contain all" in issue for issue in failed["validation"]["issues"])

    cited = {
        **state,
        "draft": {
            **valid_draft("Approved guidance applies here. [TEST-FAQ-1]"),
            "source_ids": ["TEST-FAQ-1"],
        },
    }
    assert validation_node(cited)["validation"]["passed"] is True


def test_langgraph_visits_all_nodes_in_order(db_session, users, departments):
    llm, _ = make_llm(
        [
            valid_classification(),
            valid_routing(departments["registry"].id),
            valid_draft(),
        ]
    )
    result = run_workflow(
        _base_state(departments["registry"].id),
        llm=llm,
        db=db_session,
        user=users["admin"],
        knowledge_repository=InMemoryKnowledgeRepository([]),
    )
    assert [step["node"] for step in result["execution"]] == [
        "classification",
        "routing",
        "knowledge_research",
        "response_drafting",
        "validation",
    ]
    assert result["validation"]["passed"] is True
    assert result["no_evidence"] is True
    assert result["draft"]["needs_staff_review"] is True


def test_langgraph_stops_after_fatal_classification_error(db_session, users, departments):
    llm, _ = make_llm([{"invalid": True}, {"invalid": True}])
    result = run_workflow(
        _base_state(departments["registry"].id),
        llm=llm,
        db=db_session,
        user=users["admin"],
        knowledge_repository=InMemoryKnowledgeRepository([]),
    )
    assert [step["node"] for step in result["execution"]] == ["classification"]
    assert result["errors"][0]["node"] == "classification"
    assert result.get("draft") is None
