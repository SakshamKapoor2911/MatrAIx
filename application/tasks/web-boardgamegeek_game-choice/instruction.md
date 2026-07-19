# BoardGameGeek — Board Game Choice & Selection

## Your situation
You are a board game enthusiast browsing BoardGameGeek (`https://boardgamegeek.com/`) for top-ranked board games to play with your gaming group.

## Your goal
Browse the top ranked games or hotness list on BoardGameGeek, evaluate game complexity and community ratings, and select a single board game to add to your wishlist.

## Constraints on your behavior
- Do not attempt to log in, create a user collection, or post forum messages.
- Base your decision on visible game rankings, weight (complexity), and geek rating.

## Interaction requirements
Save your board game selection to `/app/output/game_choice.json` using the following exact JSON schema:

```json
{
  "decision_subject_id": "<slugified-game-title-or-bgg-id>",
  "decision_subject_label": "<game title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<explanation of why this board game was selected>",
  "task_geek_rating": "<geek rating e.g. 8.5>",
  "task_weight_complexity": "<weight score e.g. 3.4 / 5>"
}
```

## Termination criteria
- EITHER save `/app/output/game_choice.json` with your selected game and exit,
- OR if no appealing game is found, save with `"decision_outcome": "deferred"` and exit.

## Success judgment
Your submission will be evaluated on:
1. Valid JSON schema structure saved to `/app/output/game_choice.json`.
2. Factual accuracy of `decision_subject_label`, `task_geek_rating`, and `task_weight_complexity`.
3. Clarity and relevance of the `reason` provided.

Read `input/context.md` for background. No login required.
Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.
