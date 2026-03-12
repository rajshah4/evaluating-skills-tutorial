from __future__ import annotations

import importlib.util
from pathlib import Path

from .constants import get_task_config
from .verification import VerificationResult


def _load_task_verify(task: str):
    config = get_task_config(task)
    verify_path = config.task_dir / "verify.py"
    spec = importlib.util.spec_from_file_location(f"skill_eval_task_{config.dir_name}", verify_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Unable to load verifier for task: {task}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    verify_fn = getattr(module, "verify", None)
    if verify_fn is None:
        raise ValueError(f"Task verifier missing verify() function: {verify_path}")
    return verify_fn


def verify_task_output(task: str, report_path: Path, expected_path: Path | None = None) -> VerificationResult:
    config = get_task_config(task)
    expected_path = expected_path or config.expected_output
    verify_fn = _load_task_verify(task)
    return verify_fn(report_path, expected_path)
