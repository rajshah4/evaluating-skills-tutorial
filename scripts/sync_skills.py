from __future__ import annotations

import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skill_eval.constants import TASKS

AGENTS_SKILLS_DIR = ROOT / ".agents" / "skills"
OPENHANDS_SKILLS_DIR = ROOT / ".openhands" / "skills"


def iter_task_skills() -> list[tuple[str, str, Path]]:
    entries: list[tuple[str, str, Path]] = []
    for config in TASKS.values():
        for variant_dir in sorted(config.skills_dir.iterdir()):
            if not variant_dir.is_dir():
                continue
            skill_path = variant_dir / "SKILL.md"
            if skill_path.is_file():
                entries.append((config.dir_name, variant_dir.name, skill_path))
    return entries


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def sync_agents_skills(entries: list[tuple[str, str, Path]]) -> None:
    ensure_clean_dir(AGENTS_SKILLS_DIR)
    for dir_name, variant, skill_path in entries:
        target_dir = AGENTS_SKILLS_DIR / f"{dir_name}_{variant}"
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(skill_path, target_dir / "SKILL.md")


def sync_openhands_skills(entries: list[tuple[str, str, Path]]) -> None:
    ensure_clean_dir(OPENHANDS_SKILLS_DIR)
    for dir_name, variant, skill_path in entries:
        target_path = OPENHANDS_SKILLS_DIR / f"{dir_name}_{variant}.md"
        shutil.copyfile(skill_path, target_path)


def main() -> None:
    entries = iter_task_skills()
    sync_agents_skills(entries)
    sync_openhands_skills(entries)
    print(f"Synced {len(entries)} skills from task folders.")


if __name__ == "__main__":
    main()
