# Evaluating Skills Tutorial

This repo is a small OpenHands tutorial for evaluating skills on deterministic tasks. It is intentionally not a full benchmark harness.

The loop is simple:

1. run a task with `no-skill`
2. run the same task with a skill
3. verify the output locally
4. compare pass/fail, runtime, and event count

Current task examples:

- `software-dependency-audit`
- `sec-financial-report`
- `sales-pivot-analysis`

These examples are adapted from SkillsBench:

- https://github.com/benchflow-ai/skillsbench

## Why This Repo Exists

This tutorial is meant to show a reusable pattern for testing whether a skill actually helps. The three included tasks intentionally show different outcomes:

- `software-dependency-audit`: strong positive skill lift
- `sec-financial-report`: small or mostly neutral lift
- `sales-pivot-analysis`: a case where a skill can help some runs but still hurt one task/model pair

That mix is useful. Skills are hypotheses, not guarantees.

## Repo Layout

- `tasks/`
  Inputs, prompts, and expected outputs
- `skills/`
  Skill variants used by each task
- `.openhands/skills/`
  Repo-native project skills used by Cloud repo-backed V1 runs
- `scripts/run_eval.py`
  Run one task/condition through the OpenHands SDK
- `scripts/run_model_matrix.py`
  Run one task/condition across multiple models
- `verify.py`
  Re-check a saved artifact locally
- `results/`
  Saved artifacts, metrics, summaries, and visuals
- `docs/METHODOLOGY.md`
  How to think about evaluating your own skills

## Quickstart

- Python 3.12+
- `uv`
- OpenHands credentials
- Docker Desktop if you want a locally hosted runtime

Install:

```bash
uv sync
```

Set the credentials for the path you want to use.

For all runs, choose an OpenHands-routed model:

```bash
export LLM_MODEL=openhands/claude-sonnet-4-5-20250929
```

For OpenHands Cloud:

```bash
export OPENHANDS_CLOUD_API_KEY=...
```

- `OPENHANDS_CLOUD_API_KEY`
  Used to create Cloud conversations and start Cloud runs.
  Get it from OpenHands Cloud API Keys:
  https://docs.openhands.dev/openhands/usage/cloud/cloud-api
- For repo-backed Cloud runs, also make sure OpenHands Cloud can access your GitHub repo:
  https://docs.openhands.dev/usage/cloud/github-installation

For the local agent-server path:

```bash
export LLM_API_KEY=...
```

- `LLM_API_KEY`
  Used by the local agent server to call the OpenHands model provider.
  Get the OpenHands LLM key from API Keys settings:
  https://docs.openhands.dev/openhands/usage/settings/api-keys-settings
- `LLM_MODEL`
  Picks the routed model for the run, for example `openhands/claude-sonnet-4-5-20250929`.

If you want the local agent-server pattern explained in more detail, see:
https://docs.openhands.dev/sdk/guides/agent-server/local-server

Optional tracing:

```bash
export LMNR_PROJECT_API_KEY=...
```

Or point OpenTelemetry somewhere else:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=...
export OTEL_EXPORTER_OTLP_HEADERS=...
```

## OpenHands Cloud

Recommended path: run against a GitHub repo in OpenHands Cloud.

Use this when the task fixtures already live in a repo and you want Cloud to run directly against that repo instead of uploading files into a fresh workspace.

```bash
uv run python scripts/run_eval.py \
  --task sec-financial-report \
  --backend cloud \
  --execution-mode repo \
  --condition improved-skill \
  --cloud-repo rajshah4/evaluating-skills-tutorial
