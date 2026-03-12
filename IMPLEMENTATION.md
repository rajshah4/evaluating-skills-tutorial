# Local Implementation

This document explains the local agent-server setup used by this tutorial.

## Why This Path

The recommended local path is a pre-started OpenHands agent server. The evaluation runner then connects to that server over HTTP.

This is closer to the hosted OpenHands model than creating one-off Docker sandboxes inside the runner:

- the runner acts as a client
- the agent server owns the runtime
- task files live in a mounted repo
- outputs are written back through the same repo-backed flow

## Start The Agent Server

Use the helper script:

```bash
./scripts/start_local_agent_server.sh
```

That script starts the OpenHands agent-server container and mounts this repo into:

```text
/workspace/project/evaluating-skills-tutorial
```

The server listens on:

```text
http://127.0.0.1:8000
```

## Required Environment Variables

Set these before running the local path:

```bash
export LLM_API_KEY=...
export LLM_MODEL=openhands/claude-sonnet-4-5-20250929
export OPENHANDS_AGENT_SERVER_URL=http://127.0.0.1:8000
export OPENHANDS_AGENT_REPO_DIR=/workspace/project/evaluating-skills-tutorial
```

What they do:

- `LLM_API_KEY`
  Authenticates model calls made by the local agent server.
- `LLM_MODEL`
  Selects the routed OpenHands model.
- `OPENHANDS_AGENT_SERVER_URL`
  Tells the runner where the local agent server is listening.
- `OPENHANDS_AGENT_REPO_DIR`
  Tells the runner where the repo is mounted inside the container.

## How Repo-Backed Local Runs Work

For repo-backed tasks, the local agent-server flow works directly inside the task folder under:

- `tasks/sec_financial_report`
- `tasks/sales_pivot_analysis`

The runner maps each task to one of those directories inside the mounted repo and asks OpenHands to write the output artifact there.

`software-dependency-audit` is handled differently: it stays upload-based so the pinned offline Trivy snapshot under `tasks/software_dependency_audit/skill_input/` is not visible during `no-skill` runs.

Example:

```bash
uv run python scripts/run_eval.py \
  --task sec-financial-report \
  --backend agent-server \
  --execution-mode repo \
  --condition improved-skill
```

For that run, the agent works against:

```text
/workspace/project/evaluating-skills-tutorial/tasks/sec_financial_report
```

## Outputs

After the run completes, the runner copies the final artifact and metadata into local `results/`.

Typical local files:

- `results/<task>/<condition>/<artifact>`
- `results/<task>/<condition>/metrics.json`
- `results/<task>/<condition>/events.json`

If you pass `--model-label`, the run is saved under:

- `results/<task>/<model-label>/<condition>/...`

These per-run outputs are treated as local working artifacts and are not kept in Git. The committed repo keeps only the summary matrix files and generated visuals.

## How This Differs From Cloud

Cloud repo-backed runs:

- create V1 app conversations in OpenHands Cloud
- require `OPENHANDS_CLOUD_API_KEY`
- discover project skills from `.openhands/skills/*.md`

Local agent-server runs:

- connect to your own running OpenHands agent server
- do not require `OPENHANDS_CLOUD_API_KEY`
- are useful when you want a local runtime with the same general client-to-server shape

## Related Files

- `scripts/start_local_agent_server.sh`
- `scripts/run_eval.py`
- `docs/ADDING_A_TASK.md`
