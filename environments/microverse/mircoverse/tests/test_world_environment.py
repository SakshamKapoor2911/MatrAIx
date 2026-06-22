"""Tests for the per-tick environment / water-production layer (mircoverse.world.environment).

The env layer is the world's SUPPLY side, run before the resolver consumes. It must: re-stock the
Siphon to its scheduled output (so the chokepoint dispenses), regenerate oases toward a cap (so they
renew rather than drain to nothing), leave everything else untouched, and stay PURE (no mutation of
the input world). No I/O, no DB — these never skip.
"""

from __future__ import annotations

from mircoverse.world.environment import (
    OASIS_REGEN_PER_TICK,
    OASIS_WATER_CAP,
    apply_environment,
)
from mircoverse.world.state import Cell, WorldState


def _world(cells: list[Cell]) -> WorldState:
    return WorldState(
        tick=0, width=50, height=50,
        cells={c.pos: c for c in cells},
        agents={},
    )


def test_siphon_restocked_to_scheduled_output() -> None:
    """The Siphon cell's drawable water AND siphon_units are both set to the scheduled output —
    this is what makes the central cell actually dispense (the bug the first runs exposed)."""
    sip = Cell(x=25, y=25, terrain="settlement", siphon=True, water=0, siphon_units=0)
    w = apply_environment(_world([sip]), tick=0, siphon_units=37)
    assert w.cells[(25, 25)].water == 37
    assert w.cells[(25, 25)].siphon_units == 37


def test_siphon_does_not_accumulate_across_ticks() -> None:
    """A re-stock is a hard SET, not an add: unused output is lost, so a camper cannot bank supply
    into a surplus (keeps the supply genuinely insufficient — World.md §3)."""
    sip = Cell(x=25, y=25, terrain="settlement", siphon=True, water=30, siphon_units=30)
    w = apply_environment(_world([sip]), tick=5, siphon_units=37)
    assert w.cells[(25, 25)].water == 37  # set to schedule, NOT 30+37


def test_siphon_none_leaves_it_untouched() -> None:
    """With siphon_units=None the Siphon is not modified (caller threads the schedule elsewhere)."""
    sip = Cell(x=25, y=25, terrain="settlement", siphon=True, water=12, siphon_units=12)
    w = apply_environment(_world([sip]), tick=0, siphon_units=None)
    assert w.cells[(25, 25)].water == 12
    assert w.cells[(25, 25)].siphon_units == 12


def test_oasis_regenerates_toward_cap() -> None:
    """A drained oasis tops up by the per-tick regen, never above the cap."""
    low = Cell(x=1, y=1, terrain="oasis", water=0)
    near = Cell(x=2, y=2, terrain="oasis", water=OASIS_WATER_CAP - 1)
    full = Cell(x=3, y=3, terrain="oasis", water=OASIS_WATER_CAP)
    w = apply_environment(_world([low, near, full]), tick=0, siphon_units=37)
    assert w.cells[(1, 1)].water == OASIS_REGEN_PER_TICK         # 0 -> regen
    assert w.cells[(2, 2)].water == OASIS_WATER_CAP              # clamped at cap, not cap-1+regen
    assert w.cells[(3, 3)].water == OASIS_WATER_CAP              # already full, unchanged


def test_non_oasis_non_siphon_cells_untouched() -> None:
    """Desert/mountain/ruins water is not produced by the env layer (only oases replenish)."""
    desert = Cell(x=5, y=5, terrain="desert", water=0)
    ruins = Cell(x=6, y=6, terrain="ruins", water=2)
    w = apply_environment(_world([desert, ruins]), tick=0, siphon_units=37)
    assert w.cells[(5, 5)].water == 0
    assert w.cells[(6, 6)].water == 2


def test_apply_environment_is_pure() -> None:
    """The input world is never mutated — a fresh world is returned (matches resolver purity)."""
    sip = Cell(x=25, y=25, terrain="settlement", siphon=True, water=0, siphon_units=0)
    oasis = Cell(x=1, y=1, terrain="oasis", water=0)
    src = _world([sip, oasis])
    _ = apply_environment(src, tick=0, siphon_units=37)
    assert src.cells[(25, 25)].water == 0   # original untouched
    assert src.cells[(1, 1)].water == 0
