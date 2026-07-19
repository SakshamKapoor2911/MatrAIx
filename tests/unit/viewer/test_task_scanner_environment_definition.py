from pathlib import Path

from harbor.viewer.task_scanner import TaskDefinitionScanner


def test_task_scanner_tolerates_invalid_environment_definition(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "demo"
    task.mkdir(parents=True)
    (task / "task.toml").write_text(
        "[environment]\n"
        'definition = "../outside"\n'
    )

    info = TaskDefinitionScanner(tmp_path / "tasks").get_task_paths_info("demo")

    assert info["has_config"] is True
    assert info["has_environment"] is False
