"""Node 4: grounded draft generation with a safe abstention fallback."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable

from app.agents.prompts.response import DRAFT_SYSTEM_PROMPT, DRAFT_USER_PROMPT
from app.agents.services.llm_service import LlmError, LlmService
from app.agents.state import (
    AgentState,
    DraftOutput,
    append_execution,
    append_warning,
)

DraftingNode = Callable[[AgentState], AgentState]
_CITATION_RE = re.compile(r"\[([^\[\]]{1,80})\]")

_FALLBACK_BODY = (
    "Thanks for contacting us. I could not verify an answer from approved university "
    "sources, so I cannot provide a definitive response yet. A staff member will review "
    "your query and confirm the next step."
)


def _safe_draft(state: AgentState) -> dict:
    return {
        "body": _FALLBACK_BODY,
        "language": (state.get("classification") or {}).get("language") or "en",
        "confidence": 0.0,
        "source_ids": [],
        "needs_staff_review": True,
    }


def make_drafting_node(llm: LlmService) -> DraftingNode:
    def drafting_node(state: AgentState) -> AgentState:
        started = time.perf_counter()
        evidence = state.get("knowledge", [])
        allowed_sources = [item["source_id"] for item in evidence]
        user_prompt = DRAFT_USER_PROMPT.format(
            subject=state.get("subject", ""),
            description=state.get("query_text", ""),
            classification=json.dumps(state.get("classification") or {}, ensure_ascii=False),
            routing=json.dumps(
                {
                    "department": state.get("department_recommendation") or {},
                    "staff": state.get("staff_recommendation") or {},
                },
                ensure_ascii=False,
            ),
            evidence=json.dumps(evidence, ensure_ascii=False),
            source_ids=", ".join(allowed_sources) if allowed_sources else "none",
        )

        try:
            result = llm.generate_structured(
                schema=DraftOutput,
                system_prompt=DRAFT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            draft = result.data.model_dump()
            attempts = result.metadata.get("attempts")
            status = "completed"
        except LlmError as exc:
            draft = _safe_draft(state)
            attempts = 1
            status = "fallback"
            state = append_warning(
                state,
                {"node": "response_drafting", "code": exc.category, "message": exc.message},
            )

        cited = [source_id for source_id in draft.get("source_ids", []) if source_id in allowed_sources]
        if cited != draft.get("source_ids", []):
            state = append_warning(
                state,
                {
                    "node": "response_drafting",
                    "code": "unverified_sources_removed",
                    "message": "Unrecognized source references were removed from the draft.",
                },
            )
        draft["source_ids"] = cited
        body = str(draft.get("body") or "")
        # Remove any bracketed reference that the approved repository did not
        # supply, so a hallucinated citation can never reach a published reply.
        body = _CITATION_RE.sub(
            lambda match: match.group(0) if match.group(1) in allowed_sources else "",
            body,
        )
        if state.get("no_evidence"):
            draft["source_ids"] = []
            body = _CITATION_RE.sub("", body)
        elif cited:
            missing = [source_id for source_id in cited if f"[{source_id}]" not in body]
            if missing:
                suffix = "\nSources: " + ", ".join(f"[{source_id}]" for source_id in cited)
                body = body.rstrip()
                if len(body) + len(suffix) > 4000:
                    body = body[: max(0, 4000 - len(suffix))].rstrip()
                body = f"{body}{suffix}"
        draft["body"] = body.strip()

        return {
            **state,
            "draft": draft,
            "execution": append_execution(
                state,
                {
                    "node": "response_drafting",
                    "status": status,
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "attempts": attempts,
                    "detail": "abstention_fallback" if status == "fallback" else None,
                },
            ),
        }

    return drafting_node
