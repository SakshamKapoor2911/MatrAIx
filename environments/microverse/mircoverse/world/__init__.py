"""The pure world core (BUILD_SPEC §1, Protocol.md §11 step 1).

Pure functions over plain dataclasses: NO database, NO network, NO clock. All stochastic
resolution flows through a single seeded ``random.Random`` passed in (World.md §11). This is the
testable, replayable heart of the engine; the persistence/resolution layers wrap it with I/O.
"""

from mircoverse.world.environment import (
    OASIS_REGEN_PER_TICK,
    OASIS_WATER_CAP,
    apply_environment,
)
from mircoverse.world.fov import FOV_RADIUS, compute_fov
from mircoverse.world.geometry import (
    DIRECTION_DELTAS,
    chebyshev,
    contention_key,
    contention_winner,
    fov_cells,
    is_adjacent,
    moore_neighbors,
    step_direction,
    step_toward,
)
from mircoverse.world.resolver import ActionResult, resolve_tick
from mircoverse.world.state import (
    ACTION_WATER_COST_TENTHS,
    TERRAIN_FOOD_COST,
    TERRAIN_WATER_COST,
    Agent,
    Cell,
    DeathCache,
    PendingMessage,
    WorldState,
    copy_world,
)

__all__ = [
    "Agent",
    "Cell",
    "DeathCache",
    "PendingMessage",
    "WorldState",
    "copy_world",
    "TERRAIN_WATER_COST",
    "TERRAIN_FOOD_COST",
    "ACTION_WATER_COST_TENTHS",
    "ActionResult",
    "resolve_tick",
    "compute_fov",
    "FOV_RADIUS",
    "apply_environment",
    "OASIS_WATER_CAP",
    "OASIS_REGEN_PER_TICK",
    "chebyshev",
    "is_adjacent",
    "moore_neighbors",
    "step_toward",
    "step_direction",
    "fov_cells",
    "contention_key",
    "contention_winner",
    "DIRECTION_DELTAS",
]
