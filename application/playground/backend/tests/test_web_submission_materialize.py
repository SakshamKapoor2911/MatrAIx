"""Tests for web submission extraction from OpenHands trajectories."""

from __future__ import annotations

import json

from matraix.agents.persona.cua_submission import (
    extract_ecommerce_interaction_from_trajectory,
)


def _payload() -> dict[str, object]:
    return {
        "selected_product_id": "desk-002",
        "selected_product_name": "FocusDesk Pro",
        "need_satisfaction": 8,
        "ease_of_use": 7,
        "overall_experience_rating": 6,
        "reason": (
            "The FocusDesk Pro matched my workspace needs with drawer storage "
            "and cable routing for multiple devices."
        ),
    }


def test_extract_ecommerce_interaction_from_trajectory_message_fence() -> None:
    trajectory = {
        "steps": [
            {
                "source": "agent",
                "message": "Summary\n```json\n{}\n```".format(json.dumps(_payload())),
            }
        ]
    }
    recovered = extract_ecommerce_interaction_from_trajectory(trajectory)
    assert recovered == _payload()


def test_extract_ecommerce_interaction_rejects_short_reason() -> None:
    bad = dict(_payload())
    bad["reason"] = "too short"
    trajectory = {
        "steps": [
            {
                "source": "agent",
                "message": "```json\n{}\n```".format(json.dumps(bad)),
            }
        ]
    }
    assert extract_ecommerce_interaction_from_trajectory(trajectory) is None
