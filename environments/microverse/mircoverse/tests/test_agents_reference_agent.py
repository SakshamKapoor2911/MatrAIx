"""Tests for the reference agent loop (mircoverse/agents/reference_agent.py).

Covers the three things §7 requires of the controlled-arm agent:
  1. The loop produces a contract-valid envelope from a sample observation using
     the MockLLM (no API key, deterministic).
  2. Index-driven retrieval ranks relevant entries first (no embeddings).
  3. Reflection fires exactly at the importance threshold and not before.
"""

from __future__ import annotations

import json

import httpx

from mircoverse.agents.mock_llm import MockLLM
from mircoverse.agents.reference_agent import (
    REFLECTION_THRESHOLD,
    ReferenceAgent,
    pick_relevant,
    score_index_entry,
)
from mircoverse.contracts import (
    ActionEnvelope,
    Fov,
    FovAgent,
    FovCell,
    GlobalView,
    MemoryIndexEntry,
    Observation,
    SelfView,
    SoulFile,
)


def make_obs(*, tick: int = 10, water: int = 30, index=None, neighbour: bool = True) -> Observation:
    cells = [FovCell(pos=(24, 25), terrain="desert")]
    agents = (
        [FovAgent(agent_id="agent_12", pos=(25, 26), stance="neutral", visible_water="low")]
        if neighbour else []
    )
    return Observation(
        tick=tick,
        tick_ends_at="2026-05-30T12:00:30Z",
        **{"self": SelfView(agent_id="agent_07", pos=(24, 25), water=water, food=10,
                            goods=2, on_terrain="desert", stance="neutral")},
        fov=Fov(radius=2, cells=cells, agents=agents),
        **{"global": GlobalView(alive_count=21, storm_active=False, siphon_units_this_tick=37)},
        memory_index=index or [],
    )


SOUL = SoulFile(
    core_values=["Keep my word"],
    moral_boundaries=["I will not steal", "I will not kill"],
    personality="Cautious.",
    goals=["Survive"],
)


def _make_transport(obs: Observation, sink: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/world/observe"):
            return httpx.Response(200, json=obs.model_dump(mode="json", by_alias=True))
        if path.endswith("/action"):
            sink["action"] = ActionEnvelope.model_validate(json.loads(request.content))
            return httpx.Response(202, json={"accepted": True})
        if path.endswith("/reflection"):
            sink["reflection"] = json.loads(request.content)
            return httpx.Response(200, json={"ok": True})
        if "/memory/" in path:
            return httpx.Response(200, json={"content": "Looted the cache earlier."})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


async def test_reference_loop_produces_valid_envelope() -> None:
    """One §7 step with the MockLLM yields a contract-valid envelope the server
    accepts. Uses an in-memory transport — no real server, no API key."""
    obs = make_obs(
        index=[MemoryIndexEntry(ref="events#88", tick=9, importance=9,
                                summary="Watched agent_12 nearby.")]
    )
    sink: dict = {}
    transport = _make_transport(obs, sink)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ReferenceAgent("http://test", "agent_07", "key",
                               llm=MockLLM(seed=1), original_soul=SOUL, client=client)
        env = await agent.step()
    assert env is not None
    assert "action" in sink
    # the captured envelope re-validates against the frozen contract
    assert sink["action"].tick == obs.tick


def test_index_driven_retrieval_ranks_relevant_first() -> None:
    """pick_relevant (no embeddings) surfaces the entry about a visible neighbour
    above an unrelated, older, low-importance entry."""
    obs = make_obs(neighbour=True)
    relevant = MemoryIndexEntry(ref="relationships#agent_12", tick=9, importance=6,
                                summary="agent_12 shared a real oasis.")
    irrelevant = MemoryIndexEntry(ref="events#1", tick=1, importance=2,
                                  summary="Crossed a mountain pass alone.")
    ranked = pick_relevant([irrelevant, relevant], obs, top_k=2)
    assert ranked[0].ref == "relationships#agent_12"
    # and its score is strictly higher
    assert score_index_entry(relevant, obs, obs.tick) > score_index_entry(
        irrelevant, obs, obs.tick
    )


async def test_reflection_fires_at_threshold() -> None:
    """Reflection triggers exactly when accumulated importance reaches the threshold,
    not before — and resets the accumulator after firing (§6.3)."""
    obs = make_obs()
    sink: dict = {}
    transport = _make_transport(obs, sink)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ReferenceAgent("http://test", "agent_07", "key",
                               llm=MockLLM(seed=3), original_soul=SOUL, client=client)
        agent._last_detail = ["Looted the cache earlier."]

        # just below threshold -> no reflection
        agent.importance_accum = REFLECTION_THRESHOLD - 1
        assert agent.should_reflect() is False
        assert await agent.maybe_reflect(tick=10) is None
        assert agent.importance_accum == REFLECTION_THRESHOLD - 1

        # at threshold -> reflection fires and accumulator resets
        agent.importance_accum = REFLECTION_THRESHOLD
        assert agent.should_reflect() is True
        refl = await agent.maybe_reflect(tick=10)
        assert refl is not None
        assert agent.importance_accum == 0


async def test_reflection_revises_identity_posts_reflection() -> None:
    """When the (seeded) reflection revises identity, the agent POSTs /reflection
    and updates its local current_identity cache. Seed chosen to force revision."""
    obs = make_obs()
    sink: dict = {}
    transport = _make_transport(obs, sink)
    # find a seed where MockLLM.reflect revises identity given a 'looted' memory
    forcing_seed = next(
        s for s in range(50)
        if MockLLM(seed=s).reflect(SOUL, SOUL, ["Looted the cache earlier."]).revises_identity
    )
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ReferenceAgent("http://test", "agent_07", "key",
                               llm=MockLLM(seed=forcing_seed), original_soul=SOUL, client=client)
        agent._last_detail = ["Looted the cache earlier."]
        agent.importance_accum = REFLECTION_THRESHOLD
        refl = await agent.maybe_reflect(tick=12)
    assert refl is not None and refl.revises_identity
    assert "reflection" in sink
    # identity drifted: the 'steal' boundary was dropped
    assert all("steal" not in b.lower() for b in agent.current_identity.moral_boundaries)
