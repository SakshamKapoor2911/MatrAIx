"""Unit tests for the world generators (mircoverse.manifest.generators).

Verifies: both generators produce valid, in-bounds, deterministic worlds; same seed => identical
grid; different seed => different layout; the seed-run / scale shapes match Protocol.md §2.
"""

from __future__ import annotations

from mircoverse.manifest.generators import (
    gen_scale_world,
    gen_seed_world,
    generate_world,
    scale_manifest,
    seed_manifest,
)
from mircoverse.world.state import WorldState

VALID_TERRAIN = {"desert", "oasis", "mountain", "settlement", "ruins"}


def _assert_valid_world(w: WorldState, width: int, height: int, population: int) -> None:
    assert (w.width, w.height) == (width, height)
    assert w.tick == 0
    assert len(w.cells) == width * height
    # Every cell is in bounds with a legal terrain.
    for (x, y), cell in w.cells.items():
        assert w.in_bounds((x, y))
        assert cell.terrain in VALID_TERRAIN
    # Every agent is alive, in bounds, knows its spawn, and has positive water.
    assert len(w.agents) == population
    for a in w.agents.values():
        assert w.in_bounds(a.pos)
        assert a.alive and a.water > 0
        assert a.pos in a.known_locations


def test_seed_manifest_shape() -> None:
    m = seed_manifest()
    assert (m.grid.width, m.grid.height) == (50, 50)
    assert m.population == 25
    assert m.siphon.pos == (25, 25) and m.siphon.base_units == 37


def test_scale_manifest_shape() -> None:
    m = scale_manifest(n=1000)
    assert (m.grid.width, m.grid.height) == (200, 200)
    assert m.population == 1000
    assert m.siphon.base_units == 1500  # ~1.5 x population insufficiency ratio


def test_generate_world_places_siphon_at_settlement() -> None:
    w = generate_world(seed_manifest(seed=1))
    sc = w.cell((25, 25))
    assert sc is not None and sc.siphon and sc.terrain == "settlement"
    assert sc.siphon_units == 37  # units_at(0)


def test_generate_world_uses_per_arm_siphon_at_tick0() -> None:
    """REGRESSION (2026-06-06 tick-0 coupling bug): the t0 Siphon cell water/units must come from the
    manifest's OWN SiphonCurve, so per-arm scarcity is applied at generation — not hardcoded to the
    default 37. Before the fix the driver built the world via gen_seed_world(seed), which rebuilt the
    DEFAULT manifest (base_units=37), so control-arm agents saw 'siphon: 37' while the schedule said 80.
    """
    from mircoverse.manifest.schema import SiphonCurve

    for base in (80, 46, 23):
        m = seed_manifest(seed=1).model_copy(update={
            "siphon": SiphonCurve(pos=(25, 25), base_units=base),
        })
        w = generate_world(m)
        sc = w.cell((25, 25))
        assert sc is not None and sc.siphon
        assert sc.siphon_units == base, f"arm base={base}: cell.siphon_units={sc.siphon_units}"
        assert sc.water == base, f"arm base={base}: cell.water={sc.water} (t0 drawable must match)"


def test_manifest_carries_oasis_supply_bundle() -> None:
    """The oasis renewal knobs (the dominant keep-alive lever) are first-class manifest fields, so the
    whole water-supply bundle is seed-pinned + serializable, not a CLI-only constant (2026-06-06)."""
    m = seed_manifest(seed=1)
    assert hasattr(m, "oasis_regen") and hasattr(m, "oasis_cap")
    m2 = m.model_copy(update={"oasis_regen": 12, "oasis_cap": 55})
    assert (m2.oasis_regen, m2.oasis_cap) == (12, 55)


def test_gen_seed_world_is_valid_and_unequal_water() -> None:
    w = gen_seed_world(seed=0)
    _assert_valid_world(w, 50, 50, 25)
    waters = sorted(a.water for a in w.agents.values())
    # Deliberately unequal starting water: at least two low and a spread (Protocol.md §2.2).
    assert waters[0] <= 12
    assert max(waters) - min(waters) >= 20


def test_gen_seed_world_is_deterministic() -> None:
    a = gen_seed_world(seed=123)
    b = gen_seed_world(seed=123)
    assert {p: c.terrain for p, c in a.cells.items()} == {p: c.terrain for p, c in b.cells.items()}
    assert {aid: (ag.pos, ag.water) for aid, ag in a.agents.items()} == {
        aid: (ag.pos, ag.water) for aid, ag in b.agents.items()
    }


def test_different_seed_changes_grid() -> None:
    a = gen_seed_world(seed=1)
    b = gen_seed_world(seed=2)
    grid_a = {p: c.terrain for p, c in a.cells.items()}
    grid_b = {p: c.terrain for p, c in b.cells.items()}
    assert grid_a != grid_b


def test_gen_scale_world_is_valid_and_deterministic() -> None:
    a = gen_scale_world(n=1000, seed=9)
    _assert_valid_world(a, 200, 200, 1000)
    b = gen_scale_world(n=1000, seed=9)
    assert {aid: ag.pos for aid, ag in a.agents.items()} == {
        aid: ag.pos for aid, ag in b.agents.items()
    }
    # Spawn cells are distinct (no two agents share a cell).
    positions = [ag.pos for ag in a.agents.values()]
    assert len(set(positions)) == len(positions)
