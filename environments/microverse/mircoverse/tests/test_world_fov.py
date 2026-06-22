"""Unit tests for pure FOV computation (mircoverse.world.fov). No I/O — never skips."""

from __future__ import annotations

from mircoverse.contracts import Fov
from mircoverse.world.fov import compute_fov
from mircoverse.world.state import Agent, Cell, DeathCache, WorldState


def _world() -> WorldState:
    cells: dict[tuple[int, int], Cell] = {}
    for x in range(10):
        for y in range(10):
            cells[(x, y)] = Cell(x=x, y=y, terrain="desert")
    return WorldState(tick=0, width=10, height=10, cells=cells, agents={})


def test_compute_fov_5x5_window_and_clipping() -> None:
    w = _world()
    w.agents["a"] = Agent("a", (0, 0), water=50)  # corner ⇒ window clipped to grid
    fov = compute_fov(w, "a", radius=2)
    assert isinstance(fov, Fov)
    assert fov.radius == 2
    # corner agent: cells with x,y in {0,1,2} → 3x3 = 9 in-bounds cells of the 5x5 window
    assert len(fov.cells) == 9
    assert all(0 <= c.pos[0] <= 2 and 0 <= c.pos[1] <= 2 for c in fov.cells)


def test_compute_fov_sees_neighbors_coarse_water() -> None:
    w = _world()
    w.agents["a"] = Agent("a", (5, 5), water=50)
    w.agents["b"] = Agent("b", (6, 6), water=8, stance="aggressive")    # low band
    w.agents["c"] = Agent("c", (9, 9), water=50)                       # out of FOV
    fov = compute_fov(w, "a", radius=2)
    seen = {fa.agent_id: fa for fa in fov.agents}
    assert "b" in seen and "c" not in seen
    assert seen["b"].visible_water == "low"     # coarse, never exact
    assert seen["b"].stance == "aggressive"
    assert "a" not in seen                       # self excluded


def test_compute_fov_reports_death_cache_hint() -> None:
    w = _world()
    w.agents["a"] = Agent("a", (5, 5), water=50)
    w.cells[(5, 6)].death_cache = DeathCache(water=9, food=3, location_facts=[(1, 1), (2, 2)])
    fov = compute_fov(w, "a", radius=2)
    cache_cells = [c for c in fov.cells if c.death_cache is not None]
    assert len(cache_cells) == 1
    dc = cache_cells[0].death_cache
    assert dc is not None
    assert dc.water == 9 and dc.food == 3
    assert dc.locations_hint == 2  # count of droppable facts, not their values
