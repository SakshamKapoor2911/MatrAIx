# Persona Survey

PersonaBench application task for structured persona surveys. A persona agent
acts as the respondent. The application runner appends a survey instrument and maps
the saved artifact into answers, metrics, and the telemetry-style trajectory.

Canonical shared runtime content lives here:

- `environment/task-environments/application/shared-survey-form/content/instruction.md`
- `environment/task-environments/application/shared-survey-form/content/output_schema.md`

Concrete survey tasks now own their task-specific docs under:

- `application/tasks/<survey-task>/instruction.md`
- `application/tasks/<survey-task>/input/context.md`
- `application/tasks/<survey-task>/input/questionnaire.yaml`
- `application/tasks/<survey-task>/input/output_schema.md`

The shared `shared-survey-form` runtime stays generic; concrete survey tasks own the
task instruction, context, questionnaire, and contributor-owned output schema.
The backend/runtime appends the standardized survey trajectory after execution.

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

## Smoke run

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/persona-survey \
  --execution-mode auto \
  --persona-ids 0042
# Script prints export lines and the job YAML path — then: harbor run -c …
```

See [Application Quickstart](../../QUICKSTART.md).
