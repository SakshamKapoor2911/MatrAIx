from __future__ import annotations

import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]
SNIPPET_NAME = "install-claude-code.sh"


def _task_roots() -> tuple[pathlib.Path, ...]:
    return (
        ROOT / "application" / "tasks",
        ROOT / "persona" / "tasks",
    )


def _dockerfiles_using_snippet() -> list[pathlib.Path]:
    dockerfiles: list[pathlib.Path] = []
    for task_root in _task_roots():
        for dockerfile in sorted(task_root.glob("*/environment/Dockerfile")):
            if SNIPPET_NAME in dockerfile.read_text(encoding="utf-8"):
                dockerfiles.append(dockerfile)
    return dockerfiles


def test_claude_code_docker_snippets_are_in_sync() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/sync_docker_snippets.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_claude_code_snippet_copies_match_dockerfile_usage() -> None:
    expected = {
        dockerfile.parent / SNIPPET_NAME for dockerfile in _dockerfiles_using_snippet()
    }
    actual = {
        path
        for task_root in _task_roots()
        for path in task_root.glob(f"*/environment/{SNIPPET_NAME}")
    }

    assert actual == expected


def test_legacy_task_docker_template_dirs_are_removed() -> None:
    assert not (ROOT / "application" / "tasks" / "_docker").exists()
    assert not (ROOT / "persona" / "tasks" / "_docker").exists()
