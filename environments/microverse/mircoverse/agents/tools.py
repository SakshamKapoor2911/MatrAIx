"""The four canonical agent tools, provider-neutral (Protocol.md §7.2).

Protocol.md §7.2 fixes the reference agent's tool surface at EXACTLY FOUR tools, each
mapping to a NORMATIVE §5 endpoint. This module defines those four as vendor-neutral
dicts ({name, description, input_schema}) and the parsers that turn a model's
`submit_action` / `submit_reflection` arguments back into the frozen Pydantic
contracts — validating them, and raising a feedable error on violation so the loop
can hand the model a correction and retry.

    read_memory(ref)            -> GET /agents/{id}/memory/{file}?ref=<entry>
    search_memory(file, pattern)-> GET /agents/{id}/memory/{file}?q=<kw>  (LEXICAL, §6.2)
    submit_action(envelope)     -> POST /agents/{id}/action  (the one tick decision)
    submit_reflection(identity) -> POST /agents/{id}/reflection  (only on revision, §6.3)

CROSS-PROVIDER NOTE — `submit_action`'s `input_schema` is deliberately PERMISSIVE.
The §4 `Action` is a discriminated union (params keyed on `type`); inlining that as
`$defs`/`anyOf` makes Bedrock and OpenAI choke. So the tool advertises a flat,
freeform `params` object and we enforce the real shape *server-side of the boundary*
by validating through the frozen Pydantic contracts in `parse_submit_action`. The
JSON-Schema is a hint to the model; the Pydantic models are the law.
"""

from __future__ import annotations

from typing import Optional

from pydantic import ValidationError

from mircoverse.agents.mock_llm import LLMDecision, LLMReflection
from mircoverse.contracts import (
    Action,
    ActionType,
    MemoryUpdate,
    SoulFile,
)


