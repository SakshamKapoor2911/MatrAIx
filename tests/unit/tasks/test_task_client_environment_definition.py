from pathlib import Path

from harbor.tasks.client import TaskClient


def test_git_task_copy_inlines_environment_definition(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    source_task = repo / "application" / "tasks" / "demo-task"
    source_env = repo / "environment" / "task-environments" / "application" / "demo-task"
    target_task = tmp_path / "downloaded" / "demo-task"
    source_task.mkdir(parents=True)
    source_env.mkdir(parents=True)
    (source_task / "task.toml").write_text(
        "[environment]\n"
        'definition = "application/demo-task"\n'
    )
    (source_env / "Dockerfile").write_text("FROM alpine\n")

    TaskClient()._copy_task_source_to_target(repo, source_task, target_task)

    assert (target_task / "environment" / "Dockerfile").read_text() == "FROM alpine\n"
