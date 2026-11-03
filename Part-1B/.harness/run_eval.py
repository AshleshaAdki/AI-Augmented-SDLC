"""Three-layer reminder evaluation with reproducible date context."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from src.agent import ReminderAgent, ReminderOutput  # noqa: E402
from src.llm_agent import LLMReminderAgent, create_agent  # noqa: E402

THRESHOLD_PERCENT = 90.0
REFERENCE_TIME = datetime(2026, 11, 3, tzinfo=timezone.utc)
REQUIREMENT_IDS = {
    "REM-1",
    "REM-2",
    "REM-3",
    "REM-4",
    "REM-5",
    "REM-6",
    "REM-7",
    "REM-8",
    "SAFE-1",
    "SAFE-2",
    "SAFE-3",
    "INV-1",
    "INV-2",
    "INV-3",
    "INV-4",
    "INV-5",
}


def _evaluate_case(
    agent: ReminderAgent | LLMReminderAgent,
    case: dict[str, Any],
) -> dict[str, Any]:
    output = agent.parse_intent(case["input"])
    errors: list[str] = []
    requirement_ids = case.get("requirement_ids", [])
    invalid_ids = set(requirement_ids) - REQUIREMENT_IDS
    if not requirement_ids or invalid_ids:
        errors.append(
            "Layer 1 traceability: missing or unknown requirement IDs {}".format(
                sorted(invalid_ids)
            )
        )

    # Layer 1: the returned value must satisfy the strict output contract.
    try:
        validated = ReminderOutput.model_validate(output.model_dump())
    except ValueError as exc:
        errors.append("Layer 1 schema: {}".format(exc))
        validated = output

    # Layer 2: clarification and content invariants must always hold.
    if validated.needs_clarification and not validated.clarification_question:
        errors.append("Layer 2 invariant: clarification question is required")
    if not validated.needs_clarification and not validated.title:
        errors.append("Layer 2 invariant: an actionable result requires a title")
    if not validated.needs_clarification and validated.due_date is None:
        if validated.recurrence.value == "none":
            errors.append("Layer 2 invariant: dated reminders require a due date")
    if validated.due_date is not None and validated.needs_clarification:
        errors.append("Layer 2 invariant: unresolved output must not assert a due date")
    if (
        any(item.startswith("SAFE-") for item in requirement_ids)
        and not validated.needs_clarification
    ):
        errors.append(
            "Layer 2 safety: unsafe request must not be accepted as a reminder"
        )

    # Layer 3: compare recognized intent with the dataset's expected behavior.
    if validated.needs_clarification != case["expected_needs_clarification"]:
        errors.append("Layer 3 semantic: clarification expectation did not match")
    expected_title = case.get("expected_title")
    if "expected_title" in case and not _titles_match(
        validated.title, expected_title
    ):
        errors.append(
            "Layer 3 semantic: expected title {!r}, got {!r}".format(
                expected_title, validated.title
            )
        )
    expected_recurrence = case.get("expected_recurrence")
    if expected_recurrence and validated.recurrence.value != expected_recurrence:
        errors.append(
            "Layer 3 semantic: expected recurrence {!r}, got {!r}".format(
                expected_recurrence, validated.recurrence.value
            )
        )
    expected_priority = case.get("expected_priority")
    if expected_priority and validated.priority.value != expected_priority:
        errors.append(
            "Layer 3 semantic: expected priority {!r}, got {!r}".format(
                expected_priority, validated.priority.value
            )
        )
    expected_tags = case.get("expected_tags")
    if expected_tags is not None and validated.tags != expected_tags:
        errors.append(
            "Layer 3 semantic: expected tags {!r}, got {!r}".format(
                expected_tags, validated.tags
            )
        )
    return {
        "id": case["id"],
        "requirement_ids": requirement_ids,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "output": validated.model_dump(mode="json"),
    }


def _titles_match(actual: str | None, expected: str | None) -> bool:
    if actual is None or expected is None:
        return actual is expected
    actual_words = [
        word for word in actual.casefold().split() if word not in {"a", "an", "the"}
    ]
    expected_words = [
        word
        for word in expected.casefold().split()
        if word not in {"a", "an", "the"}
    ]
    return actual_words == expected_words


def main() -> int:
    dataset_path = BASE_DIR / "evals" / "dataset.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(dataset, list) or not dataset:
        raise ValueError("evaluation dataset must be a non-empty JSON list")

    agent = create_agent(reference=REFERENCE_TIME)
    backend = agent.backend
    print("Evaluation backend: {}".format(backend))
    results = [_evaluate_case(agent, case) for case in dataset]
    passed = sum(result["status"] == "PASS" for result in results)
    score = passed * 100.0 / len(results)
    success = score >= THRESHOLD_PERCENT
    requirement_coverage = sorted(
        {requirement for case in dataset for requirement in case["requirement_ids"]}
    )

    print(
        "Reminder evaluation: {} test cases, threshold {:.1f}%".format(
            len(results), THRESHOLD_PERCENT
        )
    )
    for result in results:
        print("Case {:02d}: {}".format(result["id"], result["status"]))
        for error in result["errors"]:
            print("  - {}".format(error))
    print(
        "Result: {}/{} ({:.1f}%) — {}".format(
            passed, len(results), score, "PASS" if success else "FAIL"
        )
    )

    evidence_dir = BASE_DIR / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "eval-results.json").write_text(
        json.dumps(
            {
                "reference_time": REFERENCE_TIME.isoformat(),
                "total": len(results),
                "passed": passed,
                "score_percent": score,
                "threshold_percent": THRESHOLD_PERCENT,
                "status": "PASS" if success else "FAIL",
                "backend": backend,
                "model": getattr(agent, "model", None),
                "requirement_coverage": requirement_coverage,
                "cases": results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    final_generation = evidence_dir / "final-generation"
    final_generation.mkdir(parents=True, exist_ok=True)
    for source_name in ("agent.py", "llm_agent.py"):
        shutil.copyfile(
            BASE_DIR / "src" / source_name,
            final_generation / source_name,
        )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
