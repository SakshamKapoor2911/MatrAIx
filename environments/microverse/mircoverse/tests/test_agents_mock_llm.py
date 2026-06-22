"""Tests for the MockLLM (mircoverse/agents/mock_llm.py).

The MockLLM exists so the reference agent is testable with NO API key. Its defining
property is determinism: same seed + same observation ⇒ identical decision. We also
check the legible policy branches and that decisions are contract-valid.
"""

from __future__ import annotations

from mircoverse.agents.mock_llm import MockLLM
from mircoverse.contracts import (
    ActionEnvelope,
    ActionType,
    Fov,
    FovAgent,
    FovCell,
    GlobalView,
    Observation,
    SelfView,
    SoulFile,
)
from mircoverse.contracts.observation import DeathCache


def make_obs(*, water: int = 30, cells=None, agents=None, self_pos=(24, 25),
             terrain: str = "desert") -> Observation:
    return Observation(
        tick=5,
        tick_ends_at="2026-05-30T12:00:30Z",
        **{"self": SelfView(agent_id="agent_07", pos=self_pos, water=water, food=10,
                            goods=2, on_terrain=terrain, stance="neutral")},
        fov=Fov(radius=2, cells=cells or [], agents=agents or []),
        **{"global": GlobalView(alive_count=21, storm_active=False, siphon_units_this_tick=37)},
        memory_index=[],
    )


def test_decide_is_deterministic_given_seed() -> None:
    """Same seed + same observation ⇒ identical action and importance, every run."""
    obs = make_obs(water=50, agents=[
        FovAgent(agent_id="agent_12", pos=(25, 26), stance="neutral", visible_water="low")
    ])
    d1 = MockLLM(seed=42).decide(obs)
    d2 = MockLLM(seed=42).decide(obs)
    assert d1.action.model_dump() == d2.action.model_dump()
    assert d1.importance == d2.importance


def test_decide_outputs_are_contract_valid() -> None:
    """Every decision wraps into a valid ActionEnvelope (frozen contract)."""
    cases = [
        make_obs(water=3),  # critical, no water visible -> blind move
        make_obs(water=3, self_pos=(25, 25), terrain="settlement",
                 cells=[FovCell(pos=(25, 25), terrain="settlement", water=37, siphon=True)]),
        make_obs(water=3, cells=[FovCell(pos=(26, 25), terrain="oasis", water=5)]),
        make_obs(water=30, self_pos=(24, 25),
                 cells=[FovCell(pos=(24, 25), terrain="ruins",
                                death_cache=DeathCache(water=9, food=3))]),
        make_obs(water=30, agents=[
            FovAgent(agent_id="a2", pos=(25, 25), stance="neutral", visible_water="low")]),
        make_obs(water=30),  # idle -> wait
    ]
    for obs in cases:
        d = MockLLM(seed=1).decide(obs)
        ActionEnvelope(tick=obs.tick, action=d.action, memory_update=d.memory_update)


def test_critical_water_on_water_cell_consumes() -> None:
    """Low water while standing on a water-bearing cell -> consume water (survival)."""
    obs = make_obs(water=3, self_pos=(25, 25), terrain="settlement",
                   cells=[FovCell(pos=(25, 25), terrain="settlement", water=37, siphon=True)])
    d = MockLLM(seed=1).decide(obs)
    assert d.action.type is ActionType.CONSUME
    assert d.action.params.resource == "water"


def test_death_cache_underfoot_scavenges() -> None:
    """An unlooted cache on the current cell -> scavenge, logged at high importance (P4)."""
    obs = make_obs(water=30, self_pos=(24, 25),
                   cells=[FovCell(pos=(24, 25), terrain="ruins",
                                  death_cache=DeathCache(water=9, food=3))])
    d = MockLLM(seed=1).decide(obs)
    assert d.action.type is ActionType.SCAVENGE
    assert d.memory_update is not None and d.memory_update.importance >= 7


def test_reflect_is_deterministic_and_mostly_non_revising() -> None:
    """reflect is deterministic per seed; with no moral marker it never revises."""
    soul = SoulFile(moral_boundaries=["I will not steal"])
    r1 = MockLLM(seed=9).reflect(soul, soul, ["Crossed the desert."])
    r2 = MockLLM(seed=9).reflect(soul, soul, ["Crossed the desert."])
    assert r1.revises_identity == r2.revises_identity
    assert r1.revises_identity is False  # no 'loot'/'cache' marker -> no revision
