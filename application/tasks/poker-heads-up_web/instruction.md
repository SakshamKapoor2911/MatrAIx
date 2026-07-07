# Heads-up poker hand

You are playing a one-hand, two-player poker game at:

http://poker-web:8000/

The table uses a simplified Kuhn-poker-style ruleset:

- Each player antes 1 chip.
- You receive one private card from J, Q, K.
- Higher card wins at showdown.
- You act first and may check or bet 1 chip.
- If you check, the opponent may bet; then you may call or fold.
- If you bet, the opponent may call or fold.

Play the hand as yourself, using the persona's risk tolerance, competitiveness,
curiosity, and comfort with uncertainty. The opponent profile and current game
state are shown on the page. After the hand ends, save your result to
`/app/output/poker_result.json`.

```json
{
  "game_id": "kuhn-heads-up-fixed-v1",
  "player_card": "Q",
  "opponent_model": "deterministic-kuhn-bot-v1",
  "action_sequence": ["check", "call"],
  "opponent_action_sequence": ["bet"],
  "terminal_state": "showdown",
  "winner": "player",
  "chip_delta": 2,
  "pot_size": 4,
  "showdown_revealed": true,
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
  "reason": "Briefly explain why this betting line fit your persona."
}
```

Use the exact `game_id`, `player_card`, and `opponent_model` shown on the site.
Ratings must be integers from 1 to 10. `basis_primary` must be one of the shared
web decision buckets; use `other` for poker-specific strategy and put the actual
strategy reason in `task_strategy_basis`.

