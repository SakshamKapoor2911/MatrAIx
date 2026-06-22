"""OpenAI (and OpenAI-compatible) `LLMProvider` translator (Protocol.md §7.3).

Adapts the neutral tool-use surface (`mircoverse.agents.llm_types`) to the OpenAI
Chat Completions dialect (openai>=1.30). This is participant-side only: the engine
never calls an LLM on the hot path (§7.3); only the reference agent's tool-use loop
does.

The provider is STATELESS w.r.t. the conversation. Every `complete()` re-translates
the FULL neutral history into native OpenAI messages, wraps the four neutral §7.2
tool dicts in OpenAI's `{"type":"function","function":{...}}` envelope, makes one
`chat.completions.create` call, and normalizes the response back into a neutral
`Completion`. Nothing here keeps server-side state; the loop owns the transcript.

The vendor SDK is imported LAZILY — only when no client is injected — so the test
suite (which injects a fake client) runs with the `openai` package absent. The
faked client only needs to expose `chat.completions.create(...)`.

`OpenAICompatibleProvider` is the same translator pointed at any OpenAI-compatible
endpoint (Groq / Together / OpenRouter / Ollama / vLLM — the 'other' provider) by
threading a `base_url` into the SDK constructor.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from mircoverse.agents.llm_types import Completion, ToolCall


class OpenAIProvider:
    """Neutral surface -> OpenAI Chat Completions, normalized back to `Completion`.

    `model` is the OpenAI model id (e.g. "gpt-4o"). When `client` is None the
    `openai` SDK is lazy-imported and an `AsyncOpenAI` client is built from
    `api_key` (else the SDK's own env default); inject a fake `client` in tests to
    keep the suite SDK-free. Extra keyword arguments (e.g. `base_url`) are forwarded
    to the SDK constructor."""

    provider_name: str = "openai"

    def __init__(
        self,
        model: str,
        *,
        client: Optional[Any] = None,
        api_key: Optional[str] = None,
        **client_kwargs: Any,
    ) -> None:
        self.model = model
        if client is not None:
            self._client = client
        else:
            self._client = self._build_client(api_key=api_key, **client_kwargs)

    def _build_client(self, *, api_key: Optional[str], **client_kwargs: Any) -> Any:
        """Lazy-import the openai SDK and construct an AsyncOpenAI client.

        Only reached when no client was injected — keeps the SDK import out of the
        test path. Subclasses extend `client_kwargs` (e.g. `base_url`)."""
        import openai  # lazy: SDK only needed for a real, non-injected client

        kwargs: dict[str, Any] = dict(client_kwargs)
        if api_key is not None:
            kwargs["api_key"] = api_key
        return openai.AsyncOpenAI(**kwargs)

    async def complete(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> Completion:
        """Translate (system, neutral history, neutral tools) -> one native call -> Completion."""
        native_messages = _to_native_messages(system, messages)
        native_tools = _to_native_tools(tools)
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=native_messages,
            tools=native_tools,
            tool_choice="auto",
        )
        return _to_completion(resp)


class OpenAICompatibleProvider(OpenAIProvider):
    """OpenAI-compatible backend (Groq/Together/OpenRouter/Ollama/vLLM — 'other').

    Identical translation to `OpenAIProvider`; it only threads a `base_url` into the
    SDK constructor so the same Chat Completions dialect is spoken to a third-party
    endpoint. As with the base provider, the SDK is lazy-imported only when no client
    is injected, so an injected fake keeps tests SDK-free."""

    provider_name: str = "openai-compatible"

    def __init__(
        self,
        model: str,
        *,
        base_url: str,
        client: Optional[Any] = None,
        api_key: Optional[str] = None,
        **client_kwargs: Any,
    ) -> None:
        self.base_url = base_url
        super().__init__(
            model,
            client=client,
            api_key=api_key,
            base_url=base_url,
            **client_kwargs,
        )


# ── Neutral -> native translation (pure, unit-testable) ──────────────────────────

def _to_native_messages(system: str, messages: list[dict]) -> list[dict]:
    """Render (system arg + neutral history) into native OpenAI chat messages.

    The system arg is prepended as a `{"role":"system"}` message. Then each neutral
    role maps to its OpenAI shape:

      * user           -> {"role":"user","content":text}
      * assistant      -> {"role":"assistant","tool_calls":[{id,type:function,
                            function:{name,arguments:json.dumps(input)}}]} (+ content)
      * tool_results   -> ONE {"role":"tool","tool_call_id":id,"content":content}
                          message PER result, in order.
    """
    native: list[dict] = []
    if system:
        native.append({"role": "system", "content": system})

    for msg in messages:
        role = msg.get("role")
        if role == "user":
            native.append({"role": "user", "content": msg.get("content", "")})
        elif role == "assistant":
            entry: dict[str, Any] = {"role": "assistant"}
            text = msg.get("text") or ""
            # OpenAI requires `content` to be present (may be null) alongside tool_calls.
            entry["content"] = text or None
            calls = msg.get("tool_calls") or []
            if calls:
                entry["tool_calls"] = [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {
                            "name": c["name"],
                            "arguments": json.dumps(c.get("input", {})),
                        },
                    }
                    for c in calls
                ]
            native.append(entry)
        elif role == "tool_results":
            for res in msg.get("results", []):
                native.append(
                    {
                        "role": "tool",
                        "tool_call_id": res["id"],
                        "content": res.get("content", ""),
                    }
                )
        else:  # pragma: no cover - defensive; the loop only emits the three roles
            raise ValueError(f"Unknown neutral message role: {role!r}")

    return native


def _to_native_tools(tools: list[dict]) -> list[dict]:
    """Wrap each neutral {name, description, input_schema} tool in OpenAI's envelope."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]


def _to_completion(resp: Any) -> Completion:
    """Normalize a native OpenAI chat-completion response into a neutral `Completion`.

    Reads `resp.choices[0]`: its `.message.tool_calls` (each `.id`, `.function.name`,
    `.function.arguments` as a JSON STRING -> parsed to a dict) become `ToolCall`s;
    `.message.content` becomes `text`; `.finish_reason` becomes `stop_reason`."""
    choice = resp.choices[0]
    message = choice.message

    tool_calls: list[ToolCall] = []
    for tc in getattr(message, "tool_calls", None) or []:
        raw_args = tc.function.arguments
        if isinstance(raw_args, str):
            parsed = json.loads(raw_args) if raw_args else {}
        else:
            # Some compatible backends already hand back a parsed object.
            parsed = raw_args or {}
        tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, input=parsed))

    text = getattr(message, "content", None) or ""
    stop_reason = getattr(choice, "finish_reason", None) or ""
    return Completion(tool_calls=tool_calls, text=text, stop_reason=stop_reason)
