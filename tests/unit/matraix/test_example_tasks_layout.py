"""Static guards for MatrAIx application/ and persona/ example Harbor tasks."""

from __future__ import annotations

from pathlib import Path

import pytest
import toml
from harbor.models.task.config import TaskConfig
from harbor.models.task.task import Task

from matraix.task_catalog import (
    APPLICATION_TASK_METADATA,
    PERSONA_BENCH_TASK_METADATA,
    build_application_task_toml_dict,
    build_persona_task_toml_dict,
    load_grounding_toml,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _task_dirs(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )


APPLICATION_TASK_DIRS = _task_dirs(REPO_ROOT / "application" / "tasks")
PERSONA_TASK_DIRS = _task_dirs(REPO_ROOT / "persona" / "tasks")


@pytest.mark.parametrize(
    "task_dir",
    APPLICATION_TASK_DIRS,
    ids=lambda p: p.relative_to(REPO_ROOT).as_posix(),
)
def test_application_task_directory_is_valid(task_dir: Path) -> None:
    assert Task.is_valid_dir(task_dir), f"{task_dir}: invalid Harbor task layout"
    assert (task_dir / "instruction.md").is_file()
    assert (task_dir / "environment").is_dir()
    assert (task_dir / "tests" / "test.sh").is_file()


@pytest.mark.parametrize(
    "task_dir",
    APPLICATION_TASK_DIRS,
    ids=lambda p: p.relative_to(REPO_ROOT).as_posix(),
)
def test_application_task_registered_in_catalog(task_dir: Path) -> None:
    dirname = task_dir.name
    assert dirname in APPLICATION_TASK_METADATA, (
        f"{dirname}: add to APPLICATION_TASK_METADATA in task_catalog.py"
    )
    expected = build_application_task_toml_dict(dirname)
    actual = toml.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
    assert actual["task"]["name"] == expected["task"]["name"]
    for key in ("type", "domain", "tags"):
        assert actual["metadata"][key] == expected["metadata"][key], key


def test_application_catalog_covers_all_example_tasks() -> None:
    on_disk = {p.name for p in APPLICATION_TASK_DIRS}
    in_catalog = set(APPLICATION_TASK_METADATA)
    assert on_disk == in_catalog, (
        f"mismatch: only on disk {on_disk - in_catalog}, "
        f"only in catalog {in_catalog - on_disk}"
    )


@pytest.mark.parametrize(
    "task_dir",
    PERSONA_TASK_DIRS,
    ids=lambda p: p.relative_to(REPO_ROOT).as_posix(),
)
def test_persona_task_directory_is_valid(task_dir: Path) -> None:
    assert Task.is_valid_dir(task_dir), f"{task_dir}: invalid Harbor task layout"
    assert (task_dir / "instruction.md").is_file()
    assert (task_dir / "grounding.toml").is_file()
    assert (task_dir / "environment" / "Dockerfile").is_file()
    assert (task_dir / "tests" / "test.sh").is_file()
    grounding = load_grounding_toml(
        task_dir.relative_to(REPO_ROOT).as_posix(),
        repo_root=REPO_ROOT,
    )
    assert grounding is not None
    assert grounding.get("probe_dimension")


@pytest.mark.parametrize(
    "task_dir",
    PERSONA_TASK_DIRS,
    ids=lambda p: p.relative_to(REPO_ROOT).as_posix(),
)
def test_persona_task_registered_in_catalog(task_dir: Path) -> None:
    dirname = task_dir.name
    assert dirname in PERSONA_BENCH_TASK_METADATA, (
        f"{dirname}: add to PERSONA_BENCH_TASK_METADATA in task_catalog.py"
    )
    expected = build_persona_task_toml_dict(dirname)
    actual = toml.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
    assert actual["task"]["name"] == expected["task"]["name"]
    for key in ("type", "domain", "tags"):
        assert actual["metadata"][key] == expected["metadata"][key], key
    cfg = TaskConfig.model_validate_toml((task_dir / "task.toml").read_text())
    assert cfg.task is not None
    assert cfg.task.name.startswith("matraix/persona-bench-")


def test_persona_catalog_covers_all_example_tasks() -> None:
    on_disk = {p.name for p in PERSONA_TASK_DIRS}
    in_catalog = set(PERSONA_BENCH_TASK_METADATA)
    assert on_disk == in_catalog, (
        f"mismatch: only on disk {on_disk - in_catalog}, "
        f"only in catalog {in_catalog - on_disk}"
    )
