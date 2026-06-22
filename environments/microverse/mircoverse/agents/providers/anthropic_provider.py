"""Anthropic (Claude) provider for the reference agent's tool-use loop (Protocol.md §7).

A thin translator at the edge of the neutral `complete(system, messages, tools)`
surface (mircoverse/agents/llm_types.py). It speaks the Anthropic Messages dialect:
the neutral three-role history is rendered into native `messages` blocks every call
(the provider is STATELESS — it never holds server-side conversation state), the
four §7.2 tool dicts are passed straight through (Anthropic's tool envelope already
uses `{name, description, input_schema}` verbatim), and the response's content
blocks are normalized back into a `Completion` of `ToolCall`s + text.

The `anthropic` SDK is LAZY-imported: only when no `client` is injected do we touch
`anthropic.AsyncAnthropic`. Tests inject a fake client, so the suite runs with no
SDK installed, no API key, and no network. The engine never calls any of this on the
hot path (§7.3) — only the participant-side reference agent does.
"""

from __future__ import annotations

from typing import Any, Optional

from mircoverse.agents.llm_types import Completion, ToolCall

# Anthropic's API caps the response; the reference agent's turns are small (one
# tool call + brief preamble), so a modest ceiling is ample headroom.
_DEFAULT_MAX_TOKENS = 2048


class AnthropicProvider:
    """`LLMProvider` over Anthropic's Messages API (anthropic>=0.25).

    Construct with a model id; the `anthropic.AsyncAnthropic` client is built lazily
    on first construction *only when no `client` is injected*, so tests can pass a
    fake exposing just `messages.create(...)`. `max_tokens` and any extra create-time
    kwargs (e.g. `temperature`) may be supplied at construction and are forwarded on
    every call. `api_key` is optional — when omitted the SDK reads ANTHROPIC_API_KEY.
    """

    provider_name: str = "anthropic"

    def __init__(
        self,
        model: str,
        *,
        client: Any = None,
        api_key: Optional[str] = None,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        **create_kwargs: Any,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        # Extra per-call create kwargs (temperature, top_p, …). Kept verbatim and
        # spread into every messages.create call.
        self._create_kwargs = dict(create_kwargs)
        if client is not None:
            self._client = client
        else:
            # LAZY import: only reached when no fake client is injected, so the test
            # suite (which always injects) never requires the SDK to be installed.
            import anthropic  # noqa: PLC0415  (intentional lazy import)

            self._client = anthropic.AsyncAnthropic(api_key=api_key)

    # ── the neutral surface ──────────────────────────────────────────────────
    async def complete(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> Completion:
        """Translate the neutral request to native, call Claude, normalize the reply.

        `messages` is the full neutral history (the provider is stateless); `tools`
        are the neutral §7.2 dicts, which Anthropic accepts verbatim. Returns a
        `Completion` whose `tool_calls` carry already-parsed dict inputs.
        """
        native_messages = _to_native_messages(messages)
        resp = await self._client.messages.create(
            model=self.model,
            system=system,
            messages=native_messages,
            tools=tools,
            max_tokens=self.max_tokens,
            **self._create_kwargs,
        )
        return _from_native_response(resp)


# ── pure translators (kept module-level + unit-testable) ────────────────────────

def _to_native_messages(messages: list[dict]) -> list[dict]:
    """Render the neutral three-role history into Anthropic `messages` blocks.

    Mapping (Anthropic content-block dialect):
      * user           -> {"role":"user","content":[{"type":"text","text":...}]}
      * assistant      -> {"role":"assistant","content":[{"type":"tool_use",...}
                            (+ a leading {"type":"text"} when text is present)]}
      * tool_results   -> {"role":"user","content":[{"type":"tool_result",
                            "tool_use_id":id,"content":...}, ...]}

    Pure: no I/O, no SDK. An unknown role raises `ValueError` so a malformed history
    fails loudly rather than being silently dropped on the wire.
    """
    native: list[dict] = []
    for msg in messages:
        role = msg.get("role")
        if role == "user":
            native.append(
                {
                    "role": "user",
                    "content": [{"type": "text", "text": msg.get("content", "")}],
                }
            )
        elif role == "assistant":
            content: list[dict] = []
            text = msg.get("text") or ""
            if text:
                content.append({"type": "text", "text": text})
            for call in msg.get("tool_calls", []):
                content.append(
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call.get("input", {}),
                    }
                )
            native.append({"role": "assistant", "content": content})
        elif role == "tool_results":
            native.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": res["id"],
                            "content": res.get("content", ""),
                        }
                        for res in msg.get("results", [])
                    ],
                }
            )
        else:
            raise ValueError(f"Unknown neutral message role: {role!r}")
    return native


def _from_native_response(resp: Any) -> Completion:
    """Normalize an Anthropic Messages response into a neutral `Completion`.

    Walks `resp.content` (a list of blocks): `tool_use` blocks become `ToolCall`s
    (with `input` kept as the parsed dict the SDK already provides), `text` blocks
    are concatenated into `Completion.text`. `resp.stop_reason` is carried through.
    """
    tool_calls: list[ToolCall] = []
    text_parts: list[str] = []
    for block in getattr(resp, "content", []) or []:
        btype = getattr(block, "type", None)
        if btype == "tool_use":
            raw_input = getattr(block, "input", {})
            tool_calls.append(
                ToolCall(
                    id=getattr(block, "id", ""),
                    name=getattr(block, "name", ""),
                    input=dict(raw_input) if isinstance(raw_input, dict) else raw_input,
                )
            )
        elif btype == "text":
            text_parts.append(getattr(block, "text", "") or "")
    return Completion(
        tool_calls=tool_calls,
        text="".join(text_parts),
        stop_reason=getattr(resp, "stop_reason", "") or "",
    )
