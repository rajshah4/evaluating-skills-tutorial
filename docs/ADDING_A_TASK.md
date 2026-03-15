# Adding A Task

This repo is designed so you can add a new skill evaluation without changing the overall loop.

The pattern is:

1. create one bounded task
2. define one output artifact
3. write one deterministic verifier
4. add one or more skill variants
5. run `no-skill` vs `skill`

## What A Good Task Looks Like

A good tutorial task has:

- one clear goal
- local inputs only
- one output artifact
- a verifier that can return pass/fail deterministically
- a real procedural gap the skill is supposed to help with

Good output artifacts:

- `report.json`
- `answers.json`
- `result.xlsx`

Less ideal tasks are open-ended, subjective, or depend on external services.

## Step 1: Create The Task Folder

Add a new folder under `tasks/`.

Example:

```text
tasks/my_new_task/
```

Add these files:

- `task_prompt.txt`
- one expected output file such as `expected_report.json`
- an `input/` folder if the task needs local artifacts
- an `output/` folder with a committed `.gitkeep`

Example:

```text
tasks/my_new_task/
  task_prompt.txt
  expected_report.json
  input/
    sample_input.json
  output/
    .gitkeep
```

For most tasks, that single folder is enough for both:

- local agent-server repo-backed runs
- Cloud repo-backed runs, where OpenHands clones the GitHub repo and writes into the task folder there

If a task has skill-only helper artifacts that must not be visible in `no-skill`, keep them under a separate subfolder such as:

```text
tasks/my_new_task/
  skill_input/
    helper.json
```

Then expose those files only for the relevant condition through `conditional_input_paths`.

## Step 2: Define The Output Contract

Pick one output artifact the agent must write.

Examples from this repo:

- `software-dependency-audit` -> `report.json`
- `sec-financial-report` -> `answers.json`
- `sales-pivot-analysis` -> `result.xlsx`

Keep the contract small and deterministic. Prefer checking the final output over checking internal mechanics.

## Step 3: Add The Task To The Registry

Edit [constants.py](../src/skill_eval/constants.py) and add a new `TaskConfig` entry.

You need to define:

- task key
- folder name
- output file name
- expected output file name
- prompt file name
- input files to upload
- optional condition-specific input files

This is what lets `scripts/run_eval.py` know what to upload, where to download the artifact, and which verifier data to use.

If you are using repo-backed runs, the runner uses `tasks/<dir_name>/` directly.

## Step 4: Add Verifier Logic

Create a task-local verifier at:

```text
tasks/my_new_task/verify.py
```

Add a `verify(report_path, expected_path)` function that:

- checks required fields or sheets
- checks expected values or tolerances
- returns a clear pass/fail message
- returns a simple item count

The shared [verify.py](../verify.py) CLI and [src/skill_eval/verify.py](../src/skill_eval/verify.py) dispatcher will load the task verifier automatically from the task folder.

Guidelines:

- prefer semantic checks over one exact rendering
- avoid verifying formatting unless formatting is truly the task
- keep failure messages specific enough to debug quickly

## Step 5: Add Skill Variants

Create skill folders under `skills/`.

Example:

```text
skills/my_new_task/baseline/SKILL.md
skills/my_new_task/improved/SKILL.md
```

The runner will look for task-specific skills first.

If you also want Cloud repo-backed V1 runs to discover the skill automatically, add a flat project skill file under:

```text
.openhands/skills/my_new_task_improved.md
```

Current state of the world:

- `skills/.../SKILL.md` is the SDK-oriented path used by local agent-server runs and explicit SDK skill injection.
- `.openhands/skills/*.md` is the project-skill layout the current Cloud V1 runtime discovers in repo-backed runs.
- This split is awkward, but it reflects the current V1 versus SDK control-plane behavior.

A useful skill should encode:

- a concrete workflow
- tool usage guidance
- output constraints
- fallback rules when the first approach fails

Avoid generic advice and documentation dumps.

## Step 6: Write The Prompt

Your `task_prompt.txt` should:

- tell the agent exactly where it is working
- name the local input files
- name the exact output path
- describe the required output structure
- forbid internet use or package installs if the task should stay local and deterministic

Keep the prompt aligned with what the verifier actually checks.

## Step 7: Run The Baseline First

Before you run it, add a thin task-specific wrapper in `scripts/`. The wrappers in this repo keep the tutorial approachable because each task looks like its own evaluation command even though they all share the same engine.

Example:

```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RUN_EVAL = SCRIPT_DIR / "run_eval.py"

if __name__ == "__main__":
    raise SystemExit(
        subprocess.run(
            [sys.executable, str(RUN_EVAL), "--task", "my-new-task", *sys.argv[1:]],
            check=False,
        ).returncode
    )
```

Then your task has a clean entrypoint like:

```bash
uv run python scripts/run_my_new_task_eval.py --backend cloud --condition no-skill
```

Before tuning the skill, run:

```bash
uv run python scripts/run_<task>_eval.py --condition no-skill
```

That tells you:

- whether the task is already easy
- what failure modes the base model has
- whether the skill should optimize for correctness, efficiency, or both

## Step 8: Run The Skill Condition

Then run:

```bash
uv run python scripts/run_<task>_eval.py --condition improved-skill
```

Compare:

- pass/fail
- runtime
- event count
- traces, if you have observability enabled

```bash
uv run python scripts/run_<task>_eval.py --backend agent-server --execution-mode repo --condition improved-skill
```

```bash
uv run python scripts/run_<task>_eval.py --backend cloud --execution-mode repo --condition improved-skill --cloud-repo <owner/repo>
```

## Step 9: Add Model Matrix Runs If Useful

Once the task is stable, run it across models:

```bash
uv run python scripts/run_model_matrix.py \
  --task <task-name> \
  --backend agent-server \
  --condition improved-skill \
  --model openhands/claude-sonnet-4-5-20250929
```

That helps you see whether a skill is broadly useful or only works for one model.

## Practical Checklist

Before calling a new task ready, check:

- can a user run it with one command?
- does it produce exactly one output artifact?
- can the verifier give a clear pass/fail answer?
- does `no-skill` tell you something useful?
- does the skill encode a real workflow rather than vague advice?
- are failures diagnosable from the artifact, verifier message, and trace?

If any answer is no, tighten the task before expanding the evaluation.
