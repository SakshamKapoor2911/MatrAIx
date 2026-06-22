"""World generators: build an initial ``WorldState`` (world core) from a manifest + seeded RNG.

PURE + SEEDED (World.md §11): identical seed => byte-identical world. All randomness flows through
the single ``random.Random`` built by ``seeded_rng(manifest)``; nothing here touches ``time`` or a
global RNG. The output is the world-core ``WorldState`` (plain dataclasses, no I/O) that the
resolution layer then drives tick by tick.

Two convenience constructors match the seed-run defaults:
  * ``gen_seed_world()``  — 50x50, 25 agents, Siphon at (25,25), unequal starting water.
  * ``gen_scale_world(n)`` — 200x200, ``n`` (default 1000) agents, same rules at scale.
Both delegate to ``generate_world(manifest)`` so the generation logic is single-sourced.
"""

from __future__ import annotations

import random

from mircoverse.manifest.loader import seeded_rng
from mircoverse.manifest.schema import (
    ExperimentManifest,
    GridConfig,
    PressureSchedule,
    ResourceDistribution,
    SiphonCurve,
)
from mircoverse.world.state import Agent, Cell, WorldState


def _rand_int(rng: random.Random, span: tuple[int, int]) -> int:
    lo, hi = span
    return rng.randint(lo, hi)


def _carve_terrain(
    manifest: ExperimentManifest, rng: random.Random
) -> dict[tuple[int, int], Cell]:
    """Lay the base terrain, then carve oases/mountains/ruins and place the Siphon cell.

    Cells are visited in a fixed (x, y) raster order and feature positions are drawn from a sorted
    candidate pool with the seeded RNG, so terrain layout is fully determined by the seed.
    """
    g: GridConfig = manifest.grid
    td = manifest.terrain
    cells: dict[tuple[int, int], Cell] = {}
    for x in range(g.width):
        for y in range(g.height):
            cells[(x, y)] = Cell(x=x, y=y, terrain=td.base_terrain)

    siphon_pos = manifest.siphon.pos
    total = g.width * g.height
    # Candidate cells exclude the Settlement (Siphon) cell so it is never overwritten.
    candidates = [pos for pos in cells if pos != siphon_pos]
    candidates.sort()  # deterministic order before the seeded shuffle
    rng.shuffle(candidates)

    n_oasis = int(total * td.oasis_fraction)
    n_mountain = int(total * td.mountain_fraction)
    n_ruins = int(total * td.ruins_fraction)

    idx = 0
    for _ in range(n_oasis):
        if idx >= len(candidates):
            break
        cells[candidates[idx]].terrain = "oasis"
        idx += 1
    for _ in range(n_mountain):
        if idx >= len(candidates):
            break
        cells[candidates[idx]].terrain = "mountain"
        idx += 1
    for _ in range(n_ruins):
        if idx >= len(candidates):
            break
        cells[candidates[idx]].terrain = "ruins"
        idx += 1

    # The Settlement cell holds the Siphon (Protocol.md §2.3). It starts the run with its tick-0
    # output ALREADY on the cell as drawable water — the per-tick re-stock (apply_environment) keeps
    # it topped to the schedule thereafter. Without this the Siphon would be dry on tick 0 and only
    # come alive once a tick had resolved.
    siphon_cell = cells[siphon_pos]
    siphon_cell.terrain = "settlement"
    siphon_cell.siphon = True
    siphon_cell.siphon_units = manifest.siphon.units_at(0)
    siphon_cell.water = manifest.siphon.units_at(0)
    return cells


def _stock_resources(
    cells: dict[tuple[int, int], Cell],
    res: ResourceDistribution,
    rng: random.Random,
) -> None:
    """Stock standing per-cell resources. Oases hold water; all cells may hold a little food/goods.

    Cells are visited in sorted order so the RNG draw sequence is deterministic across runs.
    """
    for pos in sorted(cells):
        c = cells[pos]
        if c.terrain == "oasis":
            c.water = _rand_int(rng, res.oasis_water_range)
        c.food = _rand_int(rng, res.cell_food_range)
        c.goods = _rand_int(rng, res.cell_goods_range)


