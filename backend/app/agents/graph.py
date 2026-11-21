"""Bounded LangGraph StateGraph: classify -> route -> research -> draft -> validate."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.nodes.classification import make_classification_node
from app.agents.nodes.knowledge_research import make_knowledge_node
from app.agents.nodes.response_drafting import make_drafting_node
from app.agents.nodes.routing import make_routing_node
from app.agents.nodes.validation import validation_node
from app.agents.services.llm_service import LlmService
from app.agents.state import AgentState
from app.agents.tools.knowledge_search import (
    InMemoryKnowledgeRepository,
    get_knowledge_repository,
)
from app.core.config import settings
from app.models import User


def _after_classification(state: AgentState) -> str:
    """A fatal classification error stops the graph; there is no retry loop."""
    return "stop" if state.get("errors") else "continue"


def build_agent_graph(
    *,
    llm: LlmService,
    db: Session,
    user: User,
    knowledge_repository: InMemoryKnowledgeRepository | None = None,
) -> Any:
    """Compile a fresh graph with injected, read-only dependencies."""
    repository = knowledge_repository or get_knowledge_repository()
    builder = StateGraph(AgentState)
    builder.add_node("classification", make_classification_node(llm))
    builder.add_node("routing", make_routing_node(llm, db, user))
    builder.add_node("knowledge_research", make_knowledge_node(repository))
    builder.add_node("response_drafting", make_drafting_node(llm))
    builder.add_node("validation", validation_node)

    builder.add_edge(START, "classification")
    builder.add_conditional_edges(
        "classification",
        _after_classification,
        {"stop": END, "continue": "routing"},
    )
    builder.add_edge("routing", "knowledge_research")
    builder.add_edge("knowledge_research", "response_drafting")
    builder.add_edge("response_drafting", "validation")
    builder.add_edge("validation", END)
    return builder.compile()


def run_workflow(
    state: AgentState,
    *,
    llm: LlmService,
    db: Session,
    user: User,
    knowledge_repository: InMemoryKnowledgeRepository | None = None,
) -> AgentState:
    """Run one bounded invocation. Retries live in the LLM wrapper, not the graph."""
    graph = build_agent_graph(
        llm=llm,
        db=db,
        user=user,
        knowledge_repository=knowledge_repository,
    )
    return graph.invoke(
        state,
        config={"recursion_limit": settings.AI_GRAPH_RECURSION_LIMIT},
    )
