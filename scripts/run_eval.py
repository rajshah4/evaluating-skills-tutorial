from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import SecretStr

from openhands.sdk import Agent, AgentContext, Conversation, Event, LLM, Tool
from openhands.sdk.context import Skill
from openhands.sdk.event import LLMConvertibleEvent
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool
from openhands.workspace import DockerWorkspace, OpenHandsCloudWorkspace

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

load_dotenv(ROOT / ".env")

from skill_eval.constants import (
    REMOTE_INPUT_DIR,
    REMOTE_OUTPUT_DIR,
    REMOTE_PROJECT_DIR,
    RESULTS_DIR,
    get_task_config,
)
from skill_eval.verify import verify_task_output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a tutorial task through OpenHands.")
    parser.add_argument(
        "--task",
        default="software-dependency-audit",
        choices=["software-dependency-audit", "sec-financial-report", "sales-pivot-analysis"],
        help="Tutorial task to run.",
    )
    parser.add_argument(
        "--condition",
        default="no-skill",
        choices=["no-skill", "baseline-skill", "improved-skill"],
        help="Evaluation condition to run.",
    )
    parser.add_argument(
        "--backend",
        default="cloud",
        choices=["cloud", "docker"],
        help="Execution backend to use.",
    )
    parser.add_argument(
        "--results-dir",
        default=str(RESULTS_DIR),
        help="Directory where run outputs should be written.",
    )
    parser.add_argument(
        "--keep-alive",
        action="store_true",
        help="Keep the cloud sandbox alive after the run finishes.",
    )
    parser.add_argument(
        "--docker-image",
        default=os.getenv("OPENHANDS_DOCKER_IMAGE", "ghcr.io/openhands/agent-server:latest-python"),
        help="Docker agent-server image to use when --backend docker is selected.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", "openhands/claude-sonnet-4-5-20250929"),
        help="Model name to use for the run.",
    )
    parser.add_argument(
        "--model-label",
        default="",
        help="Optional results subfolder label for this model run.",
    )
    return parser.parse_args()


def build_llm(model: str) -> LLM:
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    return LLM(
        usage_id="dependency-audit-eval",
        model=model,
        api_key=SecretStr(api_key) if api_key else None,
        base_url=base_url,
    )


def build_agent_context(task: str, condition: str) -> AgentContext | None:
    if condition == "no-skill":
        return None

    task_skill_dir = ROOT / "skills" / task.replace("-", "_") / condition.replace("-skill", "")
    fallback_skill_dir = ROOT / "skills" / condition.replace("-skill", "")
    skill_dir = task_skill_dir if task_skill_dir.exists() else fallback_skill_dir
    skill_path = skill_dir / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    return AgentContext(
        skills=[
            Skill(
                name=skill_path.name,
                content=content,
                source=str(skill_path),
                trigger=None,
            )
        ]
    )


def build_prompt(task: str, condition: str) -> str:
    config = get_task_config(task)
    snapshot_context = ""
    deterministic_rule = ""
    if task == "software-dependency-audit" and condition != "no-skill":
        snapshot_context = (
            f"- A pinned offline scan snapshot may also be present at "
            f"`{REMOTE_PROJECT_DIR}/input/trivy_report.json`.\n"
        )
        deterministic_rule = "- Prefer deterministic local inputs over refreshing live vulnerability data.\n"

    return config.prompt_template.read_text(encoding="utf-8").format(
        remote_project_dir=REMOTE_PROJECT_DIR,
        remote_lockfile=f"{REMOTE_INPUT_DIR}/package-lock.json",
        remote_report=config.remote_output,
        remote_output_dir=REMOTE_OUTPUT_DIR,
        snapshot_context=snapshot_context,
        deterministic_rule=deterministic_rule,
    )


def build_agent(agent_context: AgentContext | None, model: str) -> Agent:
    return Agent(
        llm=build_llm(model),
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
        ],
        agent_context=agent_context,
    )


def ensure_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def create_workspace(args: argparse.Namespace):
    if args.backend == "cloud":
        cloud_api_key = ensure_env("OPENHANDS_CLOUD_API_KEY")
        cloud_api_url = os.getenv("OPENHANDS_CLOUD_API_URL", "https://app.all-hands.dev")
        return OpenHandsCloudWorkspace(
            cloud_api_url=cloud_api_url,
            cloud_api_key=cloud_api_key,
            keep_alive=args.keep_alive,
        )

    forward_env = [
        "LMNR_PROJECT_API_KEY",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_HEADERS",
        "OTEL_SERVICE_NAME",
        "DEBUG",
    ]
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        host_port = sock.getsockname()[1]
    return DockerWorkspace(
        server_image=args.docker_image,
        host_port=host_port,
        forward_env=forward_env,
        detach_logs=False,
    )


def serialize_event(event: Event) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": event.__class__.__name__,
    }
    if hasattr(event, "source"):
        payload["source"] = getattr(event, "source")
    if hasattr(event, "message"):
        payload["message"] = getattr(event, "message")
    if isinstance(event, LLMConvertibleEvent):
        payload["llm_message"] = str(event.to_llm_message())
    return payload


def main() -> int:
    args = parse_args()
    results_root = Path(args.results_dir)
    config = get_task_config(args.task)
    run_dir = results_root / args.task
    if args.model_label:
        run_dir = run_dir / args.model_label
    run_dir = run_dir / args.condition
    run_dir.mkdir(parents=True, exist_ok=True)

    events: list[dict[str, Any]] = []

    def callback(event: Event) -> None:
        events.append(serialize_event(event))

    workspace = create_workspace(args)

    start_time = time.perf_counter()
    try:
        workspace.execute_command(f"mkdir -p {REMOTE_INPUT_DIR} {REMOTE_OUTPUT_DIR}")
        input_dir = config.task_dir / "input"
        upload_names = list(config.input_paths)
        if args.condition != "no-skill":
            upload_names.extend(config.conditional_input_paths)

        for name in upload_names:
            local_path = input_dir / name
            if local_path.is_file():
                remote_path = f"{REMOTE_INPUT_DIR}/{name}"
                remote_parent = str(Path(remote_path).parent)
                workspace.execute_command(f"mkdir -p {remote_parent}")
                workspace.file_upload(str(local_path), remote_path)

        conversation = Conversation(
            agent=build_agent(build_agent_context(args.task, args.condition), args.model),
            workspace=workspace,
            callbacks=[callback],
        )
        conversation.send_message(build_prompt(args.task, args.condition))
        conversation.run()

        local_report = run_dir / config.output_name
        workspace.file_download(config.remote_output, str(local_report))

        verification = verify_task_output(args.task, local_report)
        duration_seconds = round(time.perf_counter() - start_time, 2)

        metrics = {
            "task": args.task,
            "condition": args.condition,
            "backend": args.backend,
            "model": args.model,
            "model_label": args.model_label or None,
            "passed": verification.passed,
            "message": verification.message,
            "runtime_seconds": duration_seconds,
            "event_count": len(events),
            "item_count": verification.item_count,
            "sandbox_id": getattr(workspace, "sandbox_id", None),
            "remote_output": config.remote_output,
        }

        (run_dir / "metrics.json").write_text(
            json.dumps(metrics, indent=2) + "\n",
            encoding="utf-8",
        )
        (run_dir / "events.json").write_text(
            json.dumps(events, indent=2) + "\n",
            encoding="utf-8",
        )

        print(json.dumps(metrics, indent=2))
        return 0 if verification.passed else 1
    finally:
        workspace.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
