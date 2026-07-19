from pathlib import Path

from harbor.publisher.packager import Packager


def test_packager_maps_external_environment_into_archive_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    task = repo / "application" / "tasks" / "demo-task"
    env = repo / "environment" / "task-environments" / "application" / "demo-task"
    task.mkdir(parents=True)
    env.mkdir(parents=True)
    (task / "instruction.md").write_text("Do something\n")
    (task / "task.toml").write_text(
        "[task]\n"
        'name = "demo/task"\n'
        "\n"
        "[environment]\n"
        'definition = "application/demo-task"\n'
    )
    (task / "tests").mkdir()
    (task / "tests" / "test.sh").write_text("#!/bin/sh\nexit 0\n")
    (env / "Dockerfile").write_text("FROM alpine\n")

    files = Packager.collect_files(task)
    rel_paths = [
        Packager.package_rel_path(task, path).as_posix()
        for path in files
    ]

    assert "environment/Dockerfile" in rel_paths
    assert "task.toml" in rel_paths
