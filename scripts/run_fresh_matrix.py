from __future__ import annotations

import argparse
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
RUN_EVAL = SCRIPT_DIR / "run_eval.py"
START_AGENT_SERVER = SCRIPT_DIR / "start_local_agent_server.sh"
RUNNER_PYTHON = ROOT / ".venv" / "bin" / "python"

TASKS = [
    "software-dependency-audit",
    "sec-financial-report",
    "sales-pivot-analysis",
]
CONDITIONS = [
    "no-skill",
    "improved-skill",
]
BACKENDS = [
    "agent-server",
    "cloud",
]
DEFAULT_MODELS = [
    "openhands/claude-sonnet-4-5-20250929",
    "openhands/minimax-m2.5",
    "openhands/gemini-3-pro-preview",
    "openhands/gemini-3-flash-preview",
    "openhands/kimi-k2-0711-preview",
]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "run"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a fresh full matrix for the current tutorial paths.")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Repeat to evaluate multiple models. Defaults to the validated model set.",
    )
    parser.add_argument(
        "--cloud-repo",
        default=os.getenv("OPENHANDS_CLOUD_REPO", "rajshah4/evaluating-skills-tutorial"),
    )
    parser.add_argument("--skip-cloud", action="store_true")
    parser.add_argument("--skip-local", action="store_true")
    return parser.parse_args()


def wait_for_server(url: str, timeout_seconds: float = 60.0) -> None:
    import httpx

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = httpx.get(f"{url.rstrip('/')}/health", timeout=2.0)
            if response.status_code < 500:
                return
        except Exception:
            pass
        time.sleep(1.0)
    raise RuntimeError(f"Agent server did not become ready at {url}")


def start_local_agent_server() -> subprocess.Popen[str]:
    env = os.environ.copy()
    process = subprocess.Popen(
        [str(START_AGENT_SERVER)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        text=True,
    )
    wait_for_server(env.get("OPENHANDS_AGENT_SERVER_URL", "http://127.0.0.1:8000"))
    return process


def stop_process(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def execution_mode_for(task: str) -> str:
    return "upload" if task == "software-dependency-audit" else "repo"


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def load_manifest(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a list in {path}")
    normalized: list[dict[str, object]] = []
    for row in data:
        metrics_path = row.get("metrics_path")
        if "metrics" not in row and isinstance(metrics_path, str):
            resolved = ROOT / metrics_path
            if resolved.exists():
                row["metrics"] = json.loads(resolved.read_text(encoding="utf-8"))
        normalized.append(row)
    return normalized


def runner_python() -> str:
    current = Path(sys.executable)
    if current.exists():
        return str(current)
    if RUNNER_PYTHON.exists():
        return str(RUNNER_PYTHON)
    resolved = shutil.which("python3")
    if resolved:
        return resolved
    return sys.executable


def run_one(
    *,
    task: str,
    condition: str,
    backend: str,
    model: str,
    model_label: str,
    results_dir: str,
    cloud_repo: str,
) -> dict[str, object]:
    cmd = [
        runner_python(),
        str(RUN_EVAL),
        "--task",
        task,
        "--condition",
        condition,
        "--backend",
        backend,
        "--execution-mode",
        execution_mode_for(task),
        "--model",
        model,
        "--model-label",
        model_label,
        "--results-dir",
        results_dir,
    ]
    if backend == "cloud":
        cmd.extend(["--cloud-repo", cloud_repo])

    started = time.time()
    completed = subprocess.run(cmd, cwd=ROOT)
    metrics_path = ROOT / results_dir / task / model_label / condition / "metrics.json"
    row: dict[str, object] = {
        "task": task,
        "condition": condition,
        "backend": backend,
        "model": model,
        "model_label": model_label,
        "exit_code": completed.returncode,
        "started_at_epoch": started,
        "metrics_path": str(metrics_path.relative_to(ROOT)),
    }
    if metrics_path.exists():
        row["metrics"] = json.loads(metrics_path.read_text(encoding="utf-8"))
    return row


def main() -> int:
    args = parse_args()
    models = args.models or list(DEFAULT_MODELS)
    manifest_path = ROOT / args.results_dir / "fresh_matrix_manifest.json"
    rows = load_manifest(manifest_path)
    index_by_key: dict[tuple[object, object, object, object], int] = {}
    completed_keys = set()
    for idx, row in enumerate(rows):
        key = (
            row.get("task"),
            row.get("condition"),
            row.get("backend"),
            row.get("model"),
        )
        index_by_key[key] = idx
        if "metrics" in row:
            completed_keys.add(key)
    failed = False
    local_process: subprocess.Popen[str] | None = None

    try:
        if not args.skip_local:
            local_process = start_local_agent_server()

        for backend in BACKENDS:
            if backend == "cloud" and args.skip_cloud:
                continue
            if backend == "agent-server" and args.skip_local:
                continue

            for model in models:
                label = f"fresh-{backend}-{slugify(model)}"
                for task in TASKS:
                    for condition in CONDITIONS:
                        key = (task, condition, backend, model)
                        if key in completed_keys:
                            continue
                        row = run_one(
                            task=task,
                            condition=condition,
                            backend=backend,
                            model=model,
                            model_label=label,
                            results_dir=args.results_dir,
                            cloud_repo=args.cloud_repo,
                        )
                        if key in index_by_key:
                            rows[index_by_key[key]] = row
                        else:
                            index_by_key[key] = len(rows)
                            rows.append(row)
                        if "metrics" in row:
                            completed_keys.add(key)
                        write_manifest(manifest_path, rows)
                        failed = failed or row["exit_code"] != 0
    finally:
        stop_process(local_process)

    print(json.dumps(rows, indent=2))
    print(f"Wrote {manifest_path.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
