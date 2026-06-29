# Product concept survey (FocusLoop)

PersonaBench **survey** reference task: read a product brief and structured questions, then submit persona-aligned answers as JSON.

- Inputs: `/app/input/product_brief.md`, `/app/input/survey_questions.md`
- Output: `/app/output/survey_responses.json`

See [Application Tasks](../README.md).

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-claude-code` |
| Environment | `docker` (default) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-survey_product-feedback
```

## What this exercises

- Persona voice in **written survey** responses (not chat or browser)
- `/app/input` → read materials → `/app/output` submission contract
- Schema verifier (question coverage + interest scale)