```

Cloud repo-backed mode uses the V1 app conversations API. The repo must be reachable from OpenHands Cloud. For this runtime path, project skills are currently discovered from `.openhands/skills/*.md`.

You can use the same pattern for the other tasks:

```bash
uv run python scripts/run_eval.py --task software-dependency-audit --backend cloud --execution-mode repo --condition no-skill --cloud-repo rajshah4/evaluating-skills-tutorial
uv run python scripts/run_eval.py --task software-dependency-audit --backend cloud --execution-mode repo --condition improved-skill --cloud-repo rajshah4/evaluating-skills-tutorial
uv run python scripts/run_eval.py --task sales-pivot-analysis --backend cloud --execution-mode repo --condition improved-skill --cloud-repo rajshah4/evaluating-skills-tutorial
```

If you just want the simplest SDK path, you can still use uploaded fixtures instead of a repo-backed conversation:

```bash
uv run python scripts/run_eval.py --task software-dependency-audit --condition no-skill
uv run python scripts/run_eval.py --task software-dependency-audit --condition improved-skill
```

Current limitation:

- Use Cloud repo-backed runs when you want OpenHands to discover project skills from the repo.
- Use the SDK upload-based path when you want to inject skill text manually from the runner.
- OpenHands is still converging these two paths. Background: [OpenHands/OpenHands#13268](https://github.com/OpenHands/OpenHands/issues/13268).

This should improve over time. For now, this repo keeps both:

- `skills/` for SDK-driven runs
- `.openhands/skills/*.md` for Cloud repo-backed V1 runs

## Local

Use a local agent server when you want a locally hosted OpenHands runtime that is closer to the Cloud model than mounting files directly into a one-off container.

Start the server:

```bash
./scripts/start_local_agent_server.sh
```

This mounts this repo into the container at:

- `/workspace/project/evaluating-skills-tutorial`

Then run an eval against that server:

```bash
uv run python scripts/run_eval.py \
  --task sec-financial-report \
  --backend agent-server \
  --execution-mode repo \
  --condition improved-skill
```

Environment variables for this flow:

```bash
export OPENHANDS_AGENT_SERVER_URL=http://127.0.0.1:8000
export OPENHANDS_AGENT_REPO_DIR=/workspace/project/evaluating-skills-tutorial
```

This is closer to the local flow used in `OpenHands/vulnerability-fixer` than creating Docker sandboxes inside the runner.

The runner then uses:

- `/workspace/project/evaluating-skills-tutorial/task_repos/software_dependency_audit`
- `/workspace/project/evaluating-skills-tutorial/task_repos/sec_financial_report`
- `/workspace/project/evaluating-skills-tutorial/task_repos/sales_pivot_analysis`

Each run writes:

- `results/<task>/<condition>/<artifact>`
- `results/<task>/<condition>/metrics.json`
- `results/<task>/<condition>/events.json`

With `--model-label`, runs are written under:

- `results/<task>/<model-label>/<condition>/...`

## Verify A Saved Run

```bash
uv run python verify.py --task software-dependency-audit results/software-dependency-audit/improved-skill/report.json
uv run python verify.py --task sec-financial-report results/sec-financial-report/improved-skill/answers.json
uv run python verify.py --task sales-pivot-analysis results/sales-pivot-analysis/improved-skill/result.xlsx
```

## Compare Runs And Generate Visuals

```bash
uv run python scripts/compare_runs.py
uv run python scripts/export_metrics_summary.py
uv run python scripts/generate_visuals.py
```

Saved outputs:

- [summary csv](results/model_matrix_summary.csv)
- [summary json](results/model_matrix_summary.json)
- [dashboard](results/visuals/index.html)
- [pass rate](results/visuals/pass_rate_by_task.svg)
- [runtime](results/visuals/runtime_by_task.svg)
- [model scorecard](results/visuals/model_scorecard.svg)

Example visuals:

![Pass rate by task](results/visuals/pass_rate_by_task.svg)

![Model breakdown by task](results/visuals/model_breakdown_by_task.svg)

## Compare Models

Use the OpenHands-routed model format: `openhands/<model>`.

Validated examples in this repo:

- `openhands/claude-sonnet-4-5-20250929`
- `openhands/minimax-m2.5`
- `openhands/gemini-3-pro-preview`
- `openhands/gemini-3-flash-preview`
- `openhands/kimi-k2-0711-preview`

Example:

```bash
uv run python scripts/run_model_matrix.py \
  --task sec-financial-report \
  --backend agent-server \
  --condition improved-skill \
  --model openhands/claude-sonnet-4-5-20250929 \
  --model openhands/minimax-m2.5 \
  --model openhands/gemini-3-pro-preview \
  --model openhands/gemini-3-flash-preview \
  --model openhands/kimi-k2-0711-preview
```

## Observability Philosophy

This tutorial uses Laminar as the example tracing backend, but the evaluation loop is not tied to Laminar. The important contract is local and deterministic: run a condition, save the artifact, verify it locally, and compare outcomes. Traces are there to explain behavior and debug failures.

## Extend This Tutorial

If you want to adapt this repo for your own skills:

1. Pick a bounded task with a deterministic output contract.
2. Create a verifier that returns pass/fail and a few simple metrics.
3. Run at least two conditions:
   - `no-skill`
   - `skill enabled`
4. Use traces to explain behavior, not to decide correctness.
5. Compare both outcome metrics and behavioral differences.

The more detailed reasoning about evaluation design lives in [docs/METHODOLOGY.md](docs/METHODOLOGY.md).
If you want to add a new example task, see [docs/ADDING_A_TASK.md](docs/ADDING_A_TASK.md).

## Acknowledgements

This tutorial is inspired by SkillsBench and reuses its core idea of evaluating skills on deterministic tasks with local verifiers.

- Paper: https://arxiv.org/abs/2602.12670
- GitHub: https://github.com/benchflow-ai/skillsbench
