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


def _application_task_environment_dockerfiles_using_snippet() -> list[pathlib.Path]:
    task_env_root = ROOT / "environment" / "task-environments" / "application"
    return [
        dockerfile
        for dockerfile in sorted(task_env_root.glob("*/Dockerfile"))
        if SNIPPET_NAME in dockerfile.read_text(encoding="utf-8")
    ]


def test_application_task_environment_dockerfiles_normalize_shell_snippet() -> None:
    dockerfiles = _application_task_environment_dockerfiles_using_snippet()
    assert dockerfiles

    for dockerfile in dockerfiles:
        text = dockerfile.read_text(encoding="utf-8")
        assert "sed -i 's/\\r$//'" in text, dockerfile
        assert "bash /tmp/install-claude-code.sh" in text, dockerfile


def test_uv_installer_scripts_do_not_source_missing_env_file() -> None:
    shell_scripts = [
        *sorted((ROOT / "application" / "tasks").glob("*/tests/test.sh")),
        *sorted((ROOT / "application" / "tasks").glob("*/solution/solve.sh")),
        ROOT / "environment" / "runtime" / "harbor" / "cli" / "template-task" / "pytest-tests" / "test.sh",
    ]

    checked = 0
    for script in shell_scripts:
        if not script.is_file():
            continue
        text = script.read_text(encoding="utf-8")
        if "uv" not in text:
            continue
        checked += 1
        assert ".local/bin/env" not in text, script

    assert checked
