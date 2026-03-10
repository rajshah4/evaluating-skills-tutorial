from __future__ import annotations

import argparse
import json
import os
import time

import httpx
from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect repo-native skill discovery for a Cloud V1 app conversation.")
    parser.add_argument("--repo", default=os.getenv("OPENHANDS_CLOUD_REPO", "rajshah4/evaluating-skills-tutorial"))
    parser.add_argument("--branch", default=os.getenv("OPENHANDS_CLOUD_BRANCH", "main"))
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", "openhands/claude-sonnet-4-5-20250929"))
    return parser.parse_args()


def main() -> int:
    root = os.path.dirname(os.path.dirname(__file__))
    load_dotenv(os.path.join(root, ".env"))
    api_key = os.getenv("OPENHANDS_CLOUD_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENHANDS_CLOUD_API_KEY")

    args = parse_args()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    with httpx.Client(base_url="https://app.all-hands.dev", headers=headers, timeout=60.0) as client:
        create = client.post(
            "/api/v1/app-conversations",
            json={
                "selected_repository": args.repo,
                "selected_branch": args.branch,
                "git_provider": "github",
                "llm_model": args.model,
                "initial_message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "Reply with exactly: skill-check"}],
                },
            },
        )
        create.raise_for_status()
        start_task_id = create.json()["id"]

        deadline = time.monotonic() + 120
        app_conversation_id = None
        while time.monotonic() < deadline:
            poll = client.get("/api/v1/app-conversations/start-tasks", params={"ids": start_task_id})
            poll.raise_for_status()
            items = poll.json()
            info = items[0] if isinstance(items, list) else poll.json()["items"][0]
            app_conversation_id = info.get("app_conversation_id")
            if app_conversation_id:
                break
            time.sleep(2)

        if not app_conversation_id:
            raise RuntimeError("Timed out waiting for app conversation")

        conv = client.get("/api/v1/app-conversations", params={"ids": app_conversation_id})
        conv.raise_for_status()
        conv_info = conv.json()[0]
        runtime_url = conv_info["conversation_url"].rsplit("/api/conversations/", 1)[0]
        session_api_key = conv_info["session_api_key"]

        with httpx.Client(base_url=runtime_url, headers={"X-Session-API-Key": session_api_key}, timeout=60.0) as runtime:
            response = runtime.post(
                "/api/skills",
                json={
                    "load_public": False,
                    "load_user": False,
                    "load_project": True,
                    "load_org": False,
                    "project_dir": f"/workspace/project/{args.repo.split('/')[-1]}",
                },
            )
            response.raise_for_status()
            payload = response.json()

        print(json.dumps(payload, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
