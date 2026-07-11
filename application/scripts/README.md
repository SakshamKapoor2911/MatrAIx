# Application Scripts

[`generate_application_job.py`](generate_application_job.py) samples personas and
writes a multi-trial job YAML plus a `.meta.json` sidecar under
`configs/jobs/application-task-job-recipe/` by default. Playground UI launches
write to the same directory.

[`report_job.py`](report_job.py) refreshes `jobs/<job_name>/aggregation.json`
for an existing Harbor job and, by default, runs any configured `llm_*`
reporting directives in the foreground.

Generated job recipes are ignored by git unless a maintainer explicitly curates
one into the repository. Use `--out` to write to a temporary path while testing.

The script supports:

- `--sample-size`
- `--persona-ids` for explicit personas (skips random sampling)
- `--execution-mode` (default: `auto`, same as Playground UI Mode **auto**)
- repeated or comma-separated `--stratify`
- `--name`
- `--job-name`
- `--dataset`

## Auto mode (recommended)

Generate a job recipe (same logic as Playground UI Mode **auto**):

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --persona-ids 0042
```

Then run the job (the script prints the exact exports):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export MATRIX_SURVEY_TASK_PATH=application/tasks/example-survey_product-feedback
uv run harbor run -c configs/jobs/application-task-job-recipe/example-survey-product-feedback-auto-n1.yaml
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
uv run harbor run -c configs/jobs/application-task-job-recipe/recommender-agent-chat-api-auto-n1.yaml
```

Refresh reporting for a completed job:

```bash
uv run python application/scripts/report_job.py jobs/<job_name>
```

Aggregation only, without live LLM calls:

```bash
uv run python application/scripts/report_job.py jobs/<job_name> --no-llm
```
