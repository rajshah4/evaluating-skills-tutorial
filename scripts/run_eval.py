from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from pydantic import SecretStr

from openhands.sdk import Agent, AgentContext, Conversation, Event, LLM, Tool
from openhands.sdk.context import Skill
from openhands.sdk.event import LLMConvertibleEvent
from openhands.sdk.workspace import Workspace as SDKWorkspace
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool
from openhands.workspace import OpenHandsCloudWorkspace

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
        choices=["cloud", "agent-server"],
        help="Execution backend to use.",
    )
    parser.add_argument(
        "--execution-mode",
        default="upload",
        choices=["upload", "repo"],
        help="Use uploaded task fixtures or a repo-backed task layout.",
    )
    parser.add_argument(
        "--cloud-repo",
        default=os.getenv("OPENHANDS_CLOUD_REPO", "rajshah4/evaluating-skills-tutorial"),
        help="Repository to use for Cloud repo-backed runs.",
    )
    parser.add_argument(
        "--cloud-branch",
        default=os.getenv("OPENHANDS_CLOUD_BRANCH", "main"),
        help="Branch to use for Cloud repo-backed runs.",
    )
    parser.add_argument(
        "--cloud-skill-mode",
        default="auto",
        choices=["repo-message", "inline", "auto"],
        help="How Cloud repo-backed runs should provide skill guidance.",
    )
    parser.add_argument(
        "--agent-server-url",
        default=os.getenv("OPENHANDS_AGENT_SERVER_URL", "http://127.0.0.1:8000"),
        help="Base URL for a pre-started local OpenHands agent server.",
    )
    parser.add_argument(
        "--agent-server-api-key",
        default=os.getenv("OPENHANDS_AGENT_SERVER_API_KEY"),
        help="Optional API key for a pre-started local OpenHands agent server.",
    )
    parser.add_argument(
        "--agent-repo-dir",
        default=os.getenv("OPENHANDS_AGENT_REPO_DIR", "/workspace/project/evaluating-skills-tutorial"),
        help="Repo root inside a pre-started local agent server for repo-backed runs.",
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


def get_skill_paths(task: str, condition: str, *, cloud_repo: str = "evaluating-skills-tutorial") -> tuple[Path, str]:
    task_dir = ROOT / "skills" / task.replace("-", "_") / condition.replace("-skill", "")
    fallback_dir = ROOT / "skills" / condition.replace("-skill", "")
    skill_dir = task_dir if task_dir.exists() else fallback_dir
    skill_path = skill_dir / "SKILL.md"
    repo_name = cloud_repo.split("/")[-1].strip() or "evaluating-skills-tutorial"
    repo_skill_path = (
        f"/workspace/project/{repo_name}/.openhands/skills/"
        f"{task.replace('-', '_')}_{condition.replace('-skill', '')}.md"
    )
    return skill_path, repo_skill_path


def build_prompt(task: str, condition: str) -> str:
    return build_prompt_for_paths(task, condition, REMOTE_PROJECT_DIR, REMOTE_OUTPUT_DIR, get_task_config(task).remote_output)


def build_prompt_for_paths(
    task: str,
    condition: str,
    remote_project_dir: str,
    remote_output_dir: str,
    remote_report: str,
) -> str:
    config = get_task_config(task)
    snapshot_context = ""
    deterministic_rule = ""
    if task == "software-dependency-audit" and condition != "no-skill":
        snapshot_context = (
            f"- A pinned offline scan snapshot may also be present at "
            f"`{remote_project_dir}/input/trivy_report.json`.\n"
        )
        deterministic_rule = "- Prefer deterministic local inputs over refreshing live vulnerability data.\n"

    return config.prompt_template.read_text(encoding="utf-8").format(
        remote_project_dir=remote_project_dir,
        remote_lockfile=f"{remote_project_dir}/input/package-lock.json",
        remote_report=remote_report,
        remote_output_dir=remote_output_dir,
        snapshot_context=snapshot_context,
        deterministic_rule=deterministic_rule,
    )


def build_cloud_v1_message(
    task: str,
    condition: str,
    prompt: str,
    *,
    cloud_repo: str,
    cloud_skill_mode: str,
) -> dict[str, Any]:
    if condition == "no-skill":
        text = prompt
    else:
        if cloud_skill_mode == "auto":
            text = prompt
        elif cloud_skill_mode == "inline":
            skill_path, _ = get_skill_paths(task, condition, cloud_repo=cloud_repo)
            text = (
                f"{prompt}\n\n"
                "Apply the following skill guidance while solving the task. "
                "Treat it as procedural instructions, not extra commentary.\n\n"
                f"{skill_path.read_text(encoding='utf-8').strip()}"
            )
        else:
            _, repo_skill_path = get_skill_paths(task, condition, cloud_repo=cloud_repo)
            text = (
                f"{prompt}\n\n"
                "A repository skill is available for this task. Read it first, follow it during execution, "
                "and keep your workflow aligned with it:\n"
                f"- `{repo_skill_path}`\n\n"
                "Treat the repository skill as procedural guidance for how to solve the task."
            )
    return {
        "role": "user",
        "content": [{"type": "text", "text": text}],
    }


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
    if args.backend == "agent-server":
        return SDKWorkspace(
            host=args.agent_server_url,
            api_key=args.agent_server_api_key,
            working_dir="/workspace",
        )
    raise RuntimeError(f"Unsupported backend: {args.backend}")


def get_remote_paths(
    task: str,
    execution_mode: str,
    *,
    backend: str = "agent-server",
    cloud_repo: str = "",
) -> tuple[str, str, str]:
    config = get_task_config(task)
    if execution_mode == "repo":
        if backend == "cloud":
            repo_name = (cloud_repo or "").split("/")[-1].strip()
            if not repo_name:
                raise RuntimeError("cloud_repo must be set for cloud repo-backed runs")
            remote_project_dir = f"/workspace/project/{repo_name}/tasks/{config.dir_name}"
        else:
            remote_project_dir = f"{cloud_repo.rstrip('/')}/task_repos/{config.dir_name}"
        remote_output_dir = f"{remote_project_dir}/output"
        remote_report = f"{remote_output_dir}/{config.output_name}"
        return remote_project_dir, remote_output_dir, remote_report
    return REMOTE_PROJECT_DIR, REMOTE_OUTPUT_DIR, config.remote_output


def prepare_repo_backed_task(task: str) -> Path:
    config = get_task_config(task)
    repo_dir = config.local_repo_dir
    output_dir = repo_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    for child in output_dir.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_file():
            child.unlink()
    return repo_dir


def load_remote_artifact(
    client: httpx.Client,
    file_path: str,
) -> bytes:
    encoded_path = urllib.parse.quote(file_path, safe="")
    response = client.get(f"/api/file/download/{encoded_path}")
    response.raise_for_status()
    return response.content


def run_cloud_repo_mode(
    *,
    args: argparse.Namespace,
    config,
    run_dir: Path,
) -> int:
    cloud_api_key = ensure_env("OPENHANDS_CLOUD_API_KEY")
    cloud_api_url = os.getenv("OPENHANDS_CLOUD_API_URL", "https://app.all-hands.dev").rstrip("/")
    remote_project_dir, remote_output_dir, remote_report = get_remote_paths(
        args.task,
        "repo",
        backend="cloud",
        cloud_repo=args.cloud_repo,
    )
    prompt = build_prompt_for_paths(
        args.task,
        args.condition,
        remote_project_dir,
        remote_output_dir,
        remote_report,
    )
    headers = {"X-Session-API-Key": cloud_api_key, "Content-Type": "application/json"}
    events: list[dict[str, Any]] = []
    start_time = time.perf_counter()

    with httpx.Client(base_url=cloud_api_url, headers=headers, timeout=60.0) as client:
        create_response = client.post(
            "/api/v1/app-conversations",
            json={
                "selected_repository": args.cloud_repo,
                "git_provider": "github",
                "selected_branch": args.cloud_branch,
                "llm_model": args.model,
                "initial_message": build_cloud_v1_message(
                    args.task,
                    args.condition,
                    prompt,
                    cloud_repo=args.cloud_repo,
                    cloud_skill_mode=args.cloud_skill_mode,
                ),
            },
        )
        create_response.raise_for_status()
        create_payload = create_response.json()
        start_task_id = create_payload["id"]

        conversation_info: dict[str, Any] | None = None
        app_conversation_id: str | None = None
        runtime_url: str | None = None
        session_api_key: str | None = None
        artifact_bytes: bytes | None = None
        deadline = time.monotonic() + 600
        while True:
            start_response = client.get("/api/v1/app-conversations/start-tasks", params={"ids": start_task_id})
            start_response.raise_for_status()
            start_payload = start_response.json()
            start_items = start_payload if isinstance(start_payload, list) else start_payload.get("items", [])
            if not start_items:
                raise RuntimeError(f"Cloud V1 start-task lookup returned no rows for {start_task_id}")
            start_info = start_items[0]
            app_conversation_id = start_info.get("app_conversation_id")
            events.append(
                {
                    "type": "StartTaskPoll",
                    "start_task_id": start_task_id,
                    "status": start_info.get("status"),
                    "detail": start_info.get("detail"),
                    "app_conversation_id": app_conversation_id,
                }
            )

            if app_conversation_id:
                conv_response = client.get("/api/v1/app-conversations", params={"ids": app_conversation_id})
                conv_response.raise_for_status()
                conv_payload = conv_response.json()
                conv_items = conv_payload if isinstance(conv_payload, list) else conv_payload.get("items", [])
                if not conv_items:
                    raise RuntimeError(f"Cloud V1 conversation lookup returned no rows for {app_conversation_id}")
                conversation_info = conv_items[0]
                execution_status = conversation_info.get("execution_status")
                sandbox_status = conversation_info.get("sandbox_status")
                runtime_url = conversation_info.get("conversation_url", "").rsplit("/api/conversations/", 1)[0]
                session_api_key = conversation_info.get("session_api_key")
                events.append(
                    {
                        "type": "AppConversationPoll",
                        "conversation_id": app_conversation_id,
                        "execution_status": execution_status,
                        "sandbox_status": sandbox_status,
                    }
                )

                if runtime_url and session_api_key:
                    try:
                        with httpx.Client(
                            base_url=runtime_url,
                            headers={"X-Session-API-Key": session_api_key},
                            timeout=60.0,
                        ) as runtime_client:
                            artifact_bytes = load_remote_artifact(runtime_client, remote_report)
                        events.append({"type": "ArtifactFetch", "status": "ok", "path": remote_report})
                        break
                    except Exception as exc:
                        events.append(
                            {
                                "type": "ArtifactFetch",
                                "status": "pending",
                                "path": remote_report,
                                "error": str(exc),
                            }
                        )

                if execution_status in {"finished", "error", "stopped"} and artifact_bytes is None:
                    break
            if time.monotonic() > deadline:
                raise RuntimeError(f"Timed out waiting for artifact at {remote_report}")
            time.sleep(5)

        if not conversation_info:
            raise RuntimeError("Cloud repo-backed run did not return conversation info")

        local_report = run_dir / config.output_name
        if artifact_bytes is None:
            raise RuntimeError(f"Cloud repo-backed run did not produce artifact at {remote_report}")
        local_report.write_bytes(artifact_bytes)

        verification = verify_task_output(args.task, local_report)
        duration_seconds = round(time.perf_counter() - start_time, 2)
        metrics = {
            "task": args.task,
            "condition": args.condition,
            "backend": args.backend,
            "execution_mode": args.execution_mode,
            "model": args.model,
            "model_label": args.model_label or None,
            "passed": verification.passed,
            "message": verification.message,
            "runtime_seconds": duration_seconds,
            "event_count": len(events),
            "item_count": verification.item_count,
            "sandbox_id": conversation_info.get("sandbox_id"),
            "conversation_id": app_conversation_id,
            "start_task_id": start_task_id,
            "remote_output": remote_report,
            "selected_repository": args.cloud_repo,
            "selected_branch": args.cloud_branch,
            "cloud_skill_mode": args.cloud_skill_mode,
        }
        if app_conversation_id:
            event_response = client.get(f"/api/v1/conversation/{app_conversation_id}/events/search")
            event_response.raise_for_status()
            event_payload = event_response.json()
            conversation_events = event_payload.get("items", event_payload if isinstance(event_payload, list) else [])
        else:
            conversation_events = []
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        (run_dir / "events.json").write_text(
            json.dumps({"poll_events": events, "conversation_events": conversation_events}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(metrics, indent=2))
        return 0 if verification.passed else 1


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

    if args.backend == "cloud" and args.execution_mode == "repo":
        return run_cloud_repo_mode(args=args, config=config, run_dir=run_dir)

    events: list[dict[str, Any]] = []

    def callback(event: Event) -> None:
        events.append(serialize_event(event))

    workspace = create_workspace(args)
    remote_project_dir, remote_output_dir, remote_report = get_remote_paths(
        args.task,
        args.execution_mode,
        backend=args.backend,
        cloud_repo=args.cloud_repo if args.backend == "cloud" else args.agent_repo_dir,
    )

    start_time = time.perf_counter()
    try:
        if args.execution_mode == "repo":
            if args.backend != "agent-server":
                raise RuntimeError("execution-mode=repo is currently supported with --backend agent-server")
            prepare_repo_backed_task(args.task)
            workspace.execute_command(f"mkdir -p {remote_output_dir}")
        else:
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
        conversation.send_message(
            build_prompt_for_paths(
                args.task,
                args.condition,
                remote_project_dir,
                remote_output_dir,
                remote_report,
            )
        )
        conversation.run()

        local_report = run_dir / config.output_name
        if args.execution_mode == "repo":
            local_repo_report = config.local_repo_dir / "output" / config.output_name
            if not local_repo_report.exists():
                raise RuntimeError(f"Repo-backed run did not produce expected artifact: {local_repo_report}")
            local_report.write_bytes(local_repo_report.read_bytes())
        else:
            workspace.file_download(config.remote_output, str(local_report))

        verification = verify_task_output(args.task, local_report)
        duration_seconds = round(time.perf_counter() - start_time, 2)

        metrics = {
            "task": args.task,
            "condition": args.condition,
            "backend": args.backend,
            "execution_mode": args.execution_mode,
            "model": args.model,
            "model_label": args.model_label or None,
            "passed": verification.passed,
            "message": verification.message,
            "runtime_seconds": duration_seconds,
            "event_count": len(events),
            "item_count": verification.item_count,
            "sandbox_id": getattr(workspace, "sandbox_id", None),
            "remote_output": remote_report,
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
        cleanup = getattr(workspace, "cleanup", None)
        if callable(cleanup):
            cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
