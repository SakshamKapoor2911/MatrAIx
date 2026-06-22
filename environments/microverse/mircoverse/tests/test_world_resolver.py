"""Unit tests for the pure 8-action tick resolver (mircoverse.world.resolver).

Covers every action (move/wait/consume/scavenge/trade/talk/attack/signal), death + death-cache,
movement contention, and the determinism guarantee (same seed+actions ⇒ identical state).
No I/O, no DB — these never skip.
"""

from __future__ import annotations

import random

from mircoverse.contracts import (
    Action,
    ActionEnvelope,
    ActionType,
    AttackParams,
    ConsumeParams,
    MoveParams,
    SignalParams,
    TalkParams,
    TradeParams,
)
from mircoverse.world.resolver import resolve_tick
from mircoverse.world.state import Agent, Cell, DeathCache, WorldState


# ── builders ──────────────────────────────────────────────────────────────────────


def make_world(
    agents: list[Agent],
    *,
    width: int = 10,
    height: int = 10,
    terrain: str = "desert",
    tick: int = 0,
    base_drain: int = 1,
) -> WorldState:
    cells: dict[tuple[int, int], Cell] = {}
    for x in range(width):
        for y in range(height):
            cells[(x, y)] = Cell(x=x, y=y, terrain=terrain)  # type: ignore[arg-type]
    return WorldState(
        tick=tick,
        width=width,
        height=height,
        cells=cells,
        agents={a.agent_id: a for a in agents},
        base_drain=base_drain,
    )


def env(tick: int, action: Action) -> ActionEnvelope:
    return ActionEnvelope(tick=tick, action=action)


def rng() -> random.Random:
    return random.Random(12345)


# ── move ────────────────────────────────────────────────────────────────────────


def test_move_directional() -> None:
    a = Agent("a", (5, 5), water=50, known_locations={(5, 5)})
    w = make_world([a])
    acts = {"a": env(0, Action(type=ActionType.MOVE, params=MoveParams(direction="N")))}
    nw, res = resolve_tick(w, acts, rng())
    assert nw.agents["a"].pos == (5, 6)
    assert res["a"].status == "ok"
    assert (5, 6) in nw.agents["a"].known_locations


def test_move_toward_unknown_and_unseen_rejected() -> None:
    """A goal neither known nor within view is still rejected — fog of war holds for the
    genuine-hallucination case. (9,9) is Chebyshev distance 4 from (5,5), beyond FOV radius 2."""
    a = Agent("a", (5, 5), water=50, known_locations={(5, 5)})
    w = make_world([a])
    acts = {"a": env(0, Action(type=ActionType.MOVE, params=MoveParams(toward=(9, 9))))}
    nw, res = resolve_tick(w, acts, rng())
    assert nw.agents["a"].pos == (5, 5)  # stayed put
    assert res["a"].status == "rejected"
    assert "view" in res["a"].note  # message names the known-OR-visible rule


def test_move_toward_visible_but_unknown_now_allowed() -> None:
    """A goal the agent can SEE (within FOV radius) but has never stood on is now a legal goal:
    the model conflating 'I see it' with 'I may path to it' was a contract artifact, not a
    hallucination (first 25×20 run finding). The agent steps one cell toward it and LEARNS it."""
    a = Agent("a", (5, 5), water=50, known_locations={(5, 5)})  # (7,7) NOT known
    w = make_world([a])
    # (7,7) is Chebyshev distance 2 from (5,5) = within view, but not in known_locations.
    acts = {"a": env(0, Action(type=ActionType.MOVE, params=MoveParams(toward=(7, 7))))}
    nw, res = resolve_tick(w, acts, rng())
    assert res["a"].status == "ok"
    assert nw.agents["a"].pos == (6, 6)  # one Moore step toward the visible goal
    assert (7, 7) in nw.agents["a"].known_locations  # seeing-to-path = learning the goal
    assert (6, 6) in nw.agents["a"].known_locations  # and the cell actually entered


def test_move_toward_visible_goal_just_outside_radius_rejected() -> None:
    """Boundary: a goal one cell beyond FOV radius (distance 3) is neither known nor visible,
    so it is rejected — the known-OR-visible gate is exactly the FOV predicate, no looser."""
    a = Agent("a", (5, 5), water=50, known_locations={(5, 5)})
    w = make_world([a])
    acts = {"a": env(0, Action(type=ActionType.MOVE, params=MoveParams(toward=(8, 8))))}  # dist 3
    nw, res = resolve_tick(w, acts, rng())
    assert res["a"].status == "rejected"
    assert nw.agents["a"].pos == (5, 5)


# ── wait ──────────────────────────────────────────────────────────────────────────


def test_wait_default_when_no_action() -> None:
    a = Agent("a", (5, 5), water=50)
    w = make_world([a])
    nw, res = resolve_tick(w, {}, rng())  # no envelope submitted
    assert res["a"].action == "wait"
    assert res["a"].status == "defaulted"
    # desert: base_drain 1 + terrain 2 = 3 water lost, wait has no action cost.
    assert nw.agents["a"].water == 47


