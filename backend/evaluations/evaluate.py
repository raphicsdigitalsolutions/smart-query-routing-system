"""Deterministic, offline-first evaluation harness for the agent workflow.

The harness exercises the real bounded LangGraph pipeline
(classification -> routing -> knowledge_research -> response_drafting ->
validation) against a fully synthetic dataset.

Offline mode (the default) replaces the language model with a deterministic
fake that echoes the dataset labels. It never creates an OpenAI client, never
opens a network connection and uses no randomness. Live mode is strictly
opt-in via ``--live`` and requires ``OPENAI_API_KEY``.

Run from ``backend/``:

    .\\.venv\\Scripts\\python.exe -m evaluations.evaluate \
        --output-json eval_reports/evaluation.json \
        --output-md eval_reports/evaluation.md
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.graph import run_workflow
from app.agents.services.llm_service import LlmResult, LlmService
from app.agents.state import ClassificationOutput, DraftOutput, RoutingOutput
from app.agents.tools.knowledge_search import InMemoryKnowledgeRepository, KnowledgePassage
from app.core.config import settings
from app.models import Base, Department, User

DEFAULT_DATASET = Path(__file__).with_name("dataset.json")
DEFAULT_OUTPUT_JSON = Path(__file__).resolve().parents[1] / "eval_reports" / "evaluation.json"
DEFAULT_OUTPUT_MD = Path(__file__).resolve().parents[1] / "eval_reports" / "evaluation.md"
OFFLINE_MODEL_VERSION = "offline-label-echo-v1"
MIN_DATASET_RECORDS = 20

SYNTHETIC_CAVEAT = (
    "Synthetic evaluation only: these results are computed from invented queries, labels and "
    "knowledge fixtures. They are NOT real university performance and must not be used as "
    "real-world accuracy."
)

_CITATION_RE = re.compile(r"\[([^\[\]]{1,80})\]")

# Phrases that the offline fake deliberately injects for records flagged with
# expected_unsupported_claim=true, so the harness can measure whether an
# unsupported claim survives into the final draft. No production code is changed.
_UNSUPPORTED_PHRASE_MARKERS = ("guaranteed for every", "exactly forty two", "without any review")

# Synthetic approved knowledge corpus. Source ids must match dataset expectations.
# Deliberately uses invented wording so retrieval is deterministic and offline.
_SYNTHETIC_KNOWLEDGE: tuple[dict[str, Any], ...] = (
    {
        "source_id": "KB-ACCOUNT-01",
        "title": "Portal credential recovery",
        "excerpt": "Credential recovery steps are published for password reset requests.",
        "source_url": "https://example.invalid/approved/portal-credential-recovery",
        "tags": ["credential", "password", "reset", "portal", "account"],
    },
    {
        "source_id": "KB-RECORDS-01",
        "title": "Academic transcript request",
        "excerpt": "Certified academic transcript copies are issued through the records counter after identity verification.",
        "source_url": "https://example.invalid/approved/academic-transcript",
        "tags": ["transcript", "academic", "records", "certified"],
    },
    {
        "source_id": "KB-SCHOLAR-01",
        "title": "Merit scholarship application",
        "excerpt": "Merit scholarship applications require the current semester grade report before the published deadline.",
        "source_url": "https://example.invalid/approved/merit-scholarship",
        "tags": ["scholarship", "merit", "application", "deadline"],
    },
    {
        "source_id": "KB-FEES-01",
        "title": "Tuition fee payment schedule",
        "excerpt": "Tuition fee instalment dates and accepted payment methods are published each semester.",
        "source_url": "https://example.invalid/approved/tuition-fees",
        "tags": ["tuition", "fee", "payment", "instalment"],
    },
    {
        "source_id": "KB-FEES-02",
        "title": "Fee waiver eligibility",
        "excerpt": "Fee waiver eligibility is assessed from submitted financial evidence by the finance office.",
        "source_url": "https://example.invalid/approved/fee-waiver",
        "tags": ["fee", "waiver", "eligibility", "finance"],
    },
    {
        "source_id": "KB-IT-WIFI-01",
        "title": "Campus wireless network access",
        "excerpt": "Campus wireless network access uses issued credentials; report repeated disconnect events to IT Services.",
        "source_url": "https://example.invalid/approved/campus-wifi",
        "tags": ["wifi", "wireless", "campus", "network", "disconnect"],
    },
    {
        "source_id": "KB-EXAMS-01",
        "title": "Examination seat allocation",
        "excerpt": "Examination seating plans are released before each scheduled paper; clash reports require early notification.",
        "source_url": "https://example.invalid/approved/exam-seating",
        "tags": ["exam", "examination", "seating", "paper"],
    },
    {
        "source_id": "KB-LEAVE-01",
        "title": "Leave request filing",
        "excerpt": "Leave requests for personal absence must be submitted before the planned absence date.",
        "source_url": "https://example.invalid/approved/student-leave",
        "tags": ["leave", "absence", "request", "submitted"],
    },
    {
        "source_id": "KB-ID-01",
        "title": "Identity card replacement",
        "excerpt": "Replacement identity cards are issued after a verified report of a lost or damaged card.",
        "source_url": "https://example.invalid/approved/identity-card",
        "tags": ["identity", "card", "replacement", "lost"],
    },
    {
        "source_id": "KB-LIB-01",
        "title": "Library borrowing limits",
        "excerpt": "Library borrowing limits and loan renewal rules are listed in the library reader guide.",
        "source_url": "https://example.invalid/approved/library-loans",
        "tags": ["library", "borrowing", "loan", "renewal"],
    },
    {
        "source_id": "KB-HOSTEL-01",
        "title": "Hostel room allocation",
        "excerpt": "Hostel room allocation requests and room change windows are announced each term.",
        "source_url": "https://example.invalid/approved/hostel-rooms",
        "tags": ["hostel", "room", "allocation", "term"],
    },
    {
        "source_id": "KB-RESEARCH-01",
        "title": "Research proposal submission",
        "excerpt": "Research proposal submissions require a supervisor endorsement and an ethics review reference.",
        "source_url": "https://example.invalid/approved/research-proposal",
        "tags": ["research", "proposal", "supervisor", "ethics"],
    },
    {
        "source_id": "KB-DISC-01",
        "title": "Conduct hearing review",
        "excerpt": "Conduct concerns are reviewed by the discipline committee before any formal hearing.",
        "source_url": "https://example.invalid/approved/conduct-hearing",
        "tags": ["conduct", "discipline", "hearing", "committee"],
    },
)


class EvaluationRecord(BaseModel):
    """One labelled synthetic query and its expected agent outputs."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    query: str = Field(min_length=1)
    expected_intent: str = Field(min_length=1)
    expected_category: str = Field(min_length=1)
    expected_priority: Literal["low", "normal", "high", "urgent"]
    expected_department: str = Field(min_length=1)
    expected_department_keyword: str = Field(min_length=1)
    expected_sources: list[str] = Field(default_factory=list)
    expected_abstention: bool
    expected_unsupported_claim: bool = False
    entities: list[str] = Field(default_factory=list)

    @field_validator("expected_sources", "entities")
    @classmethod
    def _unique_strings(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]


