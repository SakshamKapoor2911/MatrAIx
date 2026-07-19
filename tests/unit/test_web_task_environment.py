"""Tests for web CLI environment staging."""

from __future__ import annotations

from pathlib import Path

from matraix.web_task_environment import (
    SHARED_WEB_CLI_DEFINITION,
    is_cli_web_harness,
    resolve_web_harbor_task_path,
    stage_web_task_for_cli_harness,
)


def test_is_cli_web_harness() -> None:
    assert is_cli_web_harness("persona-codex")
    assert not is_cli_web_harness("persona-openhands-sdk")


def test_stage_web_task_swaps_environment_definition(tmp_path: Path) -> None:
    task_dir = tmp_path / "example-web-playwright_quote-choice"
    task_dir.mkdir()
    (task_dir / "instruction.md").write_text("# Task\n", encoding="utf-8")
    (task_dir / "task.toml").write_text(
        "\n".join(
            [
                'version = "1.0"',
                "",
                "[metadata]",
                'type = "web"',
                "",
                "[environment]",
                'definition = "application/shared-web-playwright"',
            ]
        ),
        encoding="utf-8",
    )

    staged = stage_web_task_for_cli_harness(task_dir, cache_dir=tmp_path / "cache")
    staged_toml = (staged / "task.toml").read_text(encoding="utf-8")
    assert f'definition = "{SHARED_WEB_CLI_DEFINITION}"' in staged_toml
    assert (staged / "instruction.md").read_text(encoding="utf-8") == "# Task\n"


def test_resolve_web_harbor_task_path_leaves_browser_agents_untouched(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    task_dir = repo / "application/tasks/example-web-playwright_quote-choice"
    task_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        "[metadata]\ntype = \"web\"\n\n[environment]\n"
        'definition = "application/shared-web-playwright"\n',
        encoding="utf-8",
    )

    resolved = resolve_web_harbor_task_path(
        "application/tasks/example-web-playwright_quote-choice",
        agent_name="persona-openhands-sdk",
        repo_root=repo,
        cache_dir=repo / "cache",
    )
    assert resolved == "application/tasks/example-web-playwright_quote-choice"


def test_resolve_web_harbor_task_path_stages_cli_web_runs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    task_dir = repo / "application/tasks/example-web-playwright_quote-choice"
    task_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        "[metadata]\ntype = \"web\"\n\n[environment]\n"
        'definition = "application/shared-web-playwright"\n',
        encoding="utf-8",
    )

    resolved = resolve_web_harbor_task_path(
        "application/tasks/example-web-playwright_quote-choice",
        agent_name="persona-claude-code",
        repo_root=repo,
        cache_dir=repo / "cache",
    )
    assert resolved != "application/tasks/example-web-playwright_quote-choice"
    staged = repo / resolved
    assert staged.is_dir()
    assert SHARED_WEB_CLI_DEFINITION in (staged / "task.toml").read_text(encoding="utf-8")


def test_resolve_web_harbor_task_path_ignores_cli_on_survey_tasks(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    task_dir = repo / "application/tasks/example-survey_product-feedback"
    task_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        "[metadata]\ntype = \"survey\"\n\n[environment]\n"
        'definition = "application/shared-survey-form"\n',
        encoding="utf-8",
    )

    resolved = resolve_web_harbor_task_path(
        "application/tasks/example-survey_product-feedback",
        agent_name="persona-claude-code",
        repo_root=repo,
        cache_dir=repo / "cache",
    )
    assert resolved == "application/tasks/example-survey_product-feedback"