# ── consume ───────────────────────────────────────────────────────────────────────


def test_consume_from_cell() -> None:
    a = Agent("a", (5, 5), water=10)
    w = make_world([a])
    w.cells[(5, 5)].water = 20
    acts = {"a": env(0, Action(type=ActionType.CONSUME,
                               params=ConsumeParams(resource="water", amount=8)))}
    nw, res = resolve_tick(w, acts, rng())
    # +8 consumed, then -3 drain (desert) = 10 + 8 - 3 = 15
    assert nw.agents["a"].water == 15
    assert nw.cells[(5, 5)].water == 12
    assert res["a"].status == "ok"


# ── scavenge ──────────────────────────────────────────────────────────────────────


def test_scavenge_loots_death_cache() -> None:
    a = Agent("a", (5, 5), water=20)
    w = make_world([a], terrain="ruins")
    w.cells[(5, 5)].death_cache = DeathCache(water=9, food=3, location_facts=[(1, 1)])
    acts = {"a": env(0, Action(type=ActionType.SCAVENGE))}
    nw, res = resolve_tick(w, acts, rng())
    # +9 water from cache, then -(base 1 + ruins 1)=2 drain and -3 scavenge cost = 20+9-2-3=24
    assert nw.agents["a"].water == 24
    assert nw.agents["a"].food == 3 - 1  # +3 cache, -1 ruins food cost
    assert nw.cells[(5, 5)].death_cache is None
    assert (1, 1) in nw.agents["a"].known_locations
    assert res["a"].status == "ok"


# ── trade ─────────────────────────────────────────────────────────────────────────


def test_trade_two_tick_handshake_completes() -> None:
    a = Agent("a", (5, 5), water=50, goods=5)
    b = Agent("b", (5, 6), water=50, goods=0, food=10)
    w = make_world([a, b])
    acts = {
        "a": env(0, Action(type=ActionType.TRADE,
                           params=TradeParams(target="b", offer={"goods": 3}, request={"food": 2}))),
        "b": env(0, Action(type=ActionType.TRADE,
                           params=TradeParams(target="a", offer={"food": 2}, request={"goods": 3}))),
    }
    nw, res = resolve_tick(w, acts, rng())
    assert res["a"].status == "ok"
    assert res["b"].status == "ok"
    # a: goods 5-3=2; food 0+2(traded)-1(desert food drain)=1
    assert nw.agents["a"].goods == 2 and nw.agents["a"].food == 1
    # b: goods 0+3=3; food 10-2(traded)-1(desert food drain)=7
    assert nw.agents["b"].goods == 3 and nw.agents["b"].food == 7


def test_trade_one_sided_fails() -> None:
    a = Agent("a", (5, 5), water=50, goods=5)
    b = Agent("b", (5, 6), water=50)
    w = make_world([a, b])
    acts = {
        "a": env(0, Action(type=ActionType.TRADE,
                           params=TradeParams(target="b", offer={"goods": 3}, request={"food": 2}))),
        "b": env(0, Action(type=ActionType.WAIT)),
    }
    nw, res = resolve_tick(w, acts, rng())
    assert res["a"].status == "failed"
    assert nw.agents["a"].goods == 5  # no transfer


# ── talk ──────────────────────────────────────────────────────────────────────────


def test_talk_latency_delivers_next_tick() -> None:
    a = Agent("a", (5, 5), water=50)
    b = Agent("b", (5, 6), water=50)
    w = make_world([a, b])
    acts = {
        "a": env(0, Action(type=ActionType.TALK,
                           params=TalkParams(target="b", message="water at (1,1)",
                                             location_claim=(1, 1)))),
        "b": env(0, Action(type=ActionType.WAIT)),
    }
    nw, res = resolve_tick(w, acts, rng())
    assert res["a"].status == "ok"
    # Not delivered this tick; queued for next tick's inbox.
    assert "b" in nw.inbox and len(nw.inbox["b"]) == 1
    assert nw.inbox["b"][0].message == "water at (1,1)"
    # location_claim entered recipient's known set on routing (truth re-validated on use).
    assert (1, 1) in nw.agents["b"].known_locations


# ── attack ────────────────────────────────────────────────────────────────────────


def test_attack_seeded_outcome_transfers_water() -> None:
    a = Agent("a", (5, 5), water=90)   # strong attacker → high p(success)
    b = Agent("b", (5, 6), water=10)
    w = make_world([a, b])
    acts = {
        "a": env(0, Action(type=ActionType.ATTACK, params=AttackParams(target="b"))),
        "b": env(0, Action(type=ActionType.WAIT)),
    }
    r = random.Random(1)  # roll low → success given p≈0.9
    nw, res = resolve_tick(w, acts, r)
    assert res["a"].status == "ok"
    assert res["a"].detail["water_taken"] >= 1
    assert nw.agents["b"].water < 10  # target lost water (before its own drain)


