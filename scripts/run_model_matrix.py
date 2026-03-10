from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
RUN_EVAL = SCRIPT_DIR / "run_eval.py"


def slugify_model(model: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", model).strip("-").lower()
    return slug or "model"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a task across multiple models.")
    parser.add_argument(
        "--task",
        default="software-dependency-audit",
        choices=["software-dependency-audit", "sec-financial-report", "sales-pivot-analysis"],
    )
    parser.add_argument(
        "--condition",
        default="improved-skill",
        choices=["no-skill", "baseline-skill", "improved-skill"],
    )
    parser.add_argument(
        "--backend",
        default="docker",
        choices=["cloud", "docker"],
    )
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        required=True,
        help="Model to evaluate. Repeat for multiple models.",
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Base results directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summaries: list[dict[str, object]] = []

    for model in args.models:
        label = slugify_model(model)
        cmd = [
            sys.executable,
            str(RUN_EVAL),
            "--task",
            args.task,
            "--condition",
            args.condition,
            "--backend",
            args.backend,
            "--results-dir",
            args.results_dir,
            "--model",
            model,
            "--model-label",
            label,
        ]
        completed = subprocess.run(cmd, cwd=ROOT)
        metrics_path = ROOT / args.results_dir / args.task / label / args.condition / "metrics.json"
        summary = {
            "model": model,
            "label": label,
            "exit_code": completed.returncode,
            "metrics_path": str(metrics_path),
        }
        if metrics_path.exists():
            summary["metrics"] = json.loads(metrics_path.read_text(encoding="utf-8"))
        summaries.append(summary)

    print(json.dumps(summaries, indent=2))
    return 0 if all(item["exit_code"] == 0 for item in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
