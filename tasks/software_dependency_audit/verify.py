from __future__ import annotations

from pathlib import Path
from typing import Any

from skill_eval.verification import VerificationResult, load_json


DEPENDENCY_REQUIRED_KEYS = [
    "package",
    "version",
    "cve_id",
    "severity",
    "cvss_score",
    "fixed_version",
    "title",
    "url",
]


def _normalize_dependency_finding(finding: dict[str, Any]) -> dict[str, str]:
    normalized = {}
    for key in DEPENDENCY_REQUIRED_KEYS:
        value = finding.get(key)
        if value is None:
            raise ValueError(f"Missing required key: {key}")
        normalized[key] = str(value).strip()
    return normalized


def verify(report_path: Path, expected_path: Path) -> VerificationResult:
    report = load_json(report_path)
    expected = load_json(expected_path)

    findings = report.get("findings")
    if not isinstance(findings, list):
        return VerificationResult(False, "report.json must contain a top-level 'findings' list", 0)

    try:
        actual = sorted(
            (_normalize_dependency_finding(item) for item in findings),
            key=lambda item: (item["package"], item["version"], item["cve_id"]),
        )
        target = sorted(
            (_normalize_dependency_finding(item) for item in expected["findings"]),
            key=lambda item: (item["package"], item["version"], item["cve_id"]),
        )
    except ValueError as exc:
        return VerificationResult(False, str(exc), len(findings))

    if actual != target:
        return VerificationResult(
            False,
            "report.json does not match the expected HIGH/CRITICAL vulnerability set",
            len(findings),
        )

    return VerificationResult(True, "report.json matches the expected benchmark findings", len(findings))
