"""Tests for iOS CUA decision materialization."""

import json

import pytest

from matraix.agents.persona.ios_submission import extract_ios_decision_from_trajectory


def test_extract_decision_from_done_tool_message() -> None:
    trajectory = {
        "steps": [
            {"step_id": 1, "source": "user", "message": "task"},
            {
                "step_id": 2,
                "source": "agent",
                "tool_calls": [
                    {
                        "function_name": "done",
                        "arguments": {
                            "success": True,
                            "message": (
                                '{"keep_notifications_on": false, '
                                '"app_reviewed": "Messages", '
                                '"reason": "I mute group chats during work hours."}'
                            ),
                        },
                    }
                ],
            },
        ]
    }
    decision = extract_ios_decision_from_trajectory(trajectory)
    assert decision == {
        "keep_notifications_on": False,
        "app_reviewed": "Messages",
        "reason": "I mute group chats during work hours.",
    }


def test_extract_decision_prefers_latest_done() -> None:
    trajectory = {
        "steps": [
            {
                "source": "agent",
                "tool_calls": [
                    {
                        "function_name": "done",
                        "arguments": {
                            "success": True,
                            "message": '{"keep_notifications_on": true, "app_reviewed": "Mail", "reason": "old draft"}',
                        },
                    }
                ],
            },
            {
                "source": "agent",
                "tool_calls": [
                    {
                        "function_name": "done",
                        "arguments": {
                            "success": True,
                            "message": '{"keep_notifications_on": true, "app_reviewed": "Safari", "reason": "final choice here"}',
                        },
                    }
                ],
            },
        ]
    }
    decision = extract_ios_decision_from_trajectory(trajectory)
    assert decision["app_reviewed"] == "Safari"


def test_extract_decision_returns_none_without_done() -> None:
    trajectory = {
        "steps": [
            {
                "source": "agent",
                "tool_calls": [{"function_name": "tap", "arguments": {"x": 1, "y": 2}}],
            }
        ]
    }
    assert extract_ios_decision_from_trajectory(trajectory) is None
