"""The tick-resolution orchestration layer (BUILD_SPEC §3).

This is Architecture.md's Step Functions sequence (Steps 0-9) collapsed into ONE local
orchestration function for the seed run (Protocol.md §1: single-process Python + local Postgres,
no Lambda/Step Functions). It is the only place the PURE world core (``mircoverse.world``) is
glued to persisted state (``mircoverse.persistence``).

``resolve_tick(conn, tick_n, seeded_rng)``:

    1. Read accepted actions for tick N from ``action_log``.
    2. Load the ``WorldState`` from the DB (``agents``, ``world_cells``, known locations, the
       inbox left for tick N by tick N-1's resolution).
    3. Call the pure world-core resolver (all stochastic outcomes flow through ``seeded_rng``).
    4. Persist changed ``world_cells`` (changed only), ``agents``, and ``action_log.result``.
    5. Precompute each live agent's next-tick ``Observation`` packet (§5.2, incl. ``memory_index``)
       into ``agent_tick_results``.
    6. Advance ``tick_state`` to N+1 (``window_open = TRUE``, ``active_agent_count``).

Determinism is preserved end-to-end: the pure core is deterministic given the same world +
actions + seeded RNG (World.md §11), and this layer only does I/O around it — it never makes a
stochastic decision itself.
"""

from mircoverse.resolution.orchestrator import (
    build_observation,
    load_world_state,
    resolve_tick,
)
from mircoverse.resolution.bootstrap import BootstrapAgent, initialize_simulation

__all__ = [
    "resolve_tick",
    "load_world_state",
    "build_observation",
    "initialize_simulation",
    "BootstrapAgent",
]
