# PersonaEval Paper Experiments

This runner is for headless paper experiments. It does not start Harbor and it
does not use the PersonaEval frontend. It keeps the same plug-and-play
application boundary: each application is reached through a task-owned API, and
the experiment runner only handles persona selection, conversation control,
parallel scheduling, and artifact writing.

## Current Application Targets

```bash
PYTHONPATH=applications/persona_eval \
  python -m persona_eval.experiments --list-applications
```

Registered targets:

- `movie` or `recai:movie`
- `beauty` or `recai:beauty_product`
- `game` or `recai:game`
- `finance` or `finance_openbb:financial_research`
- `medical` or `medical_assistant:medical_consultation`
- `survey` or `survey:product_attitudes_v1`
- `web` or `web:ecommerce_product_discovery`

The batch scheduler can launch many runs at once, but each application declares
its own concurrency limit. RecAI targets are limited to one active run per
domain because the native RecAI bridge uses process-global resources. Finance,
medical, survey, and web targets allow higher HTTP-level or local-runner
concurrency.

## Start an Application API

The experiment runner expects an application chat API with:

- `GET /ready`
- `POST /v1/messages`
- `GET /v1/conversation`
- `GET /v1/application-result`

For local Python development, start the chatbot API directly:

```bash
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...

PYTHONPATH=applications/persona_eval:applications/persona_eval/backend:applications/tasks/chatbot_chat_api/environment/chatbot_api \
  python -m uvicorn harbor_api.server:app --host 127.0.0.1 --port 8000
```

For Docker-based runs, publish the chatbot router port with the experiment
override:

```bash
docker compose \
  -f applications/tasks/chatbot_chat_api/environment/docker-compose.yaml \
  -f applications/persona_eval/experiments/docker-compose.chatbot-api.yaml \
  --profile recai --profile finance --profile medical \
  up --build chatbot-api recai-api finance-api openbb-mcp medical-api medical-upstream
```

Then use `--api-url http://127.0.0.1:8000`.

## Run 50 Parallel Persona Tests

One chatbot target with 50 personas:

```bash
PYTHONPATH=applications/persona_eval \
  python -m persona_eval.experiments \
    --application movie \
    --num-personas 50 \
    --parallel 50 \
    --max-turns 3 \
    --api-url http://127.0.0.1:8000
```

All registered chatbot targets, capped to 50 total runs:

```bash
PYTHONPATH=applications/persona_eval \
  python -m persona_eval.experiments \
    --all-applications \
    --num-personas 50 \
    --max-runs 50 \
    --parallel 50 \
    --max-turns 3 \
    --api-url http://127.0.0.1:8000
```

The runner exits with status code `0` only when every run finishes without an
error.

Survey and web targets use the same command shape:

```bash
PYTHONPATH=applications/persona_eval \
  python -m persona_eval.experiments \
    --application survey \
    --num-personas 50 \
    --parallel 50

PYTHONPATH=applications/persona_eval \
  python -m persona_eval.experiments \
    --application web \
    --num-personas 50 \
    --parallel 50
```

Survey runs are local structured submissions against the built-in survey
instrument. Web runs use the task-owned ecommerce catalog as the non-Harbor
representation of the hosted website and save a structured web trace. The
browser/computer-use Harbor runtime is not required for these paper experiment
runs.

## Output Layout

By default, artifacts are written under:

```text
data/cache/persona_eval/paper_experiments/<batch_id>/
```

Batch-level files:

- `manifest.json`: selected personas, applications, run specs, and worker count.
- `results.ndjson`: one line appended as each run finishes.
- `summary.json`: updated after each run and rewritten at the end.

Per-run files:

- `runs/<run_id>/events.ndjson`: intermediate persona and application events.
- `runs/<run_id>/transcript.json`: chatbot transcript.
- `runs/<run_id>/application_result.json`: grounded chatbot items/results.
- `runs/<run_id>/persona_self_report.json`: chatbot post-interaction questionnaire.
- `runs/<run_id>/evaluation_result.json`: compact chatbot score view.
- `runs/<run_id>/run_metadata.json`: chatbot readiness and stop reason.
- `runs/<run_id>/survey_result.json`: completed survey response for survey runs.
- `runs/<run_id>/ecommerce_interaction.json`: selected product and website UX ratings for web runs.
- `runs/<run_id>/web_trace.json`: structured non-Harbor web exploration trace.
- `runs/<run_id>/experiment_run.json`: normalized run metadata.
- `runs/<run_id>/error.json`: present only when that run fails.

These files are intended for paper analysis scripts. `events.ndjson` is the
main source for intermediate progress because it records persona requests,
persona replies, application requests, application responses, and final
self-report events.
