# Application Scripts

[`generate_application_job.py`](generate_application_job.py) samples personas and
writes a multi-trial job YAML plus a `.meta.json` sidecar under
`configs/jobs/application-task-job-recipe/` by default. PersonaEval UI launches
write to the same directory.

Generated job recipes are ignored by git unless a maintainer explicitly curates
one into the repository. Use `--out` to write to a temporary path while testing.

The script supports:

- `--sample-size`
- `--persona-ids` for explicit personas (skips random sampling)
- `--execution-mode auto` — recommended; same as PersonaEval UI Mode **auto**
- repeated or comma-separated `--stratify`
- `--name`
- `--job-name`
- `--dataset`

## Auto mode (recommended)

Generate a job recipe (same logic as PersonaEval UI Mode **auto**):

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --persona-ids 0042
```

Then run the job (the script prints the exact exports):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export MATRIX_SURVEY_INSTRUMENT_ID=product_feedback_v1
uv run harbor run -c configs/jobs/application-task-job-recipe/example-survey_product-feedback-auto-n1.yaml
```

Chatbot / user simulator:

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/recommender-agent_chat_api \
  --execution-mode auto \
  --persona-ids 0042

export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export MATRIX_CHATBOT_DOMAIN=movie
export MATRIX_CHATBOT_APPLICATION_ID=recai
export MATRIX_CHATBOT_MAX_TURNS=8
uv run harbor run -c configs/jobs/application-task-job-recipe/recommender-agent_chat_api-auto-n1.yaml
```
