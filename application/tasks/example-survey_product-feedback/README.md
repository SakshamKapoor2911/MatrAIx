# Product concept survey (FocusLoop)

PersonaBench **survey** reference task: read a product brief and structured questions, then submit persona-aligned answers as JSON.

- Inputs: `/app/input/product_brief.md`, `/app/input/survey_questions.md`
- Output: `/app/output/survey_responses.json`

See [Application Tasks](../README.md).

## Smoke run

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --persona-ids 0042

export ANTHROPIC_API_KEY="sk-ant-..."
export MATRIX_SURVEY_INSTRUMENT_ID=product_feedback_v1
uv run harbor run -c configs/jobs/application-task-job-recipe/example-survey_product-feedback-auto-n1.yaml
```

See [Application Quickstart](../../QUICKSTART.md) for the UI path and full env vars.

## What this exercises

- Persona voice in **written survey** responses (not chat or browser)
- `/app/input` → read materials → `/app/output` submission contract
- Schema verifier (question coverage + interest scale)
