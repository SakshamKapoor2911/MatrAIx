"""Tests for the OpenAI / OpenAI-compatible provider (openai_provider.py).

These exercise the neutral<->native translation WITHOUT the `openai` SDK installed,
a network, or an API key: every test injects a fake client that mimics only
`chat.completions.create` and returns a canned native response. We assert that the
adapter (a) sends the right native tool/message shapes, (b) normalizes a tool_use
response into `Completion.tool_calls` (JSON-string arguments -> dict), and (c)
round-trips a neutral assistant-tool-call + tool_results turn into native form, plus
that `OpenAICompatibleProvider` forwards `base_url` to the (faked) SDK constructor.
"""

from __future__ import annotations

import json
import sys
import types
from typing import Any, Optional

import pytest

from mircoverse.agents.llm_types import (
    Completion,
    ToolCall,
    assistant_tool_msg,
    tool_results_msg,
    user_msg,
)
from mircoverse.agents.providers.openai_provider import (
    OpenAICompatibleProvider,
    OpenAIProvider,
)
from mircoverse.agents.tools import DECIDE_TOOLS, SUBMIT_ACTION


# ── Fake native response objects (attribute-shaped like the openai SDK) ──────────

class _FakeFunction:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, id: str, name: str, arguments: str) -> None:
        self.id = id
        self.type = "function"
        self.function = _FakeFunction(name, arguments)


class _FakeMessage:
    def __init__(self, content: Optional[str], tool_calls: Optional[list]) -> None:
        self.content = content
        self.tool_calls = tool_calls


class _FakeChoice:
    def __init__(self, message: _FakeMessage, finish_reason: str) -> None:
        self.message = message
        self.finish_reason = finish_reason


class _FakeResponse:
    def __init__(self, choice: _FakeChoice) -> None:
        self.choices = [choice]


class _FakeCompletions:
    def __init__(self, response: _FakeResponse, sink: dict) -> None:
        self._response = response
        self._sink = sink

    async def create(self, **kwargs: Any) -> _FakeResponse:
        # Record exactly what the adapter sent natively, for shape assertions.
        self._sink["create_kwargs"] = kwargs
        return self._response


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class FakeOpenAI:
    """Mimics just `client.chat.completions.create`; records the native call."""

    def __init__(self, response: _FakeResponse) -> None:
        self.sink: dict = {}
        self.chat = _FakeChat(_FakeCompletions(response, self.sink))


def _tool_use_response(
    *, name: str = "submit_action", arguments: Optional[str] = None
) -> _FakeResponse:
    if arguments is None:
        arguments = json.dumps({"type": "wait", "params": {}, "importance": 1})
    msg = _FakeMessage(
        content="thinking...",
        tool_calls=[_FakeToolCall("call_abc", name, arguments)],
    )
    return _FakeResponse(_FakeChoice(msg, finish_reason="tool_calls"))


# ── Tests ────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _no_openai_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard: the real `openai` SDK must NOT be needed. Poison the import so any
    accidental lazy-import (i.e. a missing client injection) fails loudly."""
    poison = types.ModuleType("openai")

    def _explode(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("openai SDK must not be imported in tests")

    poison.AsyncOpenAI = _explode  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", poison)


def test_provider_names() -> None:
    assert OpenAIProvider.provider_name == "openai"
    assert OpenAICompatibleProvider.provider_name == "openai-compatible"


async def test_complete_normalizes_tool_use_into_completion() -> None:
    """A native tool_use response normalizes into Completion.tool_calls with a
    PARSED-dict input (not the raw JSON string)."""
    client = FakeOpenAI(_tool_use_response())
    provider = OpenAIProvider(model="gpt-4o", client=client)

    completion = await provider.complete(
        system="SYS", messages=[user_msg("observe")], tools=DECIDE_TOOLS
    )

    assert isinstance(completion, Completion)
    assert completion.text == "thinking..."
    assert completion.stop_reason == "tool_calls"
    assert len(completion.tool_calls) == 1
    call = completion.tool_calls[0]
    assert isinstance(call, ToolCall)
    assert call.id == "call_abc"
    assert call.name == "submit_action"
    assert isinstance(call.input, dict)  # JSON string -> dict
    assert call.input["type"] == "wait"


async def test_complete_sends_system_and_native_tool_shapes() -> None:
    """The adapter prepends a system message and wraps tools in OpenAI's envelope."""
    client = FakeOpenAI(_tool_use_response())
    provider = OpenAIProvider(model="gpt-4o", client=client)

    await provider.complete(
        system="SYSTEM PROMPT", messages=[user_msg("hello")], tools=DECIDE_TOOLS
    )

    sent = client.sink["create_kwargs"]
    assert sent["model"] == "gpt-4o"
    assert sent["tool_choice"] == "auto"

    # system prepended, then the user turn.
    msgs = sent["messages"]
    assert msgs[0] == {"role": "system", "content": "SYSTEM PROMPT"}
    assert msgs[1] == {"role": "user", "content": "hello"}

    # tools wrapped as {"type":"function","function":{name,description,parameters}}.
    tools = sent["tools"]
    assert len(tools) == len(DECIDE_TOOLS)
    submit = next(t for t in tools if t["function"]["name"] == "submit_action")
    assert submit["type"] == "function"
    assert submit["function"]["description"] == SUBMIT_ACTION["description"]
    assert submit["function"]["parameters"] == SUBMIT_ACTION["input_schema"]


