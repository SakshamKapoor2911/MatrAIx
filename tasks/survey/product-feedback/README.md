# Product concept survey (FocusLoop)

MatrAIx **survey** reference task: read a product brief and structured questions, then submit persona-aligned answers as JSON.

- Inputs: `/app/input/product_brief.md`, `/app/input/survey_questions.md`
- Output: `/app/output/survey_responses.json`

See [task-guide.md](../../docs/applications/task-guide.md).

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-claude-code` |
| Environment | `docker` (default) |
| Persona | `personas/examples/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/survey/product-feedback
```

## What this exercises

- Persona voice in **written survey** responses (not chat or browser)
- `/app/input` → read materials → `/app/output` submission contract
- Schema verifier (question coverage + interest scale)
