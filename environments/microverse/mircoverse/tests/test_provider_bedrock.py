"""Tests for the AWS Bedrock provider (mircoverse/agents/providers/bedrock_provider.py).

Covers Protocol.md §7's neutral tool-use surface as spoken in Bedrock's Converse dialect.
A `FakeBedrock` client mimics just the `.converse` method, records the kwargs it was
called with, and returns a canned native Converse response — so these tests touch NO
network, NO API key, and import NO real AWS SDK (boto3 need not be installed). boto3 is
only ever lazy-imported when no client is injected, which we never do here.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mircoverse.agents.llm_types import (
    ToolCall,
    assistant_tool_msg,
    tool_results_msg,
    user_msg,
)
from mircoverse.agents.providers.bedrock_provider import BedrockProvider
from mircoverse.agents.tools import DECIDE_TOOLS


class FakeBedrock:
    """Stand-in for a boto3 `bedrock-runtime` client: records `.converse` kwargs.

    Its `.converse` returns a canned dict shaped exactly like a Converse response with
    one `toolUse` content item, so the adapter can be exercised with no AWS at all."""

    def __init__(self, response: dict) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def converse(self, **kwargs: Any) -> dict:
        self.calls.append(kwargs)
        return self._response


def _canned_tooluse_response() -> dict:
    """A Converse response that emits free text plus one submit_action toolUse."""
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {"text": "Water is low; heading to the oasis."},
                    {
                        "toolUse": {
                            "toolUseId": "tu_42",
                            "name": "submit_action",
                            "input": {"type": "wait", "params": {}},
                        }
                    },
                ],
            }
        },
        "stopReason": "tool_use",
    }


def test_init_with_injected_client_does_not_import_boto3() -> None:
    """Injecting a client suppresses the lazy boto3 import (SDK-free construction)."""
    provider = BedrockProvider(model="anthropic.claude-3-5-sonnet-20240620-v1:0", client=FakeBedrock({}))
    assert provider.provider_name == "bedrock"
    assert provider.model == "anthropic.claude-3-5-sonnet-20240620-v1:0"


def test_complete_sends_native_system_and_tool_config() -> None:
    """`complete` calls converse with system=[{"text":...}] and a Converse toolConfig."""
    fake = FakeBedrock(_canned_tooluse_response())
    provider = BedrockProvider(model="m", client=fake)

    asyncio.run(
        provider.complete(
            system="You are agent_07.",
            messages=[user_msg("It is tick 3. What do you do?")],
            tools=DECIDE_TOOLS,
        )
    )

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["modelId"] == "m"
    # System is the Converse [{"text": ...}] envelope.
    assert call["system"] == [{"text": "You are agent_07."}]
    # User turn became a single text content block.
    assert call["messages"] == [
        {"role": "user", "content": [{"text": "It is tick 3. What do you do?"}]}
    ]
    # Tools are wrapped in Converse toolSpec envelopes with inputSchema.json.
    tool_cfg = call["toolConfig"]
    names = [t["toolSpec"]["name"] for t in tool_cfg["tools"]]
    assert names == ["read_memory", "search_memory", "submit_action"]
    submit = next(t["toolSpec"] for t in tool_cfg["tools"] if t["toolSpec"]["name"] == "submit_action")
    assert "json" in submit["inputSchema"]
    assert submit["inputSchema"]["json"]["type"] == "object"
    assert submit["description"]  # carried through


def test_complete_normalizes_tooluse_into_completion() -> None:
    """A Converse toolUse item is normalized into Completion.tool_calls (input as dict)."""
    fake = FakeBedrock(_canned_tooluse_response())
    provider = BedrockProvider(model="m", client=fake)

    completion = asyncio.run(
        provider.complete(system="s", messages=[user_msg("go")], tools=DECIDE_TOOLS)
    )

    assert completion.stop_reason == "tool_use"
    assert completion.text == "Water is low; heading to the oasis."
    assert len(completion.tool_calls) == 1
    tc = completion.tool_calls[0]
    assert isinstance(tc, ToolCall)
    assert tc.id == "tu_42"
    assert tc.name == "submit_action"
    assert isinstance(tc.input, dict)
    assert tc.input == {"type": "wait", "params": {}}


def test_complete_round_trips_assistant_and_tool_results_history() -> None:
    """A neutral assistant-tool-call + tool_results turn translates back into native form.

    The assistant turn becomes a toolUse content block; the tool_results turn becomes a
    Converse `user` turn carrying toolResult blocks — without error."""
    fake = FakeBedrock(_canned_tooluse_response())
    provider = BedrockProvider(model="m", client=fake)

    prior_call = ToolCall(id="tu_1", name="read_memory", input={"ref": "events#88"})
    messages = [
        user_msg("It is tick 5."),
        assistant_tool_msg([prior_call], text="Let me check my notes."),
        tool_results_msg([("tu_1", "Day 2: witnessed a death at (4,9).")]),
    ]

    asyncio.run(provider.complete(system="s", messages=messages, tools=DECIDE_TOOLS))

    native = fake.calls[0]["messages"]
    assert native[0] == {"role": "user", "content": [{"text": "It is tick 5."}]}

    # Assistant turn: optional text block then a toolUse block.
    assert native[1]["role"] == "assistant"
    assert native[1]["content"][0] == {"text": "Let me check my notes."}
    assert native[1]["content"][1] == {
        "toolUse": {"toolUseId": "tu_1", "name": "read_memory", "input": {"ref": "events#88"}}
    }

    # Tool results turn: a Converse user turn carrying a toolResult block.
    assert native[2]["role"] == "user"
    assert native[2]["content"] == [
        {
            "toolResult": {
                "toolUseId": "tu_1",
                "content": [{"text": "Day 2: witnessed a death at (4,9)."}],
            }
        }
    ]
