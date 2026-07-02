"""Chat session port — protocol between UserSim and the system under test."""

from __future__ import annotations

from typing import Any, Dict, Protocol


class ChatSessionPort(Protocol):
    """Drive a multi-turn chat with an application adapter or Harbor sidecar."""

    @property
    def session_id(self) -> str:
        """Active session id after the first turn, if the SUT assigns one."""

    def run_turn_sync(self, message: str) -> Dict[str, Any]:
        """Send one user message; return assistant turn view (assistantMessage, items, …)."""


def normalize_agent_turn(view: Dict[str, Any], user_message: str) -> Dict[str, Any]:
    """Normalize heterogeneous SUT payloads into a common turn view."""
    turn = dict(view.get("turn") or view)
    recommended = list(
        view.get("recommendedItems")
        or turn.get("recommendedItems")
        or turn.get("groundedItems")
        or []
    )
    assistant = str(
        turn.get("assistantMessage")
        or turn.get("assistantReply")
        or view.get("reply")
        or view.get("assistantMessage")
        or ""
    )
    return {
        "assistantMessage": assistant,
        "recommendedItems": recommended,
        "groundedItems": list(turn.get("groundedItems") or recommended),
        "userMessage": user_message,
        "durationSeconds": turn.get("durationSeconds") or view.get("durationSeconds"),
    }
