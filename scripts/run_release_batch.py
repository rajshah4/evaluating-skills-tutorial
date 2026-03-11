from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
RUN_EVAL = SCRIPT_DIR / "run_eval.py"
START_AGENT_SERVER = SCRIPT_DIR / "start_local_agent_server.sh"

TASKS = [
    "software-dependency-audit",
    "sec-financial-report",
    "sales-pivot-analysis",
]
CONDITIONS = [
    "no-skill",
    "improved-skill",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the release-check evaluation batch.")
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Base results directory.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", "openhands/claude-sonnet-4-5-20250929"),
        help="Model to use for every run.",
    )
    parser.add_argument(
        "--cloud-repo",
        default=os.getenv("OPENHANDS_CLOUD_REPO", "rajshah4/evaluating-skills-tutorial"),
        help="GitHub repo for Cloud repo-backed runs.",
    )
    parser.add_argument(
        "--skip-cloud",
        action="store_true",
        help="Skip Cloud repo-backed runs.",
    )
    parser.add_argument(
        "--skip-local",
        action="store_true",
        help="Skip local agent-server runs.",
    )
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


def run_eval(
    *,
    task: str,
    condition: str,
    backend: str,
    execution_mode: str,
    model: str,
    model_label: str,
    results_dir: str,
    cloud_repo: str,
) -> dict[str, object]:
    cmd = [
        sys.executable,
        str(RUN_EVAL),
        "--task",
        task,
        "--condition",
        condition,
        "--backend",
        backend,
        "--execution-mode",
        execution_mode,
        "--model",
        model,
        "--model-label",
        model_label,
        "--results-dir",
        results_dir,
    ]
    if backend == "cloud":
        cmd.extend(["--cloud-repo", cloud_repo])

    completed = subprocess.run(cmd, cwd=ROOT)
    metrics_path = ROOT / results_dir / task / model_label / condition / "metrics.json"
    row: dict[str, object] = {
        "task": task,
        "condition": condition,
        "backend": backend,
        "model": model,
        "model_label": model_label,
        "exit_code": completed.returncode,
        "metrics_path": str(metrics_path.relative_to(ROOT)),
    }
    if metrics_path.exists():
        row["metrics"] = json.loads(metrics_path.read_text(encoding="utf-8"))
    return row


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


def main() -> int:
    args = parse_args()
    results: list[dict[str, object]] = []
    local_process: subprocess.Popen[str] | None = None
    failed = False

    try:
        if not args.skip_local:
            local_process = start_local_agent_server()
            for task in TASKS:
                for condition in CONDITIONS:
                    label = "release-local"
                    execution_mode = "upload" if task == "software-dependency-audit" else "repo"
                    row = run_eval(
                        task=task,
                        condition=condition,
                        backend="agent-server",
                        execution_mode=execution_mode,
                        model=args.model,
                        model_label=label,
                        results_dir=args.results_dir,
                        cloud_repo=args.cloud_repo,
                    )
                    results.append(row)
                    failed = failed or row["exit_code"] != 0

        if not args.skip_cloud:
            for task in TASKS:
                for condition in CONDITIONS:
                    label = "release-cloud"
                    execution_mode = "upload" if task == "software-dependency-audit" else "repo"
                    row = run_eval(
                        task=task,
                        condition=condition,
                        backend="cloud",
                        execution_mode=execution_mode,
                        model=args.model,
                        model_label=label,
                        results_dir=args.results_dir,
                        cloud_repo=args.cloud_repo,
                    )
                    results.append(row)
                    failed = failed or row["exit_code"] != 0
    finally:
        stop_process(local_process)

    manifest_path = ROOT / args.results_dir / "release_batch_manifest.json"
    manifest_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Wrote {manifest_path.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
