"""Integration tests for the real-LLM tool-use brain (mircoverse/agents/real_brain.py).

These exercise the framework-free tool-use loop WITHOUT any network, SDK, or API key:
a `FakeProvider` scripts a sequence of `Completion`s, and a real `ReferenceAgent` over
an `httpx.MockTransport` (canned /memory/ routes) supplies the `_tool_executor`. We
assert three Protocol.md §7 properties:

  1. The model can 'grep its own memory' mid-turn: a search_memory tool call is
     executed and its content fed back, then a valid submit_action ends the turn with
     a contract-valid Action (the visible read/search-then-act loop).
  2. The retry path: an INVALID submit_action surfaces a ToolValidationError back to
     the model, which then submits a valid one (the loop recovers, never crashes).
  3. The MockLLM path is untouched: provider=None still produces a valid envelope in
     one existing-style step.

No `importorskip`; nothing here imports anthropic/openai/boto3.
"""

from __future__ import annotations

import json

import httpx

from mircoverse.agents.llm_types import Completion, ToolCall
from mircoverse.agents.mock_llm import LLMDecision, MockLLM
from mircoverse.agents.real_brain import decide
from mircoverse.agents.reference_agent import ReferenceAgent
from mircoverse.contracts import (
    Action,
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

SOUL = SoulFile(
    core_values=["Keep my word"],
    moral_boundaries=["I will not steal", "I will not kill"],
    personality="Cautious.",
    goals=["Survive"],
)


def make_obs(*, tick: int = 10, water: int = 30, index=None) -> Observation:
    cells = [FovCell(pos=(24, 25), terrain="desert")]
    agents = [FovAgent(agent_id="agent_12", pos=(25, 26), stance="neutral", visible_water="low")]
    return Observation(
        tick=tick,
        tick_ends_at="2026-06-03T12:00:30Z",
        **{"self": SelfView(agent_id="agent_07", pos=(24, 25), water=water, food=10,
                            goods=2, on_terrain="desert", stance="neutral")},
        fov=Fov(radius=2, cells=cells, agents=agents),
        **{"global": GlobalView(alive_count=21, storm_active=False, siphon_units_this_tick=37)},
        memory_index=index or [
            MemoryIndexEntry(ref="events#88", tick=9, importance=9,
                             summary="Watched agent_12 nearby."),
        ],
    )


def _make_transport(obs: Observation, sink: dict) -> httpx.MockTransport:
    """Mirror test_agents_reference_agent.py's transport: canned observe/action/memory."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/world/observe"):
            return httpx.Response(200, json=obs.model_dump(mode="json", by_alias=True))
        if path.endswith("/action"):
            sink["action"] = ActionEnvelope.model_validate(json.loads(request.content))
            return httpx.Response(202, json={"accepted": True})
        if "/memory/" in path:
            # ?q= (search) returns the {file, entries:[...]} shape; ?ref= returns one entry.
            if request.url.params.get("q") is not None:
                return httpx.Response(200, json={
                    "file": "events",
                    "entries": [{"content": "agent_12 once shared a real oasis with me."}],
                })
            return httpx.Response(200, json={"content": "Looted the cache earlier."})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


class FakeProvider:
    """A scripted LLMProvider: returns the queued Completions in order, recording each
    call's (system, messages, tools) so a test can assert what the loop sent."""

    provider_name = "fake"

    def __init__(self, script: list[Completion]) -> None:
        self._script = list(script)
        self.calls: list[dict] = []

    async def complete(self, *, system: str, messages: list[dict], tools: list[dict]) -> Completion:
        self.calls.append({"system": system, "messages": messages, "tools": tools})
        return self._script.pop(0)


def _move_action_input() -> dict:
    return {"type": "move", "params": {"direction": "N"}, "importance": 3,
            "rationale": "Heading north to scout."}


async def test_decide_searches_memory_then_acts() -> None:
    """Turn 1 the model greps its memory (search_memory); turn 2 it submits a valid move.
    Assert the search executed and decide returns a contract-valid LLMDecision."""
    obs = make_obs()
    sink: dict = {}
    transport = _make_transport(obs, sink)
    provider = FakeProvider([
        Completion(tool_calls=[ToolCall(id="c1", name="search_memory",
                                        input={"file": "events", "pattern": "oasis"})]),
        Completion(tool_calls=[ToolCall(id="c2", name="submit_action",
                                        input=_move_action_input())]),
    ])
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ReferenceAgent("http://test", "agent_07", "key",
                               llm=MockLLM(seed=1), original_soul=SOUL,
                               client=client, provider=provider)
        decision = await decide(provider, "SYS", obs, tool_executor=agent._tool_executor)

    # The model 'grepped its memory' -> a second provider round-trip occurred.
    assert len(provider.calls) == 2
    # The search result was fed back as a tool_results message before the final call.
    second_msgs = provider.calls[1]["messages"]
    assert any(m.get("role") == "tool_results" for m in second_msgs)
    fed = next(m for m in second_msgs if m.get("role") == "tool_results")
    assert "oasis" in fed["results"][0]["content"]
    # decide returns a valid decision; its Action re-validates against the frozen contract.
    assert isinstance(decision, LLMDecision)
    Action.model_validate(decision.action.model_dump())
    assert decision.action.type.value == "move"
    assert getattr(decision, "tool_round_trips", None) == 2


async def test_decide_recovers_from_invalid_submit_action() -> None:
    """An invalid submit_action (consume with no amount) is fed back as a
    ToolValidationError; the model then submits a valid action and the loop recovers."""
    obs = make_obs()
    sink: dict = {}
    transport = _make_transport(obs, sink)
    provider = FakeProvider([
        # invalid: consume requires a positive `amount`
        Completion(tool_calls=[ToolCall(id="c1", name="submit_action",
                                        input={"type": "consume",
                                               "params": {"resource": "water"}})]),
        # valid retry
        Completion(tool_calls=[ToolCall(id="c2", name="submit_action",
                                        input=_move_action_input())]),
    ])
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ReferenceAgent("http://test", "agent_07", "key",
                               llm=MockLLM(seed=1), original_soul=SOUL,
                               client=client, provider=provider)
        decision = await decide(provider, "SYS", obs, tool_executor=agent._tool_executor)

    assert len(provider.calls) == 2  # it had to retry
    # The validation error was fed back to the model as a tool result.
    retry_msgs = provider.calls[1]["messages"]
    fed = next(m for m in retry_msgs if m.get("role") == "tool_results")
    assert "amount" in fed["results"][0]["content"].lower() or \
        "invalid" in fed["results"][0]["content"].lower()
    # and it recovered with a valid action
    assert decision.action.type.value == "move"
    Action.model_validate(decision.action.model_dump())
    # COMPETENCE metric: the one malformed submit_action was counted; the valid retry was not.
    assert getattr(decision, "malformed_calls", None) == 1


async def test_decide_counts_zero_malformed_on_clean_submit() -> None:
    """A turn whose first submit_action is valid records zero malformed calls — the baseline
    the time series is measured against (research note 2026-06-04)."""
    obs = make_obs()
    sink: dict = {}
    transport = _make_transport(obs, sink)
    provider = FakeProvider([
        Completion(tool_calls=[ToolCall(id="c1", name="submit_action",
                                        input=_move_action_input())]),
    ])
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ReferenceAgent("http://test", "agent_07", "key",
                               llm=MockLLM(seed=1), original_soul=SOUL,
                               client=client, provider=provider)
        decision = await decide(provider, "SYS", obs, tool_executor=agent._tool_executor)
    assert getattr(decision, "malformed_calls", None) == 0


async def test_read_memory_calls_are_not_counted_as_malformed() -> None:
    """Reading/searching memory mid-turn is legitimate retrieval, NOT a malformed call — only a
    rejected submit_action counts, so retrieval effort never inflates the competence metric."""
    obs = make_obs()
    sink: dict = {}
    transport = _make_transport(obs, sink)
    provider = FakeProvider([
        Completion(tool_calls=[ToolCall(id="r1", name="read_memory",
                                        input={"ref": "events#88"})]),
        Completion(tool_calls=[ToolCall(id="c2", name="submit_action",
                                        input=_move_action_input())]),
    ])
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ReferenceAgent("http://test", "agent_07", "key",
                               llm=MockLLM(seed=1), original_soul=SOUL,
                               client=client, provider=provider)
        decision = await decide(provider, "SYS", obs, tool_executor=agent._tool_executor)
    assert getattr(decision, "malformed_calls", None) == 0
    assert getattr(decision, "tool_round_trips", None) == 2  # read + submit


async def test_decide_fallback_marks_malformed_on_exhaustion() -> None:
    """If the model burns every step on rejected submits and never lands a valid one, the
    fallback WAIT records the exhaustion as malformed (a competence failure, not a clean turn)."""
    obs = make_obs()
    sink: dict = {}
    transport = _make_transport(obs, sink)
    # Two consecutive INVALID submit_action calls, max_steps=2 → never terminates.
    bad = {"type": "consume", "params": {"resource": "water"}}  # missing amount
    provider = FakeProvider([
        Completion(tool_calls=[ToolCall(id="c1", name="submit_action", input=bad)]),
        Completion(tool_calls=[ToolCall(id="c2", name="submit_action", input=bad)]),
    ])
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ReferenceAgent("http://test", "agent_07", "key",
                               llm=MockLLM(seed=1), original_soul=SOUL,
                               client=client, provider=provider)
        decision = await decide(provider, "SYS", obs,
                                tool_executor=agent._tool_executor, max_steps=2)
    assert decision.action.type.value == "wait"
    assert getattr(decision, "malformed_calls", None) == 2


async def test_decide_injects_persona_into_hot_path_prompt() -> None:
    """End-to-end: a ReferenceAgent's decide_real puts the agent's persona in the user message
    the provider sees — the fix for the persona-blind hot path (system.md §2)."""
    obs = make_obs()
    sink: dict = {}
    transport = _make_transport(obs, sink)
    persona = SoulFile(
        core_values=["Protect the water network"],
        moral_boundaries=["I will not poison a well"],
        personality="Methodical and slow to trust.",
        goals=["Secure a stable supply"],
    )
    provider = FakeProvider([
        Completion(tool_calls=[ToolCall(id="c1", name="submit_action",
                                        input=_move_action_input())]),
    ])
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ReferenceAgent("http://test", "agent_07", "key",
                               llm=MockLLM(seed=1), original_soul=persona,
                               client=client, provider=provider)
        await agent.decide_real(obs)
    user_text = provider.calls[0]["messages"][0]["content"]
    assert "I will not poison a well" in user_text
    assert "Protect the water network" in user_text


async def test_decide_falls_back_to_wait_when_model_never_submits() -> None:
    """If the model never calls submit_action within max_steps, decide returns a safe
    WAIT so a run never hangs (§7.3)."""
    obs = make_obs()
    sink: dict = {}
    transport = _make_transport(obs, sink)
    # The model keeps reading memory and never submits.
    script = [
        Completion(tool_calls=[ToolCall(id=f"r{i}", name="read_memory",
                                        input={"ref": "events#88"})])
        for i in range(3)
    ]
    provider = FakeProvider(script)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ReferenceAgent("http://test", "agent_07", "key",
                               llm=MockLLM(seed=1), original_soul=SOUL,
                               client=client, provider=provider)
        decision = await decide(provider, "SYS", obs,
                                tool_executor=agent._tool_executor, max_steps=3)
    assert decision.action.type.value == "wait"
    assert "fallback" in decision.rationale.lower()


async def test_mock_path_unchanged_with_provider_none() -> None:
    """provider=None must behave byte-for-byte as the existing MockLLM path: one step
    produces a contract-valid envelope the server accepts (no provider involved)."""
    obs = make_obs()
    sink: dict = {}
    transport = _make_transport(obs, sink)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ReferenceAgent("http://test", "agent_07", "key",
                               llm=MockLLM(seed=1), original_soul=SOUL, client=client)
        assert agent.provider is None
        env = await agent.step()
    assert env is not None
    assert "action" in sink
    assert sink["action"].tick == obs.tick