def test_attack_non_adjacent_fails() -> None:
    a = Agent("a", (5, 5), water=90)
    b = Agent("b", (9, 9), water=10)
    w = make_world([a, b])
    acts = {"a": env(0, Action(type=ActionType.ATTACK, params=AttackParams(target="b")))}
    nw, res = resolve_tick(w, acts, rng())
    assert res["a"].status == "failed"
    assert "not adjacent" in res["a"].note


# ── signal ────────────────────────────────────────────────────────────────────────


def test_signal_sets_stance() -> None:
    a = Agent("a", (5, 5), water=50, stance="neutral")
    w = make_world([a])
    acts = {"a": env(0, Action(type=ActionType.SIGNAL, params=SignalParams(stance="aggressive")))}
    nw, res = resolve_tick(w, acts, rng())
    assert nw.agents["a"].stance == "aggressive"
    assert res["a"].status == "ok"


# ── death + death-cache ─────────────────────────────────────────────────────────────


def test_death_creates_cache_and_ruins() -> None:
    a = Agent("a", (5, 5), water=2, food=4, goods=1, known_locations={(5, 5), (1, 1), (2, 2), (3, 3)})
    w = make_world([a])  # desert drain 3 ⇒ water 2-3 = -1 ⇒ death
    nw, res = resolve_tick(w, {"a": env(0, Action(type=ActionType.WAIT))}, rng())
    assert nw.agents["a"].alive is False
    assert nw.agents["a"].death_tick == nw.tick - 1 or nw.agents["a"].death_tick is not None
    cell = nw.cells[(5, 5)]
    assert cell.terrain == "ruins"
    assert cell.death_cache is not None
    # food 4 - 1 (desert food drain applied this tick) = 3 enters the cache; goods 1 unchanged
    assert cell.death_cache.food == 3 and cell.death_cache.goods == 1
    # droppable fragment: up to 3 known locations
    assert len(cell.death_cache.location_facts) == 3
    assert res["a"].detail.get("died") is True


# ── contention ──────────────────────────────────────────────────────────────────────


def test_movement_contention_single_winner() -> None:
    # Two agents both try to enter the same empty cell (6,5) from opposite sides.
    a = Agent("a", (5, 5), water=50, known_locations={(5, 5), (6, 5)})
    b = Agent("b", (7, 5), water=50, known_locations={(7, 5), (6, 5)})
    w = make_world([a, b])
    acts = {
        "a": env(0, Action(type=ActionType.MOVE, params=MoveParams(toward=(6, 5)))),
        "b": env(0, Action(type=ActionType.MOVE, params=MoveParams(toward=(6, 5)))),
    }
    nw, res = resolve_tick(w, acts, rng())
    winners = [aid for aid in ("a", "b") if nw.agents[aid].pos == (6, 5)]
    assert len(winners) == 1  # exactly one occupies the contested cell
    loser = "b" if winners[0] == "a" else "a"
    assert res[loser].status == "failed"
    assert nw.agents[loser].pos in {(5, 5), (7, 5)}


# ── determinism ─────────────────────────────────────────────────────────────────────


def _scenario() -> tuple[WorldState, dict[str, ActionEnvelope]]:
    a = Agent("a", (5, 5), water=80, known_locations={(5, 5), (6, 5)})
    b = Agent("b", (5, 6), water=20)
    c = Agent("c", (7, 5), water=60, known_locations={(7, 5), (6, 5)})
    w = make_world([a, b, c])
    acts = {
        "a": env(0, Action(type=ActionType.ATTACK, params=AttackParams(target="b"))),
        "b": env(0, Action(type=ActionType.SIGNAL, params=SignalParams(stance="friendly"))),
        "c": env(0, Action(type=ActionType.MOVE, params=MoveParams(toward=(6, 5)))),
    }
    return w, acts


def test_determinism_same_seed_identical_state() -> None:
    w1, a1 = _scenario()
    w2, a2 = _scenario()
    nw1, r1 = resolve_tick(w1, a1, random.Random(777))
    nw2, r2 = resolve_tick(w2, a2, random.Random(777))
    for aid in ("a", "b", "c"):
        assert nw1.agents[aid].pos == nw2.agents[aid].pos
        assert nw1.agents[aid].water == nw2.agents[aid].water
        assert nw1.agents[aid].alive == nw2.agents[aid].alive
        assert r1[aid].status == r2[aid].status
        assert r1[aid].detail == r2[aid].detail


def test_purity_input_world_unmutated() -> None:
    w, acts = _scenario()
    pos_before = w.agents["c"].pos
    water_before = w.agents["a"].water
    resolve_tick(w, acts, random.Random(1))
    assert w.agents["c"].pos == pos_before   # input world untouched
    assert w.agents["a"].water == water_before
    assert w.tick == 0
