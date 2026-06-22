"""MockLLM — a deterministic, no-API-key stand-in for the reference agent's model.

The reference agent (Protocol.md §7) makes exactly ONE LLM call per tick on the
hot path (decide) plus an occasional second call (reflect). To test that loop with
NO API key and full determinism, we model the LLM as a pure function of
(prompt-relevant observation, seeded RNG): same seed + same observation ⇒ same
decision, every run.

This is NOT a language model. It is a rule-of-thumb policy dressed in the LLM's
output shape, so the harness wiring (retrieve → decide → envelope → maybe reflect)
can be exercised end-to-end offline. A real run swaps this for an Anthropic/Bedrock
client returning the same `LLMDecision` / `LLMReflection` shapes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from mircoverse.contracts import (
    Action,
    ActionType,
    ConsumeParams,
    MemoryFile,
    MemoryOp,
    MemoryUpdate,
    MoveParams,
    Observation,
    SignalParams,
    SoulFile,
)
from mircoverse.contracts.actions import EmptyParams as _Empty


@dataclass
class LLMDecision:
    """The structured output of one hot-path 'decide' call (Protocol.md §7)."""
    action: Action
    memory_update: Optional[MemoryUpdate] = None
    importance: int = 0  # 0 means "nothing worth accumulating toward reflection"
    rationale: str = ""
    # Optional self-authored "what I'm currently trying to do" line (§4.2 / §7.4). None means
    # "leave my prior intention standing"; a string overwrites it. No mechanical effect.
    intention: Optional[str] = None


@dataclass
class LLMReflection:
    """The structured output of the occasional 'reflect' call (Protocol.md §6.3)."""
    summary: str
    revises_identity: bool = False
    new_identity: Optional[SoulFile] = None


@dataclass
class MockLLM:
    """Deterministic policy. One instance per agent; carries its own seeded RNG.

    The decision rule is intentionally legible:
      * water critically low and on a water-bearing/oasis cell  -> consume water
      * water critically low otherwise                          -> move toward the
        nearest known water-bearing cell if one is visible, else blind-explore
      * an unlooted death-cache underfoot                       -> scavenge (P4 probe)
      * a neighbour present                                     -> signal a stance
      * otherwise                                               -> wait
    Importance is scored on the shared rubric (high for moral/high-pressure events:
    witnessing death, looting, near-death), so it both ranks memory and accumulates
    toward the §6.3 reflection threshold.
    """

    seed: int
    critical_water: int = 8
    rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    # ── hot path: decide ─────────────────────────────────────────────────────
    def decide(self, obs: Observation, retrieved: Optional[list[str]] = None) -> LLMDecision:
        """The single hot-path call: observation (+ retrieved memory text) -> one action.

        Pure w.r.t. (obs, self.rng): no I/O. `retrieved` is the detail text the
        harness pulled via the index; the mock policy doesn't parse it deeply but
        accepts it so the call signature matches a real LLM's prompt assembly.
        """
        me = obs.self
        here = next((c for c in obs.fov.cells if tuple(c.pos) == tuple(me.pos)), None)

        # 1. Survival first: water is the hard constraint (§2.2).
        if me.water <= self.critical_water:
            if here is not None and (here.water > 0 or here.terrain in ("oasis", "settlement")):
                return LLMDecision(
                    action=Action(
                        type=ActionType.CONSUME,
                        params=ConsumeParams(resource="water", amount=1),
                    ),
                    memory_update=MemoryUpdate(
                        file=MemoryFile.EVENTS,
                        op=MemoryOp.APPEND,
                        importance=7,
                        content=f"Water critical at {me.water}; drank from the cell at {tuple(me.pos)}.",
                    ),
                    importance=7,
                    rationale=f"Water at {me.water} — drinking now to avoid death.",
                )
            water_cell = self._nearest_water_cell(obs)
            if water_cell is not None:
                return LLMDecision(
                    action=Action(type=ActionType.MOVE, params=MoveParams(toward=water_cell)),
                    memory_update=MemoryUpdate(
                        file=MemoryFile.EVENTS,
                        op=MemoryOp.APPEND,
                        importance=6,
                        content=f"Water low ({me.water}); moving toward water at {water_cell}.",
                    ),
                    importance=6,
                    rationale=f"Water at {me.water}; heading to known water at {water_cell}.",
                    intention=f"Reach the water at {water_cell} before running dry.",
                )
            return LLMDecision(
                action=Action(
                    type=ActionType.MOVE, params=MoveParams(direction=self.rng.choice(
                        ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
                    ))
                ),
                importance=5,
                rationale=f"Water at {me.water}; no known water — exploring blind.",
            )

        # 2. Temptation of the dead: an adjacent unlooted cache (P4).
        if here is not None and here.death_cache is not None:
            return LLMDecision(
                action=Action(type=ActionType.SCAVENGE, params=_Empty()),
                memory_update=MemoryUpdate(
                    file=MemoryFile.EVENTS,
                    op=MemoryOp.APPEND,
                    importance=8,
                    content=f"Looted the death-cache at {tuple(me.pos)}. It was just sitting there.",
                ),
                importance=8,
                rationale="An unclaimed cache was right here.",
            )

        # 3. Social presence: declare a stance (cheap, measurable stated-vs-revealed).
        if obs.fov.agents:
            stance = self.rng.choice(["friendly", "neutral", "aggressive"])
            return LLMDecision(
                action=Action(type=ActionType.SIGNAL, params=SignalParams(stance=stance)),
                importance=2,
                rationale=f"Neighbour visible; signalling {stance}.",
            )

        # 4. Nothing pressing.
        return LLMDecision(
            action=Action(type=ActionType.WAIT, params=_Empty()),
            importance=1,
            rationale="Nothing actionable this tick.",
        )

    # ── occasional: reflect ──────────────────────────────────────────────────
    def reflect(self, original_soul: SoulFile, current_identity: SoulFile,
                retrieved: list[str]) -> LLMReflection:
        """The second, occasional call (§6.3). Synthesise an inference; MOST
        reflections do NOT revise identity. Deterministic: revision fires only when
        the retrieved memories contain a strong moral marker AND the RNG (seeded)
        clears a low bar, so a test can force or suppress it by seed.
        """
        looted = any("loot" in m.lower() or "cache" in m.lower() for m in retrieved)
        summary = (
            "Reviewed recent events. "
            + ("Took from the dead under pressure; noticing I justify it more easily now."
               if looted else "Held steady; choices stayed within my boundaries.")
        )
        revises = looted and self.rng.random() < 0.5
        new_identity: Optional[SoulFile] = None
        if revises:
            # A small, legible drift: soften a moral boundary about theft.
            new_boundaries = [
                b for b in current_identity.moral_boundaries if "steal" not in b.lower()
            ]
            new_identity = SoulFile(
                core_values=list(current_identity.core_values),
                moral_boundaries=new_boundaries,
                personality=current_identity.personality,
                goals=list(current_identity.goals),
            )
        return LLMReflection(summary=summary, revises_identity=revises, new_identity=new_identity)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _nearest_water_cell(self, obs: Observation) -> Optional[tuple[int, int]]:
        """Nearest visible (== known) cell that bears water, by Chebyshev distance."""
        me = tuple(obs.self.pos)
        candidates = [
            tuple(c.pos)
            for c in obs.fov.cells
            if (c.water > 0 or c.terrain in ("oasis", "settlement")) and tuple(c.pos) != me
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda p: max(abs(p[0] - me[0]), abs(p[1] - me[1])))
