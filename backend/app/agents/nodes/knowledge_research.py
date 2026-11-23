"""Node 3: read-only retrieval from approved knowledge sources."""

from __future__ import annotations

import time
from collections.abc import Callable

from app.agents.state import AgentState, append_execution
from app.agents.tools.knowledge_search import (
    DatabaseKnowledgeRepository,
    InMemoryKnowledgeRepository,
)

KnowledgeNode = Callable[[AgentState], AgentState]


def make_knowledge_node(repository: InMemoryKnowledgeRepository) -> KnowledgeNode:
    def knowledge_node(state: AgentState) -> AgentState:
        started = time.perf_counter()
        entities = (state.get("classification") or {}).get("entities") or []
        query_text = state.get("query_text", "")
        if isinstance(repository, DatabaseKnowledgeRepository):
            routed_dept = (state.get("department_recommendation") or {}).get("department_id")
            target_dept_id = (
                routed_dept
                if isinstance(routed_dept, int)
                else (
                    state.get("department_id")
                    if isinstance(state.get("department_id"), int)
                    else None
                )
            )
            if target_dept_id is not None:
                scoped_repo = DatabaseKnowledgeRepository(
                    repository.db, department_id=target_dept_id
                )
                passages = scoped_repo.search(query_text, entities=entities, limit=3)
                if not passages:
                    passages = repository.search(query_text, entities=entities, limit=3)
            else:
                passages = repository.search(query_text, entities=entities, limit=3)
        else:
            passages = repository.search(
                query_text,
                entities=entities,
                limit=3,
            )
        no_evidence = not passages
        return {
            **state,
            "knowledge": passages,
            "no_evidence": no_evidence,
            "abstention_reason": (
                "No approved knowledge source matched this query." if no_evidence else state.get("abstention_reason")
            ),
            "execution": append_execution(
                state,
                {
                    "node": "knowledge_research",
                    "status": "completed",
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "detail": "no_evidence" if no_evidence else f"{len(passages)} source(s)",
                },
            ),
        }

    return knowledge_node