async def test_round_trips_assistant_tool_call_and_tool_results() -> None:
    """A neutral assistant-tool-call turn + tool_results turn translate into native
    OpenAI form without error: assistant.tool_calls carry json-string arguments and
    each result becomes its own role:"tool" message keyed by tool_call_id."""
    client = FakeOpenAI(_tool_use_response())
    provider = OpenAIProvider(model="gpt-4o", client=client)

    prior_call = ToolCall(id="call_1", name="read_memory", input={"ref": "events#88"})
    history = [
        user_msg("observe"),
        assistant_tool_msg([prior_call], text="let me check memory"),
        tool_results_msg([("call_1", "remembered: water at (3,4)")]),
    ]

    await provider.complete(system="SYS", messages=history, tools=DECIDE_TOOLS)

    msgs = client.sink["create_kwargs"]["messages"]
    # [system, user, assistant(tool_calls), tool]
    assistant = msgs[2]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == "let me check memory"
    tc = assistant["tool_calls"][0]
    assert tc == {
        "id": "call_1",
        "type": "function",
        "function": {
            "name": "read_memory",
            "arguments": json.dumps({"ref": "events#88"}),
        },
    }
    # arguments must be a JSON STRING that re-parses to the original input.
    assert json.loads(tc["function"]["arguments"]) == {"ref": "events#88"}

    tool_msg = msgs[3]
    assert tool_msg == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "remembered: water at (3,4)",
    }


async def test_no_tool_calls_yields_empty_list_and_text() -> None:
    """A plain text response (no tool calls) normalizes to empty tool_calls + text."""
    msg = _FakeMessage(content="just talking", tool_calls=None)
    resp = _FakeResponse(_FakeChoice(msg, finish_reason="stop"))
    client = FakeOpenAI(resp)
    provider = OpenAIProvider(model="gpt-4o", client=client)

    completion = await provider.complete(
        system="SYS", messages=[user_msg("hi")], tools=DECIDE_TOOLS
    )
    assert completion.tool_calls == []
    assert completion.text == "just talking"
    assert completion.stop_reason == "stop"


async def test_compatible_provider_forwards_base_url_to_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAICompatibleProvider threads base_url into the (faked) SDK constructor,
    proving the 'other provider' (Groq/Together/OpenRouter/Ollama/vLLM) path."""
    captured: dict = {}

    def fake_ctor(**kwargs: Any) -> FakeOpenAI:
        captured.update(kwargs)
        return FakeOpenAI(_tool_use_response())

    # Patch the lazy-imported module's AsyncOpenAI so NO client is injected here.
    # monkeypatch.setitem restores sys.modules at teardown, so no leak into later tests.
    fake_module = types.ModuleType("openai")
    fake_module.AsyncOpenAI = fake_ctor  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", fake_module)

    provider = OpenAICompatibleProvider(
        model="llama-3.1-70b",
        base_url="https://api.groq.com/openai/v1",
        api_key="sk-test",
    )

    assert provider.base_url == "https://api.groq.com/openai/v1"
    assert captured["base_url"] == "https://api.groq.com/openai/v1"
    assert captured["api_key"] == "sk-test"
    # And it still completes via the constructed fake client.
    completion = await provider.complete(
        system="SYS", messages=[user_msg("hi")], tools=DECIDE_TOOLS
    )
    assert completion.tool_calls[0].name == "submit_action"
