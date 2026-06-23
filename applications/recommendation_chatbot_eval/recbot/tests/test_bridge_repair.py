import json

from recbot.interecagent_bridge import (
    _force_hard_filter_selectable_sql,
    _normalize_plan_inputs,
    _repair_empty_tool_plan_response,
    _retry_malformed_plan,
)
from recbot.types import NativeAction


def test_retry_malformed_plan_resamples_until_valid():
    """A malformed (e.g. prose) plan returns the error sentinel; re-sampling the
    LLM usually yields a valid plan, so we retry instead of dying on the turn."""
    calls = []

    def call():
        calls.append(1)
        return (
            "Something went wrong, please retry.\n[can not be parsed]"
            if len(calls) < 3
            else "Here are recommendations: ABZU; Hook"
        )

    out = _retry_malformed_plan(call, max_attempts=3)
    assert out.startswith("Here are recommendations")
    assert len(calls) == 3  # initial attempt + 2 retries


def test_retry_malformed_plan_bounded_by_max_attempts():
    """Retries are bounded — a persistently bad plan doesn't loop forever."""
    calls = []

    def call():
        calls.append(1)
        return "Something went wrong, please retry."

    out = _retry_malformed_plan(call, max_attempts=3)
    assert out.startswith("Something went wrong")
    assert len(calls) == 3


def test_retry_malformed_plan_no_retry_on_success():
    """A good plan is returned immediately, with no extra LLM calls."""
    calls = []

    def call():
        calls.append(1)
        return "Here are recommendations: Far Cry 3"

    assert _retry_malformed_plan(call) == "Here are recommendations: Far Cry 3"
    assert len(calls) == 1


def test_hard_filter_normalizes_select_but_preserves_tags_filter():
    """The HardFilter adapter normalizes the SELECT clause to ``SELECT *`` so item
    ids stay selectable, but must NOT rewrite the genre filter on the categorical
    ``tags`` column. BaseGallery loads ``tags`` as a comma-joined string, so
    ``WHERE tags LIKE '%Strategy%'`` filters correctly (~2978 games); rewriting it
    to ``display_text`` (not a real column) breaks genre retrieval — the agent then
    falls back to base-knowledge fabrication.
    """
    out = _force_hard_filter_selectable_sql(
        "SELECT id FROM game_information WHERE tags LIKE '%Strategy%'"
    )
    assert out == "SELECT * FROM game_information WHERE tags LIKE '%Strategy%'"
    # The column must be preserved verbatim (no display_text rewrite).
    assert "display_text" not in out
    # NOT LIKE is preserved too.
    out2 = _force_hard_filter_selectable_sql(
        "SELECT title FROM game_information WHERE tags NOT LIKE '%Indie%'"
    )
    assert "tags NOT LIKE" in out2 and "display_text" not in out2


def test_normalize_plan_inputs_decodes_double_encoded_plan():
    """A plan double-encoded as a JSON string is unwrapped to a raw JSON array.

    gpt-4o-mini intermittently emits the tool plan wrapped/escaped as a JSON
    string; RecAI's strict ``json.loads`` then fails and the turn errors. The
    bridge un-wraps that outer layer so RecAI's parser sees clean JSON.
    """
    plan = [{"tool_name": "Look Up Tool", "input": "SELECT price FROM t WHERE x"}]
    raw = json.dumps(plan)  # well-behaved: raw JSON array
    double = json.dumps(raw)  # the bug: the array wrapped as a JSON string

    assert _normalize_plan_inputs(double) == raw  # unwrapped to clean JSON
    assert _normalize_plan_inputs(raw) == raw  # valid plan untouched
    assert _normalize_plan_inputs("not json at all") == "not json at all"
    assert _normalize_plan_inputs('"just a quoted string, not a plan"') == (
        '"just a quoted string, not a plan"'
    )  # a quoted non-array stays as-is (RecAI handles the error)


def _empty_plan_action():
    return NativeAction(raw="Action: x\nAction Input: []", raw_tool_plan=[])


def test_repair_uses_domain_noun_not_movie():
    out = _repair_empty_tool_plan_response("Something went wrong, please retry.", _empty_plan_action(), "game")
    assert "game" in out
    assert "movie" not in out.lower()


def test_repair_humanizes_underscored_domain():
    out = _repair_empty_tool_plan_response("Something went wrong, please retry.", _empty_plan_action(), "beauty_product")
    assert "beauty product" in out


def test_repair_passes_through_normal_response():
    action = NativeAction(raw="Final Answer: hi", raw_tool_plan=[{"tool": "x"}])
    assert _repair_empty_tool_plan_response("Here are some games.", action, "game") == "Here are some games."
