# Survey Application Tasks

Survey tasks ask the simulated user to answer a defined form or questionnaire.
The active survey protocol uses a generic survey-form task. The application
runner supplies the survey instrument as task context, then maps the resulting
artifact into answers, metrics, and a telemetry-style trajectory.

## Contract

- Task instruction: define the survey context and output schema.
- Interaction protocol: answer a structured survey instrument.
- Task-specific environment: a survey form task plus an application-supplied instrument prompt.
- Stop conditions: `survey_result.json` exists and matches the schema.
- Artifacts: survey result JSON with `answers` and `trajectory`.
- Evaluation contract: schema validation, answer coverage, type checks, and metrics.

## Canonical Task

`application/tasks/persona-survey`

The product-feedback survey remains as a lightweight reference task:

`application/tasks/example-survey_product-feedback`
