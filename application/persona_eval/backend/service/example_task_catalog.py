"""Discover Harbor example tasks from ``application/tasks/example-*``."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TASKS_DIR = _REPO_ROOT / "application" / "tasks"


@dataclass(frozen=True)
class ExampleTaskRecord:
    folder_name: str
    task_path: str
    task_name: str
    meta_type: str
    title: str
    description: str
    category: str


def repo_root() -> Path:
    return _REPO_ROOT


def task_id_from_folder(folder_name: str) -> str:
    slug = folder_name
    stripped = False
    for prefix in ("example-survey_", "survey_"):
        if slug.startswith(prefix):
            slug = slug[len(prefix) :]
            stripped = True
            break
    if not stripped and slug.startswith("example-"):
        slug = slug[len("example-") :]
    return slug.replace("_", "-")


def survey_task_slug(folder_name: str) -> str:
    """Strip ``example-survey_`` or ``survey_`` prefix from a task folder name."""
    for prefix in ("example-survey_", "survey_"):
        if folder_name.startswith(prefix):
            return folder_name[len(prefix) :]
    return folder_name


def _read_instruction_meta(instruction_path: Path) -> tuple[str, str]:
    if not instruction_path.is_file():
        return "", ""
    title = ""
    description = ""
    for line in instruction_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not title:
            title = stripped.lstrip("# ").strip()
            continue
        if title and not description and stripped and not stripped.startswith("#"):
            description = stripped
            break
    return title, description


def _humanize_folder(folder_name: str) -> str:
    stem = folder_name
    for prefix in ("example-survey_", "survey_", "example-"):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    stem = re.sub(r"^(web|computer-use)-", "", stem)
    stem = stem.replace("_", " ").replace("-", " ")
    return stem.strip().title() or folder_name


def _parse_task_toml(task_dir: Path) -> Dict[str, object]:
    toml_path = task_dir / "task.toml"
    if not toml_path.is_file():
        return {}
    return tomllib.loads(toml_path.read_text(encoding="utf-8"))


def categorize_task(folder_name: str, meta_type: str) -> Optional[str]:
    lowered = folder_name.lower()
    if lowered.startswith("example-computer-use-"):
        return "cua"
    if lowered.startswith("example-web-cua_"):
        return "cua"
    if lowered.startswith("example-survey_"):
        return "survey"
    if lowered.startswith("survey_"):
        return "survey"
    if lowered.startswith("example-web-"):
        return "web"
    normalized = meta_type.strip().lower()
    if normalized == "survey":
        return "survey"
    if normalized == "web":
        return "web"
    if normalized == "desktop":
        return "cua"
    return None


def discover_example_tasks(*, category: Optional[str] = None) -> List[ExampleTaskRecord]:
    if not _TASKS_DIR.is_dir():
        return []

    records: List[ExampleTaskRecord] = []
    for child in sorted(_TASKS_DIR.iterdir()):
        if not child.is_dir() or not child.name.startswith("example-"):
            continue
        if not (child / "task.toml").is_file():
            continue

        raw = _parse_task_toml(child)
        meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        meta_type = str(meta.get("type") or "")
        task_category = categorize_task(child.name, meta_type)
        if task_category is None:
            continue
        if category is not None and task_category != category:
            continue

        task_block = raw.get("task") if isinstance(raw.get("task"), dict) else {}
        task_name = str(task_block.get("name") or child.name)
        instruction_title, instruction_description = _read_instruction_meta(child / "instruction.md")
        title = instruction_title or _humanize_folder(child.name)
        description = instruction_description or f"Harbor {task_category} task ({child.name})."

        records.append(
            ExampleTaskRecord(
                folder_name=child.name,
                task_path="application/tasks/{}".format(child.name),
                task_name=task_name,
                meta_type=meta_type,
                title=title,
                description=description,
                category=task_category,
            )
        )
    return records


def discover_survey_application_tasks() -> List[ExampleTaskRecord]:
    """Discover registered application survey tasks (example + contributing)."""
    from environment.integrations.persona_eval.survey_task_content import (
        SURVEY_INSTRUMENT_TASK_FOLDERS,
        is_example_survey_task_folder,
    )

    if not _TASKS_DIR.is_dir():
        return []

    records: List[ExampleTaskRecord] = []
    for folder in sorted(set(SURVEY_INSTRUMENT_TASK_FOLDERS.values())):
        child = _TASKS_DIR / folder
        if not child.is_dir() or not (child / "task.toml").is_file():
            continue
        raw = _parse_task_toml(child)
        meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        meta_type = str(meta.get("type") or "")
        task_category = categorize_task(child.name, meta_type)
        if task_category != "survey":
            continue
        task_block = raw.get("task") if isinstance(raw.get("task"), dict) else {}
        task_name = str(task_block.get("name") or child.name)
        instruction_title, instruction_description = _read_instruction_meta(child / "instruction.md")
        title = instruction_title or _humanize_folder(child.name)
        if is_example_survey_task_folder(child.name):
            description = instruction_description or "Reference survey example for contributors."
        else:
            description = instruction_description or "Application survey task ({}).".format(child.name)
        records.append(
            ExampleTaskRecord(
                folder_name=child.name,
                task_path="application/tasks/{}".format(child.name),
                task_name=task_name,
                meta_type=meta_type,
                title=title,
                description=description,
                category=task_category,
            )
        )
    return records
