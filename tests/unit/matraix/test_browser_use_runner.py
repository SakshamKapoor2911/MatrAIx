from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from harbor.models.trajectories.trajectory import Trajectory
from matraix.agents.installed.browser_use_runner import (
    history_to_atif,
    promote_browser_use_outputs,
)


def test_promote_browser_use_outputs_copies_sandbox_files(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "matraix.agents.installed.browser_use_runner.OUTPUT_DIR", tmp_path / "output"
    )
    data_dir = tmp_path / "output" / "browseruse_agent_data"
    data_dir.mkdir(parents=True)
    (data_dir / "book_interest.json").write_text('{"interested": true}\n', encoding="utf-8")

    agent = SimpleNamespace(file_system=SimpleNamespace(get_dir=lambda: data_dir))
    promoted = promote_browser_use_outputs(agent)

    dest = tmp_path / "output" / "book_interest.json"
    assert promoted == [str(dest)]
    assert dest.read_text(encoding="utf-8") == '{"interested": true}\n'


def test_promote_browser_use_outputs_no_file_system():
    assert promote_browser_use_outputs(SimpleNamespace()) == []


def _make_action(name: str, **params):
    return SimpleNamespace(
        model_dump=lambda exclude_none=True, mode="json": {name: params}
    )


def _make_history_item(
    *,
    screenshot_path: Path | None = None,
    actions: list | None = None,
    results: list | None = None,
):
    actions = actions or [_make_action("navigate", url="https://example.com")]
    results = results or [
        SimpleNamespace(
            extracted_content="Navigated",
            error=None,
            long_term_memory=None,
        )
    ]
    return SimpleNamespace(
        model_output=SimpleNamespace(
            evaluation_previous_goal="Success",
            memory="On homepage",
            next_goal="Continue",
            thinking="Need to browse",
            action=actions,
        ),
        result=results,
        state=SimpleNamespace(screenshot_path=str(screenshot_path) if screenshot_path else None),
        metadata=SimpleNamespace(step_start_time=1_700_000_000.0),
    )


@pytest.mark.unit
def test_history_to_atif_builds_valid_trajectory(tmp_path: Path) -> None:
    screenshot = tmp_path / "shot.png"
    screenshot.write_bytes(b"png")

    history = SimpleNamespace(
        history=[_make_history_item(screenshot_path=screenshot)],
        usage=None,
        final_result=lambda: "Done",
        is_done=lambda: True,
        is_successful=lambda: True,
        urls=lambda: ["https://example.com"],
        action_names=lambda: ["navigate"],
    )

    trajectory_path = tmp_path / "agent" / "trajectory.json"
    data = history_to_atif(
        history,
        instruction="Browse the catalog",
        model_name="anthropic/claude-sonnet-4-6",
        trajectory_path=trajectory_path,
        agent_version="0.13.1",
        promoted_outputs=["/app/output/book.json"],
    )

    trajectory = Trajectory.model_validate(data)
    assert trajectory.schema_version == "ATIF-v1.6"
    assert len(trajectory.steps) == 2
    assert trajectory.steps[0].source == "user"
    assert trajectory.steps[1].source == "agent"
    assert trajectory.steps[1].tool_calls
    assert trajectory.steps[1].tool_calls[0].function_name == "navigate"
    assert trajectory.steps[1].observation
    assert isinstance(trajectory.steps[1].message, list)
    assert trajectory.extra["browser_use"]["final_result"] == "Done"

    copied = tmp_path / "agent" / "images" / "step_001.png"
    assert copied.is_file()
