# Product concept survey (FocusLoop)

PersonaBench **survey** reference task: read product context and a structured
questionnaire, then submit persona-aligned answers as JSON.

Canonical task-owned content lives in:

- `application/tasks/example-survey_product-feedback/instruction.md`
- `application/tasks/example-survey_product-feedback/input/context.md`
- `application/tasks/example-survey_product-feedback/input/questionnaire.yaml`

This task now reuses the shared `application/shared-survey-form` runtime
environment. The platform derives runtime prompts and task-detail UI from the
task-local `input/` bundle.

See [Application Tasks](../README.md).

## Smoke run

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --persona-ids 0042

export ANTHROPIC_API_KEY="sk-ant-..."
export MATRIX_SURVEY_TASK_PATH=application/tasks/example-survey_product-feedback
uv run harbor run -c configs/jobs/application-task-job-recipe/example-survey-product-feedback-auto-n1.yaml
```

See [Application Quickstart](../../QUICKSTART.md) for the UI path and full env vars.

## What this exercises

- Task-local survey docs in `input/` plus the shared `shared-survey-form` runtime
- `/app/input` → read materials → `/app/output` submission contract
- Schema verifier (question coverage + interest scale)
