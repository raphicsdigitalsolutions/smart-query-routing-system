"""Node 3: read-only retrieval from approved knowledge sources."""

from __future__ import annotations

import time
from collections.abc import Callable

from app.agents.state import AgentState, append_execution
from app.agents.tools.knowledge_search import InMemoryKnowledgeRepository

KnowledgeNode = Callable[[AgentState], AgentState]


def make_knowledge_node(repository: InMemoryKnowledgeRepository) -> KnowledgeNode:
    def knowledge_node(state: AgentState) -> AgentState:
        started = time.perf_counter()
        entities = (state.get("classification") or {}).get("entities") or []
        passages = repository.search(
            state.get("query_text", ""),
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