def _place_agents(
    manifest: ExperimentManifest, rng: random.Random
) -> dict[str, Agent]:
    """Spawn the roster (or synthetic ``agent_NNN`` ids) on distinct in-bounds cells with
    deliberately-unequal starting water (Protocol.md §2.2). A few agents start critically low."""
    g = manifest.grid
    res = manifest.resources
    n = manifest.population

    if manifest.roster:
        ids = [spec.agent_id for spec in manifest.roster]
    else:
        width = max(3, len(str(n - 1)))
        ids = [f"agent_{i:0{width}d}" for i in range(n)]

    all_cells = [(x, y) for x in range(g.width) for y in range(g.height)]
    all_cells.sort()
    rng.shuffle(all_cells)
    spawn_cells = all_cells[:n]

    # Which agents start critically low: a fixed seeded sample of indices.
    crit_count = min(res.critical_water_count, n)
    crit_idx = set(rng.sample(range(n), crit_count)) if crit_count else set()

    agents: dict[str, Agent] = {}
    for i, aid in enumerate(ids):
        pos = spawn_cells[i]
        if i in crit_idx:
            water = _rand_int(rng, res.critical_water_range)
        else:
            water = _rand_int(rng, res.start_water_range)
        agents[aid] = Agent(
            agent_id=aid,
            pos=pos,
            water=water,
            food=_rand_int(rng, res.start_food_range),
            goods=_rand_int(rng, res.start_goods_range),
            stance="neutral",
            alive=True,
            known_locations={pos},  # an agent begins knowing only its spawn cell (Protocol.md §4.3)
        )
    return agents


def generate_world(
    manifest: ExperimentManifest, rng: random.Random | None = None
) -> WorldState:
    """Build the initial ``WorldState`` for a run. Pure + seeded (World.md §11).

    If ``rng`` is omitted, the single seeded RNG is built from ``manifest.seed``. Identical seed =>
    identical world. The RNG draw order (terrain, then resources, then agents) is fixed so adding a
    later stage never perturbs an earlier stage's stream.
    """
    if rng is None:
        rng = seeded_rng(manifest)
    cells = _carve_terrain(manifest, rng)
    _stock_resources(cells, manifest.resources, rng)
    agents = _place_agents(manifest, rng)
    return WorldState(
        tick=0,
        width=manifest.grid.width,
        height=manifest.grid.height,
        cells=cells,
        agents=agents,
        base_drain=manifest.base_drain,
    )


def seed_manifest(seed: int = 0) -> ExperimentManifest:
    """The 25-agent / 50x50 seed-run manifest (Protocol.md §2, §8 Slow Squeeze default)."""
    return ExperimentManifest(
        seed=seed,
        narrative_framing="neutral",
        grid=GridConfig(width=50, height=50),
        population=25,
        siphon=SiphonCurve(pos=(25, 25), base_units=37),
        pressure=PressureSchedule(preset="slow_squeeze"),
    )


def scale_manifest(n: int = 1000, seed: int = 0) -> ExperimentManifest:
    """The scale-test manifest: 200x200 / ``n`` agents (BUILD_SPEC manifest deliverable).

    Siphon output scales to ~1.5x population to keep the same insufficiency ratio (Protocol.md §2.3).
    """
    return ExperimentManifest(
        seed=seed,
        narrative_framing="neutral",
        grid=GridConfig(width=200, height=200),
        population=n,
        siphon=SiphonCurve(pos=(100, 100), base_units=int(1.5 * n)),
        pressure=PressureSchedule(preset="slow_squeeze"),
        resources=ResourceDistribution(critical_water_count=max(2, n // 50)),
    )


def gen_seed_world(seed: int = 0) -> WorldState:
    """Generate the seed-run world: 50x50, 25 agents, Siphon at (25,25), unequal starting water.

    Pure + seeded: ``gen_seed_world(s)`` == ``gen_seed_world(s)`` for any ``s`` (World.md §11).
    """
    return generate_world(seed_manifest(seed))


def gen_scale_world(n: int = 1000, seed: int = 0) -> WorldState:
    """Generate the scale world: 200x200 with ``n`` agents (default 1000). Pure + seeded."""
    return generate_world(scale_manifest(n=n, seed=seed))
