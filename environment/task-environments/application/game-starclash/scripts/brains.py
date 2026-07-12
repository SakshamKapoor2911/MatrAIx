"""Persona "brain" implementations for the Starclash task.

An ArenaBrain turns an observation dict (see observations.py) into a
legal action dict matching one of the entries in
`observation["action_menu"]["actions"]`. The engine treats brains as
black boxes - it never inspects *how* a decision was made, only whether
the returned action is legal (and defensively falls back if not).
"""

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

CARD_TYPES = ("Rock", "Paper", "Scissors")

_SAY_LINES = [
    "Anyone seen spare rations?",
    "This mess hall gives me a bad feeling.",
    "Care to test your luck?",
    "Someone's been eyeing my cards.",
    "Quiet shift so far, all things considered.",
    "I could use a good hand right about now.",
    "Who's brave enough for a duel?",
    "The recycled air in here never gets better.",
    "Stars are just luck with extra steps.",
    "Keep your friends close and your cards closer.",
]

_PRIVATE_LINES = [
    "Don't tell the others, but I'll go easy on you.",
    "Watch your back after this.",
    "I've got a good feeling about this one - between us.",
    "Keep this quiet: I'm low on cards.",
    "Meet me by the airlock later, just the two of us.",
]

_PRIVATE_MESSAGE_CHANCE = 0.20

# Generic flavor "reasoning" lines for MockArenaBrain, kept deliberately
# separate from _SAY_LINES/_PRIVATE_LINES (those are in-character chat
# content; these are out-of-character rationale strings attached to every
# decision so the reasoning-trajectory pipeline has real data to work with
# even in demos run without an API key).
_REASONING_LINES = [
    "Seemed like the safest option available.",
    "Went with instinct here.",
    "Wanted to test the waters before committing.",
    "Nothing else stood out, so this felt reasonable.",
    "Figured it was worth the risk.",
    "Playing it cautious for now.",
    "Just going with the flow of the room.",
    "This felt like the right call in the moment.",
]


class ArenaBrain(ABC):
    @abstractmethod
    def decide(self, observation: dict) -> dict:
        """Return {"action": <menu item>, **params}.

        Must return a fully legal choice from
        observation["action_menu"]["actions"] and its parameters, e.g.:
            {"action": "say", "text": "..."}
            {"action": "challenge", "target_id": "0010"}
            {"action": "accept"}
            {"action": "decline"}
            {"action": "play_card", "card": "Rock"}
            {"action": "wait"}
            {"action": "move", "target_x": 12.5, "target_y": 8.0}
            {"action": "private_message", "private_message": {"target_id": "0010", "text": "..."}}

        Additionally, in sub-steps 1 and 2 (and optionally alongside a
        sub-step-3 "challenge"), the response may carry an OPTIONAL
        piggybacked private_message alongside the primary action, e.g.:
            {"action": "play_card", "card": "Rock",
             "private_message": {"target_id": "<battle opponent id>", "text": "..."}}
        The engine silently drops any piggybacked private_message whose
        target isn't the contextually-legal partner (see
        observation["action_menu"]["private_message_targets"]) - it never
        crashes and never logs an illegal piggyback attempt.

        The returned dict MAY also optionally include a "reasoning" key: a
        short free-text string explaining the persona's rationale for this
        decision, e.g.:
            {"action": "challenge", "target_id": "0010",
             "reasoning": "They looked distracted, good opening."}
        This is purely optional bookkeeping for downstream reporting (per-
        persona reasoning trajectories fed into later rubric/analysis work)
        - omitting it is completely legal and has no effect on whether the
        decision itself is legal.
        """
        raise NotImplementedError


