"""Tests for prompt assembly (mircoverse/agents/prompts.py).

The reference agent's prompts are pure text + pure functions (Protocol.md §7.2/§7.4):
every byte the model would see is logged and diffable, so we assert structure, not LLM
behaviour. No LLM, no network.

Covers:
  * load_system_prompt() returns the fixed scaffold, naming all four tools and the
    importance rubric (§7.2's required sections).
  * render_user_turn() surfaces the FREE memory_index (each ref) and live self state
    (water) from an Observation (§5.2/§6.2).
"""

from __future__ import annotations

from mircoverse.agents.prompts import (
    load_system_prompt,
    render_reflection_turn,
    render_user_turn,
)
from mircoverse.contracts import (
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


def test_system_prompt_nonempty_names_four_tools_and_rubric() -> None:
    text = load_system_prompt()
    assert text.strip(), "system prompt must be non-empty"
    # all four tools (§7.2) are named
    for tool in ("read_memory", "search_memory", "submit_action", "submit_reflection"):
        assert tool in text, f"system prompt must name the {tool} tool"
    # the one-action-per-tick rule and reflect-only-when-it-matters guidance
    assert "one" in text.lower() and "submit_action" in text
    # the typed-file taxonomy
    for f in ("events", "relationships", "reflections"):
        assert f in text
    # the concrete importance 1-to-10 rubric (endpoints present)
    assert "1" in text and "10" in text
    assert "importance" in text.lower()


def test_system_prompt_is_cached() -> None:
    a = load_system_prompt()
    b = load_system_prompt()
    assert a is b  # cached object identity, read once


def test_render_user_turn_includes_index_refs_and_self_water() -> None:
    index = [
        MemoryIndexEntry(ref="events#88", tick=9, importance=9,
                         summary="Watched agent_12 nearby."),
        MemoryIndexEntry(ref="relationships#agent_03", tick=8, importance=6,
                         summary="agent_03 shared a real oasis."),
    ]
    obs = make_obs(water=31, index=index)
    rendered = render_user_turn(obs)
    # every memory_index ref appears (the free TOC / "ls")
    for e in index:
        assert e.ref in rendered, f"missing index ref {e.ref}"
        assert e.summary in rendered
    # live self state: the water value
    assert "31" in rendered
    # working memory pieces are present
    assert "agent_12" in rendered  # FOV agent
    assert str(obs.tick) in rendered


def test_render_user_turn_is_deterministic_and_pure() -> None:
    obs = make_obs()
    assert render_user_turn(obs) == render_user_turn(obs)


def test_render_user_turn_omits_identity_when_no_souls_passed() -> None:
    """Back-compat: the legacy Observation-only call renders without an identity block, so
    pure-text callers/tests that never had a soul keep working unchanged."""
    rendered = render_user_turn(make_obs())
    assert "Your original self" not in rendered
    assert "moral boundaries" not in rendered.lower()


def test_render_user_turn_injects_identity_on_hot_path() -> None:
    """The hot path MUST show the persona (system.md §2's promise). When souls are passed,
    both selves' values/boundaries appear in the decide message — otherwise the agent decides
    persona-blind and the drift instrument measures nothing."""
    current = SoulFile(
        core_values=["Keep my word"],
        moral_boundaries=["I will not steal", "I will not abandon a partner"],
        personality="Hardened by the dunes.",
        goals=["Survive"],
    )
    rendered = render_user_turn(make_obs(), original_soul=SOUL, current_identity=current)
    # original self re-presented (the immutable T=0 anchor) ...
    assert "I will not kill" in rendered
    # ... and the current (possibly drifted) self ...
    assert "Hardened by the dunes." in rendered
    assert "I will not abandon a partner" in rendered
    # ... framed as a chosen change, never amnesia (decision 2026-06-02).
    assert "original self" in rendered.lower()
    # working memory still follows the identity block
    assert str(make_obs().tick) in rendered


def test_render_user_turn_includes_retrieved_block() -> None:
    obs = make_obs(index=[MemoryIndexEntry(ref="events#1", tick=1, importance=3,
                                           summary="A move.")])
    rendered = render_user_turn(obs, retrieved=["Looted the cache earlier."])
    assert "Looted the cache earlier." in rendered


def test_render_reflection_turn_presents_both_souls_and_memories() -> None:
    original = SOUL
    current = SoulFile(
        core_values=["Keep my word"],
        moral_boundaries=["I will not kill"],  # dropped the theft boundary
        personality="Hardened.",
        goals=["Survive"],
    )
    rendered = render_reflection_turn(original, current, ["Took from the dead."])
    assert "I will not steal" in rendered  # original re-presented
    assert "Hardened." in rendered          # current self
    assert "Took from the dead." in rendered
    # invites an OPTIONAL revision, signalling most reflections change nothing
    assert "ONLY" in rendered or "only" in rendered
