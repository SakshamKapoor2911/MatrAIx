"""The environment layer — per-tick water PRODUCTION, run before agents act (World.md §2-3).

The pure 8-action resolver (``world.resolver``) only CONSUMES and drains water; its docstring is
explicit that "drink-from-cell setup is left to the caller's env layer." This module IS that layer.
It is the world's supply side: each tick, before the resolver runs, it

  * re-stocks the **Siphon** to its scheduled output (``SiphonCurve.units_at(tick)``) — the
    deliberately-insufficient fixed supply that makes the central cell the contested chokepoint
    (World.md §3, ~1.5 units/agent/tick against higher demand);
  * **replenishes oases** toward a per-cell cap (World.md §2: "Oasis — replenishes water"), so an
    oasis is a slowly-renewing source rather than a one-shot puddle that drains to nothing.

Without this layer the Siphon produces zero drawable water (``cell.water`` stays 0 while
``consume``/``scavenge`` read ``cell.water``), oases are a fixed pool that only depletes, and agents
have no reason to converge — exactly the degenerate "everyone scatters to drain the periphery" world
the first real runs exhibited.

PURE: like the resolver, this mutates a COPY and returns a new ``WorldState``; no I/O, no clock, no
RNG (production is deterministic physics, never fairness — World.md §3). The resolution layer calls
it once per tick on the loaded world immediately before ``resolve_tick``.
"""

from __future__ import annotations

from typing import Optional

from mircoverse.world.state import WorldState, copy_world

# Per-oasis standing-water cap and per-tick regen (World.md §2 "replenishes water"). An oasis tops
# up by OASIS_REGEN_PER_TICK each tick but never above OASIS_WATER_CAP, so a drained oasis recovers
# over several ticks (a renewing-but-finite minor source) rather than refilling instantly or never.
# These mirror the generator's oasis stocking range (ResourceDistribution.oasis_water_range = 20..40).
OASIS_WATER_CAP = 40
OASIS_REGEN_PER_TICK = 4


def apply_environment(
    world: WorldState,
    tick: int,
    *,
    siphon_units: Optional[int] = None,
    oasis_cap: int = OASIS_WATER_CAP,
    oasis_regen: int = OASIS_REGEN_PER_TICK,
) -> WorldState:
    """Return a NEW world with this tick's water production applied (pure; no I/O, no RNG).

    ``siphon_units`` is the Siphon's scheduled output for ``tick`` (from ``SiphonCurve.units_at``).
    When provided, the Siphon cell's drawable ``water`` and its ``siphon_units`` are BOTH set to it
    (a hard re-stock to the schedule — the supply does not accumulate across ticks; unused output is
    lost, which is what keeps the supply genuinely insufficient rather than letting a camper bank it).
    When ``siphon_units`` is None the Siphon is left untouched (callers that thread the schedule
    elsewhere, or tests that pin the cell directly).

    Oases regenerate toward ``oasis_cap`` by at most ``oasis_regen`` per tick.
    """
    w = copy_world(world)
    for cell in w.cells.values():
        if cell.siphon:
            if siphon_units is not None:
                cell.siphon_units = siphon_units
                cell.water = siphon_units
        elif cell.terrain == "oasis":
            if cell.water < oasis_cap:
                cell.water = min(oasis_cap, cell.water + oasis_regen)
    return w
