from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skill_eval.constants import RESULTS_DIR


def main() -> int:
    rows = []
    metric_paths = sorted(RESULTS_DIR.rglob("metrics.json"))
    for metrics_path in metric_paths:
        data = json.loads(metrics_path.read_text(encoding="utf-8"))
        data.setdefault("task", "software-dependency-audit")
        data.setdefault("item_count", data.get("finding_count"))
        rows.append(data)

    if not rows:
        print("No runs found under results/.")
        return 1

    print("task\tmodel_label\tcondition\tpassed\truntime_seconds\tevent_count\titem_count")
    for row in rows:
        print(
            f"{row['task']}\t{row.get('model_label') or '-'}\t{row['condition']}\t{row['passed']}\t{row['runtime_seconds']}\t"
            f"{row['event_count']}\t{row['item_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
