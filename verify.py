from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skill_eval.verify import verify_task_output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a generated tutorial task output.")
    parser.add_argument(
        "artifact",
        nargs="?",
        default="results/software-dependency-audit/improved-skill/report.json",
        help="Path to the generated output artifact to verify.",
    )
    parser.add_argument(
        "--task",
        default="software-dependency-audit",
        choices=["software-dependency-audit", "sec-financial-report", "sales-pivot-analysis"],
        help="Task to verify against.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = verify_task_output(args.task, Path(args.artifact))
    print(result.message)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
