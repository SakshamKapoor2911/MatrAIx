"""Tests for the Anthropic provider adapter (mircoverse/agents/providers/anthropic_provider.py).

These exercise the translator at both edges of the neutral `complete()` surface with
a FAKE Anthropic client — NO network, NO API key, NO real `anthropic` SDK import:

  * the native request shape sent to `messages.create` (system/model/max_tokens,
    tools passed verbatim, and the neutral three-role history rendered into
    Anthropic content blocks);
  * normalization of a `tool_use`/`text` response into `Completion.tool_calls`/`text`;
  * a full round-trip of a neutral assistant-tool-call + tool_results turn back into
    native form without error.

The fake client records the kwargs it was called with and returns a stub response
whose `.content` is a list of simple-namespace blocks, mimicking just the surface
the adapter reads.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mircoverse.agents.llm_types import (
    Completion,
    ToolCall,
    assistant_tool_msg,
    tool_results_msg,
    user_msg,
)
from mircoverse.agents.providers.anthropic_provider import (
    AnthropicProvider,
    _from_native_response,
    _to_native_messages,
)
from mircoverse.agents.tools import DECIDE_TOOLS, SUBMIT_ACTION


class FakeAnthropic:
    """Mimics the slice of `anthropic.AsyncAnthropic` the adapter touches.

    `messages.create` is an async method that records its kwargs and returns the
    canned response the test configured. No SDK, no network, no key.
    """

    def __init__(self, response: object) -> None:
        self._response = response
        self.calls: list[dict] = []
        # Match the SDK's nested attribute access: client.messages.create(...).
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self._response


def _tool_use_response(
    *, tool_id: str = "toolu_01", name: str = "submit_action", input: dict | None = None,
    text: str = "", stop_reason: str = "tool_use",
) -> SimpleNamespace:
    """Build a stub Anthropic response with an optional text block + a tool_use block."""
    blocks = []
    if text:
        blocks.append(SimpleNamespace(type="text", text=text))
    blocks.append(
        SimpleNamespace(
            type="tool_use",
            id=tool_id,
            name=name,
            input=input if input is not None else {"type": "wait", "params": {}},
        )
    )
    return SimpleNamespace(content=blocks, stop_reason=stop_reason)


# ── construction ────────────────────────────────────────────────────────────────

def test_injected_client_skips_sdk_import() -> None:
    """With a client injected, construction never imports the anthropic SDK."""
    provider = AnthropicProvider("claude-x", client=FakeAnthropic(_tool_use_response()))
    assert provider.provider_name == "anthropic"
    assert provider.model == "claude-x"
    assert provider.max_tokens == 2048


# ── native request shape ──────────────────────────────────────────────────────

async def test_complete_sends_native_request_shape() -> None:
    """complete() forwards model/system/max_tokens and tools verbatim, with native messages."""
    fake = FakeAnthropic(_tool_use_response())
    provider = AnthropicProvider("claude-test", client=fake, max_tokens=512)

    await provider.complete(
        system="SYS PROMPT",
        messages=[user_msg("observe this tick")],
        tools=DECIDE_TOOLS,
    )

    assert len(fake.calls) == 1
    kw = fake.calls[0]
    assert kw["model"] == "claude-test"
    assert kw["system"] == "SYS PROMPT"
    assert kw["max_tokens"] == 512
    # Tools are passed through verbatim — Anthropic accepts {name,description,input_schema}.
    assert kw["tools"] is DECIDE_TOOLS
    assert SUBMIT_ACTION in kw["tools"]
    # The neutral user turn became an Anthropic text content block.
    assert kw["messages"] == [
        {"role": "user", "content": [{"type": "text", "text": "observe this tick"}]}
    ]


async def test_complete_forwards_extra_create_kwargs() -> None:
    """Extra construction kwargs (e.g. temperature) ride along on every create call."""
    fake = FakeAnthropic(_tool_use_response())
    provider = AnthropicProvider("claude-test", client=fake, temperature=0.2)
    await provider.complete(system="s", messages=[user_msg("hi")], tools=[])
    assert fake.calls[0]["temperature"] == 0.2


# ── response normalization ──────────────────────────────────────────────────────

async def test_complete_normalizes_tool_use_into_completion() -> None:
    """A tool_use block normalizes into Completion.tool_calls[0] with a parsed dict input."""
    payload = {"type": "move", "params": {"direction": "NE"}, "importance": 5}
    fake = FakeAnthropic(
        _tool_use_response(tool_id="toolu_42", name="submit_action", input=payload,
                           text="thinking...", stop_reason="tool_use")
    )
    provider = AnthropicProvider("claude-test", client=fake)

    completion = await provider.complete(system="s", messages=[user_msg("go")], tools=DECIDE_TOOLS)

    assert isinstance(completion, Completion)
    assert completion.stop_reason == "tool_use"
    assert completion.text == "thinking..."
    assert len(completion.tool_calls) == 1
    call = completion.tool_calls[0]
    assert isinstance(call, ToolCall)
    assert call.id == "toolu_42"
    assert call.name == "submit_action"
    assert call.input == payload
    assert isinstance(call.input, dict)  # parsed dict, not a JSON string


def test_from_native_response_multiple_blocks() -> None:
    """text blocks concatenate; every tool_use block becomes a ToolCall in order."""
    resp = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="a"),
            SimpleNamespace(type="text", text="b"),
            SimpleNamespace(type="tool_use", id="t1", name="read_memory", input={"ref": "events#1"}),
            SimpleNamespace(type="tool_use", id="t2", name="search_memory",
                            input={"file": "events", "pattern": "x"}),
        ],
        stop_reason="tool_use",
    )
    completion = _from_native_response(resp)
    assert completion.text == "ab"
    assert [c.name for c in completion.tool_calls] == ["read_memory", "search_memory"]
    assert completion.tool_calls[0].input == {"ref": "events#1"}


def test_from_native_response_text_only() -> None:
    """A response with no tool_use yields empty tool_calls but carries text + stop_reason."""
    resp = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="no tools here")],
        stop_reason="end_turn",
    )
    completion = _from_native_response(resp)
    assert completion.tool_calls == []
    assert completion.text == "no tools here"
    assert completion.stop_reason == "end_turn"


# ── neutral history -> native round-trip ────────────────────────────────────────

def test_to_native_round_trips_assistant_and_tool_results() -> None:
    """An assistant-tool-call turn + tool_results turn translate into native blocks."""
    history = [
        user_msg("first observation"),
        assistant_tool_msg(
            [ToolCall(id="toolu_9", name="read_memory", input={"ref": "events#3"})],
            text="let me check my notes",
        ),
        tool_results_msg([("toolu_9", "events#3: I saw a death cache.")]),
    ]
    native = _to_native_messages(history)

    assert native[0] == {
        "role": "user",
        "content": [{"type": "text", "text": "first observation"}],
    }
    # assistant turn: leading text block, then the tool_use block.
    assert native[1] == {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "let me check my notes"},
            {"type": "tool_use", "id": "toolu_9", "name": "read_memory",
             "input": {"ref": "events#3"}},
        ],
    }
    # tool_results becomes a user turn carrying a tool_result block.
    assert native[2] == {
        "role": "user",
        "content": [
            {"type": "tool_result", "tool_use_id": "toolu_9",
             "content": "events#3: I saw a death cache."}
        ],
    }


def test_to_native_assistant_without_text_omits_text_block() -> None:
    """An assistant turn with no preamble text emits only the tool_use block(s)."""
    native = _to_native_messages(
        [assistant_tool_msg([ToolCall(id="t", name="submit_action", input={"type": "wait"})])]
    )
    assert native[0]["content"] == [
        {"type": "tool_use", "id": "t", "name": "submit_action", "input": {"type": "wait"}}
    ]


def test_to_native_unknown_role_raises() -> None:
    """A malformed neutral message role fails loudly rather than dropping silently."""
    with pytest.raises(ValueError, match="Unknown neutral message role"):
        _to_native_messages([{"role": "system", "content": "nope"}])


async def test_complete_round_trips_full_history_without_error() -> None:
    """complete() accepts a full neutral history (all three roles) and returns a Completion."""
    fake = FakeAnthropic(_tool_use_response(name="submit_action"))
    provider = AnthropicProvider("claude-test", client=fake)
    history = [
        user_msg("observation"),
        assistant_tool_msg([ToolCall(id="t1", name="read_memory", input={"ref": "events#1"})]),
        tool_results_msg([("t1", "events#1: something happened")]),
        user_msg("now decide"),
    ]
    completion = await provider.complete(system="s", messages=history, tools=DECIDE_TOOLS)
    assert isinstance(completion, Completion)
    # The full history was rendered: 4 native messages in order.
    sent = fake.calls[0]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user", "user"]
