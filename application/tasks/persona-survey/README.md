# Persona survey

MatrAIx application task for structured persona surveys. The Harbor
`persona-claude-code` agent acts as the respondent using Harbor's native persona
prompt injection. The application runner appends a survey instrument and maps
the saved artifact into answers, metrics, and the telemetry-style trajectory.

## Expected artifact

The persona agent writes:

- `/app/output/survey_result.json`

The backend runner validates answer coverage and enforces the trajectory event
shape:

```json
{
  "timestamp": "...",
  "actor": "user",
  "action": "answer_question",
  "context": {},
  "outcome": {}
}
```

## Local smoke

After the Harbor runtime is available:

```bash
uv run harbor run \
  -a persona-claude-code \
  -m "${MATRIX_HARBOR_PERSONA_MODEL:-anthropic/claude-haiku-4-5}" \
  --ak persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml \
  -p application/tasks/persona-survey
```

For production-style runs, use
`backend.service.harbor_survey_eval.HarborSurveyEvalRunner`; it writes the
survey instrument as an extra instruction and chooses the configured persona
model.
