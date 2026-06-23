from __future__ import annotations

import base64
from pathlib import Path

import pytest

from harbor.models.trajectories.trajectory import Trajectory
from matraix.agents.installed.cocoa_runner import cocoa_to_atif


def _sample_result(*, with_screenshot: bool = False) -> dict:
    screenshot = None
    if with_screenshot:
        screenshot = base64.b64encode(b"png-bytes").decode("ascii")

    return {
        "status": "success",
        "iterations": 2,
        "answer": "",
        "conversation": [
            {"role": "user", "content": "system prompt"},
            {
                "role": "assistant",
                "content": "Thought: Open the catalog homepage.",
                "tool_calls": [
                    {
                        "id": "call_nav",
                        "type": "function",
                        "function": {
                            "name": "browser_navigate",
                            "arguments": '{"url": "https://books.toscrape.com/"}',
                        },
                    }
                ],
            },
            {"role": "user", "content": "feedback"},
            {
                "role": "assistant",
                "content": "Thought: Mark interactive elements.",
                "tool_calls": [
                    {
                        "id": "call_dom",
                        "type": "function",
                        "function": {
                            "name": "dom_mark_elements",
                            "arguments": "{}",
                        },
                    }
                ],
            },
        ],
        "execution_trace": [
            {
                "action": {
                    "action_type": "browser_navigate",
                    "url": "https://books.toscrape.com/",
                    "tool_call_id": "call_nav",
                },
                "feedback": {
                    "done": False,
                    "message": "Successfully navigated to https://books.toscrape.com/",
                },
            },
            {
                "action": {
                    "action_type": "dom_mark_elements",
                    "tool_call_id": "call_dom",
                },
                "feedback": {
                    "done": False,
                    "message": "Found 3 interactive element(s)",
                },
            },
        ],
        "api_cost_stats": {
            "total_input_tokens": 1200,
            "total_output_tokens": 80,
            "total_cached_tokens": 400,
            "total_cost_usd": 0.12,
        },
        "visualization_data": {
            "iterations": [
                {
                    "iteration": 1,
                    "actions": [
                        {
                            "action": {
                                "action_type": "browser_navigate",
                                "tool_call_id": "call_nav",
                            },
                            "observation": "Successfully navigated",
                            "screenshot": screenshot,
                        }
                    ],
                }
            ]
        },
    }


@pytest.mark.unit
def test_cocoa_to_atif_builds_valid_trajectory(tmp_path: Path) -> None:
    trajectory_path = tmp_path / "agent" / "trajectory.json"
    data = cocoa_to_atif(
        _sample_result(with_screenshot=True),
        instruction="Browse the catalog",
        model_name="anthropic/claude-sonnet-4-6",
        trajectory_path=trajectory_path,
        agent_version="installed",
    )

    trajectory = Trajectory.model_validate(data)
    assert trajectory.schema_version == "ATIF-v1.6"
    assert len(trajectory.steps) == 3
    assert trajectory.steps[0].source == "user"
    assert trajectory.steps[1].source == "agent"
    assert trajectory.steps[1].tool_calls
    assert trajectory.steps[1].tool_calls[0].function_name == "browser_navigate"
    assert trajectory.steps[1].tool_calls[0].arguments == {
        "url": "https://books.toscrape.com/"
    }
    assert trajectory.steps[1].observation
    assert trajectory.steps[1].reasoning_content == "Open the catalog homepage."
    assert trajectory.final_metrics
    assert trajectory.final_metrics.total_cost_usd == 0.12
    assert trajectory.extra["cocoa"]["is_successful"] is True
    assert trajectory.extra["cocoa"]["action_names"] == [
        "browser_navigate",
        "dom_mark_elements",
    ]
    assert trajectory.extra["cocoa"]["urls"] == ["https://books.toscrape.com/"]
    assert isinstance(trajectory.steps[1].message, list)

    copied = tmp_path / "agent" / "images" / "step_001.png"
    assert copied.is_file()
    assert copied.read_bytes() == b"png-bytes"
