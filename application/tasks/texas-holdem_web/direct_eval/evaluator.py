"""In-process game simulator that bypasses LLM, Docker, and network overhead."""
from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add holdem-web directory to sys.path to import game and bot logic
_HOLDEM_WEB_DIR = Path(__file__).resolve().parents[4] / "environment" / "task-environments" / "application" / "texas-holdem_web" / "holdem-web"
if str(_HOLDEM_WEB_DIR) not in sys.path:
    sys.path.insert(0, str(_HOLDEM_WEB_DIR))

import game as g
from bot import apply_bot_action

from .policy_registry import build_policy


class DirectEngineEvaluator:
    """Run a Texas Hold'em persona trial entirely in-process.

    Produces holdem_result.json matching the exact schema expected by test_state.py.
    """

    def __init__(
        self,
        persona_dimensions: Dict[str, str],
        seed: Optional[int] = None,
        raise_size: int = g.RAISE_SIZE,
    ):
        from .policies import PersonaValueNormalizer

        self.dims = persona_dimensions
        self.norm_dims = PersonaValueNormalizer.normalize_all(persona_dimensions)
        self.seed = seed
        self.raise_size = raise_size
        self.policy = build_policy(self.norm_dims)
        self.persona_seed = self._derive_persona_seed(persona_dimensions, seed)
        self.rng = random.Random(self.persona_seed)

    @staticmethod
    def _derive_persona_seed(dims: Dict[str, str], base_seed: Optional[int]) -> int:
        if base_seed is None:
            return random.randint(0, 2**31)
        persona_hash = hash(tuple(sorted(dims.items())))
        return (persona_hash ^ base_seed) & 0x7FFFFFFF

    def run(self) -> Dict[str, Any]:
        state = g.new_game(seed=self.persona_seed)

        # Max safety iterations to avoid potential infinite loops
        max_turns = 100
        turns = 0

        while state.status == "playing" and turns < max_turns:
            turns += 1

            if state.player_to_act:
                action = self.policy.decide(state, self.norm_dims, self.rng)
                g.apply_action(state, action, self.raise_size)

        return self._state_to_result(state)

    def _state_to_result(self, state: g.GameState) -> Dict[str, Any]:
        derived = self.policy.derive_output_fields(self.norm_dims)

        risk_posture = derived.get("risk_posture", "balanced")
        exploration_style = derived.get("exploration_style", "deep_research")
        task_strategy_basis = derived.get("task_strategy_basis", "hand_strength")

        reason = (
            f"Played as {risk_posture}/{exploration_style} persona with {task_strategy_basis} basis. "
            f"Seed {state.seed}, won {state.chip_delta} chips. "
            f"Actions: {self._summarize_actions(state)}."
        )

        return {
            "game_id": "texas-holdem-heads-up-v1",
            "seed": state.seed,
            "hole_cards": state.hole_cards,
            "community_cards": state.community_cards,
            "final_hand_rank": state.final_hand_rank,
            "street_actions": {
                s: [a for a in acts if a in ("fold", "check", "call", "raise")]
                for s, acts in state.street_actions.items()
            },
            "winner": state.winner,
            "chip_delta": state.chip_delta,
            "pot_size": state.pot,
            "decision_outcome": "selected" if state.chip_delta >= 0 else "rejected",
            "basis_primary": "quality" if state.chip_delta >= 0 else "price",
            "risk_posture": risk_posture,
            "exploration_style": exploration_style,
            "task_strategy_basis": task_strategy_basis,
            "need_satisfaction": 7 if state.chip_delta >= 0 else 5,
            "ease_of_use": 8,
            "overall_experience_rating": 8 if state.chip_delta >= 0 else 5,
            "reason": reason,
            "_mode": "direct",
        }

    def _summarize_actions(self, state: g.GameState) -> str:
        parts = []
        for street, acts in state.street_actions.items():
            if acts:
                parts.append(f"{street}: {','.join(acts)}")
        return " | ".join(parts) if parts else "none"
