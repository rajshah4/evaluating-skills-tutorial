from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skill_eval.constants import RESULTS_DIR


SUMMARY_FIELDS = [
    "task",
    "backend",
    "condition",
    "model",
    "model_label",
    "passed",
    "runtime_seconds",
    "event_count",
    "item_count",
    "trace_id",
    "conversation_id",
    "remote_output",
]


def load_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for metrics_path in sorted(RESULTS_DIR.rglob("metrics.json")):
        data = json.loads(metrics_path.read_text(encoding="utf-8"))
        data.setdefault("task", "software-dependency-audit")
        data.setdefault("backend", "unknown")
        data.setdefault("model", "")
        data.setdefault("model_label", "")
        data.setdefault("item_count", data.get("finding_count"))
        data.setdefault("trace_id", "")
        data.setdefault("conversation_id", "")
        data.setdefault("remote_output", "")
        data["metrics_path"] = str(metrics_path.relative_to(ROOT))
        rows.append(data)
    return rows


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metrics_path", *SUMMARY_FIELDS])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in ["metrics_path", *SUMMARY_FIELDS]})


def write_json(rows: list[dict[str, object]], path: Path) -> None:
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def main() -> int:
    rows = load_rows()
    if not rows:
        print("No runs found under results/.")
        return 1

    csv_path = RESULTS_DIR / "model_matrix_summary.csv"
    json_path = RESULTS_DIR / "model_matrix_summary.json"
    write_csv(rows, csv_path)
    write_json(rows, json_path)
    print(f"Wrote {csv_path.relative_to(ROOT)}")
    print(f"Wrote {json_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
