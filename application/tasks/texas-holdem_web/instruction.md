# Heads-up Texas Hold'em

You are playing a one-hand, two-player Texas Hold'em game at:

http://holdem-web:8000/

## Rules

- Both players start with **1000 chips**. Blinds are 10 (small) / 20 (big). You post the small blind.
- You receive **2 private hole cards**.
- Four betting rounds: **preflop → flop → turn → river**.
  - Flop: 3 community cards revealed.
  - Turn: 1 more community card.
  - River: 1 final community card.
- On each street you may: **Fold**, **Check**, **Call**, or **Raise**.
- At showdown the best 5-card hand (from your 2 hole cards + 5 community cards) wins.
- Hand ranks from strongest to weakest: straight flush, four of a kind, full house, flush, straight, three of a kind, two pair, pair, high card.

## Playing the game

Use the buttons on the page to make decisions. The action log on the right tracks what happened each street.

When the hand finishes (showdown or fold), the page displays your **Result JSON** in the right panel.
Copy that JSON exactly, then save it to `/app/output/holdem_result.json`.

## Output format

```json
{
  "game_id": "texas-holdem-heads-up-v1",
  "hole_cards": ["Ah", "Kd"],
  "community_cards": ["Qs", "Jc", "Ts", "2h", "7d"],
  "final_hand_rank": "straight",
  "street_actions": {
    "preflop": ["raise"],
    "flop": ["check"],
    "turn": ["call"],
    "river": ["fold"]
  },
  "winner": "player",
  "chip_delta": 150,
  "pot_size": 300,
  "risk_posture": "balanced",
  "exploration_style": "compared_multiple",
  "basis_primary": "other",
  "task_strategy_basis": "hand_strength",
  "decision_outcome": "selected",
  "need_satisfaction": 8,
  "ease_of_use": 7,
  "overall_experience_rating": 8,
  "reason": "Explain why you played the way you did, reflecting your persona's style."
}
```

- `risk_posture`: one of `risk_averse`, `balanced`, `risk_seeking`, `opportunistic`
- `exploration_style`: one of `quick_pick`, `compared_multiple`, `deep_research`, `hesitant`
- `basis_primary`: use `other` for poker; put actual poker reasoning in `task_strategy_basis`
- `task_strategy_basis`: one of `hand_strength`, `pot_odds`, `position_play`, `bluff`, `pot_control`, `other`
- `decision_outcome`: one of `selected`, `considered`, `rejected`, `deferred`, `skipped`
- Ratings must be integers from **1 to 10**
- `reason` must be at least 20 characters
