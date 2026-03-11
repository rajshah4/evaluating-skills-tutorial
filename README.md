# Evaluating Skills Tutorial

This repo shows a simple pattern for evaluating OpenHands skills on deterministic tasks:

1. run a task with `no-skill`
2. run the same task with a skill
3. verify the output locally
4. compare pass/fail, runtime, and event count

It is intentionally tutorial-sized, not a full benchmark harness.

Current task examples:

- `software-dependency-audit`
- `sec-financial-report`
- `sales-pivot-analysis`

These examples are adapted from SkillsBench:

- https://github.com/benchflow-ai/skillsbench

## Quickstart

Requirements:

- Python 3.12+
- `uv`
- OpenHands credentials
- Docker Desktop if you want the local agent-server path

Install:

```bash
uv sync
```

Choose a routed model:

```bash
export LLM_MODEL=openhands/claude-sonnet-4-5-20250929
```

For OpenHands Cloud:

```bash
export OPENHANDS_CLOUD_API_KEY=...
```

- `OPENHANDS_CLOUD_API_KEY`: your OpenHands Cloud API key
  https://docs.openhands.dev/openhands/usage/cloud/cloud-api
- `GitHub token`: create a token with `repo` scope if you are using a token-based GitHub connection for repo-backed Cloud runs
  https://docs.openhands.dev/usage/cloud/github-installation

For the local agent-server path:

```bash
export LLM_API_KEY=...
```

- `LLM_API_KEY`: your OpenAI, Anthropic, or OpenHands LLM key
  https://docs.openhands.dev/openhands/usage/settings/api-keys-settings

Optional tracing:

```bash
export LMNR_PROJECT_API_KEY=...
```

## OpenHands Cloud

This is the main tutorial path.

Run against the GitHub repo directly:

```bash
uv run python scripts/run_eval.py \
  --task sec-financial-report \
  --backend cloud \
  --execution-mode repo \
  --condition improved-skill \
  --cloud-repo rajshah4/evaluating-skills-tutorial
```

The same pattern works for the other tasks:

```bash
uv run python scripts/run_eval.py --task software-dependency-audit --backend cloud --execution-mode repo --condition no-skill --cloud-repo rajshah4/evaluating-skills-tutorial
uv run python scripts/run_eval.py --task software-dependency-audit --backend cloud --execution-mode repo --condition improved-skill --cloud-repo rajshah4/evaluating-skills-tutorial
uv run python scripts/run_eval.py --task sales-pivot-analysis --backend cloud --execution-mode repo --condition improved-skill --cloud-repo rajshah4/evaluating-skills-tutorial
```

For repo-backed Cloud runs, project skills are discovered from `.openhands/skills/*.md`.

If you want the simpler SDK upload path instead of repo-backed Cloud:

```bash
uv run python scripts/run_eval.py --task software-dependency-audit --condition no-skill
uv run python scripts/run_eval.py --task software-dependency-audit --condition improved-skill
```

Current limitation:

- use repo-backed Cloud when you want OpenHands to discover project skills from the repo
- use the upload-based SDK path when you want to inject skill text directly from the runner
- background: [OpenHands/OpenHands#13268](https://github.com/OpenHands/OpenHands/issues/13268)

## Local

Use a local agent server when you want a local runtime with a similar client-to-server shape.

Start the server:

```bash
./scripts/start_local_agent_server.sh
```

Run an evaluation:

```bash
uv run python scripts/run_eval.py \
  --task sec-financial-report \
  --backend agent-server \
  --execution-mode repo \
  --condition improved-skill
```

Recommended local env vars:

```bash
export OPENHANDS_AGENT_SERVER_URL=http://127.0.0.1:8000
```

For the exact local setup, see [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Verify And Compare

Verify a saved run:

```bash
uv run python verify.py --task software-dependency-audit results/software-dependency-audit/improved-skill/report.json
uv run python verify.py --task sec-financial-report results/sec-financial-report/improved-skill/answers.json
uv run python verify.py --task sales-pivot-analysis results/sales-pivot-analysis/improved-skill/result.xlsx
```

Generate summaries and visuals:

```bash
uv run python scripts/compare_runs.py
uv run python scripts/export_metrics_summary.py
uv run python scripts/generate_visuals.py
```

Saved outputs:

- [summary csv](results/model_matrix_summary.csv)
- [summary json](results/model_matrix_summary.json)
- [dashboard](results/visuals/index.html)

Example visuals:

![Pass rate by task](results/visuals/pass_rate_by_task.svg)

![Model breakdown by task](results/visuals/model_breakdown_by_task.svg)

## Compare Models

Use the OpenHands-routed model format: `openhands/<model>`.

Validated examples:

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

## Notes

This tutorial uses Laminar as the example tracing backend, but the evaluation loop is not tied to Laminar. Traces help explain behavior; the verifier decides correctness.

If you want to adapt this repo for your own skills:

- evaluation methodology: [docs/METHODOLOGY.md](docs/METHODOLOGY.md)
- add a new task: [docs/ADDING_A_TASK.md](docs/ADDING_A_TASK.md)

## Acknowledgements

This tutorial is inspired by SkillsBench and reuses its core idea of evaluating skills on deterministic tasks with local verifiers.

- Paper: https://arxiv.org/abs/2602.12670
- GitHub: https://github.com/benchflow-ai/skillsbench
