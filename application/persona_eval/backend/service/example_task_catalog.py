"""Discover Harbor application tasks for PersonaEval from ``application/tasks/*/task.toml``."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from backend.service.application_task_metadata import ApplicationTaskRecord, parse_application_task
from backend.service.persona_eval_task_registry import get_persona_eval_entry

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TASKS_DIR = _REPO_ROOT / "application" / "tasks"


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


def discover_application_tasks(
    *,
    application_type: Optional[str] = None,
) -> List[ApplicationTaskRecord]:
    """Return tasks indexed in PersonaEval registry with Harbor metadata from task.toml."""
    if not _TASKS_DIR.is_dir():
        return []

    records: List[ApplicationTaskRecord] = []
    for child in sorted(_TASKS_DIR.iterdir()):
        if not child.is_dir():
            continue
        record = parse_application_task(child)
        if record is None or record.persona_eval is None:
            continue
        if application_type is not None and record.persona_eval.application_type != application_type:
            continue
        records.append(record)
    return records


# Backward-compatible aliases used by existing imports/tests.
ExampleTaskRecord = ApplicationTaskRecord


def categorize_task(folder_name: str, meta_type: str) -> Optional[str]:
    entry = get_persona_eval_entry(folder_name)
    if entry is not None:
        return entry.application_type
    return None


def discover_example_tasks(*, category: Optional[str] = None) -> List[ApplicationTaskRecord]:
    return [
        record
        for record in discover_application_tasks(application_type=category)
        if record.folder_name.startswith("example-")
    ]


def discover_survey_application_tasks() -> List[ApplicationTaskRecord]:
    return discover_application_tasks(application_type="survey")
