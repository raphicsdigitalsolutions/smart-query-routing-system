"""Application service that runs, persists and approves AI drafts.

This is the only write boundary for Phase 6. It reuses ticket authorization and
message creation services, so agents never bypass existing permissions.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.agents.graph import run_workflow
from app.agents.services.llm_service import LlmError, LlmService, get_llm_service
from app.agents.state import AgentState
from app.agents.tools.knowledge_search import InMemoryKnowledgeRepository
from app.agents.tools.privacy import sanitize_ticket_text
from app.core.config import settings
from app.core.errors import AppError
from app.models import AgentRun, Message, Ticket, TicketAiAnalysis, User
from app.schemas.ai import AiAnalysisResponse, AiDraftApprovalResponse
from app.schemas.ticket import MessageCreate, MessageResponse
from app.services import byok
from app.services.audit import record_audit
from app.services.knowledge import get_database_knowledge_repository
from app.services.tickets import create_message, get_accessible_ticket

AI_OPERATOR_ROLES = {"staff", "hod", "admin"}
_AGENT_RUN_STATUSES = {"completed", "failed", "abstained"}

_ERROR_STATUS = {
    "not_configured": 503,
    "invalid_api_key": 503,
    "insufficient_credits": 503,
    "model_access": 503,
    "rate_limited": 429,
    "network_error": 504,
    "timeout": 504,
    "workflow_timeout": 504,
    "invalid_response": 502,
    "provider_error": 502,
    "ai_analysis_failed": 502,
}


class _UsageTracker:
    """Pass-through LLM wrapper that collects token totals for run telemetry."""

    def __init__(self, service: LlmService) -> None:
        self._service = service
        self.model: str | None = None
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.calls = 0

    def generate_structured(self, **kwargs: Any):
        result = self._service.generate_structured(**kwargs)
        metadata = result.metadata or {}
        self.calls += 1
        if metadata.get("model"):
            self.model = str(metadata["model"])
        for field, attribute in (
            ("prompt_tokens", "prompt_tokens"),
            ("completion_tokens", "completion_tokens"),
        ):
            value = metadata.get(field)
            if isinstance(value, int) and not isinstance(value, bool):
                setattr(self, attribute, getattr(self, attribute) + value)
        return result


def _resolve_agent_api_key(db: Session, user: User) -> str | None:
    """Return a usable key for a real run, enforcing the BYOK-only policy."""
    personal = byok.resolve_api_key(db, user.id)
    if personal:
        return personal
    fallback_allowed = (
        settings.ALLOW_GLOBAL_OPENAI_FALLBACK
        and str(settings.ENVIRONMENT).strip().lower() != "production"
    )
    if fallback_allowed:
        return settings.OPENAI_API_KEY or None
    raise AppError(
        "A personal OpenAI API key is required to run AI analysis. Add one in Settings.",
        402,
        code="ai_personal_key_required",
    )


def _record_agent_run(
    db: Session,
    *,
    ticket: Ticket,
    user: User,
    analysis: TicketAiAnalysis,
    started: float,
    tracker: _UsageTracker | None = None,
) -> None:
    """Persist one bounded-agent telemetry row for a persisted analysis."""
    has_usage = tracker is not None and tracker.calls > 0
    db.add(
        AgentRun(
            ticket_id=ticket.id,
            requested_by_id=user.id,
            analysis_id=analysis.id,
            workflow="ticket_analysis",
            model=(tracker.model if tracker and tracker.model else settings.OPENAI_MODEL),
            status=analysis.status if analysis.status in _AGENT_RUN_STATUSES else "failed",
            prompt_tokens=tracker.prompt_tokens if has_usage else None,
            completion_tokens=tracker.completion_tokens if has_usage else None,
            permission_outcome="allowed",
            duration_ms=max(0, int((time.perf_counter() - started) * 1000)),
        )
    )


def _ensure_ai_operator(user: User) -> None:
    if user.role not in AI_OPERATOR_ROLES:
        raise AppError("AI operations require staff access", 403, code="forbidden")


def _enforce_rate_limit(db: Session, user: User) -> None:
    """Bound requests per user using the durable AgentRun audit trail."""
    window_start = datetime.now(timezone.utc) - timedelta(seconds=60)
    recent = db.scalar(
        select(func.count(AgentRun.id)).where(
            AgentRun.requested_by_id == user.id,
            AgentRun.created_at >= window_start,
        )
    )
    if int(recent or 0) >= settings.AI_RATE_LIMIT_PER_MINUTE:
        raise AppError(
            f"AI rate limit of {settings.AI_RATE_LIMIT_PER_MINUTE} runs per minute reached",
            429,
            code="ai_rate_limited",
        )


def _initial_state(ticket: Ticket) -> AgentState:
    # Deliberately excludes student name, email, internal notes and other domain
    # records. Ticket text is redacted before it becomes untrusted prompt data.
    subject = sanitize_ticket_text(ticket.subject)
    description = sanitize_ticket_text(ticket.description)
    return {
        "ticket_id": ticket.id,
        "subject": subject,
        "query_text": f"{subject}\n\n{description}",
        "category": ticket.category,
        "priority": ticket.priority,
        "department_id": ticket.department_id,
        "department_name": ticket.department.name if ticket.department else None,
        "status": ticket.status,
        "student_context": {
            "context_kind": "minimal_ticket_metadata",
            "department_id": ticket.department_id,
            "ticket_status": ticket.status,
            "is_escalated": ticket.is_escalated,
        },
        "knowledge": [],
        "errors": [],
        "warnings": [],
        "execution": [],
    }


def _next_version(db: Session, ticket_id: int) -> int:
    latest = db.scalar(select(func.max(TicketAiAnalysis.version)).where(TicketAiAnalysis.ticket_id == ticket_id))
    return int(latest or 0) + 1


def _analysis_payload(row: TicketAiAnalysis) -> dict[str, Any]:
    return {
        "id": row.id,
        "ticket_id": row.ticket_id,
        "version": row.version,
        "status": row.status,
        "is_current": row.is_current,
        "classification": row.classification_json,
        "priority_recommendation": row.priority_recommendation,
        "department_recommendation": row.department_recommendation_json,
        "staff_recommendation": row.staff_recommendation_json,
        "knowledge_sources": row.knowledge_sources_json or [],
        "no_evidence": row.no_evidence,
        "draft": row.draft_json,
        "validation": row.validation_json,
        "confidence": row.confidence,
        "abstention_reason": row.abstention_reason,
        "error": (
            {"code": row.error_code, "message": row.error_message}
            if row.error_code
            else None
        ),
        "execution_metadata": row.execution_metadata_json or [],
        "approved_message_id": row.approved_message_id,
        "approved_at": row.approved_at,
        "created_at": row.created_at,
    }


def _persist_failed(
    db: Session,
    *,
    ticket: Ticket,
    user: User,
    error_code: str,
    error_message: str,
    execution_metadata: list[dict[str, Any]] | None = None,
    tracker: _UsageTracker | None = None,
    started: float | None = None,
) -> TicketAiAnalysis:
    db.execute(
        update(TicketAiAnalysis)
        .where(TicketAiAnalysis.ticket_id == ticket.id, TicketAiAnalysis.is_current.is_(True))
        .values(is_current=False)
    )
    row = TicketAiAnalysis(
        ticket_id=ticket.id,
        requested_by_id=user.id,
        version=_next_version(db, ticket.id),
        status="failed",
        is_current=True,
        error_code=error_code[:50],
        error_message=error_message[:1000],
        execution_metadata_json=execution_metadata or [],
        knowledge_sources_json=[],
        no_evidence=True,
        abstention_reason="AI analysis failed; no draft was produced.",
    )
    db.add(row)
    db.flush()
    _record_agent_run(
        db,
        ticket=ticket,
        user=user,
        analysis=row,
        started=started if started is not None else time.perf_counter(),
        tracker=tracker,
    )
    record_audit(
        db,
        actor=user,
        action="ai.analysis_failed",
        entity_type="ticket",
        entity_id=ticket.id,
        details={"analysis_id": row.id, "version": row.version, "error_code": row.error_code},
    )
    db.commit()
    db.refresh(row)
    return row


def _raise_analysis_error(error_code: str, message: str) -> None:
    code = error_code if error_code.startswith("ai_") else f"ai_{error_code}"
    raise AppError(
        message,
        _ERROR_STATUS.get(error_code, 502),
        code=code,
    )


def run_ticket_analysis(
    db: Session,
    ticket_id: int,
    user: User,
    *,
    llm: LlmService | None = None,
    knowledge_repository: InMemoryKnowledgeRepository | None = None,
) -> AiAnalysisResponse:
    """Run the bounded graph and persist its output. No message is published."""
    _ensure_ai_operator(user)
    ticket = get_accessible_ticket(db, ticket_id, user)
    _enforce_rate_limit(db, user)
    started = time.perf_counter()
    # Injected LLMs (tests) bypass credential resolution entirely. Real runs
    # use the requesting user's personal key, with tightly gated fallback.
    if llm is None:
        api_key = _resolve_agent_api_key(db, user)
        service = (get_llm_service(api_key=api_key) if api_key else get_llm_service())
    else:
        service = llm
    # A monotonic deadline is enforced by the LLM wrapper on every call; the
    # fixed graph shape bounds the number of calls without spawning threads.
    tracker = _UsageTracker(service.with_deadline(settings.AI_GRAPH_TIMEOUT_SECONDS))
    # Real runs read only approved, active knowledge from the database; tests
    # may inject an in-memory repository without touching persisted content.
    repository = knowledge_repository or get_database_knowledge_repository(db, user=user)

    try:
        state = run_workflow(
            _initial_state(ticket),
            llm=tracker,
            db=db,
            user=user,
            knowledge_repository=repository,
        )
    except LlmError as exc:
        _persist_failed(
            db,
            ticket=ticket,
            user=user,
            error_code=exc.category,
            error_message=exc.message,
            tracker=tracker,
            started=started,
        )
        _raise_analysis_error(exc.category, exc.message)
    errors = state.get("errors") or []
    if errors:
        first = errors[0]
        code = str(first.get("code") or "ai_analysis_failed")
        message = str(first.get("message") or "AI analysis could not be completed.")
        _persist_failed(
            db,
            ticket=ticket,
            user=user,
            error_code=code[:50],
            error_message=message,
            execution_metadata=state.get("execution") or [],
            tracker=tracker,
            started=started,
        )
        _raise_analysis_error(code, message)

    validation = state.get("validation") or {}
    confidence = state.get("confidence")
    if confidence is None and isinstance(validation.get("overall_confidence"), (int, float)):
        confidence = float(validation["overall_confidence"])

    version = _next_version(db, ticket.id)
    db.execute(
        update(TicketAiAnalysis)
        .where(TicketAiAnalysis.ticket_id == ticket.id, TicketAiAnalysis.is_current.is_(True))
        .values(is_current=False)
    )
    row = TicketAiAnalysis(
        ticket_id=ticket.id,
        requested_by_id=user.id,
        version=version,
        status="completed",
        is_current=True,
        classification_json=state.get("classification"),
        priority_recommendation=state.get("priority_recommendation"),
        department_recommendation_json=state.get("department_recommendation"),
        staff_recommendation_json=state.get("staff_recommendation"),
        knowledge_sources_json=state.get("knowledge", []),
        draft_json=state.get("draft"),
        validation_json=validation or None,
        no_evidence=bool(state.get("no_evidence")),
        confidence=confidence,
        abstention_reason=state.get("abstention_reason"),
        execution_metadata_json=state.get("execution", []),
    )
    db.add(row)
    db.flush()
    _record_agent_run(
        db,
        ticket=ticket,
        user=user,
        analysis=row,
        started=started,
        tracker=tracker,
    )
    record_audit(
        db,
        actor=user,
        action="ai.analysis_created",
        entity_type="ticket",
        entity_id=ticket.id,
        details={"analysis_id": row.id, "version": row.version, "validation_passed": validation.get("passed")},
    )
    db.commit()
    db.refresh(row)
    return AiAnalysisResponse(**_analysis_payload(row))


def get_latest_analysis(db: Session, ticket_id: int, user: User) -> AiAnalysisResponse:
    _ensure_ai_operator(user)
    ticket = get_accessible_ticket(db, ticket_id, user)
    row = db.scalar(
        select(TicketAiAnalysis)
        .where(TicketAiAnalysis.ticket_id == ticket.id, TicketAiAnalysis.is_current.is_(True))
        .order_by(TicketAiAnalysis.version.desc())
    )
    if row is None:
        raise AppError("No AI analysis exists for this ticket", 404, code="ai_analysis_not_found")
    return AiAnalysisResponse(**_analysis_payload(row))


def approve_draft(db: Session, ticket_id: int, user: User) -> AiDraftApprovalResponse:
    """Publish a draft only after explicit authorized human approval."""
    _ensure_ai_operator(user)
    ticket = get_accessible_ticket(db, ticket_id, user)

    statement = (
        select(TicketAiAnalysis)
        .where(TicketAiAnalysis.ticket_id == ticket.id, TicketAiAnalysis.is_current.is_(True))
        .order_by(TicketAiAnalysis.version.desc())
    )
    if db.get_bind().dialect.name == "postgresql":
        statement = statement.with_for_update()
    analysis = db.scalar(statement)
    if analysis is None or not analysis.draft_json:
        raise AppError("No AI draft is available for this ticket", 409, code="ai_no_draft")

    if analysis.approved_message_id:
        already = db.get(Message, analysis.approved_message_id)
        if already is not None:
            return AiDraftApprovalResponse(
                analysis_id=analysis.id,
                message=MessageResponse.model_validate(already),
                already_approved=True,
            )

    validation = analysis.validation_json or {}
    if validation and validation.get("passed") is False:
        raise AppError(
            "This draft failed AI validation and cannot be approved",
            409,
            code="ai_validation_failed",
        )

    body = str((analysis.draft_json or {}).get("body") or "").strip()
    if not body:
        raise AppError("The stored AI draft is empty", 409, code="ai_no_draft")

    published = create_message(
        db,
        ticket.id,
        MessageCreate(message_body=body, is_internal=False),
        user,
        commit=False,
    )
    analysis.approved_by_id = user.id
    analysis.approved_at = datetime.now(timezone.utc)
    analysis.approved_message_id = published.id
    record_audit(
        db,
        actor=user,
        action="ai.draft_approved",
        entity_type="ticket",
        entity_id=ticket.id,
        details={
            "analysis_id": analysis.id,
            "version": analysis.version,
            "message_id": published.id,
            "is_internal": False,
        },
    )
    db.commit()
    return AiDraftApprovalResponse(
        analysis_id=analysis.id,
        message=published,
        already_approved=False,
    )
