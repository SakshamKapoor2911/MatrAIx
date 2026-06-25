from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


_ALLOWED_ROLES = {"system", "user", "assistant"}


def _require_non_empty_string(name: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _require_non_negative_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


@dataclass
class ChatMessage:
    role: str
    content: str

    def __post_init__(self) -> None:
        _require_non_empty_string("role", self.role)
        _require_non_empty_string("content", self.content)
        if self.role not in _ALLOWED_ROLES:
            raise ValueError(f"role must be one of {sorted(_ALLOWED_ROLES)}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        return cls(
            role=data["role"],
            content=data["content"],
        )


@dataclass
class NativeAction:
    raw: str
    raw_tool_plan: Any | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string("raw", self.raw)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "raw_tool_plan": self.raw_tool_plan,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["NativeAction"]:
        if data is None:
            return None
        return cls(
            raw=data["raw"],
            raw_tool_plan=data.get("raw_tool_plan"),
        )


@dataclass
class RecBotTrace:
    raw_tool_plan: List[Dict[str, Any]] = field(default_factory=list)
    raw_tool_outputs: Any = None
    recommended_item_ids: List[str] = field(default_factory=list)
    recommended_items: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.raw_tool_plan is None:
            self.raw_tool_plan = []
        if self.recommended_item_ids is None:
            self.recommended_item_ids = []
        if self.recommended_items is None:
            self.recommended_items = []
        if not isinstance(self.raw_tool_plan, list):
            raise ValueError("raw_tool_plan must be a list")
        if not isinstance(self.recommended_item_ids, list):
            raise ValueError("recommended_item_ids must be a list")
        for item_id in self.recommended_item_ids:
            _require_non_empty_string("recommended_item_id", item_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_tool_plan": self.raw_tool_plan,
            "raw_tool_outputs": self.raw_tool_outputs,
            "recommended_item_ids": self.recommended_item_ids,
            "recommended_items": self.recommended_items,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "RecBotTrace":
        if data is None:
            return cls()
        return cls(
            raw_tool_plan=data.get("raw_tool_plan", []),
            raw_tool_outputs=data.get("raw_tool_outputs"),
            recommended_item_ids=data.get("recommended_item_ids", []),
            recommended_items=data.get("recommended_items", []),
        )


@dataclass
class RecBotRequest:
    conversation_id: str
    turn_id: int
    messages: List[ChatMessage]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty_string("conversation_id", self.conversation_id)
        _require_non_negative_int("turn_id", self.turn_id)
        if not isinstance(self.messages, list) or not self.messages:
            raise ValueError("messages must be a non-empty list")
        self.messages = [
            message if isinstance(message, ChatMessage) else ChatMessage.from_dict(message)
            for message in self.messages
        ]
        if self.metadata is None:
            self.metadata = {}
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dictionary")
        if not self.latest_user_message:
            raise ValueError("messages must include at least one user message")

    @property
    def latest_user_message(self) -> str:
        for message in reversed(self.messages):
            if message.role == "user":
                return message.content
        return ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "turn_id": self.turn_id,
            "messages": [message.to_dict() for message in self.messages],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecBotRequest":
        return cls(
            conversation_id=data["conversation_id"],
            turn_id=data["turn_id"],
            messages=[ChatMessage.from_dict(message) for message in data["messages"]],
            metadata=data.get("metadata", {}),
        )


@dataclass
class RecBotTurnResult:
    backend: str
    conversation_id: str
    turn_id: int
    user_message: str
    assistant_message: str
    native_action: Optional[NativeAction] = None
    trace: RecBotTrace = field(default_factory=RecBotTrace)

    def __post_init__(self) -> None:
        _require_non_empty_string("backend", self.backend)
        _require_non_empty_string("conversation_id", self.conversation_id)
        _require_non_negative_int("turn_id", self.turn_id)
        _require_non_empty_string("user_message", self.user_message)
        _require_non_empty_string("assistant_message", self.assistant_message)
        if self.native_action is not None and not isinstance(self.native_action, NativeAction):
            self.native_action = NativeAction.from_dict(self.native_action)
        if self.trace is None:
            self.trace = RecBotTrace()
        elif not isinstance(self.trace, RecBotTrace):
            self.trace = RecBotTrace.from_dict(self.trace)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "conversation_id": self.conversation_id,
            "turn_id": self.turn_id,
            "user_message": self.user_message,
            "assistant_message": self.assistant_message,
            "native_action": self.native_action.to_dict() if self.native_action else None,
            "trace": self.trace.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecBotTurnResult":
        return cls(
            backend=data["backend"],
            conversation_id=data["conversation_id"],
            turn_id=data["turn_id"],
            user_message=data["user_message"],
            assistant_message=data["assistant_message"],
            native_action=NativeAction.from_dict(data.get("native_action")),
            trace=RecBotTrace.from_dict(data.get("trace")),
        )