class EvaluationDataset(BaseModel):
    """Versioned dataset container with strict schema validation."""

    model_config = ConfigDict(extra="forbid")

    dataset_version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    records: list[EvaluationRecord] = Field(min_length=MIN_DATASET_RECORDS)


def load_dataset(path: Path | str = DEFAULT_DATASET) -> EvaluationDataset:
    """Load and validate the synthetic evaluation dataset."""
    dataset_path = Path(path)
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset = EvaluationDataset.model_validate(raw)
    ids = [record.id for record in dataset.records]
    if len(ids) != len(set(ids)):
        raise ValueError("Dataset record ids must be unique")
    if "synthetic" not in dataset.description.casefold():
        raise ValueError("Dataset description must state that the data is synthetic")
    return dataset


def build_knowledge_repository() -> InMemoryKnowledgeRepository:
    """Build the read-only synthetic corpus used by the retrieval node."""
    documents = [KnowledgePassage.model_validate(item) for item in _SYNTHETIC_KNOWLEDGE]
    return InMemoryKnowledgeRepository(documents)


class LabelEchoLlm:
    """Deterministic fake LLM whose outputs come only from dataset labels.

    No network, clock, random state or provider SDK client is used. This is a
    harness smoke test of the pipeline and metrics, not a measure of model quality.
    """

    def __init__(self, record: EvaluationRecord, department_ids: dict[str, int]) -> None:
        self.record = record
        self.department_ids = department_ids

    def generate_structured(self, *, schema: Any, system_prompt: str, user_prompt: str) -> LlmResult:
        record = self.record
        metadata = {"model": OFFLINE_MODEL_VERSION, "attempts": 1}

        if schema is ClassificationOutput:
            data = ClassificationOutput(
                intent=record.expected_intent,
                category=record.expected_category,
                urgency=record.expected_priority,
                language="en",
                entities=record.entities[:10],
                confidence=0.9,
                rationale="Synthetic label echo for deterministic offline evaluation.",
            )
        elif schema is RoutingOutput:
            data = RoutingOutput(
                department_id=self.department_ids[record.expected_department],
                department_name=record.expected_department,
                staff_id=None,
                staff_name=None,
                confidence=0.85,
                reason=f"Synthetic routing label: {record.expected_department_keyword}.",
            )
        elif schema is DraftOutput:
            if record.expected_abstention:
                body = (
                    "I cannot verify an answer from approved sources; a staff member will "
                    "review this synthetic query and confirm the next step."
                )
            else:
                body = (
                    f"Synthetic grounded draft for {record.expected_category}: "
                    "approved guidance is summarised for staff review."
                )
                if record.expected_sources:
                    body += " Sources: " + ", ".join(f"[{sid}]" for sid in record.expected_sources)
                if record.expected_unsupported_claim:
                    # Deliberate negative fixture: a fabricated citation and phrase.
                    body += " [SYNTHETIC-UNVERIFIED-REF] This is guaranteed for every applicant."
            data = DraftOutput(
                body=body,
                language="en",
                confidence=0.0 if record.expected_abstention else 0.8,
                source_ids=list(record.expected_sources),
                needs_staff_review=True,
            )
        else:
            raise AssertionError(f"Unexpected schema in offline fake: {schema!r}")
        return LlmResult(data=data, metadata=metadata)