class MockArenaBrain(ArenaBrain):
    """Deterministic, seeded mock brain - no API key required.

    Uses its own private random.Random instance (never the global `random`
    module) so it cannot perturb engine-level shuffling/dealing determinism.
    """

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def decide(self, observation: dict) -> dict:
        menu = observation.get("action_menu", {})
        actions: List[str] = list(menu.get("actions", []))

        if "play_card" in actions:
            decision = self._decide_play_card(observation, menu)
        elif "accept" in actions and "decline" in actions:
            decision = self._decide_challenge_response(menu)
        else:
            decision = self._decide_free_action(observation, menu)

        # MockArenaBrain always attaches a reasoning flavor line (unlike
        # ClaudeArenaBrain, which only includes one when the model actually
        # provided one) - it costs nothing and gives the reasoning-
        # trajectory pipeline real data in demos without an API key.
        decision.setdefault("reasoning", self._rng.choice(_REASONING_LINES))
        return decision

    # -- shared helpers -----------------------------------------------

    def _maybe_attach_private_message(
        self, decision: Dict[str, Any], menu: dict, target_override: Optional[str] = None
    ) -> None:
        """With probability _PRIVATE_MESSAGE_CHANCE, attach a piggybacked
        {"target_id", "text"} private_message onto `decision` in place, iff
        `menu["private_message_targets"]` is non-empty. If `target_override`
        is given, it is used only when it's itself a legal target (this is
        how the sub-step-3 "challenge" piggyback keeps its private message
        aimed at the same persona being challenged)."""
        targets: List[str] = list(menu.get("private_message_targets") or [])
        if not targets:
            return
        if self._rng.random() >= _PRIVATE_MESSAGE_CHANCE:
            return
        if target_override is not None:
            if target_override not in targets:
                return
            target_id = target_override
        else:
            target_id = self._rng.choice(targets)
        decision["private_message"] = {"target_id": target_id, "text": self._rng.choice(_PRIVATE_LINES)}

    # -- sub-step 1 -------------------------------------------------

    def _decide_play_card(self, observation: dict, menu: dict) -> dict:
        available = menu.get("available_cards") or observation["self"]["hand"]
        if not available:
            # Should not happen (persona wouldn't be BATTLE_CARD_PENDING with
            # an empty hand under normal engine operation), but stay defensive.
            card = self._rng.choice(list(CARD_TYPES))
        else:
            card = self._rng.choice(list(available))
        decision: Dict[str, Any] = {"action": "play_card", "card": card}
        self._maybe_attach_private_message(decision, menu)
        return decision

    # -- sub-step 2 -------------------------------------------------

    def _decide_challenge_response(self, menu: dict) -> dict:
        # Uniform accept/decline, with no trait bias (spec only calls for
        # biasing challenge *initiation* frequency, not response).
        action = self._rng.choice(["accept", "decline"])
        decision: Dict[str, Any] = {"action": action}
        self._maybe_attach_private_message(decision, menu)
        return decision

    # -- sub-step 3 -------------------------------------------------

    def _decide_free_action(self, observation: dict, menu: dict) -> dict:
        actions: List[str] = list(menu.get("actions", []))
        targets: List[str] = list(menu.get("challengeable_targets", []))

        if "challenge" in actions and targets:
            p_challenge = self._challenge_probability(observation, len(actions))
            if self._rng.random() < p_challenge:
                target_id = self._rng.choice(targets)
                decision: Dict[str, Any] = {"action": "challenge", "target_id": target_id}
                # Sub-step-3 "challenge" is the one primary action (besides
                # play_card/accept/decline in sub-steps 1/2) that may also
                # carry a piggybacked private message - a private taunt
                # aimed at the same persona being publicly challenged.
                self._maybe_attach_private_message(decision, menu, target_override=target_id)
                return decision
            # Fall through to a uniform choice among the remaining actions.
            remaining = [a for a in actions if a != "challenge"]
            action = self._rng.choice(remaining) if remaining else "wait"
        else:
            action = self._rng.choice(actions) if actions else "wait"

        if action == "say":
            return {"action": "say", "text": self._rng.choice(_SAY_LINES)}
        if action == "move":
            return self._decide_move(observation, menu)
        if action == "private_message":
            target_id = self._rng.choice(list(menu.get("private_message_targets", [])))
            return {
                "action": "private_message",
                "private_message": {"target_id": target_id, "text": self._rng.choice(_PRIVATE_LINES)},
            }
        return {"action": action}

    def _decide_move(self, observation: dict, menu: dict) -> Dict[str, Any]:
        """Pick a random point within `max_move_distance` of the persona's
        current position, clamped to the room's bounds. No pathfinding or
        strategy here by design - MockArenaBrain is the "no preset
        strategy" mock, not meant to be smart; a random walk within legal
        bounds is enough to guarantee a LEGAL move every time, making the
        engine's own defensive clamping a backstop rather than something
        this brain relies on.
        """
        self_state = observation.get("self", {})
        x = float(self_state.get("x", 0.0))
        y = float(self_state.get("y", 0.0))
        bounds = menu.get("movable_bounds", {})
        max_distance = float(bounds.get("max_distance", 0.0))
        room_width = float(bounds.get("room_width", x))
        room_height = float(bounds.get("room_height", y))

        angle = self._rng.uniform(0.0, 2 * math.pi)
        distance = self._rng.uniform(0.0, max_distance)
        target_x = min(max(x + distance * math.cos(angle), 0.0), room_width)
        target_y = min(max(y + distance * math.sin(angle), 0.0), room_height)
        return {"action": "move", "target_x": target_x, "target_y": target_y}

    def _challenge_probability(self, observation: dict, num_actions: int) -> float:
        """Base uniform probability of picking "challenge" among the
        available actions, nudged +/-15% by a couple of flavor traits.
        Nice-to-have flavor only - not load-bearing game logic.
        """
        base = 1.0 / num_actions
        traits = observation.get("self", {}).get("traits") or {}
        dims = traits.get("dimensions", traits) if isinstance(traits, dict) else {}
        if not isinstance(dims, dict):
            dims = {}

        adjustment = 0.0
        if dims.get("risk_tolerance") == "Cautious":
            adjustment -= 0.15
        dominant_trait = str(dims.get("dominant_trait", ""))
        if "openness" in dominant_trait.lower():
            adjustment += 0.15

        return min(0.95, max(0.0, base + adjustment))


