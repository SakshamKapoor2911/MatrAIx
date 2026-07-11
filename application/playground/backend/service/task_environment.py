from __future__ import annotations

import tomllib
from pathlib import Path, PurePosixPath


TASK_ENVIRONMENTS_ROOT = Path("environment") / "task-environments"


def resolve_task_environment_dir(task_dir: Path) -> Path:
    """Resolve a task's runtime environment directory.

    The Harbor runtime owns the canonical resolver. This fallback keeps the
    Playground app importable from source before Harbor is on PYTHONPATH.
    """
    try:
        from harbor.models.task.paths import TaskPaths
    except ModuleNotFoundError:
        return _resolve_without_harbor(task_dir)
    return TaskPaths.from_task_dir(task_dir).environment_dir


def _resolve_without_harbor(task_dir: Path) -> Path:
    task_dir = task_dir.resolve()
    local_environment_dir = task_dir / "environment"
    if local_environment_dir.exists():
        return local_environment_dir

    definition = _read_environment_definition(task_dir / "task.toml")
    if definition is None:
        return local_environment_dir

    repo_root = _repo_root_for_task(task_dir)
    if repo_root is None:
        return local_environment_dir
    return (repo_root / TASK_ENVIRONMENTS_ROOT / definition).resolve()


def _read_environment_definition(config_path: Path) -> str | None:
    try:
        raw_config = tomllib.loads(config_path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return None

    raw_environment = raw_config.get("environment")
    if not isinstance(raw_environment, dict):
        return None
    definition = raw_environment.get("definition")
    if not isinstance(definition, str):
        return None

    clean = definition.strip()
    posix_path = PurePosixPath(clean)
    if (
        not clean
        or "\\" in clean
        or posix_path.is_absolute()
        or any(part in {"", ".", ".."} for part in posix_path.parts)
    ):
        return None
    return posix_path.as_posix()


def _repo_root_for_task(task_dir: Path) -> Path | None:
    for candidate in (task_dir, *task_dir.parents):
        if (candidate / TASK_ENVIRONMENTS_ROOT).exists():
            return candidate
        if (candidate / "pyproject.toml").exists():
            return candidate
    return None
