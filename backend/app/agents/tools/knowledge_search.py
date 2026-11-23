"""Extensible, read-only retrieval over approved knowledge documents.

The repository is empty by default. That is deliberate: with no configured
trusted source the research node must abstain instead of inventing policy.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import KnowledgeDocument, User

logger = logging.getLogger(__name__)
_TOKEN_RE = re.compile(r"[a-z0-9]+")


class KnowledgePassage(BaseModel):
    """A single approved passage with a stable source reference."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    excerpt: str = Field(min_length=1, max_length=2000)
    source_url: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("source_id", "title", "excerpt")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


def _tokens(value: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(value.lower()) if len(token) > 2}


def _load_configured_documents() -> list[KnowledgePassage]:
    """Load optional approved documents from a server-local JSON file."""
    configured = settings.AI_KNOWLEDGE_FILE.strip()
    if not configured:
        return []

    path = Path(configured)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # Never log file contents; the path is configuration, not a secret.
        logger.warning("Configured AI knowledge file could not be loaded; retrieval will abstain")
        return []

    if not isinstance(raw, list):
        logger.warning("Configured AI knowledge file is not a JSON list; retrieval will abstain")
        return []

    documents: list[KnowledgePassage] = []
    for item in raw:
        try:
            documents.append(KnowledgePassage.model_validate(item))
        except ValueError:
            logger.warning("Skipped an invalid entry in the configured AI knowledge file")
    return documents


class InMemoryKnowledgeRepository:
    """Deterministic keyword retriever with no network or database writes."""

    def __init__(self, documents: Iterable[KnowledgePassage] | None = None) -> None:
        self.documents = list(documents) if documents is not None else _load_configured_documents()

    def search(
        self,
        query: str,
        *,
        entities: Iterable[str] | None = None,
        limit: int = 3,
    ) -> list[dict]:
        """Return only passages with a positive keyword overlap."""
        query_tokens = _tokens(query)
        for entity in entities or []:
            query_tokens.update(_tokens(entity))
        if not query_tokens or not self.documents:
            return []

        scored: list[tuple[float, KnowledgePassage]] = []
        for document in self.documents:
            document_tokens = _tokens(
                " ".join([document.title, document.excerpt, *document.tags])
            )
            overlap = query_tokens & document_tokens
            if not overlap:
                continue
            score = len(overlap) / ((len(query_tokens) * len(document_tokens)) ** 0.5)
            scored.append((score, document))

        scored.sort(key=lambda pair: (-pair[0], pair[1].source_id))
        return [
            {
                "source_id": document.source_id,
                "title": document.title,
                "excerpt": document.excerpt,
                "source_url": document.source_url,
                "tags": document.tags,
                "relevance_score": round(score, 4),
            }
            for score, document in scored[: max(1, limit)]
        ]


def get_knowledge_repository() -> InMemoryKnowledgeRepository:
    return InMemoryKnowledgeRepository()


class DatabaseKnowledgeRepository:
    """Read-only retrieval over approved, active governed documents.

    This class has the same ``search`` contract as
    :class:`InMemoryKnowledgeRepository`, so the existing research node can use
    it without modification. Rows that are unapproved or deactivated are never
    loaded, and an optional department scope limits results to global (NULL)
    documents plus documents belonging to that department.
    """

    def __init__(
        self,
        db: Session,
        *,
        department_id: int | None = None,
        global_only: bool = False,
        user: User | None = None,
    ) -> None:
        self.db = db
        self.department_id = department_id
        self.global_only = global_only
        if user is not None and department_id is None and not global_only:
            if user.role != "admin":
                if user.department_id is None:
                    self.global_only = True
                else:
                    self.department_id = user.department_id

    def _load_documents(self) -> list[KnowledgePassage]:
        statement = select(KnowledgeDocument).where(
            KnowledgeDocument.is_approved.is_(True),
            KnowledgeDocument.is_active.is_(True),
        )
        if self.global_only:
            statement = statement.where(KnowledgeDocument.department_id.is_(None))
        elif self.department_id is not None:
            statement = statement.where(
                or_(
                    KnowledgeDocument.department_id.is_(None),
                    KnowledgeDocument.department_id == self.department_id,
                )
            )

        passages: list[KnowledgePassage] = []
        for row in self.db.scalars(statement).all():
            excerpt = (row.content_text or "").strip()
            if not excerpt:
                continue
            passages.append(
                KnowledgePassage(
                    # Stable citation: the document id and its exact version.
                    source_id=f"kb-{row.id}-v{row.version}",
                    title=(row.title or "Untitled document")[:160],
                    excerpt=excerpt[:2000],
                    source_url=None,
                    tags=[row.source_type, f"v{row.version}"],
                )
            )
        return passages

    def search(
        self,
        query: str,
        *,
        entities: Iterable[str] | None = None,
        limit: int = 3,
    ) -> list[dict]:
        """Rank only approved/active rows with the existing deterministic scorer."""
        results = InMemoryKnowledgeRepository(self._load_documents()).search(
            query, entities=entities, limit=limit
        )
        if len(results) > 1 and limit <= 3:
            top_score = float(results[0].get("relevance_score") or 0.0)
            if top_score > 0:
                threshold = round(top_score * 0.45, 4)
                results = [
                    item
                    for item in results
                    if float(item.get("relevance_score") or 0.0) >= threshold
                ]
        return results

    def query(
        self,
        query: str,
        *,
        entities: Iterable[str] | None = None,
        limit: int = 3,
    ) -> list[dict]:
        """Alias for :meth:`search` for callers using query terminology."""
        return self.search(query, entities=entities, limit=limit)
