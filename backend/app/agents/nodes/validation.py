"""Deterministic final validation: no model call, no side effects."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone

from app.agents.state import AgentState, append_execution
from app.core.config import settings

_UNCERTAINTY_MARKERS = (
    "cannot verify",
    "can't verify",
    "unable to verify",
    "unable to confirm",
    "cannot confirm",
    "insufficient",
    "no verified",
    "no approved",
    "staff will review",
    "staff member will review",
    "staff will confirm",
)


def _has_uncertainty(body: str) -> bool:
    lowered = body.casefold()
    return any(marker in lowered for marker in _UNCERTAINTY_MARKERS)


def validation_node(state: AgentState) -> AgentState:
    started = time.perf_counter()
    issues: list[str] = []
    classification = state.get("classification") or {}
    routing = state.get("department_recommendation") or {}
    draft = state.get("draft") or {}
    evidence = state.get("knowledge", [])
    no_evidence = bool(state.get("no_evidence"))

    classification_confidence = float(classification.get("confidence") or 0)
    draft_confidence = float(draft.get("confidence") or 0)

    if not classification:
        issues.append("No classification result was produced.")
    elif classification_confidence < settings.AI_MIN_CONFIDENCE:
        issues.append("Classification confidence is below the configured minimum.")

    if not routing.get("department_id"):
        issues.append("No validated department recommendation is available.")

    body = str(draft.get("body") or "").strip()
    if len(body) < 20:
        issues.append("Draft response is missing or too short.")
    if len(body) > 4000:
        issues.append("Draft response exceeds the configured length limit.")

    source_ids = set(draft.get("source_ids") or [])
    allowed_source_ids = {item["source_id"] for item in evidence}
    if not source_ids.issubset(allowed_source_ids):
        issues.append("Draft cites sources that were not retrieved from the approved repository.")

    inline_references = set(re.findall(r"\[([^\[\]]{1,80})\]", body))
    unapproved_references = inline_references - allowed_source_ids
    if unapproved_references:
        issues.append("Draft body contains source references outside the approved repository.")
    missing_references = source_ids - inline_references
    if missing_references:
        issues.append("Draft body does not contain all of its approved source citations.")

    if no_evidence:
        if source_ids:
            issues.append("An abstaining draft must not cite sources.")
        if body and not _has_uncertainty(body):
            issues.append("No-evidence draft does not clearly state uncertainty.")
    else:
        if not source_ids:
            issues.append("Evidence was available but the draft cited no trusted source.")
        if draft_confidence < settings.AI_MIN_CONFIDENCE:
            issues.append("Draft confidence is below the configured minimum.")

    confidences = [
        value
        for value in (classification_confidence, float(routing.get("confidence") or 0), draft_confidence)
        if value is not None
    ]
    overall_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
    passed = not issues

    abstention_reason = state.get("abstention_reason")
    if no_evidence and not abstention_reason:
        abstention_reason = "No approved knowledge source matched this query."
    if not passed and not abstention_reason:
        abstention_reason = "Validation did not pass; staff review is required before any use."

    validation = {
        "passed": passed,
        "issues": issues,
        "overall_confidence": overall_confidence,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    return {
        **state,
        "validation": validation,
        "confidence": overall_confidence,
        "abstention_reason": abstention_reason,
        "execution": append_execution(
            state,
            {
                "node": "validation",
                "status": "passed" if passed else "needs_review",
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "detail": f"{len(issues)} issue(s)",
            },
        ),
    }
