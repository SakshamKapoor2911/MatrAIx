# PersonaEval Unified Runtime Runbook

This runbook explains how to start PersonaEval so the chatbot, survey, web, and
AppWorld surfaces all use the same backend and the same runtime boundary.

The public API is always the PersonaEval FastAPI app. Runtime selection is an
environment setting behind that API:

- `local`: use the in-process/local runners.
- `harbor`: run chatbot, survey, and web evals through Harbor-backed runners.
  AppWorld is not implemented for Harbor and returns an explicit unsupported
  runtime error.
- `benchflow`: send supported eval jobs to a BenchFlow-compatible runner API and
  normalize returned artifacts back into the same job views.

## Prerequisites

From the repository root, create or activate the Python environment used for
PersonaEval and install the frontend dependencies:

```bash
# Use the project venv your checkout already uses. This example assumes .venv.
PYTHON=.venv/bin/python

cd application/persona_eval/frontend
npm ci
cd ../../..
```

Optional but usually required for real LLM-backed runs:

```bash
export OPENAI_API_KEY=...
```

Local no-auth BenchFlow-compatible runs do not require `BENCHFLOW_API_KEY`.

## Option A: Local Direct Runtime

Use this when you only need the PersonaEval backend and local deterministic
surface runners.

```bash
PYTHONPATH=application/persona_eval \
  .venv/bin/python -m uvicorn backend.api.app:app \
  --host 127.0.0.1 --port 8765 --workers 1
```

In a second terminal, start the Vite frontend:

```bash
cd application/persona_eval/frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The frontend calls the API at `http://127.0.0.1:8765`.

## Option B: Unified BenchFlow Boundary, Local Compat Server

Use this for the full unified shape without a deployed BenchFlow service. The
PersonaEval backend calls `http://127.0.0.1:9000/v1/runs`; the local compatibility
server returns deterministic web/AppWorld artifacts by default.

Terminal 1: start the BenchFlow-compatible runner API.

```bash
PYTHONPATH=.:application/persona_eval:environment/runtime \
  .venv/bin/python -m uvicorn environment.integrations.persona_eval.benchflow.compat_server:app \
  --host 127.0.0.1 --port 9000
```

Terminal 2: start the PersonaEval backend in BenchFlow mode.

```bash
export MATRIX_PERSONA_EVAL_RUNTIME=benchflow
export BENCHFLOW_API_URL=http://127.0.0.1:9000
unset BENCHFLOW_API_KEY

PYTHONPATH=.:application/persona_eval:environment/runtime \
  .venv/bin/python -m uvicorn backend.api.app:app \
  --host 127.0.0.1 --port 8765 --workers 1
```

Terminal 3: start the frontend.

```bash
cd application/persona_eval/frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

This mode validates the same HTTP contract used by a real BenchFlow deployment:

```text
PersonaEval API -> BenchFlow-compatible /v1/runs -> artifacts -> PersonaEval job view
```

## Option C: Single-Origin Backend After Frontend Build

Use this when you want the backend to serve both `/api` and the built SPA from
one origin.

```bash
cd application/persona_eval/frontend
npm run build
cd ../../..

export MATRIX_PERSONA_EVAL_RUNTIME=benchflow
export BENCHFLOW_API_URL=http://127.0.0.1:9000
unset BENCHFLOW_API_KEY

PYTHONPATH=.:application/persona_eval:environment/runtime \
  .venv/bin/python -m uvicorn backend.api.app:app \
  --host 127.0.0.1 --port 8765 --workers 1
```

Open:

```text
http://127.0.0.1:8765
```

## Option D: Real BenchFlow Service

When BenchFlow is deployed as a service, replace the local compat URL with the
real endpoint:

```bash
export MATRIX_PERSONA_EVAL_RUNTIME=benchflow
export BENCHFLOW_API_URL=https://benchflow.example.com
export BENCHFLOW_API_KEY=...

PYTHONPATH=.:application/persona_eval:environment/runtime \
  .venv/bin/python -m uvicorn backend.api.app:app \
  --host 127.0.0.1 --port 8765 --workers 1
```

The BenchFlow-compatible service must support:

- `POST /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/artifacts/{name}`

For web runs it should return `trace.json` plus `ecommerce_interaction.json` or
`web_result.json`. For AppWorld runs it should return `trace.json` plus
`appworld_result.json`.

## Running Real Web or AppWorld Behind the Compat Server

The compat server can delegate work to a command instead of returning mock
artifacts.

```bash
export BENCHFLOW_COMPAT_WEB_COMMAND="/path/to/web_runner"
export BENCHFLOW_COMPAT_APPWORLD_COMMAND="/path/to/appworld_runner"
export BENCHFLOW_COMPAT_COMMAND_TIMEOUT=1800

PYTHONPATH=.:application/persona_eval:environment/runtime \
  .venv/bin/python -m uvicorn environment.integrations.persona_eval.benchflow.compat_server:app \
  --host 127.0.0.1 --port 9000