class RecordingLlm:
    """Thin delegating wrapper that records provider token usage when present."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self._token_values_seen = False

    def generate_structured(self, **kwargs: Any) -> LlmResult:
        result = self._inner.generate_structured(**kwargs)
        self.calls += 1
        metadata = result.metadata or {}
        prompt = metadata.get("prompt_tokens")
        completion = metadata.get("completion_tokens")
        if isinstance(prompt, int):
            self.prompt_tokens += prompt
            self._token_values_seen = True
        if isinstance(completion, int):
            self.completion_tokens += completion
            self._token_values_seen = True
        return result

    def token_usage(self) -> dict[str, int | None]:
        if not self._token_values_seen:
            return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
        }


def _department_ids(records: list[EvaluationRecord]) -> dict[str, int]:
    names = sorted({record.expected_department for record in records})
    return {name: index for index, name in enumerate(names, start=1)}


@contextmanager
def _evaluation_db(
    department_ids: dict[str, int],
) -> Iterator[tuple[Session, User]]:
    """Fresh in-memory SQLite DB: deterministic, offline and never persisted."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory() as session:
            for name, identifier in department_ids.items():
                session.add(
                    Department(
                        id=identifier,
                        name=name,
                        description="Synthetic evaluation department.",
                        is_active=True,
                    )
                )
            actor = User(
                full_name="Synthetic Evaluation Runner",
                email="eval-runner@example.invalid",
                password_hash="synthetic-not-a-login",
                role="admin",
                is_active=True,
            )
            session.add(actor)
            session.commit()
            yield session, actor
    finally:
        engine.dispose()


def _initial_state(record: EvaluationRecord, index: int, fallback_department_id: int) -> dict[str, Any]:
    return {
        "ticket_id": index + 1,
        "subject": record.query,
        "query_text": record.query,
        "category": None,
        "priority": "normal",
        "department_id": fallback_department_id,
        "department_name": None,
        "status": "new",
        "student_context": {"context_kind": "synthetic_evaluation"},
        "knowledge": [],
        "errors": [],
        "warnings": [],
        "execution": [],
    }


def _unsupported_details(
    body: str, cited_ids: set[str], retrieved_ids: set[str]
) -> tuple[list[str], list[str]]:
    bad_ids = sorted(cited_ids - retrieved_ids)
    lowered = body.casefold()
    bad_phrases = [marker for marker in _UNSUPPORTED_PHRASE_MARKERS if marker in lowered]
    return bad_ids, bad_phrases


