import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "environment" / "runtime"))

from harbor.models.task.paths import TaskPaths


def test_game_starclash_task_resolves_external_environment_definition() -> None:
    task_dir = repo_root / "application" / "tasks" / "game-starclash"
    environment_dir = (
        repo_root
        / "environment"
        / "task-environments"
        / "application"
        / "game-starclash"
    )

    assert task_dir.exists()
    assert environment_dir.exists()

    resolved_environment_dir = TaskPaths.from_task_dir(task_dir).environment_dir

    assert resolved_environment_dir == environment_dir.resolve()