class ToolValidationError(Exception):
    """A tool's arguments failed contract validation.

    Carries a human-readable `message` the loop can feed straight back to the model
    as a tool-result so it can correct and retry (rather than crashing the tick)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# ── The four neutral tool definitions (Protocol.md §7.2) ────────────────────────

READ_MEMORY: dict = {
    "name": "read_memory",
    "description": (
        "Pull the full text of one long-term memory entry by its index ref "
        "(e.g. 'events#88' or 'relationships#agent_03'), or a whole file when ref "
        "names only a file (e.g. 'reflections'). Call this AFTER judging the "
        "memory_index that arrived in your observation — only for entries a decision "
        "needs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ref": {
                "type": "string",
                "description": "Index ref like 'events#88', or a bare file name.",
            },
        },
        "required": ["ref"],
    },
}

SEARCH_MEMORY: dict = {
    "name": "search_memory",
    "description": (
        "Keyword (substring/regex) scan over one of your markdown memory files. "
        "This is 'grep your own notes' — LEXICAL, not semantic: there are no "
        "embeddings. Use it to find an old fact the compact index did not summarize."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "file": {
                "type": "string",
                "enum": ["events", "relationships", "reflections"],
                "description": "Which memory file to scan.",
            },
            "pattern": {
                "type": "string",
                "description": "Substring or regex to match against the file's lines.",
            },
        },
        "required": ["file", "pattern"],
    },
}

SUBMIT_ACTION: dict = {
    "name": "submit_action",
    "description": (
        "Submit this tick's single decision: one action (+ optional memory write + "
        "optional rationale). Exactly one submit_action call ends your turn. The "
        "action.type is one of the eight world verbs; put its arguments in `params`."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": [t.value for t in ActionType],
                "description": "The action verb for this tick.",
            },
            "params": {
                "type": "object",
                "description": (
                    "Arguments for the chosen action.type. Shape depends on the verb: "
                    "move: {toward:[x,y]} OR {direction:'N'..'NW'}; "
                    "consume: {resource:'water'|'food'|'goods', amount:int} (from your cell); "
                    "talk: {target:'agent_id'|broadcast:true, message:str, location_claim?:[x,y]} "
                    "(received NEXT turn; truth not checked); "
                    "trade: {target:'agent_id', offer:{res:int}, request:{res:int}} — completes ONLY "
                    "if BOTH name each other this turn, are adjacent, and terms mirror "
                    "(your offer == their request); talking about a trade does not perform one; "
                    "attack: {target:'agent_id'} (must be adjacent); "
                    "signal: {stance:'friendly'|'neutral'|'aggressive'}; "
                    "wait/scavenge: {} (none)."
                ),
                "additionalProperties": True,
            },
            "memory_update": {
                "type": ["object", "null"],
                "description": (
                    "Optional subjective-memory delta to write this tick: "
                    "{file: events|relationships|reflections, op: append|update, "
                    "subject_agent_id (required for relationships), importance 1-10, "
                    "content}."
                ),
            },
            "importance": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": "How much this tick matters (1-10), accruing toward reflection.",
            },
            "intention": {
                "type": ["string", "null"],
                "description": (
                    "Optional single line of what you are currently trying to do. It "
                    "carries forward to your next turns until you change it; omit it to "
                    "leave your prior intention standing. No mechanical effect — logged."
                ),
            },
            "rationale": {
                "type": "string",
                "description": "Optional free-text reasoning; logged, no mechanical effect.",
            },
        },
        "required": ["type"],
    },
}

SUBMIT_REFLECTION: dict = {
    "name": "submit_reflection",
    "description": (
        "Use ONLY when a reflection genuinely warrants revising who you are (§6.3). "
        "Never required to end a tick. Provide a summary; set revises_identity true "
        "and supply the full new_identity only if you are deliberately changing it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "What you concluded from reviewing recent events.",
            },
            "revises_identity": {
                "type": "boolean",
                "description": "True only if you are deliberately revising your identity.",
            },
            "new_identity": {
                "type": ["object", "null"],
                "description": "The full replacement soul when revises_identity is true.",
                "properties": {
                    "core_values": {"type": "array", "items": {"type": "string"}},
                    "moral_boundaries": {"type": "array", "items": {"type": "string"}},
                    "personality": {"type": "string"},
                    "goals": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "required": ["summary"],
    },
}

# The two per-call tool sets (Protocol.md §7.2). decide gets submit_action;
# reflect gets submit_reflection. Both keep the read/search retrieval tools.
DECIDE_TOOLS: list[dict] = [READ_MEMORY, SEARCH_MEMORY, SUBMIT_ACTION]
REFLECT_TOOLS: list[dict] = [READ_MEMORY, SEARCH_MEMORY, SUBMIT_REFLECTION]


# ── Parsers: model arguments -> frozen contracts, validated ─────────────────────

def parse_submit_action(input: dict) -> LLMDecision:
    """Validate a `submit_action` argument object into an `LLMDecision` (Protocol §4.2).

    Assembles + validates through the frozen Pydantic `Action` (which enforces the
    type↔params discriminated union) and, when present, `MemoryUpdate`. On any
    pydantic `ValidationError` (or a structurally wrong payload) raises
    `ToolValidationError` with a readable message for a model retry."""
    if not isinstance(input, dict):
        raise ToolValidationError(f"submit_action expects an object, got {type(input).__name__}.")

    raw_type = input.get("type")
    if raw_type is None:
        raise ToolValidationError("submit_action requires a `type` (one of the eight action verbs).")

    params = input.get("params") or {}
    if not isinstance(params, dict):
        raise ToolValidationError("`params` must be an object.")

    try:
        action = Action(type=raw_type, params=params)
    except ValidationError as exc:
        raise ToolValidationError(f"Invalid action: {_fmt(exc)}") from exc

    memory_update: Optional[MemoryUpdate] = None
    raw_mu = input.get("memory_update")
    if raw_mu is not None:
        if not isinstance(raw_mu, dict):
            raise ToolValidationError("`memory_update` must be an object or null.")
        try:
            memory_update = MemoryUpdate(**raw_mu)
        except ValidationError as exc:
            raise ToolValidationError(f"Invalid memory_update: {_fmt(exc)}") from exc

    importance = input.get("importance", 0)
    try:
        importance = int(importance)
    except (TypeError, ValueError):
        raise ToolValidationError("`importance` must be an integer.") from None

    rationale = input.get("rationale") or ""
    if not isinstance(rationale, str):
        raise ToolValidationError("`rationale` must be a string.")

    intention = input.get("intention")
    if intention is not None and not isinstance(intention, str):
        raise ToolValidationError("`intention` must be a string or null.")

    return LLMDecision(
        action=action,
        memory_update=memory_update,
        importance=importance,
        rationale=rationale,
        intention=intention or None,
    )


def parse_submit_reflection(input: dict) -> LLMReflection:
    """Validate a `submit_reflection` argument object into an `LLMReflection` (§6.3).

    When `revises_identity` is true, `new_identity` is validated into a `SoulFile`;
    otherwise `new_identity` is forced to None (most reflections do not revise)."""
    if not isinstance(input, dict):
        raise ToolValidationError(
            f"submit_reflection expects an object, got {type(input).__name__}."
        )

    summary = input.get("summary")
    if not isinstance(summary, str) or not summary:
        raise ToolValidationError("submit_reflection requires a non-empty `summary` string.")

    revises = bool(input.get("revises_identity", False))
    new_identity: Optional[SoulFile] = None
    if revises:
        raw = input.get("new_identity")
        if not isinstance(raw, dict):
            raise ToolValidationError(
                "revises_identity is true but `new_identity` is missing or not an object."
            )
        try:
            new_identity = SoulFile(**raw)
        except ValidationError as exc:
            raise ToolValidationError(f"Invalid new_identity: {_fmt(exc)}") from exc

    return LLMReflection(summary=summary, revises_identity=revises, new_identity=new_identity)


def _fmt(exc: ValidationError) -> str:
    """Compact, model-readable rendering of a pydantic ValidationError."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ())) or "(root)"
        parts.append(f"{loc}: {err.get('msg', 'invalid')}")
    return "; ".join(parts)
