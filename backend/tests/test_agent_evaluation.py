"""Deterministic offline tests for the agent evaluation harness.

These tests never call a live model. They validate the synthetic dataset schema,
run the real bounded workflow with a label-echoing fake LLM, and check that the
JSON/Markdown reports contain computed metrics, version metadata and the
synthetic-data caveat.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluations import evaluate
from evaluations.evaluate import EvaluationDataset, SYNTHETIC_CAVEAT

REQUIRED_TOPICS = {
    "password_reset",
    "transcript",
    "scholarship",
    "fee",
    "wifi",
    "exam",
    "leave",
    "id_card",
    "library",
    "hostel",
    "research",
    "disciplinary",
    "ambiguous",
    "unsupported",
}


@pytest.fixture(scope="module")
def dataset() -> EvaluationDataset:
    return evaluate.load_dataset()


@pytest.fixture(scope="module")
def offline_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """Run the offline evaluator once, with any live-model path hard-disabled."""
    output_dir = tmp_path_factory.mktemp("offline_eval")
    json_path = output_dir / "evaluation.json"
    md_path = output_dir / "evaluation.md"

    patcher = pytest.MonkeyPatch()

    def _forbidden_client(*args: object, **kwargs: object) -> None:
        raise AssertionError("Offline evaluation must never construct an OpenAI client")

    patcher.setattr("openai.OpenAI", _forbidden_client)
    patcher.setattr(
        evaluate,
        "_live_llm",
        lambda *args, **kwargs: pytest.fail("Offline evaluation must not call _live_llm"),
    )
    try:
        report = evaluate.run_evaluation(
            mode="offline",
            model_version="offline-test-v1",
            output_json=json_path,
            output_md=md_path,
        )
    finally:
        patcher.undo()

    return {
        "report": report,
        "json_path": json_path,
        "md_path": md_path,
        "json_text": json_path.read_text(encoding="utf-8"),
        "md_text": md_path.read_text(encoding="utf-8"),
    }


def test_dataset_schema_is_valid_and_covers_required_topics(dataset: EvaluationDataset) -> None:
    assert dataset.dataset_version
    assert "synthetic" in dataset.description.casefold()
    assert "NOT real university" in dataset.description
    assert len(dataset.records) >= 20

    ids = [record.id for record in dataset.records]
    assert len(ids) == len(set(ids))

    topics = {record.topic for record in dataset.records}
    assert REQUIRED_TOPICS.issubset(topics)

    allowed_sources = {item.source_id for item in evaluate.build_knowledge_repository().documents}
    for record in dataset.records:
        assert record.query.strip()
        assert record.expected_intent.strip()
        assert record.expected_category.strip()
        assert record.expected_priority in {"low", "normal", "high", "urgent"}
        assert record.expected_department.strip()
        assert record.expected_department_keyword.strip()
        assert set(record.expected_sources).issubset(allowed_sources)
        assert isinstance(record.expected_abstention, bool)
        assert isinstance(record.expected_unsupported_claim, bool)

    assert any(record.expected_abstention for record in dataset.records)
    assert any(not record.expected_abstention for record in dataset.records)
    assert any(record.expected_unsupported_claim for record in dataset.records)
    assert any(not record.expected_unsupported_claim for record in dataset.records)


def test_offline_evaluator_writes_files_with_matching_counts(
    dataset: EvaluationDataset, offline_artifacts: dict[str, object]
) -> None:
    json_path = Path(offline_artifacts["json_path"])
    md_path = Path(offline_artifacts["md_path"])
    report = offline_artifacts["report"]
    assert isinstance(report, dict)
    assert json_path.is_file() and md_path.is_file()

    on_disk = json.loads(offline_artifacts["json_text"])
    assert on_disk == report
    assert on_disk["metrics"]["record_count"] == len(dataset.records)
    assert len(on_disk["per_record"]) == len(dataset.records)
    assert [item["id"] for item in on_disk["per_record"]] == [
        record.id for record in dataset.records
    ]


def test_reports_include_version_metadata_and_synthetic_caveat(
    dataset: EvaluationDataset, offline_artifacts: dict[str, object]
) -> None:
    report = offline_artifacts["report"]
    json_text = str(offline_artifacts["json_text"])
    md_text = str(offline_artifacts["md_text"])

    assert report["dataset_version"] == dataset.dataset_version
    assert report["model_version"] == "offline-test-v1"
    assert report["synthetic_data_caveat"] == SYNTHETIC_CAVEAT
    assert "NOT real university performance" in SYNTHETIC_CAVEAT

    for text in (json_text, md_text):
        assert dataset.dataset_version in text
        assert "offline-test-v1" in text
        assert "NOT real university performance" in text
        assert "must not be used as real-world accuracy" in text


def test_metrics_are_recomputed_from_per_record_results(
    offline_artifacts: dict[str, object],
) -> None:
    report = offline_artifacts["report"]
    metrics = report["metrics"]
    per_record = report["per_record"]
    count = len(per_record)

    for key in (
        "intent_classification_accuracy",
        "category_classification_accuracy",
        "priority_prediction_accuracy",
        "department_routing_accuracy",
        "knowledge_retrieval_precision",
        "knowledge_retrieval_recall",
        "citation_correctness",
        "abstention_correctness",
    ):
        assert 0.0 <= metrics[key] <= 1.0

    correct_keys = ("intent", "category", "priority", "department", "citation", "abstention")
    for key in correct_keys:
        expected = round(sum(item["correct"][key] for item in per_record) / count, 4)
        metric_name = "abstention_correctness" if key == "abstention" else f"{key}_classification_accuracy"
        if key == "priority":
            metric_name = "priority_prediction_accuracy"
        if key == "department":
            metric_name = "department_routing_accuracy"
        if key == "citation":
            metric_name = "citation_correctness"
        assert metrics[metric_name] == expected

    tp = sum(item["retrieval_true_positives"] for item in per_record)
    retrieved = sum(len(item["observed"]["retrieved_sources"]) for item in per_record)
    expected_total = sum(len(item["expected"]["sources"]) for item in per_record)
    assert metrics["knowledge_retrieval_precision"] == round(tp / retrieved, 4)
    assert metrics["knowledge_retrieval_recall"] == round(tp / expected_total, 4)

    detected = sum(item["correct"]["unsupported_claim_detected"] for item in per_record)
    assert metrics["unsupported_claim_count"] == detected
    assert metrics["unsupported_claim_expected_count"] == sum(
        item["expected"]["unsupported_claim"] for item in per_record
    )


def test_offline_mode_uses_no_network_tokens_or_cost(
    offline_artifacts: dict[str, object],
) -> None:
    report = offline_artifacts["report"]
    assert report["mode"] == "offline"
    assert report["token_usage"]["prompt_tokens"] is None
    assert report["token_usage"]["completion_tokens"] is None
    assert report["token_usage"]["total_tokens"] is None
    assert report["token_usage"]["estimated_cost_usd"] is None

    latency = report["latency"]
    assert "Synthetic-run latency" in latency["label"]
    assert latency["mean_ms"] >= 0
    assert latency["p95_ms"] >= latency["mean_ms"] or latency["p95_ms"] > 0


def test_abstention_cases_are_handled_without_citations(
    offline_artifacts: dict[str, object],
) -> None:
    report = offline_artifacts["report"]
    abstaining = [item for item in report["per_record"] if item["expected"]["abstention"]]
    supported = [item for item in report["per_record"] if item["expected"]["sources"]]
    assert abstaining
    assert supported

    for item in abstaining:
        assert item["observed"]["abstention"] is True
        assert item["observed"]["retrieved_sources"] == []
        assert item["observed"]["cited_ids"] == []
        assert item["observed"]["draft_source_ids"] == []
        assert item["correct"]["abstention"] is True
    assert report["metrics"]["abstention_correctness"] == 1.0


def test_cli_offline_mode_writes_requested_paths(tmp_path: Path) -> None:
    json_path = tmp_path / "cli.json"
    md_path = tmp_path / "cli.md"
    exit_code = evaluate.main(
        [
            "--output-json",
            str(json_path),
            "--output-md",
            str(md_path),
            "--model-version",
            "cli-test-v1",
        ]
    )
    assert exit_code == 0
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["mode"] == "offline"
    assert report["model_version"] == "cli-test-v1"
    assert "NOT real university performance" in md_path.read_text(encoding="utf-8")


def test_live_mode_requires_explicit_opt_in_and_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(evaluate.settings, "OPENAI_API_KEY", "")

    def _client_should_not_be_created(*args: object, **kwargs: object) -> None:
        pytest.fail("No OpenAI client may be created without a key")

    monkeypatch.setattr("openai.OpenAI", _client_should_not_be_created)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        evaluate.run_evaluation(
            mode="live",
            output_json=tmp_path / "live.json",
            output_md=tmp_path / "live.md",
        )
    assert not (tmp_path / "live.json").exists()
    assert not (tmp_path / "live.md").exists()
