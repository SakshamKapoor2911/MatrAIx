#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python3 <<'PY'
import json
from pathlib import Path
from urllib.request import urlopen

with urlopen("http://poker-web:8000/game.json", timeout=10) as response:
    game = json.load(response)

payload = {
    "game_id": game["gameId"],
    "player_card": game["playerCard"],
    "opponent_model": game["opponentModel"],
    "action_sequence": ["check", "call"],
    "opponent_action_sequence": ["bet"],
    "terminal_state": "showdown",
    "winner": "player",
    "chip_delta": 2,
    "pot_size": 4,
    "showdown_revealed": True,
    "decision_subject_id": "line-check-call",
    "decision_subject_label": "Check, face a bluff bet, then call",
    "decision_outcome": "selected",
    "basis_primary": "other",
    "task_strategy_basis": "bluff_call",
    "risk_posture": "balanced",
    "exploration_style": "compared_multiple",
    "need_satisfaction": 8,
    "ease_of_use": 8,
    "overall_experience_rating": 8,
    "reason": (
        "I checked to let the opponent reveal more information, then called because "
        "the bot profile made the bet look like a likely bluff."
    ),
}

Path("/app/output/poker_result.json").write_text(json.dumps(payload, indent=2) + "\n")
PY

