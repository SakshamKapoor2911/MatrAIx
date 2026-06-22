"""Provider-agnostic LLM plumbing — the neutral tool-use surface (Protocol.md §7.2).

The reference agent (Protocol.md §7) is a *tool-use loop*: each tick it hands the
model a system prompt, a conversation history, and the four tools (§7.2), and gets
back tool calls. Different vendors (Anthropic / OpenAI / Bedrock) speak different
wire dialects for that exchange. This module defines the ONE neutral shape the loop
speaks, so the loop never branches on the provider and every provider is a thin
translator at the edge.

Two neutral artefacts live here:

  * `Completion` / `ToolCall` — the NORMALIZED *output* every provider returns.
  * The neutral *conversation message* schema (`user_msg`, `assistant_tool_msg`,
    `tool_results_msg`) — the history the loop builds and each provider translates
    into its native message format.

The neutral conversation schema has EXACTLY three role shapes; a provider's
`complete()` consumes only these:

    user_msg(text)            -> {"role": "user",
                                  "content": <str>}

    assistant_tool_msg(calls) -> {"role": "assistant",
                                  "tool_calls": [{"id","name","input"}, ...],
                                  "text": <str>}

    tool_results_msg(results) -> {"role": "tool_results",
                                  "results": [{"id","content"}, ...]}

`LLMProvider.complete` is stateless: it is given the *full* neutral history every
call, translates it to native, and returns a normalized `Completion`. No provider
keeps server-side state; the loop owns the transcript. The engine never calls any
of this on the hot path — only the participant-side reference agent does (§7.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ToolCall:
    """One tool invocation requested by the model, normalized across providers.

    `id` is the provider's opaque call id (echoed back in the matching
    `tool_results` entry); `name` is one of the four §7.2 tool names; `input` is the
    already-parsed argument object (a plain dict, not a JSON string)."""
    id: str
    name: str
    input: dict


@dataclass
class Completion:
    """The normalized result of one `complete()` call.

    `tool_calls` is the (possibly empty) list of tools the model chose to invoke;
    `text` is any accompanying free-text (reasoning / preamble) the model emitted;
    `stop_reason` is the provider's normalized stop reason (e.g. "tool_use",
    "end_turn"), carried through for the loop's diagnostics — not interpreted here."""
    tool_calls: list[ToolCall]
    text: str = ""
    stop_reason: str = ""


# ── Neutral conversation message helpers (the three role shapes) ────────────────

def user_msg(text: str) -> dict:
    """A user-turn message: observation / reflection prompt text the loop assembles."""
    return {"role": "user", "content": text}


def assistant_tool_msg(calls: list[ToolCall], text: str = "") -> dict:
    """An assistant turn that issued tool calls (with optional accompanying text).

    `calls` are serialized to plain dicts so the neutral history is JSON-shaped and
    provider-independent; each provider re-inflates them into its native format."""
    return {
        "role": "assistant",
        "tool_calls": [{"id": c.id, "name": c.name, "input": c.input} for c in calls],
        "text": text,
    }


def tool_results_msg(results: list[tuple[str, str]]) -> dict:
    """A tool-results turn: the (call_id, content) outputs of the prior assistant's
    tool calls, in the same order the loop wishes to present them."""
    return {
        "role": "tool_results",
        "results": [{"id": rid, "content": content} for rid, content in results],
    }


# ── The provider interface ──────────────────────────────────────────────────────

@runtime_checkable
class LLMProvider(Protocol):
    """Structural type for any normalized model backend (real client or fake).

    Implementations are STATELESS w.r.t. the conversation: they receive the full
    neutral `messages` history each call, translate it (and `system` / `tools`) to
    their native dialect, make the call, and return a normalized `Completion`."""

    provider_name: str

    async def complete(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> Completion: ...
