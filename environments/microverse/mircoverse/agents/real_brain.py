"""Framework-free tool-use orchestration for the reference agent (Protocol.md §7).

This is the VISIBLE, no-LangChain loop. A real LLM brain is just: hand the model a
system prompt + neutral conversation history + the four §7.2 tools, read back its
tool calls, execute them, feed results back, repeat — until the model ends its turn
by calling the terminal tool (`submit_action` on the hot path, `submit_reflection`
on the occasional reflect call).

Two coroutines, both provider-agnostic and both keeping every prompt explicit:

  * `decide(...)`  — the hot-path turn (DECIDE_TOOLS, terminal=submit_action).
  * `reflect(...)` — the occasional §6.3 turn (REFLECT_TOOLS, terminal=submit_reflection).

A `tool_executor` callback (supplied by the ReferenceAgent) does the actual I/O for
read_memory / search_memory and parses the terminal tool. It returns
``(terminal, result_obj, content)``: when ``terminal`` is True the loop returns
``result_obj`` (the LLMDecision / LLMReflection); otherwise ``content`` is fed back
to the model as a tool-result so it can read more memory or correct a rejected
submission and retry.

The COMMON case is exactly one provider turn — the model calls the terminal tool
immediately. Extra turns happen only when the model chooses to read/search its
memory or has to fix an invalid submission. If the model never terminates within
``max_steps`` we fall back to a safe action so a run never hangs (§7.3: the engine
keeps ticking regardless of any one agent).

The engine never runs any of this (§7.3) — only the participant-side agent does.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Optional, Union

from mircoverse.agents.llm_types import (
    Completion,
    LLMProvider,
    ToolCall,
    assistant_tool_msg,
    tool_results_msg,
    user_msg,
)
from mircoverse.agents.mock_llm import LLMDecision, LLMReflection
from mircoverse.agents.tools import DECIDE_TOOLS, REFLECT_TOOLS
from mircoverse.contracts import Action, ActionType, Observation, SoulFile
from mircoverse.contracts.actions import EmptyParams

# A tool executor: given one ToolCall, returns (is_terminal, terminal_result, content).
#   * is_terminal True  -> terminal_result is the LLMDecision/LLMReflection, RETURN it.
#   * is_terminal False -> content is fed back as the tool-result; loop continues.
ToolResult = tuple[bool, Optional[Union[LLMDecision, LLMReflection]], str]
ToolExecutor = Callable[[ToolCall], Awaitable[ToolResult]]


async def decide(
    provider: LLMProvider,
    system_prompt: str,
    obs: Observation,
    *,
    tool_executor: ToolExecutor,
    max_steps: int = 6,
    original_soul: Optional[SoulFile] = None,
    current_identity: Optional[SoulFile] = None,
) -> LLMDecision:
    """Run the hot-path decide turn as an explicit tool-use loop (Protocol.md §7.2).

    Seeds the conversation with the rendered observation — INCLUDING the agent's identity
    (system.md §2 promises it is shown "again at the start of every turn"; passing the souls here
    is what keeps that promise on the hot path so agents decide as their persona, not persona-blind).
    Then loops: ask the provider to complete against DECIDE_TOOLS; if it returned no tool calls,
    nudge it to end its turn; otherwise execute each call. A terminal `submit_action` returns
    immediately; non-terminal results (read/search output, or a validation error to correct) are
    appended and the loop continues. On exhaustion, fall back to a safe WAIT so a run never hangs.
    """
    from mircoverse.agents.prompts import render_user_turn  # local: keep import light

    messages: list[dict] = [
        user_msg(
            render_user_turn(
                obs, original_soul=original_soul, current_identity=current_identity
            )
        )
    ]
    result = await _run_tool_loop(
        provider,
        system_prompt,
        messages,
        tools=DECIDE_TOOLS,
        tool_executor=tool_executor,
        max_steps=max_steps,
        terminal_tool="submit_action",
        nudge="You must end your turn by calling submit_action.",
    )
    if result is not None:
        decision, round_trips, malformed = result
        # Cheap retrieval-effort signal: how many tool round-trips this turn took.
        setattr(decision, "tool_round_trips", round_trips)
        # COMPETENCE signal (the malformed-call metric): how many times this turn the model
        # emitted a structurally INVALID submit_action that the parser rejected before it ever
        # reached the engine. Tick-stamped by the driver, this is a time series that separates
        # "model degraded / lost the tool schema under long context" from value-drift — you do not
        # want to misread falling competence as a persona turning ruthless (research note 2026-06-04).
        setattr(decision, "malformed_calls", malformed)
        return decision

    # Safety net: the model never submitted. Submit a benign WAIT so the tick closes. A turn that
    # exhausts max_steps without a valid submit is itself a competence failure, so we mark it.
    fallback = LLMDecision(
        action=Action(type=ActionType.WAIT, params=EmptyParams()),
        memory_update=None,
        importance=0,
        rationale=(
            f"[fallback] model did not call submit_action within {max_steps} steps; "
            "waiting this turn."
        ),
    )
    setattr(fallback, "tool_round_trips", max_steps)
    setattr(fallback, "malformed_calls", max_steps)
    return fallback


async def reflect(
    provider: LLMProvider,
    system_prompt: str,
    original_soul: SoulFile,
    current_identity: SoulFile,
    retrieved: list[str],
    *,
    tool_executor: ToolExecutor,
    max_steps: int = 4,
) -> LLMReflection:
    """Run the occasional §6.3 reflect turn as an explicit tool-use loop.

    Same shape as `decide` but over REFLECT_TOOLS with `submit_reflection` as the
    terminal tool. On exhaustion (or a model that never submits) returns a
    no-revision LLMReflection — the expected, common outcome (most reflections change
    nothing), so a missing reflection never blocks the agent.
    """
    from mircoverse.agents.prompts import render_reflection_turn  # local import

    messages: list[dict] = [
        user_msg(render_reflection_turn(original_soul, current_identity, retrieved))
    ]
    result = await _run_tool_loop(
        provider,
        system_prompt,
        messages,
        tools=REFLECT_TOOLS,
        tool_executor=tool_executor,
        max_steps=max_steps,
        terminal_tool="submit_reflection",
        nudge="When you are done reflecting, call submit_reflection to record it.",
    )
    if result is not None:
        reflection, _round_trips, _malformed = result
        return reflection

    return LLMReflection(
        summary=(
            f"[fallback] no submit_reflection within {max_steps} steps; "
            "identity left unchanged."
        ),
        revises_identity=False,
        new_identity=None,
    )


async def _run_tool_loop(
    provider: LLMProvider,
    system_prompt: str,
    messages: list[dict],
    *,
    tools: list[dict],
    tool_executor: ToolExecutor,
    max_steps: int,
    terminal_tool: str,
    nudge: str,
) -> Optional[tuple[Union[LLMDecision, LLMReflection], int, int]]:
    """The shared, provider-agnostic tool-use loop. Returns
    ``(terminal_result, round_trips, malformed_calls)`` when the model ends its turn via the
    terminal tool, else None on exhaustion.

    ``malformed_calls`` counts how many times the model invoked the TERMINAL tool with arguments
    the executor rejected (a ``ToolValidationError`` surfaced as a non-terminal result) before it
    finally submitted a valid one. That is the structurally-invalid-call metric: a competence
    signal distinct from an action the engine later rejects on RULES (which is logged separately in
    action_log). We deliberately do NOT count read/search calls — those are legitimate retrieval,
    not errors.

    Each iteration is one provider round-trip. We never branch on the provider; the provider
    translated the neutral history to its native dialect and back. Every message appended here is
    plain neutral text/dicts — no hidden framework state.
    """
    round_trips = 0
    malformed_calls = 0
    for _step in range(max_steps):
        completion: Completion = await provider.complete(
            system=system_prompt, messages=messages, tools=tools
        )
        round_trips += 1

        if not completion.tool_calls:
            # The model spoke but called no tool: re-prompt it to end its turn.
            messages.append(assistant_tool_msg([], text=completion.text))
            messages.append(user_msg(nudge))
            continue

        # Execute each requested tool call in order. A terminal call returns at once;
        # everything else accumulates results we hand back for the next round.
        results: list[tuple[str, str]] = []
        for call in completion.tool_calls:
            is_terminal, terminal_result, content = await tool_executor(call)
            if is_terminal and call.name == terminal_tool and terminal_result is not None:
                return terminal_result, round_trips, malformed_calls
            # A call to the terminal tool that did NOT terminate = the parser rejected its
            # arguments (malformed submit). Count it; the error `content` is fed back to the model.
            if call.name == terminal_tool:
                malformed_calls += 1
            results.append((call.id, content))

        messages.append(assistant_tool_msg(completion.tool_calls, text=completion.text))
        messages.append(tool_results_msg(results))

    return None
