"""World-core state dataclasses (PURE — no I/O, no clock, no DB).

These are the in-memory representation the resolver operates on. They are deliberately
plain `@dataclass`es, not the Pydantic wire contracts in ``mircoverse.contracts``: the
wire contracts are what crosses the HTTP boundary, these are the engine's internal physics
state. The resolution layer (``mircoverse.resolution``) is responsible for translating
between persisted rows / wire packets and these dataclasses.

Canonical vocabulary only (World.md §1, BUILD_SPEC): resources are ``water``/``food``/``goods``;
terrain is ``desert|oasis|mountain|settlement|ruins``; the water machine is the ``siphon``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal, Optional

Terrain = Literal["desert", "oasis", "mountain", "settlement", "ruins"]
Stance = Literal["friendly", "neutral", "aggressive"]


# ── Per-terrain costs (World.md §2 / Protocol.md §2.2) ──────────────────────────
# water cost on the cell per tick, food cost per tick. (Ticks-to-cross is a movement
# concern handled by the mover, not a per-tick drain.)
TERRAIN_WATER_COST: dict[str, int] = {
    "desert": 2,
    "mountain": 1,
    "oasis": 0,
    "settlement": 0,
    "ruins": 1,
}
TERRAIN_FOOD_COST: dict[str, int] = {
    "desert": 1,
    "mountain": 2,
    "oasis": 0,
    "settlement": 0,
    "ruins": 1,
}

# Per-action water cost (Protocol.md §4.1). Stored as integers in tenths to keep the
# whole engine on integer arithmetic (signal = 0.5, so 5 tenths). All other game state
# (agent water/food/goods, cell resources) is plain integer units; action cost is the
# only fractional quantity in the spec, so we scale ONLY it.
ACTION_WATER_COST_TENTHS: dict[str, int] = {
    "move": 0,       # terrain-dependent; added by the mover
    "wait": 0,
    "consume": 0,
    "scavenge": 30,
    "trade": 10,
    "talk": 10,
    "attack": 20,
    "signal": 5,
}


@dataclass
class DeathCache:
    """What a dead agent leaves on its final cell (World.md §5, Protocol.md §2.4).

    ``location_facts`` are droppable knowledge fragments (e.g. "oasis at (12,40)"); their
    *truth* is re-validated live when scavenged (Protocol.md §2.4), so we keep the count
    here for the coarse FOV hint and the facts themselves for the looter.
    """

    water: int = 0
    food: int = 0
    goods: int = 0
    location_facts: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class Cell:
    x: int
    y: int
    terrain: Terrain
    water: int = 0
    food: int = 0
    goods: int = 0
    siphon: bool = False
    siphon_units: int = 0  # water units the siphon makes available THIS tick (physics only)
    death_cache: Optional[DeathCache] = None

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)


@dataclass
class Agent:
    agent_id: str
    pos: tuple[int, int]
    water: int
    food: int = 0
    goods: int = 0
    stance: Stance = "neutral"
    alive: bool = True
    death_tick: Optional[int] = None
    # Cells this agent knows (spawn + visited + told). Goal-move is only valid to known cells.
    known_locations: set[tuple[int, int]] = field(default_factory=set)
    # Last-set self-authored intention (Protocol.md §4.2 / §7.4). No mechanical effect — it
    # carries forward across ticks (via copy_world's replace) and is surfaced in the next
    # observation's self.intention. Set by the resolution layer from the action envelope.
    intention: Optional[str] = None


@dataclass
class PendingMessage:
    """A talk message produced in tick N, delivered in tick N+1 (latency, Protocol.md §4.4)."""

    from_agent: str
    to_agent: Optional[str]  # None ⇒ local broadcast
    tick: int                # the tick it was SENT
    message: str
    location_claim: Optional[tuple[int, int]] = None
    broadcast: bool = False
    sender_pos: tuple[int, int] = (0, 0)  # for resolving local-broadcast recipients


@dataclass
class WorldState:
    tick: int
    width: int
    height: int
    cells: dict[tuple[int, int], Cell]
    agents: dict[str, Agent]
    base_drain: int = 1
    # Messages SENT this tick (delivered next tick). Keyed by sending tick.
    outbound_messages: list[PendingMessage] = field(default_factory=list)
    # Messages delivered to each agent THIS tick (sent last tick).
    inbox: dict[str, list[PendingMessage]] = field(default_factory=dict)

    def cell(self, pos: tuple[int, int]) -> Optional[Cell]:
        return self.cells.get(pos)

    def in_bounds(self, pos: tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def live_agents(self) -> dict[str, Agent]:
        return {aid: a for aid, a in self.agents.items() if a.alive}

    def alive_count(self) -> int:
        return sum(1 for a in self.agents.values() if a.alive)


def copy_world(world: WorldState) -> WorldState:
    """Deep-ish copy so the resolver never mutates the caller's input (purity).

    Copies every mutable container the resolver touches; leaves immutable scalars shared.
    """
    new_cells: dict[tuple[int, int], Cell] = {}
    for pos, c in world.cells.items():
        dc = None
        if c.death_cache is not None:
            dc = DeathCache(
                water=c.death_cache.water,
                food=c.death_cache.food,
                goods=c.death_cache.goods,
                location_facts=list(c.death_cache.location_facts),
            )
        new_cells[pos] = replace(c, death_cache=dc)
    new_agents: dict[str, Agent] = {}
    for aid, a in world.agents.items():
        new_agents[aid] = replace(a, known_locations=set(a.known_locations))
    return WorldState(
        tick=world.tick,
        width=world.width,
        height=world.height,
        cells=new_cells,
        agents=new_agents,
        base_drain=world.base_drain,
        outbound_messages=[],  # outbound is regenerated each tick
        inbox={k: list(v) for k, v in world.inbox.items()},
    )
