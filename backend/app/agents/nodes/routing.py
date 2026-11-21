"""Node 2: grounded routing recommendation using backend-provided records."""

from __future__ import annotations

import json
import time
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.agents.prompts.routing import ROUTING_SYSTEM_PROMPT, ROUTING_USER_PROMPT
from app.agents.services.llm_service import LlmError, LlmService
from app.agents.state import (
    AgentState,
    RoutingOutput,
    append_execution,
    append_warning,
)
from app.agents.tools.department_lookup import get_routing_options
from app.models import User

RoutingNode = Callable[[AgentState], AgentState]


def _fallback_department(state: AgentState, departments: list[dict]) -> dict | None:
    for department in departments:
        if department["id"] == state.get("department_id"):
            return department
    return departments[0] if departments else None


def make_routing_node(llm: LlmService, db: Session, user: User) -> RoutingNode:
    departments, staff = get_routing_options(db, user)
    department_ids = {item["id"] for item in departments}
    staff_ids = {item["id"] for item in staff}

    def routing_node(state: AgentState) -> AgentState:
        started = time.perf_counter()
        user_prompt = ROUTING_USER_PROMPT.format(
            subject=state.get("subject", ""),
            description=state.get("query_text", ""),
            classification=json.dumps(state.get("classification") or {}, ensure_ascii=False),
            departments=json.dumps(departments, ensure_ascii=False),
            staff=json.dumps(staff, ensure_ascii=False),
            current_department=state.get("department_name") or "unknown",
        )

        proposed: RoutingOutput | None = None
        try:
            result = llm.generate_structured(
                schema=RoutingOutput,
                system_prompt=ROUTING_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            proposed = result.data
            attempts = result.metadata.get("attempts")
        except LlmError as exc:
            attempts = 1
            state = append_warning(
                state,
                {"node": "routing", "code": exc.category, "message": exc.message},
            )

        issues: list[str] = []
        source = "model"
        department = None
        if proposed is not None:
            department = next(
                (item for item in departments if item["id"] == proposed.department_id), None
            )
            if department is None and proposed.department_name:
                wanted = proposed.department_name.casefold().strip()
                department = next(
                    (item for item in departments if item["name"].casefold().strip() == wanted),
                    None,
                )

        if department is None:
            department = _fallback_department(state, departments)
            source = "validated_fallback"
            issues.append("Model department was unavailable; used the ticket's validated department.")

        selected_staff = None
        if proposed is not None and proposed.staff_id in staff_ids:
            selected_staff = next((item for item in staff if item["id"] == proposed.staff_id), None)
        elif proposed is not None and proposed.staff_id is not None:
            issues.append("Model staff recommendation was not eligible; no staff member was recommended.")

        reason = proposed.reason if proposed else "Model unavailable; recommendation is based on existing ticket data."
        confidence = proposed.confidence if proposed and source == "model" else 0.0
        department_recommendation = {
            "department_id": department["id"] if department else None,
            "department_name": department["name"] if department else None,
            "confidence": confidence,
            "reason": reason,
            "source": source,
        }
        staff_recommendation = None
        if selected_staff:
            staff_recommendation = {
                "staff_id": selected_staff["id"],
                "staff_name": selected_staff["name"],
                "role": selected_staff["role"],
                "confidence": confidence,
                "reason": reason,
            }

        state = {
            **state,
            "department_recommendation": department_recommendation,
            "staff_recommendation": staff_recommendation,
            "routing_explanation": reason,
            "execution": append_execution(
                state,
                {
                    "node": "routing",
                    "status": "completed" if proposed else "fallback",
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "attempts": attempts,
                    "detail": "; ".join(issues) if issues else None,
                },
            ),
        }
        for issue in issues:
            state = append_warning(
                state,
                {"node": "routing", "code": "validated_fallback", "message": issue},
            )
        return state

    return routing_node
