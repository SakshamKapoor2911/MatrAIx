# Survey form

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
uv run harbor run -c configs/jobs/example-job-recipe/appSim-survey-form-local.yaml
```

For production-style runs, use
`backend.service.harbor_survey_eval.HarborSurveyEvalRunner`; it writes the
survey instrument as an extra instruction and chooses the configured persona
model.
