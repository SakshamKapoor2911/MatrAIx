"""Unit tests for the world-core dataclasses + copy_world (mircoverse.world.state)."""

from __future__ import annotations

from mircoverse.world.state import (
    ACTION_WATER_COST_TENTHS,
    TERRAIN_FOOD_COST,
    TERRAIN_WATER_COST,
    Agent,
    Cell,
    DeathCache,
    WorldState,
    copy_world,
)


def _world() -> WorldState:
    cells = {(x, y): Cell(x=x, y=y, terrain="desert") for x in range(3) for y in range(3)}
    cells[(1, 1)].death_cache = DeathCache(water=5, location_facts=[(0, 0)])
    agents = {"a": Agent("a", (0, 0), water=50, known_locations={(0, 0)})}
    return WorldState(tick=3, width=3, height=3, cells=cells, agents=agents)


def test_cost_tables_match_spec() -> None:
    # Protocol.md §2.2 / §4.1 seed-run values.
    assert TERRAIN_WATER_COST == {"desert": 2, "mountain": 1, "oasis": 0, "settlement": 0, "ruins": 1}
    assert TERRAIN_FOOD_COST == {"desert": 1, "mountain": 2, "oasis": 0, "settlement": 0, "ruins": 1}
    assert ACTION_WATER_COST_TENTHS["scavenge"] == 30   # 3.0 water
    assert ACTION_WATER_COST_TENTHS["signal"] == 5      # 0.5 water


def test_cell_pos_and_bounds() -> None:
    w = _world()
    assert w.cell((1, 1)).pos == (1, 1)
    assert w.in_bounds((2, 2)) is True
    assert w.in_bounds((3, 0)) is False
    assert w.in_bounds((-1, 0)) is False


def test_live_agents_and_alive_count() -> None:
    w = _world()
    w.agents["dead"] = Agent("dead", (2, 2), water=0, alive=False)
    assert w.alive_count() == 1
    assert set(w.live_agents()) == {"a"}


def test_copy_world_is_deep_for_mutables() -> None:
    w = _world()
    c = copy_world(w)
    # mutate the copy; original must be untouched (purity precondition for the resolver)
    c.agents["a"].water = 999
    c.agents["a"].known_locations.add((9, 9))
    c.cells[(1, 1)].death_cache.water = 999
    c.cells[(1, 1)].death_cache.location_facts.append((8, 8))
    assert w.agents["a"].water == 50
    assert (9, 9) not in w.agents["a"].known_locations
    assert w.cells[(1, 1)].death_cache.water == 5
    assert w.cells[(1, 1)].death_cache.location_facts == [(0, 0)]