class ClaudeArenaBrain(ArenaBrain):
    """Real Anthropic Claude-driven brain (opt-in, requires the `anthropic`
    package and an API key). Uses forced tool-use so every response is
    structured JSON matching one of the legal actions - never free-parsed
    natural language.

    The `anthropic` import is deliberately deferred to __init__ so that
    mock-only runs never require the dependency to be installed.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        try:
            import anthropic  # noqa: F401  (imported lazily, kept as attribute below)
        except ImportError as exc:  # pragma: no cover - exercised only with --brain claude
            raise ImportError(
                "The 'anthropic' package is required for ClaudeArenaBrain. "
                "Install it (e.g. `uv add anthropic` or `pip install anthropic`) "
                "or run with --brain mock instead."
            ) from exc

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    # -- public API ---------------------------------------------------

    def decide(self, observation: dict) -> dict:
        menu = observation.get("action_menu", {})
        actions: List[str] = list(menu.get("actions", []))
        if not actions:
            return {"action": "wait"}

        try:
            tool = self._build_tool_schema(menu)
            system_prompt = self._build_system_prompt(observation)
            user_prompt = self._build_user_prompt(observation)

            response = self._client.messages.create(
                model=self.model,
                max_tokens=512,
                system=system_prompt,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
                messages=[{"role": "user", "content": user_prompt}],
            )
            decision = self._extract_tool_input(response, tool["name"])
        except Exception:
            # Any SDK/network/parsing failure -> fall back defensively below.
            decision = None

        return self._sanitize_decision(decision, observation, menu)

    # -- prompt construction --------------------------------------------

    def _build_system_prompt(self, observation: dict) -> str:
        traits = observation.get("self", {}).get("traits") or {}
        return (
            "You are roleplaying a persona aboard a starship, sharing one "
            "open room with the rest of the crew, deciding your next action "
            "in a simple social/RPS dueling game. You must physically walk "
            "near someone (see room_bounds.proximity_radius and your own "
            "x/y in the observation) before you can see, chat with, or "
            "challenge them - so moving to find people is a normal and "
            "often necessary action. Stay in character based on the trait "
            "profile below. Reason briefly to yourself, then call the "
            "provided tool with exactly one legal action.\n\n"
            f"Persona trait profile (JSON): {traits}"
        )

    def _build_user_prompt(self, observation: dict) -> str:
        return (
            "Current observation (JSON):\n"
            f"{observation}\n\n"
            "Choose exactly one legal action from action_menu and call the "
            "decide_action tool with it."
        )

    def _build_tool_schema(self, menu: dict) -> dict:
        actions: List[str] = list(menu.get("actions", []))
        properties: Dict[str, Any] = {
            "action": {"type": "string", "enum": actions},
            "reasoning": {
                "type": "string",
                "description": "Optional: a short first-person rationale for this choice.",
            },
        }
        if "play_card" in actions:
            properties["card"] = {
                "type": "string",
                "enum": list(menu.get("available_cards", CARD_TYPES)),
                "description": "Required when action is 'play_card'.",
            }
        if "challenge" in actions:
            properties["target_id"] = {
                "type": "string",
                "enum": list(menu.get("challengeable_targets", [])),
                "description": "Required when action is 'challenge'.",
            }
        if "say" in actions:
            properties["text"] = {
                "type": "string",
                "description": "Required when action is 'say'. In-character chat line.",
            }
        if "move" in actions:
            bounds = menu.get("movable_bounds", {})
            room_width = bounds.get("room_width")
            room_height = bounds.get("room_height")
            max_distance = bounds.get("max_distance")
            properties["target_x"] = {
                "type": "number",
                "description": (
                    "Required when action is 'move'. The x coordinate you want to "
                    f"walk toward (room spans x in [0, {room_width}]). You'll move "
                    f"at most {max_distance} units this tick, clamped toward this "
                    "target - it's fine to name a point far away, you'll just take "
                    "a step in that direction."
                ),
            }
            properties["target_y"] = {
                "type": "number",
                "description": (
                    "Required when action is 'move'. The y coordinate you want to "
                    f"walk toward (room spans y in [0, {room_height}]). You'll move "
                    f"at most {max_distance} units this tick, clamped toward this "
                    "target."
                ),
            }
        if menu.get("private_message_targets"):
            properties["private_message"] = {
                "type": "object",
                "description": (
                    "Optional (or required if action is 'private_message'): "
                    "{target_id, text}."
                ),
                "properties": {
                    "target_id": {
                        "type": "string",
                        "enum": list(menu.get("private_message_targets", [])),
                    },
                    "text": {"type": "string"},
                },
            }
        return {
            "name": "decide_action",
            "description": "Submit exactly one legal action for this turn.",
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": ["action"],
            },
        }

    def _extract_tool_input(self, response: Any, tool_name: str) -> Optional[dict]:
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
                return dict(block.input)
        return None

    # -- defensive sanitization ------------------------------------------

    def _sanitize_decision(self, decision: Optional[dict], observation: dict, menu: dict) -> dict:
        actions: List[str] = list(menu.get("actions", []))
        if not isinstance(decision, dict) or decision.get("action") not in actions:
            return self._fallback(observation, menu)

        action = decision["action"]
        # Piggybacked private_message (if any) is intentionally NOT
        # validated here - the engine's _apply_piggyback_private_message
        # already silently drops illegal targets, so we just pass it
        # through untouched on whichever action carries it.
        piggyback = decision.get("private_message")

        # Optional "reasoning" (if any) is passed through untouched, same
        # pattern as the piggybacked private_message above - it's an
        # optional annotation, not something we validate the content of.
        # Omitted entirely (not defaulted) when missing/invalid: only
        # MockArenaBrain always fills reasoning; the real brain should only
        # surface it when the model actually provided one.
        raw_reasoning = decision.get("reasoning")
        reasoning = raw_reasoning if isinstance(raw_reasoning, str) and raw_reasoning.strip() else None

        if action == "play_card":
            available = menu.get("available_cards") or observation["self"]["hand"]
            card = decision.get("card")
            if card not in available:
                card = random.choice(list(available)) if available else random.choice(list(CARD_TYPES))
            result: Dict[str, Any] = {"action": "play_card", "card": card}
            if piggyback is not None:
                result["private_message"] = piggyback
            if reasoning is not None:
                result["reasoning"] = reasoning
            return result

        if action == "challenge":
            targets = menu.get("challengeable_targets", [])
            target_id = decision.get("target_id")
            if target_id not in targets:
                return self._fallback(observation, menu)
            result = {"action": "challenge", "target_id": target_id}
            if piggyback is not None:
                result["private_message"] = piggyback
            if reasoning is not None:
                result["reasoning"] = reasoning
            return result

        if action == "say":
            text = decision.get("text")
            if not isinstance(text, str) or not text.strip():
                text = "..."
            result = {"action": "say", "text": text}
            if reasoning is not None:
                result["reasoning"] = reasoning
            return result

        if action == "move":
            # Type validation only - target_x/target_y just need to be
            # numbers. Range/distance clamping is the engine's job
            # (_apply_move already clamps to room bounds and
            # max_move_distance defensively), so we don't duplicate that
            # math here.
            target_x = decision.get("target_x")
            target_y = decision.get("target_y")
            if not isinstance(target_x, (int, float)) or not isinstance(target_y, (int, float)):
                return self._fallback(observation, menu)
            result = {"action": "move", "target_x": float(target_x), "target_y": float(target_y)}
            if reasoning is not None:
                result["reasoning"] = reasoning
            return result

        if action == "private_message":
            pm_targets = menu.get("private_message_targets", [])
            pm = decision.get("private_message")
            target_id = pm.get("target_id") if isinstance(pm, dict) else None
            text = pm.get("text") if isinstance(pm, dict) else None
            if target_id not in pm_targets:
                return self._fallback(observation, menu)
            if not isinstance(text, str) or not text.strip():
                text = "..."
            result = {"action": "private_message", "private_message": {"target_id": target_id, "text": text}}
            if reasoning is not None:
                result["reasoning"] = reasoning
            return result

        # accept / decline / wait carry no extra required params, but may
        # still carry a piggybacked private_message and/or reasoning.
        result = {"action": action}
        if piggyback is not None:
            result["private_message"] = piggyback
        if reasoning is not None:
            result["reasoning"] = reasoning
        return result

    def _fallback(self, observation: dict, menu: dict) -> dict:
        actions: List[str] = list(menu.get("actions", []))
        if "wait" in actions:
            return {"action": "wait"}
        if "decline" in actions:
            return {"action": "decline"}
        if "play_card" in actions:
            available = menu.get("available_cards") or observation["self"]["hand"]
            card = random.choice(list(available)) if available else random.choice(list(CARD_TYPES))
            return {"action": "play_card", "card": card}
        # Last resort: whatever the first legal action is.
        return {"action": actions[0]} if actions else {"action": "wait"}
