"""Deterministic keyword-based department routing.

No LLM is involved: the same subject/description always produces the same
department, which keeps routing auditable and testable.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Department

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "about", "after", "again", "could", "dear", "help", "hello", "issue",
    "need", "please", "problem", "question", "query", "request", "status",
    "student", "thanks", "their", "there", "this", "with", "would", "your",
}


def _tokens(text: str | None) -> set[str]:
    tokens: set[str] = set()
    for raw in _TOKEN_RE.findall((text or "").lower()):
        word = raw
        if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        if len(word) < 4 or word in _STOPWORDS:
            continue
        tokens.add(word)
    return tokens


def resolve_department(
    db: Session,
    *,
    subject: str,
    description: str,
    category: str | None = None,
) -> tuple[Department, str] | None:
    """Return the best-matching active department and its matched keywords.

    Returns ``None`` when there is no confident match so callers can raise a
    deterministic ``routing_unresolved`` application error.
    """
    query_tokens = _tokens(f"{subject} {description} {category or ''}")
    if not query_tokens:
        return None

    best: tuple[int, int, Department, str] | None = None
    departments = db.scalars(
        select(Department)
        .where(Department.is_active.is_(True))
        .order_by(Department.id)
    ).all()
    for department in departments:
        # Routing uses only persisted department name/description fields. There
        # is no separate keywords column, so no phantom metadata is consulted.
        name_tokens = _tokens(department.name)
        description_tokens = _tokens(department.description)

        score = 0
        matched: set[str] = set()
        for token in query_tokens:
            weight = 0
            if token in name_tokens:
                weight += 3
            if token in description_tokens:
                weight += 2
            if weight:
                score += weight
                matched.add(token)
        if score < 2:
            continue
        candidate = (score, -department.id, department, ",".join(sorted(matched)))
        if best is None or candidate[:2] > best[:2]:
            best = candidate

    if best is None:
        return None
    return best[2], best[3]
