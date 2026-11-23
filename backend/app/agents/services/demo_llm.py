"""Ticket-grounded deterministic local/demo LLM responder.

Used only for disposable local demo keys (``sk-local-test-*`` or ``sk-demo-*``)
in non-production environments and deterministic consistency tests. Real OpenAI
API keys continue to use the live OpenAI SDK client in :mod:`llm_service`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.agents.state import (
    ClassificationOutput,
    ConnectivityOutput,
    DraftOutput,
    RoutingOutput,
)
from app.core.config import settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_DEMO_KEY_PREFIXES = ("sk-local-test-", "sk-demo-")


def is_demo_api_key(api_key: str | None) -> bool:
    """Return True only for explicit local demo keys outside production."""
    if not api_key:
        return False
    if str(settings.ENVIRONMENT).strip().lower() == "production":
        return False
    cleaned = api_key.strip()
    return cleaned.startswith(_DEMO_KEY_PREFIXES)


def _tokens(text: str) -> set[str]:
    return {tok for tok in _TOKEN_RE.findall(text.lower()) if len(tok) > 1}


def _extract_ticket_text(user_prompt: str) -> tuple[str, str]:
    """Extract (subject, description) from classification, routing or drafting prompts."""
    cls_match = re.search(
        r"Subject:\s*(?P<subject>[^\n]*)\s*Description:\s*(?P<desc>.*?)\s*(?:Existing ticket metadata|Classifier result:)",
        user_prompt,
        flags=re.DOTALL,
    )
    if cls_match:
        return (
            cls_match.group("subject").strip(),
            cls_match.group("desc").strip(),
        )

    draft_match = re.search(
        r"Subject:\s*(?P<subject>[^\n]*)\s*Student query:\s*(?P<desc>.*?)\s*Classification:",
        user_prompt,
        flags=re.DOTALL,
    )
    if draft_match:
        return (
            draft_match.group("subject").strip(),
            draft_match.group("desc").strip(),
        )

    return ("", user_prompt.strip())


def _extract_json_block(user_prompt: str, header: str, next_header: str | None = None) -> Any:
    if next_header:
        pattern = rf"{re.escape(header)}\s*(?P<payload>.*?)\s*{re.escape(next_header)}"
    else:
        pattern = rf"{re.escape(header)}\s*(?P<payload>.*)\Z"
    match = re.search(pattern, user_prompt, flags=re.DOTALL)
    if not match:
        return None
    raw = match.group("payload").strip()
    raw = re.sub(r"^<<<[A-Z_]+\s*", "", raw)
    raw = re.sub(r"\s*[A-Z_]+>>>$", "", raw)
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return None


def _detect_urgency(full_text: str, user_prompt: str) -> str:
    lowered = full_text.lower()
    if any(word in lowered for word in ("emergency", "critical", "immediately", "exam clash")):
        return "urgent"
    if any(
        word in lowered
        for word in (
            "urgent",
            "overdue",
            "24 hours",
            "deadline",
            "delayed",
            "payment delay",
            "delay",
            "locked out",
            "cannot access",
            "unable to access",
            "fellowship",
        )
    ):
        return "high"
    existing_prio = re.search(r"Existing priority:\s*([a-z_]+)", user_prompt, flags=re.IGNORECASE)
    if existing_prio and existing_prio.group(1).lower() in {"high", "urgent"}:
        return existing_prio.group(1).lower()
    return "normal"


def _extract_matched_entities(lowered: str, candidates: list[tuple[str, str]]) -> list[str]:
    found: list[str] = []
    for needle, label in candidates:
        if needle in lowered and label not in found:
            found.append(label)
        if len(found) >= 7:
            break
    return found


def _classify_prompt(user_prompt: str) -> dict[str, Any]:
    subject, description = _extract_ticket_text(user_prompt)
    full_text = f"{subject}\n{description}".strip()
    lowered = full_text.lower()
    urgency = _detect_urgency(full_text, user_prompt)

    cs_oop_terms = [
        ("java", "Java"),
        ("object-oriented", "object-oriented programming"),
        ("oop", "OOP"),
        ("classes", "classes"),
        ("class", "classes"),
        ("objects", "objects"),
        ("inheritance", "inheritance"),
        ("polymorphism", "polymorphism"),
        ("encapsulation", "encapsulation"),
        ("programming assignment", "programming assignment"),
        ("computer science", "Computer Science"),
        ("instructor", "Computer Science instructor"),
        ("data structures", "data structures"),
        ("algorithm", "algorithms"),
        ("debugging", "debugging"),
    ]
    cs_grading_terms = [
        ("grading rubric", "grading rubric"),
        ("rubric", "grading rubric"),
        ("regrade", "regrade review"),
        ("unit tests", "automated unit tests"),
        ("complexity analysis", "complexity analysis"),
        ("weights", "grading weights"),
        ("score", "assignment score"),
        ("late submission", "late submission"),
    ]
    it_access_terms = [
        ("password reset", "password reset"),
        ("reset my password", "password reset"),
        ("password", "password"),
        ("student portal", "student portal"),
        ("portal", "student portal"),
        ("account access", "account access"),
        ("login", "portal login"),
        ("sign in", "portal login"),
        ("locked", "account lockout"),
        ("lockout", "account lockout"),
        ("mfa", "MFA verification"),
        ("two-factor", "MFA verification"),
        ("credentials", "account credentials"),
    ]
    it_network_terms = [
        ("wifi", "campus Wi-Fi"),
        ("wi-fi", "campus Wi-Fi"),
        ("wireless", "wireless network"),
        ("vpn", "VPN access"),
        ("disconnect", "network disconnection"),
    ]
    finance_terms = [
        ("scholarship", "scholarship"),
        ("stipend", "stipend disbursement"),
        ("disbursement", "stipend disbursement"),
        ("payment delay", "payment delay"),
        ("delayed", "payment delay"),
        ("delay", "payment delay"),
        ("financial aid", "financial aid"),
        ("tuition", "tuition fee"),
        ("fee waiver", "fee waiver"),
        ("enrollment form", "enrollment confirmation form"),
        ("merit", "merit scholarship"),
    ]
    registry_terms = [
        ("transcript", "academic transcript"),
        ("verification", "transcript verification"),
        ("verify", "transcript verification"),
        ("enrollment verification", "enrollment verification"),
        ("certified", "certified transcript"),
        ("student records", "student records"),
        ("registry", "Registry Office"),
        ("fellowship", "graduate fellowship"),
        ("deferral", "semester deferral"),
        ("degree audit", "degree audit"),
    ]

    cs_oop_hits = _extract_matched_entities(lowered, cs_oop_terms)
    cs_grading_hits = _extract_matched_entities(lowered, cs_grading_terms)
    it_access_hits = _extract_matched_entities(lowered, it_access_terms)
    it_network_hits = _extract_matched_entities(lowered, it_network_terms)
    finance_hits = _extract_matched_entities(lowered, finance_terms)
    registry_hits = _extract_matched_entities(lowered, registry_terms)

    scores = {
        "cs_oop": len(cs_oop_hits) * 2
        + (4 if any(k in lowered for k in ("java", "oop", "object-oriented", "inheritance", "classes")) else 0),
        "cs_grading": len(cs_grading_hits) * 2
        + (4 if any(k in lowered for k in ("rubric", "regrade", "unit tests", "weights")) else 0),
        "it_access": len(it_access_hits) * 2
        + (5 if any(k in lowered for k in ("password", "login", "locked", "lockout", "mfa", "credentials")) else 0),
        "it_network": len(it_network_hits) * 2
        + (4 if any(k in lowered for k in ("wifi", "wi-fi", "vpn", "wireless")) else 0),
        "finance": len(finance_hits) * 2
        + (5 if any(k in lowered for k in ("scholarship", "stipend", "financial aid", "fee waiver", "tuition")) else 0),
        "registry": len(registry_hits) * 2
        + (5 if any(k in lowered for k in ("transcript", "registry", "deferral", "enrollment verification")) else 0),
    }

    best_topic, best_score = max(scores.items(), key=lambda pair: pair[1])

    if best_score == 0:
        fallback_entities = [tok for tok in _TOKEN_RE.findall(lowered) if len(tok) > 3][:5]
        return {
            "intent": "general_student_support_inquiry",
            "category": "general_inquiry",
            "urgency": urgency,
            "language": "en",
            "entities": fallback_entities or ["student query"],
            "confidence": 0.62,
            "rationale": "The student query requests general university assistance and requires staff review.",
        }

    if best_topic == "cs_oop":
        has_java_oop = any(
            k in lowered for k in ("java", "oop", "object-oriented", "classes", "objects", "inheritance")
        )
        intent = (
            "request_java_oop_academic_guidance"
            if has_java_oop
            else "request_programming_coursework_guidance"
        )
        entities = cs_oop_hits or ["programming assignment", "Computer Science"]
        concepts_str = ", ".join(entities[:5])
        return {
            "intent": intent,
            "category": "academic_support",
            "urgency": urgency,
            "language": "en",
            "entities": entities,
            "confidence": 0.94,
            "rationale": (
                f"The student is requesting Computer Science academic support and instructor "
                f"guidance regarding {concepts_str}."
            ),
        }

    if best_topic == "cs_grading":
        entities = cs_grading_hits + [e for e in cs_oop_hits if e not in cs_grading_hits]
        entities = (entities or ["programming assignment", "grading rubric"])[:6]
        return {
            "intent": "grading_rubric_and_regrade_inquiry",
            "category": "academic_assessment",
            "urgency": urgency,
            "language": "en",
            "entities": entities,
            "confidence": 0.93,
            "rationale": (
                "The student is inquiring about the Computer Science programming assignment "
                "grading rubric weights and regrade review window."
            ),
        }

    if best_topic == "it_access":
        entities = it_access_hits or ["password reset", "student portal", "account access"]
        return {
            "intent": "request_password_reset_help",
            "category": "account_access",
            "urgency": urgency,
            "language": "en",
            "entities": entities[:6],
            "confidence": 0.94,
            "rationale": (
                "The student is experiencing account access issues and requesting student "
                "portal password reset and recovery assistance from IT Services."
            ),
        }

    if best_topic == "it_network":
        entities = it_network_hits or ["campus Wi-Fi", "network connectivity"]
        return {
            "intent": "report_campus_network_issue",
            "category": "it_support",
            "urgency": urgency,
            "language": "en",
            "entities": entities[:6],
            "confidence": 0.91,
            "rationale": (
                "The student is reporting a campus wireless network or VPN connectivity issue "
                "for IT Services technical support."
            ),
        }

    if best_topic == "finance":
        has_delay = any(k in lowered for k in ("delay", "delayed", "late", "not received", "overdue"))
        intent = (
            "report_scholarship_payment_delay"
            if has_delay
            else "scholarship_stipend_disbursement_inquiry"
        )
        entities = finance_hits or ["scholarship", "stipend disbursement", "financial aid"]
        rationale = (
            "The student is reporting a scholarship or financial aid stipend payment delay "
            "and requesting disbursement verification from Scholarships & Financial Aid."
            if has_delay
            else "The student is asking about merit scholarship stipend disbursement schedules "
            "and required enrollment confirmation documents."
        )
        return {
            "intent": intent,
            "category": "financial_aid",
            "urgency": urgency,
            "language": "en",
            "entities": entities[:6],
            "confidence": 0.93,
            "rationale": rationale,
        }

    # registry / student_records
    has_deferral = any(k in lowered for k in ("deferral", "defer", "medical leave", "absence"))
    intent = "request_semester_deferral" if has_deferral else "request_transcript_verification"
    entities = registry_hits or ["academic transcript", "verification", "student records"]
    rationale = (
        "The student is requesting a semester deferral or official academic record adjustment "
        "through the Registry Office."
        if has_deferral
        else "The student is requesting official academic transcript or enrollment verification "
        "from the Registry Office."
    )
    return {
        "intent": intent,
        "category": "student_records",
        "urgency": urgency,
        "language": "en",
        "entities": entities[:6],
        "confidence": 0.94,
        "rationale": rationale,
    }


def _route_prompt(user_prompt: str) -> dict[str, Any]:
    subject, description = _extract_ticket_text(user_prompt)
    classification = _extract_json_block(
        user_prompt, "Classifier result:", "Active departments from the backend:"
    )
    departments = _extract_json_block(
        user_prompt, "Active departments from the backend:", "Eligible staff from the backend:"
    )
    staff_candidates = _extract_json_block(
        user_prompt, "Eligible staff from the backend:", "Ticket's current department:"
    )
    if staff_candidates is None:
        staff_candidates = _extract_json_block(user_prompt, "Eligible staff from the backend:")

    if not isinstance(classification, dict):
        classification = _classify_prompt(user_prompt)
    if not isinstance(departments, list):
        departments = []
    if not isinstance(staff_candidates, list):
        staff_candidates = []

    category = str(classification.get("category") or "").lower()
    intent = str(classification.get("intent") or "").lower()
    entities = [str(e) for e in (classification.get("entities") or [])]
    query_tokens = _tokens(" ".join([subject, description, category, intent, *entities]))

    category_dept_keywords: dict[str, tuple[str, ...]] = {
        "academic_support": ("computer science", "programming", "coursework", "software"),
        "academic_assessment": ("computer science", "programming", "grading", "rubric"),
        "account_access": ("it services", "technology", "portal", "login", "account", "mfa"),
        "it_support": ("it services", "technology", "wi-fi", "wifi", "vpn", "network"),
        "financial_aid": ("scholarship", "financial aid", "finance", "stipend", "tuition"),
        "student_records": ("registry", "transcript", "records", "enrollment", "deferral"),
    }
    preferred_keywords = category_dept_keywords.get(category, ())

    chosen_dept: dict[str, Any] | None = None
    best_score = -1.0

    for dept in departments:
        if not isinstance(dept, dict) or not isinstance(dept.get("id"), int):
            continue
        dept_text = f"{dept.get('name', '')} {dept.get('description', '')}".lower()
        dept_tokens = _tokens(dept_text)
        overlap_score = float(len(query_tokens & dept_tokens))
        keyword_bonus = sum(4.0 for kw in preferred_keywords if kw in dept_text)
        total_score = overlap_score + keyword_bonus
        if total_score > best_score:
            best_score = total_score
            chosen_dept = dept

    if chosen_dept is None and departments:
        first_valid = next(
            (d for d in departments if isinstance(d, dict) and isinstance(d.get("id"), int)),
            None,
        )
        chosen_dept = first_valid

    dept_id = int(chosen_dept["id"]) if chosen_dept else None
    dept_name = str(chosen_dept.get("name") or "") if chosen_dept else None

    chosen_staff: dict[str, Any] | None = None
    if dept_id is not None:
        dept_staff = [
            s
            for s in staff_candidates
            if isinstance(s, dict)
            and isinstance(s.get("id"), int)
            and s.get("department_id") == dept_id
            and "on leave" not in str(s.get("name") or s.get("full_name") or "").lower()
        ]
        if dept_staff:
            dept_staff.sort(key=lambda s: (0 if s.get("role") == "staff" else 1, int(s["id"])))
            chosen_staff = dept_staff[0]

    reason_by_category = {
        "academic_support": (
            f"The ticket requests academic coursework and Java/OOP programming concept guidance, "
            f"which is handled by {dept_name or 'Computer Science'}."
        ),
        "academic_assessment": (
            f"Programming assignment grading rubric and regrade inquiries are handled by "
            f"{dept_name or 'Computer Science'}."
        ),
        "account_access": (
            f"Student portal password reset and account access recovery requests are handled by "
            f"{dept_name or 'IT Services'}."
        ),
        "it_support": (
            f"Campus Wi-Fi, VPN, and technical connectivity requests are handled by "
            f"{dept_name or 'IT Services'}."
        ),
        "financial_aid": (
            f"Scholarship payment delays, stipend disbursements, and financial aid inquiries "
            f"are handled by {dept_name or 'Scholarships & Financial Aid'}."
        ),
        "student_records": (
            f"Official academic transcript verification and student record requests are processed "
            f"by {dept_name or 'Registry'}."
        ),
    }
    reason = reason_by_category.get(
        category,
        f"Matched the ticket topic ({intent or 'general inquiry'}) to {dept_name or 'the selected department'}.",
    )

    staff_label = (
        str(chosen_staff.get("name") or chosen_staff.get("full_name") or "")
        if chosen_staff
        else None
    )

    return {
        "department_id": dept_id,
        "department_name": dept_name,
        "staff_id": int(chosen_staff["id"]) if chosen_staff else None,
        "staff_name": staff_label,
        "confidence": 0.93 if dept_id is not None else 0.45,
        "reason": reason,
    }


def _draft_prompt(user_prompt: str) -> dict[str, Any]:
    subject, description = _extract_ticket_text(user_prompt)
    classification = _extract_json_block(
        user_prompt,
        "Classification:",
        "Routing recommendation",
    )
    routing = _extract_json_block(
        user_prompt,
        "Routing recommendation (recommendation only; not an assignment):",
        "Approved knowledge passages (trusted evidence only):",
    )
    if routing is None:
        routing = _extract_json_block(
            user_prompt,
            "Routing recommendation:",
            "Approved knowledge passages (trusted evidence only):",
        )
    evidence = _extract_json_block(
        user_prompt,
        "Approved knowledge passages (trusted evidence only):",
        "Trusted source IDs available for citation:",
    )
    if evidence is None:
        evidence = _extract_json_block(
            user_prompt, "Approved knowledge passages (trusted evidence only):"
        )

    if not isinstance(classification, dict):
        classification = {}
    if not isinstance(routing, dict):
        routing = {}
    if not isinstance(evidence, list):
        evidence = []

    language = str(classification.get("language") or "en")

    valid_passages = [
        item
        for item in evidence
        if isinstance(item, dict)
        and str(item.get("source_id") or "").strip()
        and str(item.get("excerpt") or "").strip()
    ]

    if not valid_passages:
        return {
            "body": (
                "Thank you for contacting university support regarding your query. "
                "I cannot verify the specific policy details for this request from the "
                "currently approved knowledge base sources. Your ticket has been routed for "
                "review, and a staff member will confirm the appropriate next step before "
                "sending a final reply."
            ),
            "language": language,
            "confidence": 0.0,
            "source_ids": [],
            "needs_staff_review": True,
        }

    entities = [str(e) for e in (classification.get("entities") or [])]
    query_tokens = _tokens(" ".join([subject, description, *entities]))

    def _passage_score(passage: dict[str, Any]) -> tuple[float, float]:
        p_tokens = _tokens(f"{passage.get('title', '')} {passage.get('excerpt', '')}")
        overlap = len(query_tokens & p_tokens)
        rel = float(passage.get("relevance_score") or 0.0)
        return (float(overlap), rel)

    ranked = sorted(valid_passages, key=_passage_score, reverse=True)
    primary = ranked[0]
    source_id = str(primary["source_id"]).strip()
    title = str(primary.get("title") or "Approved University Policy").strip()
    excerpt = str(primary.get("excerpt") or "").strip()
    category = str(classification.get("category") or "").lower()
    intent = str(classification.get("intent") or "").lower()
    dept_block = routing.get("department") if isinstance(routing.get("department"), dict) else routing
    dept_name = str(
        (dept_block or {}).get("department_name") or "the appropriate department"
    ).strip()

    if category == "academic_support" or "java" in intent or "oop" in intent:
        body = (
            f"Hello,\n\n"
            f"Thank you for reaching out to {dept_name} regarding your Java programming "
            f"assignment and object-oriented programming (OOP) concepts [{source_id}].\n\n"
            f"Per the {title} [{source_id}]:\n"
            f"{excerpt}\n\n"
            f"To help us guide you on classes, objects, and inheritance, please reply with the "
            f"specific Java class hierarchy or method you are working on so your assigned "
            f"Computer Science instructor can walk through the OOP concepts with you [{source_id}].\n\n"
            f"Best regards,\n"
            f"{dept_name} Academic Support"
        )
    elif category == "academic_assessment" or "rubric" in intent or "regrade" in intent:
        body = (
            f"Hello,\n\n"
            f"Thank you for contacting {dept_name} regarding the programming assignment "
            f"grading rubric and regrade policy [{source_id}].\n\n"
            f"Under the {title} [{source_id}]:\n"
            f"{excerpt}\n\n"
            f"If you would like a formal rubric breakdown or regrade review within the policy "
            f"window, please reply to this ticket with your submission details [{source_id}].\n\n"
            f"Best regards,\n"
            f"{dept_name}"
        )
    elif category in {"account_access", "it_support"} or "password" in intent:
        body = (
            f"Hello,\n\n"
            f"Thank you for contacting {dept_name} regarding your student portal account access "
            f"and password reset request [{source_id}].\n\n"
            f"According to the {title} [{source_id}]:\n"
            f"{excerpt}\n\n"
            f"For your security, please do not share passwords or verification codes in this "
            f"ticket. Complete the self-service reset or confirm your university ID so IT Services "
            f"can assist with account recovery [{source_id}].\n\n"
            f"Best regards,\n"
            f"{dept_name} Helpdesk"
        )
    elif category == "financial_aid" or "scholarship" in intent or "stipend" in intent:
        body = (
            f"Hello,\n\n"
            f"Thank you for contacting {dept_name} regarding your scholarship stipend "
            f"disbursement and payment inquiry [{source_id}].\n\n"
            f"Under the {title} [{source_id}]:\n"
            f"{excerpt}\n\n"
            f"Please ensure your signed enrollment confirmation form is uploaded to this ticket "
            f"so our office can verify your Registry enrollment lock and resolve your stipend "
            f"disbursement [{source_id}].\n\n"
            f"Best regards,\n"
            f"{dept_name}"
        )
    elif category == "student_records" or "transcript" in intent:
        body = (
            f"Hello,\n\n"
            f"Thank you for contacting {dept_name} regarding your official academic transcript "
            f"and verification request [{source_id}].\n\n"
            f"Per the {title} [{source_id}]:\n"
            f"{excerpt}\n\n"
            f"If this request is for an expedited graduate fellowship or scholarship deadline, "
            f"please attach the reference letter to this ticket so Registry staff can prioritize "
            f"verification [{source_id}].\n\n"
            f"Best regards,\n"
            f"{dept_name}"
        )
    else:
        body = (
            f"Hello,\n\n"
            f"Thank you for your query routed to {dept_name}. Based on the approved policy "
            f"{title} [{source_id}]:\n"
            f"{excerpt}\n\n"
            f"A staff member will review your ticket details before finalizing the response "
            f"[{source_id}].\n\n"
            f"Best regards,\n"
            f"{dept_name}"
        )

    return {
        "body": body,
        "language": language,
        "confidence": 0.92,
        "source_ids": [source_id],
        "needs_staff_review": True,
    }


@dataclass
class _DemoMessage:
    parsed: Any
    content: str | None = None


@dataclass
class _DemoChoice:
    message: _DemoMessage


@dataclass
class _DemoUsage:
    prompt_tokens: int = 120
    completion_tokens: int = 95


@dataclass
class _DemoResponse:
    choices: list[_DemoChoice]
    usage: _DemoUsage


class _DemoCompletions:
    def __init__(self, model: str | None = None) -> None:
        self.model = model
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> _DemoResponse:
        self.calls.append(kwargs)
        schema = kwargs.get("response_format")
        messages = kwargs.get("messages") or []
        user_prompt = ""
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_prompt = str(msg.get("content") or "")
                break

        if schema is ClassificationOutput:
            payload = _classify_prompt(user_prompt)
        elif schema is RoutingOutput:
            payload = _route_prompt(user_prompt)
        elif schema is DraftOutput:
            payload = _draft_prompt(user_prompt)
        elif schema is ConnectivityOutput:
            payload = {"status": "ok"}
        else:
            payload = {}

        return _DemoResponse(
            choices=[_DemoChoice(message=_DemoMessage(parsed=payload))],
            usage=_DemoUsage(),
        )


class TicketGroundedDemoLlmClient:
    """OpenAI-compatible structured client that derives outputs from actual ticket prompts."""

    def __init__(self, model: str | None = None) -> None:
        self.completions = _DemoCompletions(model=model)
        self.beta = type("Beta", (), {"chat": type("Chat", (), {"completions": self.completions})()})()


def make_ticket_grounded_llm(*, api_key: str | None = None, model: str | None = None):
    """Build an :class:`LlmService` backed by :class:`TicketGroundedDemoLlmClient`."""
    from app.agents.services.llm_service import LlmService

    return LlmService(
        client=TicketGroundedDemoLlmClient(model=model or settings.OPENAI_MODEL),
        api_key=api_key or "sk-local-test-grounded-demo-key",
    )
