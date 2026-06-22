"""The experiment manifest — the single config object that pins a run (Protocol.md §9, World.md §11).

A manifest is the reproducibility contract: RNG seed, grid, population, resource/terrain
distribution, the Siphon output curve, the pressure schedule, FOV radius, every action cost,
``base_drain``, measurement cadence N, the reflection threshold, the agent roster (each with an
immutable ``original_soul``), the narrative framing, and a schema version. Given the SAME manifest
+ the SAME agent actions, a run replays identically (World.md §11). Findings use deliberately
*varied* seeds (World.md §10.3); the seed pins replay, not the science.

These are Pydantic models (config crosses YAML <-> Python), distinct from the world-core's plain
dataclasses (``mircoverse.world.state``) and from the FROZEN wire contract (``mircoverse.contracts``).
The roster's ``original_soul`` reuses the frozen ``SoulFile`` so manifest and wire never diverge.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from mircoverse.contracts import SoulFile

SCHEMA_VERSION = "1.0"

Terrain = Literal["desert", "oasis", "mountain", "settlement", "ruins"]
NarrativeFraming = Literal["neutral", "scifi", "genre_loaded"]
PressurePreset = Literal["slow_squeeze", "sudden_collapse", "predators_eden", "abundance_null", "idle"]


class GridConfig(BaseModel):
    """Grid shape (Protocol.md §2.1). Integer coords ``0 <= x < width``, ``0 <= y < height``."""

    width: int = Field(50, gt=0)
    height: int = Field(50, gt=0)

    def in_bounds(self, pos: tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height


class TerrainDistribution(BaseModel):
    """How terrain is laid down on the grid (World.md §2). The generator fills the grid
    with ``base_terrain`` then carves the special features. Fractions are of total cells."""

    base_terrain: Terrain = "desert"
    oasis_fraction: float = Field(0.04, ge=0.0, le=1.0)
    mountain_fraction: float = Field(0.10, ge=0.0, le=1.0)
    ruins_fraction: float = Field(0.02, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _fractions_fit(self) -> "TerrainDistribution":
        total = self.oasis_fraction + self.mountain_fraction + self.ruins_fraction
        if total > 1.0:
            raise ValueError(f"terrain feature fractions sum to {total} > 1.0")
        return self


class ResourceDistribution(BaseModel):
    """Initial per-cell resource amounts and the deliberately-unequal starting water for agents
    (Protocol.md §2.2: 'starting state is deliberately unequal to force early negotiation')."""

    # Per-cell standing resources, sampled per matching cell.
    oasis_water_range: tuple[int, int] = (20, 40)
    cell_food_range: tuple[int, int] = (0, 5)
    cell_goods_range: tuple[int, int] = (0, 3)
    # Agent starting reserves. Most agents comfortable; a few start critically low.
    start_water_range: tuple[int, int] = (40, 60)
    start_food_range: tuple[int, int] = (8, 16)
    start_goods_range: tuple[int, int] = (0, 6)
    critical_water_count: int = Field(2, ge=0)  # agents that start critically low
    critical_water_range: tuple[int, int] = (5, 12)

    @model_validator(mode="after")
    def _ranges_ordered(self) -> "ResourceDistribution":
        for name in (
            "oasis_water_range",
            "cell_food_range",
            "cell_goods_range",
            "start_water_range",
            "start_food_range",
            "start_goods_range",
            "critical_water_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name} is inverted: {lo} > {hi}")
        return self


class SiphonCurve(BaseModel):
    """The Siphon output over time (Protocol.md §2.3, §8). Output is deliberately insufficient.

    ``base_units`` is the tick-0 output. ``decay_per_tick`` linearly erodes it (Slow Squeeze).
    ``shock_tick``/``shock_units`` apply a sudden cut at a fixed tick (Sudden Collapse). The
    actual schedule is evaluated by ``siphon_units_at`` so the curve is data, not code."""

    pos: tuple[int, int] = (25, 25)
    base_units: int = Field(37, ge=0)  # ~1.5 x 25-agent population (Protocol.md §2.3)
    decay_per_tick: float = Field(0.0, ge=0.0)
    shock_tick: Optional[int] = None
    shock_units: Optional[int] = None
    floor_units: int = Field(0, ge=0)

    def units_at(self, tick: int) -> int:
        """Siphon water units made available at ``tick`` (pure; physics only, never fairness)."""
        units = float(self.base_units) - self.decay_per_tick * max(0, tick)
        if self.shock_tick is not None and tick >= self.shock_tick and self.shock_units is not None:
            units = min(units, float(self.shock_units))
        return max(self.floor_units, int(units))


class PressureSchedule(BaseModel):
    """The independent variable (Protocol.md §8, World.md §8). A named preset plus the hazard
    parameters it activates. Controls (abundance_null, idle) disable hazards/scarcity."""

    preset: PressurePreset = "slow_squeeze"
    heat_cycle_period: int = Field(180, gt=0)  # ticks (Protocol.md §2.5)
    heat_zone_damage: int = Field(3, ge=0)
    storm_onset_prob: float = Field(0.1, ge=0.0, le=1.0)
    storm_duration: int = Field(20, ge=0)
    storm_noise_pct: float = Field(0.2, ge=0.0, le=1.0)


class ActionCosts(BaseModel):
    """Per-action water cost in WHOLE units (Protocol.md §4.1). Stored as floats because
    ``signal`` costs 0.5; the world core keeps these as tenths internally."""

    move: float = 0.0  # terrain-dependent; added by the mover
    wait: float = 0.0
    consume: float = 0.0
    scavenge: float = 3.0
    trade: float = 1.0
    talk: float = 1.0
    attack: float = 2.0
    signal: float = 0.5


class AgentSpec(BaseModel):
    """One roster entry. ``original_soul`` is immutable after registration (Architecture.md
    trigger); ``current_identity`` starts as a copy and is the drift target (Protocol.md §7.1)."""

    agent_id: str
    name: str
    original_soul: SoulFile = Field(default_factory=SoulFile)


class ExperimentManifest(BaseModel):
    """The full run specification (Protocol.md §9). Everything stochastic flows from ``seed``."""

    schema_version: str = SCHEMA_VERSION
    seed: int = 0
    narrative_framing: NarrativeFraming = "neutral"  # neutral default (Protocol.md §2.6)

    grid: GridConfig = Field(default_factory=GridConfig)
    population: int = Field(25, gt=0)

    terrain: TerrainDistribution = Field(default_factory=TerrainDistribution)
    resources: ResourceDistribution = Field(default_factory=ResourceDistribution)
    siphon: SiphonCurve = Field(default_factory=SiphonCurve)
    pressure: PressureSchedule = Field(default_factory=PressureSchedule)

    # Oasis water supply (the DISTRIBUTED, multi-drinker renewal — the dominant survival lever, vs the
    # single-occupancy Siphon which serves at most one agent/tick). Pinned in the manifest so the whole
    # water-supply bundle (Siphon curve + oasis renewal) is part of the reproducibility contract and is
    # serialized into every run artifact, not a CLI-only knob. Defaults mirror environment.py.
    oasis_regen: int = Field(4, ge=0)   # per-oasis water added per tick (capped by oasis_cap)
    oasis_cap: int = Field(40, ge=0)    # per-oasis standing-water ceiling

    fov_radius: int = Field(2, ge=0)
    action_costs: ActionCosts = Field(default_factory=ActionCosts)
    base_drain: int = Field(1, ge=0)

    measurement_cadence_n: int = Field(10, gt=0)  # engine snapshot every N ticks (Protocol.md §2.6)
    reflection_threshold: int = Field(150, gt=0)  # Joon's importance threshold (Protocol.md §6.3)

    roster: list[AgentSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> "ExperimentManifest":
        if self.roster:
            ids = [a.agent_id for a in self.roster]
            if len(set(ids)) != len(ids):
                raise ValueError("roster has duplicate agent_id values")
            if len(self.roster) != self.population:
                raise ValueError(
                    f"population={self.population} but roster has {len(self.roster)} agents"
                )
        if not self.grid.in_bounds(self.siphon.pos):
            raise ValueError(f"siphon pos {self.siphon.pos} is outside the grid")
        return self
