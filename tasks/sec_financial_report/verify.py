from __future__ import annotations

from pathlib import Path

from skill_eval.verification import VerificationResult, load_json


def verify(report_path: Path, expected_path: Path) -> VerificationResult:
    report = load_json(report_path)
    expected = load_json(expected_path)

    required_fields = expected["required_fields"]
    for field in required_fields:
        if field not in report:
            return VerificationResult(False, f"answers.json is missing required field: {field}", 0)

    for field, expected_value in expected["exact_values"].items():
        if report.get(field) != expected_value:
            return VerificationResult(
                False,
                f"answers.json field '{field}' did not match expected value",
                len(required_fields),
            )

    for field, spec in expected["numeric_values"].items():
        raw_value = report.get(field)
        try:
            actual_value = float(raw_value)
        except (TypeError, ValueError):
            return VerificationResult(
                False,
                f"answers.json field '{field}' must be numeric",
                len(required_fields),
            )

        expected_value = float(spec["value"])
        tolerance = float(spec["tolerance"])
        if abs(actual_value - expected_value) > tolerance:
            return VerificationResult(
                False,
                f"answers.json field '{field}' was outside tolerance",
                len(required_fields),
            )

    for field, substrings in expected.get("contains_values", {}).items():
        actual_value = report.get(field)
        if not isinstance(actual_value, str):
            return VerificationResult(
                False,
                f"answers.json field '{field}' must be a string",
                len(required_fields),
            )
        normalized = actual_value.lower()
        missing = [substring for substring in substrings if substring.lower() not in normalized]
        if missing:
            return VerificationResult(
                False,
                f"answers.json field '{field}' is missing expected content",
                len(required_fields),
            )

    return VerificationResult(
        True,
        "answers.json matches the expected financial extraction and calculations",
        len(required_fields),
    )
