"""Typed LangGraph state and validated structured agent outputs."""

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClassificationOutput(BaseModel):
    """Validated output of the classification node."""

    model_config = ConfigDict(extra="forbid")

    intent: str = Field(min_length=3, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    urgency: Literal["low", "normal", "high", "urgent"]
    language: str = Field(min_length=2, max_length=40)
    entities: list[str] = Field(default_factory=list, max_length=10)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=3, max_length=400)

    @field_validator("intent", "category", "language", "rationale")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("entities")
    @classmethod
    def strip_entities(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()][:10]


class RoutingOutput(BaseModel):
    """Validated model proposal; IDs are rechecked against backend data."""

    model_config = ConfigDict(extra="forbid")

    department_id: int | None = Field(default=None, ge=1)
    department_name: str | None = Field(default=None, max_length=120)
    staff_id: int | None = Field(default=None, ge=1)
    staff_name: str | None = Field(default=None, max_length=120)
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", "department_name", "staff_name")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class DraftOutput(BaseModel):
    """Validated draft response; it is never published without human approval."""

    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=20, max_length=4000)
    language: str = Field(min_length=2, max_length=40)
    confidence: float = Field(ge=0, le=1)
    source_ids: list[str] = Field(default_factory=list, max_length=10)
    needs_staff_review: bool = True

    @field_validator("body", "language")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("source_ids")
    @classmethod
    def strip_sources(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()][:10]


class ConnectivityOutput(BaseModel):
    """Minimal schema used by the safe OpenAI connectivity probe."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


class AgentError(TypedDict):
    node: str
    code: str
    message: str


class ExecutionStep(TypedDict, total=False):
    node: str
    status: str
    duration_ms: int
    detail: str
    attempts: int
    model: str


class AgentState(TypedDict, total=False):
    """Minimal, non-sensitive state shared by every node."""

    ticket_id: int
    query_text: str
    subject: str
    category: str | None
    priority: str
    department_id: int
    department_name: str | None
    status: str
    student_context: dict[str, Any]

    classification: dict[str, Any] | None
    priority_recommendation: str | None
    department_recommendation: dict[str, Any] | None
    staff_recommendation: dict[str, Any] | None
    routing_explanation: str | None
    knowledge: list[dict[str, Any]]
    no_evidence: bool
    draft: dict[str, Any] | None
    confidence: float | None
    validation: dict[str, Any] | None
    abstention_reason: str | None

    errors: list[AgentError]
    warnings: list[AgentError]
    execution: list[ExecutionStep]


def append_execution(state: AgentState, step: ExecutionStep) -> list[ExecutionStep]:
    return [*state.get("execution", []), step]


def append_error(state: AgentState, error: AgentError) -> list[AgentError]:
    return [*state.get("errors", []), error]


def append_warning(state: AgentState, warning: AgentError) -> AgentState:
    """Return a new state with a non-fatal warning appended."""
    return {**state, "warnings": [*state.get("warnings", []), warning]}
