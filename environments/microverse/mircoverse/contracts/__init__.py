"""The NORMATIVE wire contract (Protocol.md §4-5).

These Pydantic models are the single shared surface between the engine and any agent
in either arm. Everything here is enforced; violations are rejected. Kept deliberately
small (Protocol.md §0). The world core, server, and agents all build against THESE types.
"""

from mircoverse.contracts.actions import (
    ActionType,
    MemoryFile,
    MemoryOp,
    MemoryUpdate,
    MoveParams,
    ConsumeParams,
    TradeParams,
    TalkParams,
    AttackParams,
    SignalParams,
    Action,
    ActionEnvelope,
)
from mircoverse.contracts.observation import (
    SelfView,
    FovCell,
    FovAgent,
    Fov,
    GlobalView,
    InboxMessage,
    LastActionResult,
    MemoryIndexEntry,
    Observation,
)
from mircoverse.contracts.identity import SoulFile, RegistrationRequest, ReflectionRequest

__all__ = [
    "ActionType",
    "MemoryFile",
    "MemoryOp",
    "MemoryUpdate",
    "MoveParams",
    "ConsumeParams",
    "TradeParams",
    "TalkParams",
    "AttackParams",
    "SignalParams",
    "Action",
    "ActionEnvelope",
    "SelfView",
    "FovCell",
    "FovAgent",
    "Fov",
    "GlobalView",
    "InboxMessage",
    "LastActionResult",
    "MemoryIndexEntry",
    "Observation",
    "SoulFile",
    "RegistrationRequest",
    "ReflectionRequest",
]
