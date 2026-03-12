from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RUN_EVAL = SCRIPT_DIR / "run_eval.py"


def main() -> int:
    cmd = [sys.executable, str(RUN_EVAL), "--task", "sales-pivot-analysis", *sys.argv[1:]]
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
