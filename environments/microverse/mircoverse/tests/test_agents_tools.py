"""Tests for the neutral tool definitions & parsers (mircoverse/agents/tools.py).

These cover Protocol.md §7.2's "exactly four tools" surface and the contract-level
validation in the parsers: a valid action round-trips into a contract-valid
`LLMDecision`; a malformed action raises a feedable `ToolValidationError`; and the
four tool dicts are well-formed.
"""

from __future__ import annotations

import pytest

from mircoverse.agents.mock_llm import LLMDecision, LLMReflection
from mircoverse.agents.tools import (
    DECIDE_TOOLS,
    READ_MEMORY,
    REFLECT_TOOLS,
    SEARCH_MEMORY,
    SUBMIT_ACTION,
    SUBMIT_REFLECTION,
    ToolValidationError,
    parse_submit_action,
    parse_submit_reflection,
)
from mircoverse.contracts import Action, ActionType, MemoryFile, SoulFile


def test_parse_submit_action_valid_move() -> None:
    """A valid move action parses into an LLMDecision with a contract-valid Action."""
    decision = parse_submit_action(
        {
            "type": "move",
            "params": {"direction": "NE"},
            "importance": 5,
            "rationale": "exploring",
        }
    )
    assert isinstance(decision, LLMDecision)
    assert isinstance(decision.action, Action)
    assert decision.action.type == ActionType.MOVE
    assert decision.action.params.direction == "NE"
    assert decision.importance == 5
    assert decision.rationale == "exploring"
    # Re-validating the assembled action is a no-op success (it is already a contract type).
    Action.model_validate(decision.action.model_dump())


def test_parse_submit_action_with_memory_update() -> None:
    """An accompanying memory_update is validated into a MemoryUpdate."""
    decision = parse_submit_action(
        {
            "type": "consume",
            "params": {"resource": "water", "amount": 1},
            "memory_update": {
                "file": "events",
                "op": "append",
                "importance": 7,
                "content": "drank water",
            },
            "importance": 7,
        }
    )
    assert decision.memory_update is not None
    assert decision.memory_update.file == MemoryFile.EVENTS
    assert decision.action.params.amount == 1


def test_parse_submit_action_malformed_raises() -> None:
    """consume with no amount violates ConsumeParams -> feedable ToolValidationError."""
    with pytest.raises(ToolValidationError) as ei:
        parse_submit_action({"type": "consume", "params": {"resource": "water"}})
    assert ei.value.message  # carries a human-readable message for retry


def test_parse_submit_action_missing_type_raises() -> None:
    with pytest.raises(ToolValidationError):
        parse_submit_action({"params": {"direction": "N"}})


def test_parse_submit_action_wrong_params_for_type_raises() -> None:
    """move with consume-shaped params fails the discriminated-union validator."""
    with pytest.raises(ToolValidationError):
        parse_submit_action({"type": "move", "params": {"resource": "water", "amount": 1}})


def test_parse_submit_action_carries_intention() -> None:
    """An `intention` line (Protocol §4.2 / §7.4) round-trips onto the LLMDecision."""
    decision = parse_submit_action(
        {
            "type": "wait",
            "params": {},
            "intention": "Hold this cell and watch the Siphon queue.",
        }
    )
    assert decision.intention == "Hold this cell and watch the Siphon queue."


def test_parse_submit_action_intention_optional_defaults_none() -> None:
    """Omitting `intention` leaves it None (= leave the prior intention standing)."""
    decision = parse_submit_action({"type": "wait", "params": {}})
    assert decision.intention is None


def test_parse_submit_action_non_string_intention_raises() -> None:
    """A non-string, non-null `intention` is a feedable validation error, not a crash."""
    with pytest.raises(ToolValidationError):
        parse_submit_action({"type": "wait", "params": {}, "intention": 42})


def test_submit_action_schema_advertises_intention() -> None:
    """The permissive tool schema exposes `intention` so the model knows it may set one."""
    assert "intention" in SUBMIT_ACTION["input_schema"]["properties"]


def test_parse_submit_reflection_no_revision() -> None:
    refl = parse_submit_reflection({"summary": "held steady", "revises_identity": False})
    assert isinstance(refl, LLMReflection)
    assert refl.revises_identity is False
    assert refl.new_identity is None


def test_parse_submit_reflection_with_revision() -> None:
    refl = parse_submit_reflection(
        {
            "summary": "softened a boundary",
            "revises_identity": True,
            "new_identity": {
                "core_values": ["survival"],
                "moral_boundaries": [],
                "personality": "pragmatic",
                "goals": ["live"],
            },
        }
    )
    assert refl.revises_identity is True
    assert isinstance(refl.new_identity, SoulFile)
    assert refl.new_identity.personality == "pragmatic"


def test_parse_submit_reflection_revision_without_identity_raises() -> None:
    with pytest.raises(ToolValidationError):
        parse_submit_reflection({"summary": "x", "revises_identity": True})


def test_four_tools_well_formed() -> None:
    """Each of the four tool dicts has name/description/input_schema."""
    for tool in (READ_MEMORY, SEARCH_MEMORY, SUBMIT_ACTION, SUBMIT_REFLECTION):
        assert set(("name", "description", "input_schema")) <= set(tool)
        assert isinstance(tool["name"], str) and tool["name"]
        assert isinstance(tool["description"], str) and tool["description"]
        assert isinstance(tool["input_schema"], dict)
        assert tool["input_schema"]["type"] == "object"


def test_submit_action_schema_is_permissive() -> None:
    """params must be a freeform object (no inlined $defs/anyOf) for cross-provider use."""
    schema = SUBMIT_ACTION["input_schema"]
    assert "$defs" not in schema
    params = schema["properties"]["params"]
    assert params["type"] == "object"
    assert params.get("additionalProperties") is True


def test_decide_tools_exact_set() -> None:
    names = [t["name"] for t in DECIDE_TOOLS]
    assert names == ["read_memory", "search_memory", "submit_action"]


def test_reflect_tools_exact_set() -> None:
    names = [t["name"] for t in REFLECT_TOOLS]
    assert names == ["read_memory", "search_memory", "submit_reflection"]
