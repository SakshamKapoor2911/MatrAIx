"""Pure game state + tick state machine for the Starclash task.

This module has NO LLM calls and NO I/O beyond what is explicitly passed in
by the caller (a "brain" callable/object per persona, supplied at tick time).
It is intentionally self-contained so it can be unit tested or driven by any
CLI/harness without pulling in Anthropic SDKs, argparse, or file I/O.

State machine summary (see task spec for full detail):

  Sub-step 1 - Forced battle card submissions (state == BATTLE_CARD_PENDING)
  Sub-step 2 - Forced challenge responses   (state == PENDING_CHALLENGE)
  Sub-step 3 - Free actions                  (state == FREE)

Only personas eligible for a given sub-step receive a brain call in that
sub-step, bounding brain calls to at most one per persona per tick.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

CARD_TYPES = ("Rock", "Paper", "Scissors")

# Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
_BEATS = {
    "Rock": "Scissors",
    "Scissors": "Paper",
    "Paper": "Rock",
}


class PersonaLifeState(str, Enum):
    FREE = "FREE"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    PENDING_CHALLENGE = "PENDING_CHALLENGE"
    BATTLE_CARD_PENDING = "BATTLE_CARD_PENDING"
    ELIMINATED = "ELIMINATED"


@dataclass
class PersonaState:
    id: str
    display_name: str
    traits: Dict[str, Any] = field(default_factory=dict)
    stars: int = 3
    hand: List[str] = field(default_factory=list)
    state: PersonaLifeState = PersonaLifeState.FREE
    pending_partner_id: Optional[str] = None
    decline_cooldowns: Dict[str, int] = field(default_factory=dict)
    x: float = 0.0
    y: float = 0.0

    def is_eliminated(self) -> bool:
        return self.state == PersonaLifeState.ELIMINATED


@dataclass
class ChatMessage:
    persona_id: str
    text: str
    tick: int


@dataclass
class PrivateMessage:
    sender_id: str
    target_id: str
    text: str
    tick: int


class ArenaEngine:
    """Pure state machine driving the Starclash simulation.

    The caller drives ticks via `run_tick(brain_fn)`, where `brain_fn` is a
    callable `(persona: PersonaState, observation: dict) -> dict` that the
    engine invokes exactly once per eligible persona per sub-step. Building
    the observation is delegated to `observations.build_observation` via the
    `observation_builder` passed at construction time (kept as a dependency
    injection point so engine.py never imports observations.py directly and
    stays a pure state machine).
    """

    def __init__(
        self,
        personas: List[PersonaState],
        room_name: str = "Main Chat Room",
        max_ticks: int = 16,
        seed: int = 42,
        hand_size: int = 4,
        observation_builder: Optional[Callable[["ArenaEngine", PersonaState, int], dict]] = None,
        room_width: float = 20.0,
        room_height: float = 20.0,
        proximity_radius: float = 3.0,
        max_move_distance: float = 2.0,
        start_area: Optional[Dict[str, float]] = None,
    ) -> None:
        self.personas: Dict[str, PersonaState] = {p.id: p for p in personas}
        self.persona_order: List[str] = [p.id for p in personas]
        self.room_name = room_name
        self.max_ticks = max_ticks
        self.hand_size = hand_size
        self.rng = random.Random(seed)
        self.tick: int = 0
        self._event_seq: int = 0
        self.events: List[Dict[str, Any]] = []
        self.chat_log: List[ChatMessage] = []
        self.private_chat_log: List[PrivateMessage] = []
        self.termination_reason: Optional[str] = None
        self._observation_builder = observation_builder

        # There is now exactly one physical room, modeled as a continuous 2D
        # space [0, room_width] x [0, room_height]. "Same room" adjacency is
        # gone entirely - the only spatial concept left is proximity (see
        # `_distance`/`_within_proximity` below), which drives visibility,
        # chat scoping, and challenge legality.
        self.room_width = room_width
        self.room_height = room_height
        self.proximity_radius = proximity_radius
        self.max_move_distance = max_move_distance
        self.start_area: Dict[str, float] = start_area or {
            "x_min": 0.0,
            "x_max": room_width,
            "y_min": 0.0,
            "y_max": room_height,
        }

        self._spawn_personas(personas)
        self._deal_cards()
        self.initial_card_counts = self._count_cards_in_play()

    def _count_cards_in_play(self) -> Dict[str, int]:
        """Count Rock/Paper/Scissors still held across all personas."""
        counts = {card_type: 0 for card_type in CARD_TYPES}
        for persona in self.personas.values():
            for card in persona.hand:
                if card in counts:
                    counts[card] += 1
        return counts

    def _spawn_personas(self, personas: List[PersonaState]) -> None:
        """Place each persona at a random (x, y) within `start_area`, using
        the engine's seeded RNG (never the global `random` module) so spawn
        placement is part of the same determinism contract as card dealing.

        Rejection sampling enforces a minimum separation so the crew doesn't
        stack on top of each other at tick 0; if the area is tight, separation
        relaxes gradually before falling back to a plain uniform draw.
        """
        x_min = self.start_area.get("x_min", 0.0)
        x_max = self.start_area.get("x_max", self.room_width)
        y_min = self.start_area.get("y_min", 0.0)
        y_max = self.start_area.get("y_max", self.room_height)
        n = len(personas)
        area = max(0.01, (x_max - x_min) * (y_max - y_min))
        if n > 1:
            min_sep = min(self.proximity_radius * 0.95, math.sqrt(area / n) * 0.82)
            min_sep = max(1.5, min_sep)
        else:
            min_sep = 0.0

        placed: List[tuple[float, float]] = []
        max_attempts = 300

        for persona in personas:
            placed_ok = False
            for _ in range(max_attempts):
                x = self.rng.uniform(x_min, x_max)
                y = self.rng.uniform(y_min, y_max)
                if not placed or all(
                    math.hypot(x - px, y - py) >= min_sep for px, py in placed
                ):
                    persona.x = x
                    persona.y = y
                    placed.append((x, y))
                    placed_ok = True
                    break
            if placed_ok:
                continue
            for relax in (0.75, 0.5, 0.25, 0.0):
                relaxed_sep = min_sep * relax
                for _ in range(120):
                    x = self.rng.uniform(x_min, x_max)
                    y = self.rng.uniform(y_min, y_max)
                    if not placed or all(
                        math.hypot(x - px, y - py) >= relaxed_sep for px, py in placed
                    ):
                        persona.x = x
                        persona.y = y
                        placed.append((x, y))
                        placed_ok = True
                        break
                if placed_ok:
                    break
            if not placed_ok:
                x = self.rng.uniform(x_min, x_max)
                y = self.rng.uniform(y_min, y_max)
                persona.x = x
                persona.y = y
                placed.append((x, y))

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _deal_cards(self) -> None:
        """Build a deck sized num_personas * hand_size, ~evenly split across
        Rock/Paper/Scissors (remainder distributed round-robin), shuffle with
        the seeded RNG, and deal hand_size cards to each persona in order.
        """
        n = len(self.persona_order)
        deck_size = n * self.hand_size
        base, remainder = divmod(deck_size, len(CARD_TYPES))
        deck: List[str] = []
        for card_type in CARD_TYPES:
            deck.extend([card_type] * base)
        # Distribute the remainder round-robin over the three types.
        for i in range(remainder):
            deck.append(CARD_TYPES[i % len(CARD_TYPES)])
        self.rng.shuffle(deck)

        idx = 0
        for pid in self.persona_order:
            persona = self.personas[pid]
            persona.hand = deck[idx : idx + self.hand_size]
            idx += self.hand_size

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def active_personas(self) -> List[PersonaState]:
        """Non-eliminated personas, in stable registration order."""
        return [self.personas[pid] for pid in self.persona_order if not self.personas[pid].is_eliminated()]

    def log_event(self, event_type: str, **fields: Any) -> None:
        event = {"seq": self._event_seq, "tick": self.tick, "type": event_type}
        self._event_seq += 1
        event.update(fields)
        self.events.append(event)

    @staticmethod
    def _extract_reasoning(decision: Any) -> Optional[str]:
        """Pull an optional free-text "reasoning" string off a brain's
        decision dict, for threading into the event log (see brains.py:
        ArenaBrain.decide docstring). Returns None if absent, non-string, or
        blank - callers only add the "reasoning" key to a logged event when
        this returns a non-None value, so events without a reasoning never
        get a polluting `"reasoning": null`/empty entry.
        """
        if not isinstance(decision, dict):
            return None
        reasoning = decision.get("reasoning")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning
        return None

    def is_done(self) -> bool:
        if self.tick >= self.max_ticks:
            return True
        if len(self.active_personas()) <= 1:
            return True
        return False

    def _partner_target_list(self, persona: PersonaState) -> List[str]:
        """The sole legal private-message target during a forced battle-card
        or challenge-response sub-step: whoever this persona is currently
        paired with. Empty list if there is no such partner."""
        return [persona.pending_partner_id] if persona.pending_partner_id else []

    @staticmethod
    def _distance(a: PersonaState, b: PersonaState) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    def _within_proximity(self, a: PersonaState, b: PersonaState) -> bool:
        return self._distance(a, b) <= self.proximity_radius

    def _nearby_target_ids(self, persona: PersonaState) -> List[str]:
        """Other non-eliminated personas within `proximity_radius` of this
        persona's current position. There is only one physical room now, so
        proximity (not room-id equality) is the sole visibility/eligibility
        mechanism - used for challenge eligibility and for free-action
        private-message eligibility."""
        return [
            pid
            for pid in self.persona_order
            if pid != persona.id
            and not self.personas[pid].is_eliminated()
            and self._within_proximity(self.personas[pid], persona)
        ]

    def _record_private_message(
        self, sender_id: str, target_id: str, text: str, reasoning: Optional[str] = None
    ) -> None:
        self.private_chat_log.append(
            PrivateMessage(sender_id=sender_id, target_id=target_id, text=text, tick=self.tick)
        )
        extra: Dict[str, Any] = {"reasoning": reasoning} if reasoning else {}
        self.log_event(
            "private_message_sent", sender_id=sender_id, target_id=target_id, text=text, **extra
        )

    def _apply_piggyback_private_message(
        self, sender_id: str, decision: Any, legal_targets: List[str]
    ) -> None:
        """Apply an optional {"private_message": {"target_id", "text"}} field
        bundled onto a primary decision. Silently drops (no log, no crash) if
        the target isn't in `legal_targets` or the payload is malformed -
        this is the leakage-prevention / robustness contract for piggybacked
        private messages: illegal targets are simply never honored.
        """
        if not isinstance(decision, dict):
            return
        pm = decision.get("private_message")
        if not isinstance(pm, dict):
            return
        target_id = pm.get("target_id")
        text = pm.get("text")
        if target_id not in legal_targets:
            return
        if not isinstance(text, str) or not text.strip():
            return
        self._record_private_message(sender_id, target_id, text)

    def _apply_direct_private_message(
        self,
        sender_id: str,
        target_id: Optional[str],
        text: Optional[str],
        reasoning: Optional[str] = None,
    ) -> None:
        """Apply `private_message` as a full primary action (sub-step 3
        only). Nearby (within proximity_radius), non-eliminated targets
        only; illegal targets are logged as a system rejection (this is a
        primary action choice, not a best-effort piggyback, so unlike the
        piggyback path we do log the rejection for visibility)."""
        sender = self.personas[sender_id]
        legal_targets = self._nearby_target_ids(sender)
        if target_id not in legal_targets:
            self.log_event(
                "system",
                message="private_message_rejected_illegal_target",
                sender_id=sender_id,
                target_id=target_id,
            )
            return
        if not isinstance(text, str) or not text.strip():
            text = "..."
        # Here private_message IS the primary action (sub-step 3 direct
        # send, not a piggyback), so the decision's reasoning legitimately
        # explains this send and is threaded through.
        self._record_private_message(sender_id, target_id, text, reasoning=reasoning)

    def _decrement_cooldowns(self) -> None:
        for persona in self.personas.values():
            if not persona.decline_cooldowns:
                continue
            updated: Dict[str, int] = {}
            for challenger_id, remaining in persona.decline_cooldowns.items():
                new_remaining = max(0, remaining - 1)
                if new_remaining > 0:
                    updated[challenger_id] = new_remaining
            persona.decline_cooldowns = updated

    def build_observation(self, persona: PersonaState, sub_step: int) -> dict:
        if self._observation_builder is None:
            raise RuntimeError(
                "ArenaEngine was constructed without an observation_builder; "
                "pass observations.build_observation at construction time."
            )
        return self._observation_builder(self, persona, sub_step)

    # ------------------------------------------------------------------
    # Tick execution
    # ------------------------------------------------------------------

    def run_tick(self, brain_fn: Callable[[PersonaState, dict], dict]) -> None:
        """Run one full tick (sub-steps 1, 2, 3 in strict order)."""
        self._decrement_cooldowns()
        self._run_substep_1_battle_cards(brain_fn)
        self._run_substep_2_challenge_responses(brain_fn)
        self._run_substep_3_free_actions(brain_fn)
        self.tick += 1

    # -- Sub-step 1 -----------------------------------------------------

    def _run_substep_1_battle_cards(self, brain_fn: Callable[[PersonaState, dict], dict]) -> None:
        eligible_ids = [
            pid
            for pid in self.persona_order
            if self.personas[pid].state == PersonaLifeState.BATTLE_CARD_PENDING
        ]
        if not eligible_ids:
            return

        # Build ALL observations up-front, before any brain call is made, so
        # that even if both members of a pair are asked in this same batch,
        # neither observation can possibly embed the other's submission
        # (which doesn't exist yet at observation-build time regardless).
        observations = {pid: self.build_observation(self.personas[pid], sub_step=1) for pid in eligible_ids}

        submitted_cards: Dict[str, str] = {}
        submitted_reasoning: Dict[str, str] = {}
        for pid in eligible_ids:
            persona = self.personas[pid]
            decision = brain_fn(persona, observations[pid])
            card = self._extract_legal_card(persona, decision)
            submitted_cards[pid] = card
            reasoning = self._extract_reasoning(decision)
            if reasoning:
                submitted_reasoning[pid] = reasoning
            # Piggybacked private message: legal target is ONLY the current
            # battle opponent (pending_partner_id). Illegal targets are
            # silently dropped, never logged.
            self._apply_piggyback_private_message(pid, decision, self._partner_target_list(persona))

        # Resolve any battle pair where both combatants have now submitted.
        resolved_pairs: set = set()
        for pid in eligible_ids:
            if pid in resolved_pairs:
                continue
            persona = self.personas[pid]
            partner_id = persona.pending_partner_id
            if partner_id is None or partner_id not in submitted_cards:
                continue
            if partner_id in resolved_pairs:
                continue
            self._resolve_battle(
                pid,
                partner_id,
                submitted_cards[pid],
                submitted_cards[partner_id],
                reasoning_a=submitted_reasoning.get(pid),
                reasoning_b=submitted_reasoning.get(partner_id),
            )
            resolved_pairs.add(pid)
            resolved_pairs.add(partner_id)

    def _extract_legal_card(self, persona: PersonaState, decision: dict) -> str:
        card = None
        if isinstance(decision, dict) and decision.get("action") == "play_card":
            card = decision.get("card")
        if card not in persona.hand:
            # Defensive fallback: pick the first available card deterministically.
            card = persona.hand[0] if persona.hand else self.rng.choice(list(CARD_TYPES))
        return card

    def _resolve_battle(
        self,
        id_a: str,
        id_b: str,
        card_a: str,
        card_b: str,
        reasoning_a: Optional[str] = None,
        reasoning_b: Optional[str] = None,
    ) -> None:
        a = self.personas[id_a]
        b = self.personas[id_b]

        stars_before_a, stars_before_b = a.stars, b.stars

        winner_id: Optional[str] = None
        if card_a != card_b:
            if _BEATS.get(card_a) == card_b:
                winner_id = id_a
            elif _BEATS.get(card_b) == card_a:
                winner_id = id_b

        if winner_id == id_a:
            a.stars += 1
            b.stars = max(0, b.stars - 1)
        elif winner_id == id_b:
            b.stars += 1
            a.stars = max(0, a.stars - 1)
        # tie: no star change

        # Remove the played card from each hand regardless of outcome.
        if card_a in a.hand:
            a.hand.remove(card_a)
        if card_b in b.hand:
            b.hand.remove(card_b)

        for persona in (a, b):
            persona.pending_partner_id = None
            if persona.stars <= 0:
                persona.state = PersonaLifeState.ELIMINATED
            else:
                persona.state = PersonaLifeState.FREE

        # battle_resolved is unusual in that it's the merger of TWO separate
        # decisions (each combatant's play_card call); mirror each one's
        # optional reasoning as its own reasoning_a/reasoning_b field (same
        # naming convention as card_a/card_b above) rather than a single
        # "reasoning" key, so each combatant's rationale for their OWN card
        # choice stays attributable and neither is silently dropped. Each
        # field is added only when that persona's decision actually
        # supplied a non-empty reasoning string.
        extra: Dict[str, Any] = {}
        if reasoning_a:
            extra["reasoning_a"] = reasoning_a
        if reasoning_b:
            extra["reasoning_b"] = reasoning_b

        self.log_event(
            "battle_resolved",
            persona_a=id_a,
            persona_b=id_b,
            card_a=card_a,
            card_b=card_b,
            winner_id=winner_id,
            stars_before={id_a: stars_before_a, id_b: stars_before_b},
            stars_after={id_a: a.stars, id_b: b.stars},
            **extra,
        )

    # -- Sub-step 2 -----------------------------------------------------

    def _run_substep_2_challenge_responses(self, brain_fn: Callable[[PersonaState, dict], dict]) -> None:
        eligible_ids = [
            pid
            for pid in self.persona_order
            if self.personas[pid].state == PersonaLifeState.PENDING_CHALLENGE
        ]
        if not eligible_ids:
            return

        for pid in eligible_ids:
            persona = self.personas[pid]
            # Persona may have already been resolved as part of an earlier
            # iteration in this same loop (shouldn't happen since each
            # PENDING_CHALLENGE persona has a distinct challenger who is in
            # AWAITING_RESPONSE, not PENDING_CHALLENGE, but guard anyway).
            if persona.state != PersonaLifeState.PENDING_CHALLENGE:
                continue

            observation = self.build_observation(persona, sub_step=2)
            decision = brain_fn(persona, observation)
            action = decision.get("action") if isinstance(decision, dict) else None
            if action not in ("accept", "decline"):
                action = "decline"

            challenger_id = persona.pending_partner_id
            challenger = self.personas.get(challenger_id) if challenger_id else None
            reasoning = self._extract_reasoning(decision)
            reasoning_extra: Dict[str, Any] = {"reasoning": reasoning} if reasoning else {}

            # Piggybacked private message: legal target is ONLY the
            # challenger (pending_partner_id). Illegal targets dropped silently.
            self._apply_piggyback_private_message(pid, decision, self._partner_target_list(persona))

            if action == "decline" or challenger is None:
                persona.state = PersonaLifeState.FREE
                persona.pending_partner_id = None
                if challenger is not None:
                    challenger.state = PersonaLifeState.FREE
                    challenger.pending_partner_id = None
                    persona.decline_cooldowns[challenger_id] = 3
                self.log_event(
                    "challenge_declined",
                    responder_id=pid,
                    challenger_id=challenger_id,
                    **reasoning_extra,
                )
            else:  # accept
                persona.state = PersonaLifeState.BATTLE_CARD_PENDING
                challenger.state = PersonaLifeState.BATTLE_CARD_PENDING
                # pending_partner_id already set both ways from challenge issuance.
                self.log_event(
                    "challenge_accepted",
                    responder_id=pid,
                    challenger_id=challenger_id,
                    **reasoning_extra,
                )

    # -- Sub-step 3 -----------------------------------------------------

    def _run_substep_3_free_actions(self, brain_fn: Callable[[PersonaState, dict], dict]) -> None:
        eligible_ids = sorted(
            pid for pid in self.persona_order if self.personas[pid].state == PersonaLifeState.FREE
        )
        if not eligible_ids:
            return

        decisions: Dict[str, dict] = {}
        for pid in eligible_ids:
            persona = self.personas[pid]
            # A persona may have been pulled out of FREE by another
            # persona's challenge application earlier in this same
            # sub-step's application phase; brain calls all happen before
            # any application below, so re-check state at apply time, not
            # here (observation-build & brain-call happen while still FREE).
            observation = self.build_observation(persona, sub_step=3)
            decisions[pid] = brain_fn(persona, observation)

        # Apply in stable, deterministic order (sorted by persona id).
        for pid in eligible_ids:
            persona = self.personas[pid]
            if persona.state != PersonaLifeState.FREE:
                # Already consumed as a challenge target this sub-step.
                continue
            decision = decisions[pid]
            action = decision.get("action") if isinstance(decision, dict) else None
            reasoning = self._extract_reasoning(decision)
            reasoning_extra: Dict[str, Any] = {"reasoning": reasoning} if reasoning else {}

            if action == "say":
                text = decision.get("text") if isinstance(decision, dict) else None
                if not isinstance(text, str) or not text.strip():
                    text = "..."
                self.chat_log.append(ChatMessage(persona_id=pid, text=text, tick=self.tick))
                if len(self.chat_log) > 5:
                    self.chat_log = self.chat_log[-5:]
                self.log_event("say", persona_id=pid, text=text, **reasoning_extra)

            elif action == "challenge":
                target_id = decision.get("target_id") if isinstance(decision, dict) else None
                self._apply_challenge(pid, target_id, reasoning=reasoning)
                # Piggybacked private message on a challenge is the one
                # explicit exception to "private_message is its own primary
                # slot in sub-step 3": a private taunt alongside the public
                # challenge. Legal targets are nearby personas (need not
                # match the challenge target). Evaluated regardless of
                # whether the challenge itself ended up legal. The primary
                # decision's "reasoning" (if any) explains the challenge,
                # not this piggybacked private aside, so it is NOT passed
                # through here - see _apply_challenge above instead.
                self._apply_piggyback_private_message(pid, decision, self._nearby_target_ids(persona))

            elif action == "move":
                target_x = decision.get("target_x") if isinstance(decision, dict) else None
                target_y = decision.get("target_y") if isinstance(decision, dict) else None
                self._apply_move(pid, target_x, target_y, reasoning=reasoning)

            elif action == "private_message":
                pm = decision.get("private_message") if isinstance(decision, dict) else None
                target_id = pm.get("target_id") if isinstance(pm, dict) else None
                text = pm.get("text") if isinstance(pm, dict) else None
                self._apply_direct_private_message(pid, target_id, text, reasoning=reasoning)

            else:
                # "wait" or anything unrecognized -> no-op.
                self.log_event("wait", persona_id=pid, **reasoning_extra)

    def _apply_move(
        self,
        persona_id: str,
        target_x: Optional[float],
        target_y: Optional[float],
        reasoning: Optional[str] = None,
    ) -> None:
        """Move `persona_id` toward (target_x, target_y), graceful-clamping
        rather than rejecting: an out-of-range or malformed target is
        replaced with the current position (no-op move) so a brain that
        omits coordinates doesn't crash the tick, while a target that is
        simply FAR AWAY (a perfectly normal "walk toward point X" intent) is
        clamped to at most `max_move_distance` of travel in that direction -
        never rejected outright, and never taken out of the room's bounds.
        """
        persona = self.personas[persona_id]
        from_x, from_y = persona.x, persona.y
        reasoning_extra: Dict[str, Any] = {"reasoning": reasoning} if reasoning else {}

        if not isinstance(target_x, (int, float)) or not isinstance(target_y, (int, float)):
            self.log_event(
                "system",
                message="move_ignored_invalid_target",
                persona_id=persona_id,
                from_x=from_x,
                from_y=from_y,
                **reasoning_extra,
            )
            return

        # Clamp the requested target into room bounds first, then clamp the
        # travel distance to max_move_distance from the current position.
        clamped_target_x = min(max(float(target_x), 0.0), self.room_width)
        clamped_target_y = min(max(float(target_y), 0.0), self.room_height)

        dx = clamped_target_x - from_x
        dy = clamped_target_y - from_y
        distance = math.hypot(dx, dy)
        if distance > self.max_move_distance and distance > 0:
            scale = self.max_move_distance / distance
            new_x = from_x + dx * scale
            new_y = from_y + dy * scale
        else:
            new_x = clamped_target_x
            new_y = clamped_target_y

        # Bounds-clamp defensively once more (should already hold, but stay
        # defensive against float drift at the edges).
        new_x = min(max(new_x, 0.0), self.room_width)
        new_y = min(max(new_y, 0.0), self.room_height)

        persona.x, persona.y = new_x, new_y
        self.log_event(
            "move",
            persona_id=persona_id,
            from_x=from_x,
            from_y=from_y,
            to_x=new_x,
            to_y=new_y,
            **reasoning_extra,
        )

    def _apply_challenge(
        self, challenger_id: str, target_id: Optional[str], reasoning: Optional[str] = None
    ) -> None:
        challenger = self.personas[challenger_id]
        target = self.personas.get(target_id) if target_id else None

        reasoning_extra: Dict[str, Any] = {"reasoning": reasoning} if reasoning else {}

        legal = (
            target is not None
            and target.id != challenger_id
            and target.state == PersonaLifeState.FREE
            and not target.is_eliminated()
            and self._within_proximity(target, challenger)
            and challenger.decline_cooldowns.get(target_id, 0) <= 0
            and len(challenger.hand) > 0
        )

        if not legal:
            self.log_event(
                "system",
                message="challenge_rejected_busy",
                challenger_id=challenger_id,
                target_id=target_id,
                **reasoning_extra,
            )
            return

        if len(target.hand) == 0:
            # Target has no cards to fight with: auto-decline without a brain call.
            self.log_event(
                "challenge_auto_declined_no_cards",
                challenger_id=challenger_id,
                target_id=target_id,
                **reasoning_extra,
            )
            return

        challenger.state = PersonaLifeState.AWAITING_RESPONSE
        challenger.pending_partner_id = target_id
        target.state = PersonaLifeState.PENDING_CHALLENGE
        target.pending_partner_id = challenger_id
        self.log_event(
            "challenge_issued", challenger_id=challenger_id, target_id=target_id, **reasoning_extra
        )

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    def run(self, brain_fn: Callable[[PersonaState, dict], dict]) -> None:
        while not self.is_done():
            self.run_tick(brain_fn)

        if len(self.active_personas()) <= 1:
            self.termination_reason = "one_survivor"
        else:
            self.termination_reason = "max_ticks"

    def final_state(self) -> Dict[str, Any]:
        return {
            "final_state": {
                pid: {
                    "stars": self.personas[pid].stars,
                    "eliminated": self.personas[pid].is_eliminated(),
                    "final_hand_size": len(self.personas[pid].hand),
                    "x": self.personas[pid].x,
                    "y": self.personas[pid].y,
                }
                for pid in self.persona_order
            },
            "termination_reason": self.termination_reason,
        }
