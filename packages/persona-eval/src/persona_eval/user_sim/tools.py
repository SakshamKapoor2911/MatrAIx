"""Tool schemas and parsing for the user simulator."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

END_REASONS = frozenset({"satisfied", "give_up", "out_of_scope", "transferred"})


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnAction:
    """Parsed user-sim action for one driver step."""

    message: Optional[str] = None
    end_reason: Optional[str] = None
    note: str = ""

    @property
    def decision(self) -> str:
        if self.end_reason == "satisfied":
            return "satisfied"
        if self.end_reason in {"give_up", "out_of_scope", "transferred"}:
            return "give_up"
        return "continue"


def tool_definitions() -> List[Dict[str, Any]]:
    """OpenAI-compatible tool definitions."""
    return [
        {
            "type": "function",
            "function": {
                "name": "send_message",
                "description": "Send one natural-language message to the application chatbot.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The user message shown to the chatbot.",
                        }
                    },
                    "required": ["message"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "end_conversation",
                "description": "End the chat when the goal is met or you would stop in real life.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "enum": sorted(END_REASONS),
                        },
                        "note": {
                            "type": "string",
                            "description": "Private one-line rationale (not sent to the chatbot).",
                        },
                    },
                    "required": ["reason"],
                    "additionalProperties": False,
                },
            },
        },
    ]


def anthropic_tool_definitions() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for tool in tool_definitions():
        fn = tool["function"]
        out.append(
            {
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn["parameters"],
            }
        )
    return out


def _parse_arguments(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def parse_tool_calls(calls: List[ToolCall]) -> TurnAction:
    action = TurnAction()
    for call in calls:
        args = call.arguments
        if call.name == "send_message":
            message = str(args.get("message") or "").strip()
            if message:
                action.message = message
        elif call.name == "end_conversation":
            reason = str(args.get("reason") or "give_up").strip()
            if reason not in END_REASONS:
                reason = "give_up"
            action.end_reason = reason
            action.note = str(args.get("note") or action.note or "").strip()
    if (
        not action.message
        and not action.end_reason
        and len(calls) == 1
        and calls[0].name == "send_message"
    ):
        action.message = str(calls[0].arguments.get("message") or "").strip()
    return action


def extract_stop_token(message: str) -> Optional[str]:
    text = (message or "").strip()
    if "###STOP###" in text:
        return "satisfied"
    return None
