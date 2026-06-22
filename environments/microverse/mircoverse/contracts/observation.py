"""Observation packet contract — Protocol.md §5.2 (server → agent).

This IS the agent's working memory: FOV, own state, global status, inbox, last action
result, and the memory_index. The engine computes it fresh each tick; the agent never
stores it. The memory_index is how index-driven agentic retrieval works without
embeddings (Protocol.md §6.2).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SelfView(BaseModel):
    agent_id: str
    pos: tuple[int, int]
    water: int
    food: int
    goods: int
    on_terrain: str
    stance: Literal["friendly", "neutral", "aggressive"]
    # The agent's last-set intention (Protocol.md §4.2 / §5.2), carried forward each tick so
    # the agent never loses the thread of what it was trying to do. None until it sets one.
    # Stated-intention-vs-executed-action is a free third stated-vs-revealed channel (§9.5).
    intention: Optional[str] = None


class DeathCache(BaseModel):
    water: int
    food: int
    goods: int = 0
    locations_hint: int = 0  # count of droppable location facts, not their values


class FovCell(BaseModel):
    pos: tuple[int, int]
    terrain: str
    water: int = 0
    food: int = 0
    goods: int = 0
    siphon: bool = False
    death_cache: Optional[DeathCache] = None


class FovAgent(BaseModel):
    agent_id: str
    pos: tuple[int, int]
    stance: Literal["friendly", "neutral", "aggressive"]
    visible_water: Literal["low", "medium", "high"]  # coarse, never exact (info asymmetry)


class Fov(BaseModel):
    radius: int
    cells: list[FovCell]
    agents: list[FovAgent]
    noisy: bool = False  # true during a sandstorm — values above are perturbed (Protocol.md §2.5)


class GlobalView(BaseModel):
    alive_count: int
    storm_active: bool
    heat_zone_center: Optional[tuple[int, int]] = None
    siphon_units_this_tick: int


class InboxMessage(BaseModel):
    from_agent: str = Field(alias="from")
    tick: int
    message: str
    location_claim: Optional[tuple[int, int]] = None

    model_config = {"populate_by_name": True}


class LastActionResult(BaseModel):
    tick: int
    action: str
    status: Literal["ok", "rejected", "failed", "defaulted"]
    note: str = ""


class MemoryIndexEntry(BaseModel):
    """One line of the agent's long-term-store table of contents. Drives retrieval:
    the agent reads these, judges relevance itself, and pulls full entries on demand."""
    ref: str          # e.g. "events#88" or "relationships#agent_03"
    tick: int
    importance: int = Field(ge=1, le=10)
    summary: str


class Observation(BaseModel):
    tick: int
    tick_ends_at: str  # ISO8601; agents ALWAYS use server time, never a local deadline
    self: SelfView
    fov: Fov
    global_: GlobalView = Field(alias="global")
    inbox: list[InboxMessage] = Field(default_factory=list)
    last_action_result: Optional[LastActionResult] = None
    memory_index: list[MemoryIndexEntry] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