def _department_correct(record: EvaluationRecord, observed: str | None) -> bool:
    if not observed:
        return False
    value = observed.casefold().strip()
    return (
        value == record.expected_department.casefold().strip()
        or record.expected_department_keyword.casefold().strip() in value
    )


def _evaluate_record(
    *,
    record: EvaluationRecord,
    index: int,
    llm: Any,
    db: Session,
    user: User,
    repository: InMemoryKnowledgeRepository,
    department_ids: dict[str, int],
) -> dict[str, Any]:
    state = _initial_state(record, index, min(department_ids.values()))
    started = time.perf_counter()
    final = run_workflow(
        state,
        llm=llm,
        db=db,
        user=user,
        knowledge_repository=repository,
    )
    latency_ms = (time.perf_counter() - started) * 1000

    classification = final.get("classification") or {}
    routing = final.get("department_recommendation") or {}
    draft = final.get("draft") or {}
    body = str(draft.get("body") or "")
    retrieved_ids = [item["source_id"] for item in final.get("knowledge", [])]
    cited_ids = set(draft.get("source_ids") or []) | set(_CITATION_RE.findall(body))
    bad_ids, bad_phrases = _unsupported_details(body, cited_ids, set(retrieved_ids))

    expected_sources = set(record.expected_sources)
    retrieved_set = set(retrieved_ids)
    true_positives = len(expected_sources & retrieved_set)
    precision = len(expected_sources & retrieved_set) / len(retrieved_set) if retrieved_set else 1.0
    recall = true_positives / len(expected_sources) if expected_sources else 1.0

    observed = {
        "intent": classification.get("intent"),
        "category": classification.get("category"),
        "priority": final.get("priority_recommendation"),
        "department": routing.get("department_name"),
        "department_source": routing.get("source"),
        "retrieved_sources": retrieved_ids,
        "cited_ids": sorted(cited_ids),
        "abstention": bool(final.get("no_evidence")),
        "unsupported_refs": bad_ids,
        "unsupported_phrases": bad_phrases,
        "draft_source_ids": list(draft.get("source_ids") or []),
        "validation_passed": (final.get("validation") or {}).get("passed"),
        "error_codes": [item.get("code") for item in final.get("errors", [])],
    }
    correct = {
        "intent": classification.get("intent") == record.expected_intent,
        "category": classification.get("category") == record.expected_category,
        "priority": final.get("priority_recommendation") == record.expected_priority,
        "department": _department_correct(record, observed["department"]),
        "citation": cited_ids.issubset(retrieved_set),
        "abstention": observed["abstention"] == record.expected_abstention,
        "unsupported_claim_detected": bool(bad_ids or bad_phrases),
    }
    return {
        "id": record.id,
        "topic": record.topic,
        "expected": {
            "intent": record.expected_intent,
            "category": record.expected_category,
            "priority": record.expected_priority,
            "department": record.expected_department,
            "sources": list(record.expected_sources),
            "abstention": record.expected_abstention,
            "unsupported_claim": record.expected_unsupported_claim,
        },
        "observed": observed,
        "correct": correct,
        "retrieval_true_positives": true_positives,
        "retrieval_precision": round(precision, 4),
        "retrieval_recall": round(recall, 4),
        "latency_ms": round(latency_ms, 3),
    }


def _accuracy(results: list[dict[str, Any]], key: str) -> float:
    if not results:
        return 0.0
    return round(sum(1 for item in results if item["correct"][key]) / len(results), 4)


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return round(ordered[position], 3)


def _compute_metrics(results: list[dict[str, Any]]) -> dict[str, float | int]:
    retrieved_total = sum(len(item["observed"]["retrieved_sources"]) for item in results)
    expected_total = sum(len(item["expected"]["sources"]) for item in results)
    tp_total = sum(item["retrieval_true_positives"] for item in results)
    return {
        "record_count": len(results),
        "intent_classification_accuracy": _accuracy(results, "intent"),
        "category_classification_accuracy": _accuracy(results, "category"),
        "priority_prediction_accuracy": _accuracy(results, "priority"),
        "department_routing_accuracy": _accuracy(results, "department"),
        "knowledge_retrieval_precision": round(tp_total / retrieved_total, 4) if retrieved_total else 1.0,
        "knowledge_retrieval_recall": round(tp_total / expected_total, 4) if expected_total else 1.0,
        "citation_correctness": _accuracy(results, "citation"),
        "unsupported_claim_count": sum(
            1 for item in results if item["correct"]["unsupported_claim_detected"]
        ),
        "unsupported_claim_expected_count": sum(
            1 for item in results if item["expected"]["unsupported_claim"]
        ),
        "abstention_correctness": _accuracy(results, "abstention"),
    }


