"""Tests for the mock load-test agent (mircoverse/agents/mock_agent.py).

The defining property: for ANY observation, the mock emits an envelope the FROZEN
contract accepts. We validate by round-tripping through the Pydantic models.
"""

from __future__ import annotations

import random

import httpx
import pytest

from mircoverse.agents import mock_agent
from mircoverse.agents.mock_agent import (
    MockAgent,
    build_envelope,
    choose_action,
    _seconds_until,
)
from mircoverse.contracts import (
    ActionEnvelope,
    Fov,
    FovAgent,
    FovCell,
    GlobalView,
    InboxMessage,
    Observation,
    SelfView,
)


def make_obs(
    *,
    tick: int = 5,
    water: int = 30,
    food: int = 10,
    goods: int = 2,
    with_neighbours: bool = True,
    with_cells: bool = True,
) -> Observation:
    agents = (
        [FovAgent(agent_id="agent_12", pos=(25, 26), stance="aggressive", visible_water="low")]
        if with_neighbours
        else []
    )
    cells = (
        [
            FovCell(pos=(25, 25), terrain="settlement", water=37, siphon=True),
            FovCell(pos=(24, 25), terrain="desert"),
        ]
        if with_cells
        else []
    )
    return Observation(
        tick=tick,
        tick_ends_at="2026-05-30T12:00:30Z",
        **{"self": SelfView(
            agent_id="agent_07", pos=(24, 25), water=water, food=food, goods=goods,
            on_terrain="desert", stance="neutral",
        )},
        fov=Fov(radius=2, cells=cells, agents=agents),
        **{"global": GlobalView(alive_count=21, storm_active=False, siphon_units_this_tick=37)},
        inbox=[InboxMessage(**{"from": "agent_03"}, tick=tick - 1, message="hi")],
        memory_index=[],
    )


@pytest.mark.parametrize("seed", range(50))
def test_choose_action_always_contract_valid(seed: int) -> None:
    """Across many seeds and varied observations, every chosen action is a valid
    contract Action (constructed via the frozen validators) and re-validates."""
    rng = random.Random(seed)
    for kw in (
        dict(water=4, with_neighbours=True, with_cells=True),
        dict(water=50, with_neighbours=False, with_cells=False),
        dict(goods=0, food=0, water=1, with_neighbours=True),
        dict(with_neighbours=False, with_cells=True),
    ):
        obs = make_obs(**kw)
        action = choose_action(obs, rng)
        # round-trip through the frozen contract to prove validity
        ActionEnvelope(tick=obs.tick, action=action)


def test_build_envelope_validates() -> None:
    """build_envelope produces an ActionEnvelope that survives model_validate."""
    obs = make_obs()
    env = build_envelope(obs, random.Random(1))
    dumped = env.model_dump(mode="json", by_alias=True)
    assert ActionEnvelope.model_validate(dumped).tick == obs.tick


def test_choose_action_no_toward_for_unknown_cells() -> None:
    """With no visible cells, the mock never emits a goal-move toward an unknown
    cell — every move must be blind directional (§4.3)."""
    rng = random.Random(0)
    obs = make_obs(with_cells=False, with_neighbours=False)
    for _ in range(100):
        a = choose_action(obs, rng)
        if a.type.value == "move":
            assert a.params.toward is None
            assert a.params.direction is not None


def test_seconds_until_clamps_past_deadline() -> None:
    """A deadline already in the past yields a non-negative (zero) sleep."""
    assert _seconds_until("2000-01-01T00:00:00Z") == 0.0
    assert _seconds_until("not-a-date") == 0.0


@pytest.mark.asyncio
async def test_mock_agent_step_against_mock_transport() -> None:
    """A full observe->submit step against an in-memory transport: the agent reads
    a valid observation and POSTs a contract-valid envelope (verified server-side)."""
    obs = make_obs()
    seen: dict[str, ActionEnvelope] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/world/observe"):
            return httpx.Response(200, json=obs.model_dump(mode="json", by_alias=True))
        if request.url.path.endswith("/action"):
            import json as _json

            seen["env"] = ActionEnvelope.model_validate(_json.loads(request.content))
            return httpx.Response(202, json={"accepted": True})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = MockAgent("http://test", "agent_07", "key", seed=7, client=client)
        env = await agent.step()
    assert env is not None
    assert "env" in seen  # the server received and validated an envelope
    assert seen["env"].tick == obs.tick
