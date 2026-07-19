from __future__ import annotations

from pathlib import Path

from harbor.trial.trial import build_task_input_mounts


def test_build_task_input_mounts_binds_task_input_files(tmp_path: Path) -> None:
    task_dir = tmp_path / "application" / "tasks" / "example-chat-demo"
    input_dir = task_dir / "input"
    nested_dir = input_dir / "nested"
    nested_dir.mkdir(parents=True)
    (input_dir / "context.md").write_text("Task context", encoding="utf-8")
    (input_dir / "chatbot.yaml").write_text("transport: sidecar_http\n", encoding="utf-8")
    (nested_dir / "notes.txt").write_text("Nested note", encoding="utf-8")

    mounts = build_task_input_mounts(task_dir)

    by_target = {mount["target"]: mount for mount in mounts}
    assert by_target["/app/input/context.md"]["source"] == (
        input_dir / "context.md"
    ).resolve().absolute().as_posix()
    assert by_target["/app/input/chatbot.yaml"]["read_only"] is True
    assert by_target["/app/input/nested/notes.txt"]["source"] == (
        nested_dir / "notes.txt"
    ).resolve().absolute().as_posix()


def test_build_task_input_mounts_returns_empty_without_input_dir(tmp_path: Path) -> None:
    task_dir = tmp_path / "application" / "tasks" / "example-web-demo"
    task_dir.mkdir(parents=True)

    assert build_task_input_mounts(task_dir) == []
