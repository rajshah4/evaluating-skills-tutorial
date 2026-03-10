from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
TASK_REPOS_DIR = ROOT / "task_repos"

REMOTE_PROJECT_DIR = "/workspace/project"
REMOTE_INPUT_DIR = f"{REMOTE_PROJECT_DIR}/input"
REMOTE_OUTPUT_DIR = f"{REMOTE_PROJECT_DIR}/output"


@dataclass(frozen=True)
class TaskConfig:
    key: str
    dir_name: str
    output_name: str
    expected_name: str
    prompt_name: str
    input_paths: tuple[str, ...]
    conditional_input_paths: tuple[str, ...] = ()

    @property
    def task_dir(self) -> Path:
        return ROOT / "tasks" / self.dir_name

    @property
    def prompt_template(self) -> Path:
        return self.task_dir / self.prompt_name

    @property
    def expected_output(self) -> Path:
        return self.task_dir / self.expected_name

    @property
    def local_repo_dir(self) -> Path:
        return TASK_REPOS_DIR / self.dir_name

    @property
    def remote_output(self) -> str:
        return f"{REMOTE_OUTPUT_DIR}/{self.output_name}"


TASKS = {
    "software-dependency-audit": TaskConfig(
        key="software-dependency-audit",
        dir_name="software_dependency_audit",
        output_name="report.json",
        expected_name="expected_report.json",
        prompt_name="task_prompt.txt",
        input_paths=("package-lock.json",),
        conditional_input_paths=("trivy_report.json",),
    ),
    "sec-financial-report": TaskConfig(
        key="sec-financial-report",
        dir_name="sec_financial_report",
        output_name="answers.json",
        expected_name="expected_answers.json",
        prompt_name="task_prompt.txt",
        input_paths=(
            "2025-q2/report.md",
            "2025-q3/report.md",
        ),
    ),
    "sales-pivot-analysis": TaskConfig(
        key="sales-pivot-analysis",
        dir_name="sales_pivot_analysis",
        output_name="result.xlsx",
        expected_name="expected_workbook.json",
        prompt_name="task_prompt.txt",
        input_paths=(
            "income.xlsx",
            "population.pdf",
        ),
    ),
}


def get_task_config(task: str) -> TaskConfig:
    try:
        return TASKS[task]
    except KeyError as exc:
        raise ValueError(f"Unknown task: {task}") from exc
