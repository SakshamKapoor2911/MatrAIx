"""Unit tests for the manifest schema (mircoverse.manifest.schema).

Pure, no I/O. One test per function/behaviour: field defaults, the SiphonCurve.units_at curve,
GridConfig.in_bounds, and the cross-field validators.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mircoverse.contracts import SoulFile
from mircoverse.manifest.schema import (
    SCHEMA_VERSION,
    AgentSpec,
    ExperimentManifest,
    GridConfig,
    SiphonCurve,
    TerrainDistribution,
)


def test_manifest_defaults_match_seed_run() -> None:
    m = ExperimentManifest()
    assert m.schema_version == SCHEMA_VERSION
    assert m.narrative_framing == "neutral"  # Protocol.md §2.6 neutral default
    assert (m.grid.width, m.grid.height) == (50, 50)
    assert m.population == 25
    assert m.fov_radius == 2
    assert m.base_drain == 1
    assert m.measurement_cadence_n == 10
    assert m.reflection_threshold == 150
    assert m.action_costs.signal == 0.5 and m.action_costs.scavenge == 3.0


def test_grid_in_bounds() -> None:
    g = GridConfig(width=50, height=50)
    assert g.in_bounds((0, 0)) and g.in_bounds((49, 49))
    assert not g.in_bounds((50, 0)) and not g.in_bounds((-1, 0))


def test_siphon_units_at_curve() -> None:
    # Flat curve.
    s = SiphonCurve(base_units=37)
    assert s.units_at(0) == 37 and s.units_at(100) == 37
    # Linear decay (Slow Squeeze) with a floor.
    d = SiphonCurve(base_units=37, decay_per_tick=1.0, floor_units=5)
    assert d.units_at(0) == 37 and d.units_at(10) == 27 and d.units_at(1000) == 5
    # Sudden shock cut at a fixed tick (Sudden Collapse).
    sk = SiphonCurve(base_units=37, shock_tick=50, shock_units=8)
    assert sk.units_at(49) == 37 and sk.units_at(50) == 8 and sk.units_at(200) == 8


def test_terrain_distribution_rejects_oversized_fractions() -> None:
    with pytest.raises(ValidationError):
        TerrainDistribution(oasis_fraction=0.6, mountain_fraction=0.6)


def test_manifest_roster_population_consistency() -> None:
    soul = SoulFile(core_values=["x"])
    roster = [AgentSpec(agent_id="agent_0", name="A", original_soul=soul)]
    # population must equal roster length when a roster is supplied.
    with pytest.raises(ValidationError):
        ExperimentManifest(population=5, roster=roster)
    ok = ExperimentManifest(population=1, roster=roster)
    assert ok.roster[0].agent_id == "agent_0"


def test_manifest_rejects_offgrid_siphon() -> None:
    with pytest.raises(ValidationError):
        ExperimentManifest(grid=GridConfig(width=10, height=10), siphon=SiphonCurve(pos=(25, 25)))
