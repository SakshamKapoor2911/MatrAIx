"""Chat session port — protocol between UserSim and the system under test."""

from __future__ import annotations

from typing import Any, Dict, Protocol, Sequence

from persona_eval.persona_exposure import build_persona_exposure


class ChatSessionPort(Protocol):
    """Drive a multi-turn chat with an application adapter or Harbor sidecar."""

    @property
    def session_id(self) -> str:
        """Active session id after the first turn, if the SUT assigns one."""

    def run_turn_sync(self, message: str) -> Dict[str, Any]:
        """Send one user message; return assistant turn view (assistantMessage, items, …)."""


def normalize_agent_turn(
    view: Dict[str, Any],
    user_message: str,
    *,
    persona_exposure_fields: Sequence[Any] | None = None,
) -> Dict[str, Any]:
    """Normalize heterogeneous SUT payloads into a common turn view."""
    turn = dict(view.get("turn") or view)
    assistant = str(
        turn.get("assistantMessage")
        or turn.get("assistantReply")
        or view.get("reply")
        or view.get("assistantMessage")
        or ""
    )
    merged = {**view, **turn}
    exposure = view.get("personaExposure") or turn.get("personaExposure")
    if not isinstance(exposure, list) or not exposure:
        exposure = build_persona_exposure(merged, persona_exposure_fields)
    return {
        "assistantMessage": assistant,
        "userMessage": user_message,
        "durationSeconds": turn.get("durationSeconds") or view.get("durationSeconds"),
        "personaExposure": list(exposure),
    }
