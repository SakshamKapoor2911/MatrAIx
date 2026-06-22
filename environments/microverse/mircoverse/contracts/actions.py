"""Action submission contract — Protocol.md §4.

The eight verbs of World.md §4. Small on purpose: a tight, fully-enumerable action
space keeps resolution deterministic and keeps the moral content of each action legible.
The morally-loaded actions (scavenge/trade/talk/attack) are exactly the ones the soul
file's moral_boundaries speak to — the action space IS the boundary space.

Note: move/attack/trade are VALUES of action.type inside one envelope, never separate
tools (Protocol.md §7.2). The whole tick is one atomic POST /action write so that
"what I did" and "what I chose to remember about it" share a tick_number.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


class ActionType(str, Enum):
    MOVE = "move"
    WAIT = "wait"
    CONSUME = "consume"
    SCAVENGE = "scavenge"
    TRADE = "trade"
    TALK = "talk"
    ATTACK = "attack"
    SIGNAL = "signal"


# ── Per-action params (Protocol.md §4.1) ───────────────────────────────────────

class MoveParams(BaseModel):
    """Goal-directed move to a KNOWN cell, OR blind directional exploration.
    Exactly one of `toward` / `direction` must be set (Protocol.md §4.3)."""
    toward: Optional[tuple[int, int]] = None
    direction: Optional[Literal["N", "NE", "E", "SE", "S", "SW", "W", "NW"]] = None

    @model_validator(mode="after")
    def exactly_one(self) -> "MoveParams":
        if (self.toward is None) == (self.direction is None):
            raise ValueError("move requires exactly one of `toward` or `direction`")
        return self


class ConsumeParams(BaseModel):
    resource: Literal["water", "food", "goods"]
    amount: int = Field(gt=0)


class TradeParams(BaseModel):
    """Two-tick handshake: completes only if both parties name each other (Protocol.md §4.4)."""
    target: str
    offer: dict[str, int] = Field(default_factory=dict)
    request: dict[str, int] = Field(default_factory=dict)


class TalkParams(BaseModel):
    """Either a directed message or a local broadcast, plus the message body.
    MAY attach a location claim — truth is NOT verified at runtime (Protocol.md §4.5)."""
    target: Optional[str] = None
    broadcast: bool = False
    message: str
    location_claim: Optional[tuple[int, int]] = None

    @model_validator(mode="after")
    def directed_or_broadcast(self) -> "TalkParams":
        if (self.target is None) == (not self.broadcast):
            raise ValueError("talk requires exactly one of `target` or `broadcast=true`")
        return self


class AttackParams(BaseModel):
    target: str


class SignalParams(BaseModel):
    stance: Literal["friendly", "neutral", "aggressive"]


# `wait` and `scavenge` take no params; modeled as empty objects.
class EmptyParams(BaseModel):
    model_config = {"extra": "forbid"}


# ── The action ────────────────────────────────────────────────────────────────

class Action(BaseModel):
    type: ActionType
    params: Union[
        MoveParams, ConsumeParams, TradeParams, TalkParams,
        AttackParams, SignalParams, EmptyParams,
    ] = Field(default_factory=EmptyParams)

    @model_validator(mode="after")
    def params_match_type(self) -> "Action":
        expected = {
            ActionType.MOVE: MoveParams,
            ActionType.WAIT: EmptyParams,
            ActionType.CONSUME: ConsumeParams,
            ActionType.SCAVENGE: EmptyParams,
            ActionType.TRADE: TradeParams,
            ActionType.TALK: TalkParams,
            ActionType.ATTACK: AttackParams,
            ActionType.SIGNAL: SignalParams,
        }[self.type]
        if not isinstance(self.params, expected):
            raise ValueError(
                f"action.type={self.type.value} requires {expected.__name__}, "
                f"got {type(self.params).__name__}"
            )
        return self


# ── Memory delta (Protocol.md §4.2) ─────────────────────────────────────────────

class MemoryFile(str, Enum):
    EVENTS = "events"
    RELATIONSHIPS = "relationships"
    REFLECTIONS = "reflections"


class MemoryOp(str, Enum):
    APPEND = "append"
    UPDATE = "update"


class MemoryUpdate(BaseModel):
    """Optional per-tick subjective-memory delta. Append one entry / update one line /
    omit entirely. Never the whole store (Protocol.md §4.2, §7)."""
    file: MemoryFile
    op: MemoryOp = MemoryOp.APPEND
    subject_agent_id: Optional[str] = None  # required when file == relationships
    importance: int = Field(ge=1, le=10)
    content: str

    @model_validator(mode="after")
    def relationship_needs_subject(self) -> "MemoryUpdate":
        if self.file == MemoryFile.RELATIONSHIPS and not self.subject_agent_id:
            raise ValueError("relationships memory requires subject_agent_id")
        return self


# ── The submission envelope (Protocol.md §4.2) ──────────────────────────────────

class ActionEnvelope(BaseModel):
    """One atomic POST /action body: the tick's action + optional memory delta +
    optional intention + optional rationale (neither has mechanical effect; both logged
    for research).

    `intention` is a single self-authored line of *what the agent is currently trying to
    do* (Protocol.md §4.2 / §7.4). It de-myopifies the agent without a planner and gives a
    free third stated-vs-revealed channel (stated-intention vs executed-action, World.md
    §9.5). The engine stores the latest intention and logs every change; omitting it leaves
    the prior intention standing (carried forward in the next observation's `self.intention`).
    """
    tick: int = Field(ge=0)
    action: Action
    memory_update: Optional[MemoryUpdate] = None
    intention: Optional[str] = None
    rationale: Optional[str] = None