```

The command receives:

- `BENCHFLOW_RUN_ID`
- `BENCHFLOW_TASK_TYPE`
- `BENCHFLOW_PAYLOAD_JSON`
- `BENCHFLOW_OUTPUT_DIR`

The command must read the payload JSON and write artifacts into
`BENCHFLOW_OUTPUT_DIR`.

Required outputs for web:

```text
trace.json
ecommerce_interaction.json
```

or:

```text
trace.json
web_result.json
```

Required outputs for AppWorld:

```text
trace.json
appworld_result.json
```

## API Smoke Commands

These commands assume:

- PersonaEval backend: `http://127.0.0.1:8765`
- BenchFlow-compatible service, if using BenchFlow mode:
  `http://127.0.0.1:9000`
- `jq` is installed.

Health and readiness:

```bash
curl -s http://127.0.0.1:8765/api/health | jq
curl -s http://127.0.0.1:8765/api/preflight | jq
```

Pick a persona:

```bash
PERSONA_ID="$(
  curl -s 'http://127.0.0.1:8765/api/persona-eval/personas?limit=1' \
    | jq -r '.personas[0].id'
)"
echo "$PERSONA_ID"
```

Start a chatbot persona eval:

```bash
CHATBOT_JOB="$(
  curl -s -X POST http://127.0.0.1:8765/api/persona-eval \
    -H 'Content-Type: application/json' \
    -d "{
      \"applicationId\": \"recai\",
      \"domain\": \"movie\",
      \"personaId\": \"$PERSONA_ID\",
      \"maxTurns\": 2,
      \"goalContextId\": \"scenario_default\"
    }" | jq -r '.jobId'
)"
curl -s "http://127.0.0.1:8765/api/persona-eval/jobs/$CHATBOT_JOB" | jq
```

Start a survey eval:

```bash
SURVEY_JOB="$(
  curl -s -X POST http://127.0.0.1:8765/api/survey-eval \
    -H 'Content-Type: application/json' \
    -d "{\"personaId\": \"$PERSONA_ID\"}" \
    | jq -r '.jobId'
)"
curl -s "http://127.0.0.1:8765/api/survey-eval/jobs/$SURVEY_JOB" | jq
```

Start a web eval:

```bash
WEB_JOB="$(
  curl -s -X POST http://127.0.0.1:8765/api/web-eval \
    -H 'Content-Type: application/json' \
    -d "{\"personaId\": \"$PERSONA_ID\"}" \
    | jq -r '.jobId'
)"
curl -s "http://127.0.0.1:8765/api/web-eval/jobs/$WEB_JOB" | jq
```

Start an AppWorld eval:

```bash
APPWORLD_JOB="$(
  curl -s -X POST http://127.0.0.1:8765/api/appworld-eval \
    -H 'Content-Type: application/json' \
    -d "{\"personaId\": \"$PERSONA_ID\"}" \
    | jq -r '.jobId'
)"
curl -s "http://127.0.0.1:8765/api/appworld-eval/jobs/$APPWORLD_JOB" | jq
```

List persisted runs:

```bash
curl -s http://127.0.0.1:8765/api/persona-eval/runs | jq
```

## Polling Helper

For command-line smoke runs, this shell helper polls a job endpoint until it
finishes.

```bash
poll_job() {
  url="$1"
  while true; do
    body="$(curl -s "$url")"
    status="$(printf '%s' "$body" | jq -r '.status')"
    printf '%s\n' "$body" | jq
    case "$status" in
      done|error) break ;;
      *) sleep 2 ;;
    esac
  done
}

poll_job "http://127.0.0.1:8765/api/survey-eval/jobs/$SURVEY_JOB"
```

## Expected Artifacts

Finished runs are persisted through the shared run store and surfaced by:

```text
GET /api/persona-eval/runs
GET /api/persona-eval/runs/{run_id}
```

Application-specific fields:

- Chatbot: `transcript`, `questionnaire`, `metricScores`, `prompts`
- Survey: `surveyResult`, `prompts`
- Web: `webResult`, `webTrace`, `prompts`
- AppWorld: `appworldResult`, `appworldTrace`, `prompts`

## Troubleshooting

`BENCHFLOW_API_URL is required`

: The backend is running with `MATRIX_PERSONA_EVAL_RUNTIME=benchflow` but no
  BenchFlow URL is configured.

`Connection refused` to `127.0.0.1:9000`

: Start the compat server or point `BENCHFLOW_API_URL` at a real BenchFlow
  service.

Job stays `running`

: Check the runner service logs. Compat command runs are bounded by
  `BENCHFLOW_COMPAT_COMMAND_TIMEOUT`.

Web screenshots return `404`

: The trace references a screenshot that the backend cannot read. Use
  `screenshotUrl` for remote-hosted screenshots, or return a `screenshots_dir`
  artifact when the backend shares the runner filesystem.

AppWorld jobs return mock-looking traces

: The compat server is running without `BENCHFLOW_COMPAT_APPWORLD_COMMAND`.
  Set that command to a real AppWorld runner if you want true AppWorld
  execution behind the local `/v1/runs` API.
