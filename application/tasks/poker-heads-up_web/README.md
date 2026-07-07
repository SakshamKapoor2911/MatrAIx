# Heads-up poker web task

PersonaBench web task for a deterministic two-player poker hand. The persona
plays one simplified Kuhn-poker-style hand against a local browser-hosted bot,
then reports the action line, terminal result, and experience.

## Application Host

| Component | Value |
| --- | --- |
| Web app sidecar | `poker-web` |
| URL inside task | `http://poker-web:8000/` |
| Interaction mode | Browser / computer-use |
| Output | `/app/output/poker_result.json` |

The game intentionally stays small: one private card per player, one betting
round, fixed bet size, and a deterministic opponent policy. This gives the
Application team a complete playable poker task without committing to the later
multi-agent architecture.

## Local Smoke

Oracle:

```bash
uv run harbor run -p application/tasks/poker-heads-up_web -a oracle
```

Persona run:

```bash
uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/poker-heads-up_web
```

## Expected Submission

The persona agent should save:

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
  "reason": "Calling after the bot bet fit my willingness to challenge a likely bluff."
}
```

