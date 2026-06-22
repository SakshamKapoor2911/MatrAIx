"""Pure FOV (field-of-view) computation: the working-memory packet the engine sends down.

Chebyshev radius 2 ⇒ a 5×5 window around the agent (Protocol.md §2.1, §5.2). Builds the FROZEN
``Fov`` wire contract (``mircoverse.contracts.observation``) — never redefines it. Neighbour water
is reported COARSELY (``low|medium|high``) to preserve the information asymmetry that makes
knowledge-of-water the central social currency (World.md §1, §6).

Pure: no I/O. The resolution layer assembles the full ``Observation`` (self/global/inbox/index)
around this; here we compute only the spatial FOV the agent can perceive.
"""

from __future__ import annotations

from mircoverse.contracts import Fov, FovAgent, FovCell
from mircoverse.contracts.observation import DeathCache as WireDeathCache
from mircoverse.world.geometry import FOV_RADIUS, fov_cells
from mircoverse.world.state import WorldState

# FOV_RADIUS is single-sourced in geometry.py (re-exported here for the existing import surface)
# so the resolver's move-gate and this FOV computation share ONE definition of "within view".


def _coarse_water(water: int) -> str:
    """Bucket exact water into the wire's coarse band (never reveals the exact number)."""
    if water <= 15:
        return "low"
    if water <= 40:
        return "medium"
    return "high"


def compute_fov(
    world: WorldState,
    agent_id: str,
    radius: int = FOV_RADIUS,
    noisy: bool = False,
) -> Fov:
    """Compute the agent's field of view as the frozen ``Fov`` contract.

    Includes every in-bounds cell within Chebyshev ``radius`` (centre included) and every OTHER
    live agent standing in that window. ``noisy=True`` marks a sandstorm (the perturbation of
    values is the env layer's job; we only set the flag and let it pass values through).
    """
    agent = world.agents[agent_id]
    center = agent.pos
    cells: list[FovCell] = []
    for pos in fov_cells(center, radius):
        if not world.in_bounds(pos):
            continue
        cell = world.cell(pos)
        if cell is None:
            continue
        wire_cache = None
        if cell.death_cache is not None:
            dc = cell.death_cache
            wire_cache = WireDeathCache(
                water=dc.water,
                food=dc.food,
                goods=dc.goods,
                locations_hint=len(dc.location_facts),
            )
        cells.append(
            FovCell(
                pos=pos,
                terrain=cell.terrain,
                water=cell.water,
                food=cell.food,
                goods=cell.goods,
                siphon=cell.siphon,
                death_cache=wire_cache,
            )
        )

    agents: list[FovAgent] = []
    for other_id, other in world.live_agents().items():
        if other_id == agent_id:
            continue
        if max(abs(other.pos[0] - center[0]), abs(other.pos[1] - center[1])) <= radius:
            agents.append(
                FovAgent(
                    agent_id=other_id,
                    pos=other.pos,
                    stance=other.stance,
                    visible_water=_coarse_water(other.water),  # type: ignore[arg-type]
                )
            )

    return Fov(radius=radius, cells=cells, agents=agents, noisy=noisy)