def _live_llm(model_version: str | None) -> RecordingLlm:
    """Create the official OpenAI SDK client only for an explicit live run."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "Live evaluation requires an OpenAI API key. Set OPENAI_API_KEY or rerun "
            "without --live for the deterministic offline evaluation."
        )
    from openai import OpenAI  # imported lazily; offline mode never loads a client

    if model_version:
        settings.OPENAI_MODEL = model_version
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.OPENAI_TIMEOUT_SECONDS,
        max_retries=0,
    )
    return RecordingLlm(LlmService(client=client))


def run_evaluation(
    *,
    dataset_path: Path | str = DEFAULT_DATASET,
    mode: Literal["offline", "live"] = "offline",
    model_version: str | None = None,
    output_json: Path | str = DEFAULT_OUTPUT_JSON,
    output_md: Path | str = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    """Run the workflow over the dataset and write JSON + Markdown reports."""
    if mode not in {"offline", "live"}:
        raise ValueError("mode must be 'offline' or 'live'")
    dataset = load_dataset(dataset_path)
    resolved_model = model_version or (
        OFFLINE_MODEL_VERSION if mode == "offline" else settings.OPENAI_MODEL
    )
    department_ids = _department_ids(dataset.records)
    repository = build_knowledge_repository()

    results: list[dict[str, Any]] = []
    token_usage = {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
    with _evaluation_db(department_ids) as (db, user):
        if mode == "offline":
            for index, record in enumerate(dataset.records):
                fake = LabelEchoLlm(record, department_ids)
                results.append(
                    _evaluate_record(
                        record=record,
                        index=index,
                        llm=fake,
                        db=db,
                        user=user,
                        repository=repository,
                        department_ids=department_ids,
                    )
                )
        else:
            usage_recorder = _live_llm(resolved_model)
            for index, record in enumerate(dataset.records):
                results.append(
                    _evaluate_record(
                        record=record,
                        index=index,
                        llm=usage_recorder,
                        db=db,
                        user=user,
                        repository=repository,
                        department_ids=department_ids,
                    )
                )
            token_usage = usage_recorder.token_usage()

    latencies = [item["latency_ms"] for item in results]
    report: dict[str, Any] = {
        "dataset_version": dataset.dataset_version,
        "model_version": resolved_model,
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_description": dataset.description,
        "synthetic_data_caveat": SYNTHETIC_CAVEAT,
        "metrics": _compute_metrics(results),
        "latency": {
            "label": (
                "Synthetic-run latency (deterministic offline fixtures; not production latency)"
                if mode == "offline"
                else "Live-run latency (small synthetic dataset; not production latency)"
            ),
            "mean_ms": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
            "p95_ms": _percentile(latencies, 0.95),
            "min_ms": round(min(latencies), 3) if latencies else 0.0,
            "max_ms": round(max(latencies), 3) if latencies else 0.0,
        },
        "token_usage": {
            **token_usage,
            "estimated_cost_usd": None,
            "cost_note": (
                "Cost is null: this harness bundles no verified price table, so no cost is estimated."
            ),
        },
        "per_record": results,
    }

    json_path = Path(output_json)
    md_path = Path(output_md)
    for path in (json_path, md_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    """Render the same computed report as a human-readable Markdown document."""
    metrics = report["metrics"]
    latency = report["latency"]
    usage = report["token_usage"]

    def display(value: Any) -> str:
        return "null" if value is None else str(value)

    lines = [
        "# Agentic AI Evaluation Report",
        "",
        f"> **Synthetic-data caveat:** {report['synthetic_data_caveat']}",
        "",
        "## Run metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Dataset version | `{report['dataset_version']}` |",
        f"| Model version | `{report['model_version']}` |",
        f"| Mode | `{report['mode']}` |",
        f"| Records | {metrics['record_count']} |",
        f"| Generated at (UTC) | {report['generated_at']} |",
        "",
        f"Dataset description: {report['dataset_description']}",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Intent classification accuracy | {metrics['intent_classification_accuracy']} |",
        f"| Category classification accuracy | {metrics['category_classification_accuracy']} |",
        f"| Priority prediction accuracy | {metrics['priority_prediction_accuracy']} |",
        f"| Department routing accuracy | {metrics['department_routing_accuracy']} |",
        f"| Knowledge retrieval precision (micro) | {metrics['knowledge_retrieval_precision']} |",
        f"| Knowledge retrieval recall (micro) | {metrics['knowledge_retrieval_recall']} |",
        f"| Citation correctness | {metrics['citation_correctness']} |",
        f"| Unsupported claim count | {metrics['unsupported_claim_count']} "
        f"(expected cases: {metrics['unsupported_claim_expected_count']}) |",
        f"| Abstention correctness | {metrics['abstention_correctness']} |",
        "",
        "## Latency and usage",
        "",
        f"- {latency['label']}: mean {latency['mean_ms']} ms, p95 {latency['p95_ms']} ms "
        f"(min {latency['min_ms']} ms, max {latency['max_ms']} ms).",
        f"- Prompt tokens: {display(usage['prompt_tokens'])}; "
        f"completion tokens: {display(usage['completion_tokens'])}; "
        f"total tokens: {display(usage['total_tokens'])}.",
        f"- Estimated cost (USD): {display(usage['estimated_cost_usd'])}. {usage['cost_note']}",
        "",
        "## Per-record results",
        "",
        "| ID | Topic | Intent OK | Category OK | Priority OK | Dept OK | Retrieved sources | "
        "Citations OK | Abstain (exp/obs) | Unsupported detected |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["per_record"]:
        correct = item["correct"]
        expected = item["expected"]
        observed = item["observed"]
        retrieved = ", ".join(observed["retrieved_sources"]) or "none"
        lines.append(
            f"| {item['id']} | {item['topic']} "
            f"| {'yes' if correct['intent'] else 'no'} "
            f"| {'yes' if correct['category'] else 'no'} "
            f"| {'yes' if correct['priority'] else 'no'} "
            f"| {'yes' if correct['department'] else 'no'} "
            f"| {retrieved} "
            f"| {'yes' if correct['citation'] else 'no'} "
            f"| {str(expected['abstention']).lower()}/{str(observed['abstention']).lower()} "
            f"| {'yes' if correct['unsupported_claim_detected'] else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Metric definitions and limitations",
            "",
            "- Accuracy metrics are the fraction of records where the observed agent output matches "
            "the synthetic label; offline labels are echoed by a deterministic fake, so high values "
            "measure pipeline wiring, not model quality.",
            "- Retrieval precision/recall are micro-averaged over retrieved and expected source ids; "
            "an empty expected set and empty retrieval score 1.0 for that record.",
            "- Citation correctness means every cited id (draft source_ids or inline brackets) is in "
            "the retrieved approved source set.",
            "- Unsupported claims count records whose final draft still contains a fabricated id or "
            "one of the harness's synthetic unsupported phrases.",
            "- Abstention correctness compares the retrieval node's no-evidence decision with the "
            "synthetic expectation; off-topic fixtures carry no approved source tokens.",
            "- These numbers come from entirely synthetic data and MUST NOT be reported as real "
            "university performance or real-world accuracy.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Opt in to real OpenAI calls (requires OPENAI_API_KEY); default is offline/fake.",
    )
    parser.add_argument(
        "--model-version",
        default=None,
        help="Model/version label recorded in the report (offline default: offline-label-echo-v1).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help=f"JSON report path (default: {DEFAULT_OUTPUT_JSON}).",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=DEFAULT_OUTPUT_MD,
        help=f"Markdown report path (default: {DEFAULT_OUTPUT_MD}).",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Dataset JSON path (default: {DEFAULT_DATASET}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_evaluation(
        dataset_path=args.dataset,
        mode="live" if args.live else "offline",
        model_version=args.model_version,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    metrics = report["metrics"]
    print(
        f"Wrote {args.output_json} and {args.output_md} "
        f"(dataset_version={report['dataset_version']}, model_version={report['model_version']}, "
        f"records={metrics['record_count']})."
    )
    print(SYNTHETIC_CAVEAT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
