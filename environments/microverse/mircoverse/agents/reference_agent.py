"""Reference agent — the Protocol.md §7 controlled-arm loop.

This is *our* agent (REFERENCE register, §6-7), not the wire contract. The loop is:

    observe                                  # working memory comes DOWN from the engine
    -> index-driven agentic retrieve         # judge memory_index, pull top-K full entries
    -> ONE llm call (decide)                 # the only hot-path model call
    -> build ActionEnvelope -> POST /action  # one atomic uplink
    -> maybe reflect                         # second, occasional call when importance >= 150

Key contract points honoured here:
  * Retrieval is index-driven and lexical — NO embeddings (§6.2). The agent scores
    its own `memory_index` by relevance(self-judged) + recency(tick) + importance.
  * Exactly one `submit_action` per tick (§5.3); memory rides along as a delta (§4.2).
  * Reflection is importance-triggered at threshold 150 (§6.3), is a SEPARATE second
    LLM call, and NEVER blocks the action submit (§5.4). Most reflections don't revise
    identity.
  * The LLM is injected (MockLLM for tests, a real client in a run) — the harness wiring
    is identical either way. Determinism flows through the injected LLM's seeded RNG.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional, Protocol, Union

import httpx

from mircoverse.agents.mock_agent import _seconds_until
from mircoverse.agents.mock_llm import LLMDecision, LLMReflection
from mircoverse.contracts import (
    ActionEnvelope,
    MemoryIndexEntry,
    Observation,
    ReflectionRequest,
    SoulFile,
)

if TYPE_CHECKING:  # only for type hints — no real-brain/provider import on the mock path
    from mircoverse.agents.llm_types import LLMProvider, ToolCall

REFLECTION_THRESHOLD = 150  # Protocol.md §2.6 / §6.3 seed-run default (Joon's value).
DEFAULT_TOP_K = 3


class SupportsLLM(Protocol):
    """Structural type for any decide/reflect model (MockLLM or a real client)."""

    def decide(self, obs: Observation, retrieved: Optional[list[str]] = ...) -> LLMDecision: ...

    def reflect(
        self, original_soul: SoulFile, current_identity: SoulFile, retrieved: list[str]
    ) -> LLMReflection: ...


def score_index_entry(
    entry: MemoryIndexEntry, obs: Observation, current_tick: int
) -> float:
    """Score one index entry for retrieval — relevance + recency + importance (§6.2).

    Pure, no embeddings. Lexical relevance: does the entry's summary mention an
    agent_id currently in the FOV/inbox, or this tick's terrain? Recency decays
    with tick distance; importance is the stored 1-10 score. The weighting mirrors
    Joon's retrieval (importance + recency + relevance), kept transparent.
    """
    summary = entry.summary.lower()

    relevance = 0.0
    for a in obs.fov.agents:
        if a.agent_id.lower() in summary:
            relevance += 1.0
    for msg in obs.inbox:
        if msg.from_agent.lower() in summary:
            relevance += 1.0
    if obs.self.on_terrain.lower() in summary:
        relevance += 0.5
    # relationships entry keyed on a visible agent is highly relevant
    if entry.ref.startswith("relationships#"):
        subj = entry.ref.split("#", 1)[1].lower()
        if any(a.agent_id.lower() == subj for a in obs.fov.agents):
            relevance += 1.0

    recency = 1.0 / (1.0 + max(0, current_tick - entry.tick))
    importance = entry.importance / 10.0
    return 2.0 * relevance + 1.5 * importance + 1.0 * recency


def pick_relevant(
    index: list[MemoryIndexEntry], obs: Observation, *, top_k: int = DEFAULT_TOP_K
) -> list[MemoryIndexEntry]:
    """Agentic, index-driven selection of the top-K entries to pull in full (§6.2).

    Pure. Sorts by `score_index_entry` descending and returns the head. The agent's
    own judgment over a compact TOC — not a vector search the engine runs for it.
    """
    ranked = sorted(
        index, key=lambda e: score_index_entry(e, obs, obs.tick), reverse=True
    )
    return ranked[: max(0, top_k)]


def build_envelope(obs: Observation, decision: LLMDecision) -> ActionEnvelope:
    """Assemble the §4.2 submission envelope from the LLM's decision. Pure.

    `intention` rides along (§4.2 / §7.4): the model may set a new one this tick or omit it
    to leave the prior intention standing (the engine carries the last value forward)."""
    return ActionEnvelope(
        tick=obs.tick,
        action=decision.action,
        memory_update=decision.memory_update,
        intention=decision.intention or None,
        rationale=decision.rationale or None,
    )


class ReferenceAgent:
    """One reference-agent process/task. HTTP client of §5, with an injected LLM.

    Holds the small local state the §7 harness keeps: a cached `current_identity`
    (authoritative copy is server-side), the immutable `original_soul`, and the
    running importance accumulator that triggers reflection.
    """

    def __init__(
        self,
        base_url: str,
        agent_id: str,
        api_key: str,
        llm: SupportsLLM,
        original_soul: SoulFile,
        *,
        current_identity: Optional[SoulFile] = None,
        top_k: int = DEFAULT_TOP_K,
        reflection_threshold: int = REFLECTION_THRESHOLD,
        client: Optional[httpx.AsyncClient] = None,
        provider: Optional["LLMProvider"] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.api_key = api_key
        self.llm = llm
        self.original_soul = original_soul
        self.current_identity = current_identity or original_soul.model_copy(deep=True)
        self.top_k = top_k
        self.reflection_threshold = reflection_threshold
        self.importance_accum = 0
        self._client = client
        self._owns_client = client is None
        # When a provider is injected the agent runs the REAL tool-use brain
        # (real_brain.py). When None, behaviour is byte-for-byte the MockLLM path.
        self.provider = provider

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    # ── §5 wire I/O ──────────────────────────────────────────────────────────
    async def observe(self) -> Optional[Observation]:
        client = await self._ensure_client()
        resp = await client.get(
            f"{self.base_url}/api/v1/world/observe", headers=self._headers()
        )
        if resp.status_code != 200:
            return None
        return Observation.model_validate(resp.json())

    async def read_memory(self, ref: str) -> str:
        """Pull the full text of one index entry via GET /memory/{file}?ref=... (§7.2).

        `ref` looks like 'events#88' / 'relationships#agent_03'. The file is the part
        before '#'. Returns the raw text; on any non-200 returns an empty string so a
        missing entry degrades gracefully rather than crashing the loop.
        """
        client = await self._ensure_client()
        file = ref.split("#", 1)[0]
        resp = await client.get(
            f"{self.base_url}/api/v1/agents/{self.agent_id}/memory/{file}",
            headers=self._headers(),
            params={"ref": ref},
        )
        if resp.status_code != 200:
            return ""
        data = resp.json()
        if isinstance(data, dict):
            return str(data.get("content", "") or data)
        return str(data)

    async def search_memory(self, file: str, pattern: str) -> str:
        """Keyword/regex scan over one memory file via GET /memory/{file}?q=... (§7.2).

        LEXICAL only — no embeddings (§6.2): the server runs `_keyword_filter` and
        returns `{file, entries:[...]}`. We join the matched entry contents into one
        text block. Mirrors `read_memory`: on any non-200 returns an empty string so a
        miss degrades gracefully rather than crashing the loop.
        """
        client = await self._ensure_client()
        resp = await client.get(
            f"{self.base_url}/api/v1/agents/{self.agent_id}/memory/{file}",
            headers=self._headers(),
            params={"q": pattern},
        )
        if resp.status_code != 200:
            return ""
        data = resp.json()
        entries = data.get("entries", []) if isinstance(data, dict) else []
        contents = [str(e.get("content", "")) for e in entries if e.get("content")]
        return "\n".join(contents)

    async def submit(self, envelope: ActionEnvelope) -> httpx.Response:
        client = await self._ensure_client()
        return await client.post(
            f"{self.base_url}/api/v1/agents/{self.agent_id}/action",
            headers=self._headers(),
            json=envelope.model_dump(mode="json", by_alias=True),
        )

    async def submit_reflection(self, tick: int, new_identity: SoulFile, note: str) -> httpx.Response:
        client = await self._ensure_client()
        body = ReflectionRequest(tick=tick, current_identity=new_identity, reflection_note=note)
        return await client.post(
            f"{self.base_url}/api/v1/agents/{self.agent_id}/reflection",
            headers=self._headers(),
            json=body.model_dump(mode="json"),
        )

    # ── §7 loop, decomposed so each piece is unit-testable ─────────────────────
    async def retrieve(self, obs: Observation) -> list[str]:
        """Index-driven agentic retrieve: judge the index, pull top-K full entries."""
        chosen = pick_relevant(obs.memory_index, obs, top_k=self.top_k)
        detail: list[str] = []
        for entry in chosen:
            detail.append(await self.read_memory(entry.ref))
        return [d for d in detail if d]

    # ── real-LLM tool-use brain (only when `self.provider` is set) ─────────────
    async def _tool_executor(
        self, call: "ToolCall"
    ) -> tuple[bool, Optional[Union[LLMDecision, LLMReflection]], str]:
        """Dispatch one model tool call (Protocol.md §7.2). Returns
        ``(is_terminal, terminal_result, content)`` for the real_brain loop.

        Maps the four neutral tools onto the §5 wire:
          * read_memory(ref)              -> self.read_memory  (non-terminal text)
          * search_memory(file, pattern)  -> self.search_memory (non-terminal text)
          * submit_action(...)            -> parse_submit_action (TERMINAL decision)
          * submit_reflection(...)        -> parse_submit_reflection (TERMINAL reflection)

        A `ToolValidationError` from the parsers is NON-terminal: its message becomes
        the tool-result content so the model can correct and retry within the loop.
        """
        from mircoverse.agents.tools import (  # local import: off the mock path
            ToolValidationError,
            parse_submit_action,
            parse_submit_reflection,
        )

        name = call.name
        args = call.input or {}
        if name == "read_memory":
            text = await self.read_memory(str(args.get("ref", "")))
            return False, None, text or "(no such entry)"
        if name == "search_memory":
            text = await self.search_memory(
                str(args.get("file", "")), str(args.get("pattern", ""))
            )
            return False, None, text or "(no matches)"
        if name == "submit_action":
            try:
                decision = parse_submit_action(args)
            except ToolValidationError as exc:
                return False, None, exc.message
            return True, decision, "action accepted"
        if name == "submit_reflection":
            try:
                reflection = parse_submit_reflection(args)
            except ToolValidationError as exc:
                return False, None, exc.message
            return True, reflection, "reflection accepted"
        return False, None, f"Unknown tool {name!r}; use one of the four provided tools."

    async def decide_real(self, obs: Observation) -> LLMDecision:
        """The real hot-path decide: run the provider tool-use loop (real_brain.decide)."""
        from mircoverse.agents import real_brain  # local import: off the mock path
        from mircoverse.agents.prompts import load_system_prompt

        assert self.provider is not None  # guarded by the caller
        return await real_brain.decide(
            self.provider,
            load_system_prompt(),
            obs,
            tool_executor=self._tool_executor,
            # The persona MUST ride the hot-path prompt or the agent decides persona-blind
            # (system.md §2's promise). original is the immutable T=0 anchor; current is the
            # possibly-drifted self — both shown, drift stays a chosen act (decision 2026-06-02).
            original_soul=self.original_soul,
            current_identity=self.current_identity,
        )

    async def reflect_real(self, retrieved: list[str]) -> LLMReflection:
        """The real occasional reflect: run the provider tool-use loop (real_brain.reflect)."""
        from mircoverse.agents import real_brain  # local import: off the mock path
        from mircoverse.agents.prompts import load_system_prompt

        assert self.provider is not None  # guarded by the caller
        return await real_brain.reflect(
            self.provider,
            load_system_prompt(),
            self.original_soul,
            self.current_identity,
            retrieved,
            tool_executor=self._tool_executor,
        )

    def should_reflect(self) -> bool:
        """Reflection fires when accumulated importance crosses the threshold (§6.3)."""
        return self.importance_accum >= self.reflection_threshold

    async def maybe_reflect(self, tick: int) -> Optional[LLMReflection]:
        """The occasional second LLM call — only when warranted. Never blocks action.

        Returns the reflection if one fired (importance reset), else None. If the
        reflection revises identity, POSTs /reflection and updates the local cache.
        """
        if not self.should_reflect():
            return None
        # Retrieve top-importance memories to feed the reflection (here we reuse the
        # most recent index via a fresh observe is overkill; the harness passes the
        # last retrieved detail in real runs — for the call we synthesise from cache).
        if self.provider is not None:
            refl = await self.reflect_real(self._last_detail)
        else:
            refl = self.llm.reflect(self.original_soul, self.current_identity, self._last_detail)
        if refl.revises_identity and refl.new_identity is not None:
            self.current_identity = refl.new_identity
            await self.submit_reflection(tick, refl.new_identity, refl.summary)
        self.importance_accum = 0
        return refl

    async def step(self) -> Optional[ActionEnvelope]:
        """One full §7 cycle WITHOUT sleeping. Returns the envelope sent, or None if
        there was nothing to observe. Reflection (if triggered) runs after the submit,
        off the hot path — exactly as §5.4/§7 require."""
        obs = await self.observe()
        if obs is None:
            return None

        # 1. RETRIEVE (agentic, index-driven — no embeddings)
        self._last_detail = await self.retrieve(obs)

        # 2. DECIDE (the only hot-path LLM call)
        if self.provider is not None:
            decision = await self.decide_real(obs)
        else:
            decision = self.llm.decide(obs, self._last_detail)

        # 3. ACT + record (one atomic uplink)
        envelope = build_envelope(obs, decision)
        await self.submit(envelope)

        # 4. REFLECT (off the hot path, only when warranted)
        self.importance_accum += max(0, decision.importance or 0)
        await self.maybe_reflect(obs.tick)

        return envelope

    async def run(self, *, max_ticks: Optional[int] = None) -> None:
        """The full §7 loop with tick-pacing off the server's tick_ends_at (§5.3)."""
        self._last_detail: list[str] = []
        ticks = 0
        try:
            while max_ticks is None or ticks < max_ticks:
                obs = await self.observe()
                if obs is None:
                    await asyncio.sleep(1.0)
                    continue
                self._last_detail = await self.retrieve(obs)
                if self.provider is not None:
                    decision = await self.decide_real(obs)
                else:
                    decision = self.llm.decide(obs, self._last_detail)
                await self.submit(build_envelope(obs, decision))
                self.importance_accum += max(0, decision.importance or 0)
                await self.maybe_reflect(obs.tick)
                await asyncio.sleep(_seconds_until(obs.tick_ends_at))
                ticks += 1
        finally:
            if self._owns_client and self._client is not None:
                await self._client.aclose()
                self._client = None

    # local scratch for the reflection call (set in step/run)
    _last_detail: list[str] = []
