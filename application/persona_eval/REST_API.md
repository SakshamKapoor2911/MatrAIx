# PersonaEval REST API

This document describes the PersonaEval HTTP API exposed by
`backend.api.app:app`. All application endpoints are mounted under `/api`.

Interactive OpenAPI documentation is also available at `/docs` when the backend
is running.

## Conventions

- JSON uses camelCase field names.
- The API does not require authentication in local development.
- `POST` endpoints that start long-running work return `{ "jobId": "..." }`.
  Clients poll the matching job endpoint until `status` is `done` or `error`.
- Common job statuses are `building`, `running`, `done`, and `error`.
- FastAPI may return `422` for malformed requests or failed validation.
- Application handlers return `404` for unknown sessions, jobs, runs, personas,
  catalog items, screenshots, or tasks where applicable.

## Runtime Boundary

The same REST contract is used for local and BenchFlow-backed execution.
Runtime selection happens behind the service layer:

```bash
MATRIX_PERSONA_EVAL_RUNTIME=local      # default
MATRIX_PERSONA_EVAL_RUNTIME=benchflow  # send supported eval runs to BenchFlow
BENCHFLOW_API_URL=http://127.0.0.1:9000
BENCHFLOW_API_KEY=...                  # optional
```

Survey, web, and AppWorld eval jobs keep the same public API shape regardless of
runtime. BenchFlow artifacts are normalized into the job view fields documented
below.

## Endpoint Index

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Backend liveness. |
| `GET` | `/api/preflight` | Environment and resource readiness checks. |
| `GET` | `/api/config/options` | Editable config knobs, defaults, and runtime facts. |
| `GET` | `/api/sessions` | List manual chat sessions. |
| `POST` | `/api/sessions` | Create a manual chat session. |
| `DELETE` | `/api/sessions` | Delete every manual chat session. |
| `GET` | `/api/sessions/{session_id}` | Read one manual chat session. |
| `DELETE` | `/api/sessions/{session_id}` | Delete one manual chat session. |
| `PATCH` | `/api/sessions/{session_id}/config` | Patch one session config. |
| `GET` | `/api/sessions/{session_id}/export` | Download one session JSON artifact. |
| `POST` | `/api/sessions/{session_id}/turns` | Submit one manual chat turn. |
| `GET` | `/api/jobs/{job_id}` | Poll one manual chat turn job. |
| `GET` | `/api/catalog/search` | Search catalog items. |
| `GET` | `/api/catalog/items/{item_id}` | Read one catalog item. |
| `GET` | `/api/persona-eval/personas` | List persona profiles. |
| `GET` | `/api/persona-eval/personas/{persona_id}` | Read one full persona profile. |
| `GET` | `/api/persona-eval/goal-contexts` | List persona-eval goal contexts. |
| `POST` | `/api/persona-eval` | Start a chatbot persona evaluation. |
| `GET` | `/api/persona-eval/runs` | List persisted eval runs. |
| `GET` | `/api/persona-eval/runs/{run_id}` | Read one persisted eval run. |
| `GET` | `/api/persona-eval/jobs/{job_id}` | Poll one chatbot persona-eval job. |
| `GET` | `/api/survey-eval/instruments` | List survey instruments. |
| `POST` | `/api/survey-eval` | Start a survey persona evaluation. |
| `GET` | `/api/survey-eval/jobs/{job_id}` | Poll one survey eval job. |
| `GET` | `/api/web-eval/tasks` | List web tasks. |
| `POST` | `/api/web-eval` | Start a web persona evaluation. |
| `GET` | `/api/web-eval/jobs/{job_id}` | Poll one web eval job. |
| `GET` | `/api/web-eval/jobs/{job_id}/screenshots/{filename}` | Fetch one web trace screenshot. |
| `GET` | `/api/appworld-eval/tasks` | List AppWorld tasks. |
| `POST` | `/api/appworld-eval` | Start an AppWorld persona evaluation. |
| `GET` | `/api/appworld-eval/jobs/{job_id}` | Poll one AppWorld eval job. |

## Health

### `GET /api/health`

Returns a process liveness response.

Response:

```json
{
  "status": "ok"
}
```

### `GET /api/preflight`

Returns user-facing readiness checks for credentials, catalogs, RecAI resources,
optional sidecars, and eval surfaces.

Response:

```json
{
  "ready": true,
  "checks": [
    {
      "group": "Core",
      "name": "OpenAI credentials",
      "ok": true,
      "detail": "Configured.",
      "optional": false
    }
  ]
}
```

`ready` ignores checks marked `optional`.

## Config

### `GET /api/config/options`

Returns the available config knobs, canonical defaults, and fixed runtime
environment metadata.

Response shape:

```json
{
  "knobs": [
    {
      "key": "domain",
      "label": "Domain",
      "description": "...",
      "options": [
        {
          "value": "movie",
          "label": "Movies",
          "description": "..."
        }
      ],
      "rebuildsAgent": true
    }
  ],
  "defaults": {
    "domain": "movie",
    "engine": "gpt-4o-mini"
  },
  "environment": {
    "runtime": "local",
    "personaAgent": "...",
    "personaModel": "anthropic/claude-haiku-4-5",
    "applicationApi": "...",
    "scorer": "...",
    "cache": "...",
    "ranker": "...",
    "resources": "...",
    "agent": "...",
    "promptOwnership": {}
  }
}
```

## Manual Chat Sessions

Manual chat sessions drive the chatbot surface turn by turn. Turn execution is
asynchronous.

### `GET /api/sessions`

Lists saved chat sessions newest-first.

Response:

```json
[
  {
    "id": "session_abc123",
    "title": "Movie recommendations",
    "config": {},
    "turnCount": 2,
    "messageCount": 4,
    "createdAt": "2026-06-29T00:00:00Z"
  }
]
```

### `POST /api/sessions`

Creates a manual chat session.

Request body:

```json
{
  "title": "Movie recommendations",
  "config": {
    "domain": "movie",
    "engine": "gpt-4o-mini"
  }
}
```

Both fields are optional. `config` accepts partial config; invalid values return
`422`.

Response:

```json
{
  "id": "session_abc123",
  "title": "Movie recommendations",
  "config": {},
  "messages": [],
  "turns": [],
  "createdAt": "2026-06-29T00:00:00Z"
}
```

### `DELETE /api/sessions`

Deletes every saved chat session from memory and disk.

Response:

```json
{
  "deleted": 3
}
```

### `GET /api/sessions/{session_id}`

Returns one full chat session.

Path parameters:

- `session_id`: session id returned by `POST /api/sessions`.

Response is the same full `Session` shape returned by `POST /api/sessions`.

Errors:

- `404` when the session does not exist.

### `DELETE /api/sessions/{session_id}`

Deletes one chat session from memory and disk.

Response:

```json
{
  "deleted": "session_abc123"
}
```

Errors:

- `404` when the session does not exist.

### `PATCH /api/sessions/{session_id}/config`

Patches a session config. Some config changes invalidate the cached application
agent for the next turn.

Request body:

```json
{
  "config": {
    "domain": "beauty_product",
    "engine": "gpt-4o-mini"
  }
}
```

Response:

```json
{
  "session": {
    "id": "session_abc123",
    "title": "Beauty recommendations",
    "config": {},
    "messages": [],
    "turns": [],
    "createdAt": "2026-06-29T00:00:00Z"
  },
  "cacheInvalidated": true
}
```

Errors:

- `404` when the session does not exist.
- `422` when config validation fails.

### `GET /api/sessions/{session_id}/export`

Downloads one full session as JSON. The response includes a
`Content-Disposition` attachment header.

Errors:

- `404` when the session does not exist.

### `POST /api/sessions/{session_id}/turns`

Submits one user turn to a manual chat session. The endpoint returns
immediately with a job id; poll `GET /api/jobs/{job_id}` for completion.

Request body:

```json
{
  "message": "I want a thoughtful sci-fi movie recommendation."
}
```

Response:

```json
{
  "jobId": "job_abc123"
}
```

Errors:

- `404` when the session does not exist.
- `422` when the message is empty or invalid.

### `GET /api/jobs/{job_id}`

Polls one manual chat turn job.

Response while running:

```json
{
  "jobId": "job_abc123",
  "status": "running",
  "turn": null,
  "error": null
}
```

Response when done:

```json
{
  "jobId": "job_abc123",
  "status": "done",
  "turn": {
    "turnId": "0",
    "conversationId": "session_abc123",
    "backend": "recai",
    "userMessage": "I want a thoughtful sci-fi movie recommendation.",
    "assistantMessage": "...",
    "plan": [],
    "recommendedItems": [
      {
        "itemId": "123",
        "rank": 1,
        "title": "Example Item",
        "meta": "Sci-fi",
        "score": 0.92
      }
    ],
    "nativeRaw": null,
    "rawToolOutputs": null
  },
  "error": null
}
```

Errors:

- `404` when the job does not exist.

## Catalog

### `GET /api/catalog/search`

Searches the configured recommendation catalog.

Query parameters:

- `q` optional search text, default `""`.
- `genre` optional category filter.
- `limit` optional integer from `0` to `500`, default `50`.
- `domain` optional catalog domain, for example `movie`, `beauty_product`, or
  `game`.

Response:

```json
{
  "items": [
    {
      "itemId": "123",
      "title": "Example Item",
      "description": "...",
      "displayText": "...",
      "categories": ["sci-fi"],
      "metadata": {}
    }
  ],
  "total": 1
}
```

### `GET /api/catalog/items/{item_id}`

Returns one catalog item.

Path parameters:

- `item_id`: catalog item id.

Query parameters:

- `domain` optional catalog domain.

Response:

```json
{
  "itemId": "123",
  "title": "Example Item",
  "description": "...",
  "displayText": "...",
  "categories": ["sci-fi"],
  "metadata": {}
}
```

Errors:

- `404` when the item does not exist.

## Persona Catalog

### `GET /api/persona-eval/personas`

Lists persona profiles for eval task pickers.

Query parameters:

- `q` optional substring search, default `""`.
- `limit` optional positive integer.
- `domain` optional SUT-description domain. When provided, the response may
  include `sutDescription`.

Response:

```json
{
  "personas": [
    {
      "id": "Nemotron_01B0D4D4",
      "name": "Persona name",
      "source": "Nemotron",
      "blurb": "Short persona preview..."
    }
  ],
  "sutDescription": "..."
}
```

Errors:

- `422` when `domain` is unknown.

### `GET /api/persona-eval/personas/{persona_id}`

Returns one full persona profile.

Path parameters:

- `persona_id`: persona id returned by the persona list endpoint.

Response:

```json
{
  "id": "Nemotron_01B0D4D4",
  "name": "Persona name",
  "source": "Nemotron",
  "context": "Full persona context..."
}
```

Errors:

- `404` when the persona does not exist.

### `GET /api/persona-eval/goal-contexts`

Lists available goal-context prompt presets for chatbot persona eval.

Response:

```json
{
  "goalContexts": [
    {
      "id": "scenario_default",
      "label": "Default",
      "description": "..."
    }
  ]
}
```

## Chatbot Persona Eval

Chatbot persona eval starts a simulated persona conversation with a chatbot
application and scores the resulting interaction.

### `POST /api/persona-eval`

Starts a chatbot persona evaluation.

Request body:

```json
{
  "applicationId": "recai",
  "domain": "movie",
  "applicationContext": "movie",
  "personaId": "Nemotron_01B0D4D4",
  "maxTurns": 8,
  "goalContextId": "scenario_default",
  "engine": "gpt-4o-mini",
  "personaModel": "anthropic/claude-haiku-4-5"
}
```

Notes:

- `applicationId` is one of `recai`, `finance_openbb`, or
  `medical_assistant`.
- `recai` uses `domain`; supported domains are `movie`, `beauty_product`, and
  `game`.
- Non-RecAI applications use `applicationContext`.
- `maxTurns` must be between `1` and `20`.
- `engine` and `personaModel` are optional and fall back to service defaults.

Response:

```json
{
  "jobId": "persona_eval_abc123"
}
```

Errors:

- `422` when the persona, domain, application id, or model is invalid.

### `GET /api/persona-eval/jobs/{job_id}`

Polls one chatbot persona-eval job.

Response while running:

```json
{
  "jobId": "persona_eval_abc123",
  "domain": "movie",
  "applicationId": "recai",
  "applicationContext": "movie",
  "personaId": "Nemotron_01B0D4D4",
  "personaName": "Persona name",
  "sutDescription": "...",
  "goalContextId": "scenario_default",
  "status": "running",
  "phase": "turn_1",
  "turns": [],
  "questionnaire": null,
  "metricScores": null,
  "prompts": null,
  "error": null
}
```

Response when done populates `turns`, `questionnaire`, `metricScores`, and
`prompts`.

Errors:

- `404` when the job does not exist.

### `GET /api/persona-eval/runs`

Lists persisted eval runs across chatbot, survey, web, and AppWorld surfaces.

Response:

```json
{
  "runs": [
    {
      "id": "persona_eval_abc123",
      "createdAt": "2026-06-29T00:00:00Z",
      "applicationType": "chatbot",
      "domain": "movie",
      "personaName": "Persona name",
      "source": "Nemotron",
      "goalContextId": "scenario_default",
      "overallRating": 8,
      "numTurns": 4
    }
  ]
}
```

The summary is permissive and may include application-specific fields.

### `GET /api/persona-eval/runs/{run_id}`

Returns one persisted eval run.

Path parameters:

- `run_id`: run id from `GET /api/persona-eval/runs`.

Response for chatbot runs:

```json
{
  "id": "persona_eval_abc123",
  "createdAt": "2026-06-29T00:00:00Z",
  "config": {},
  "persona": {},
  "sutDescription": "...",
  "transcript": [],
  "recommendedItemIds": {},
  "questionnaire": {},
  "metricScores": {},
  "prompts": {}
}
```

Survey, web, and AppWorld persisted runs include their application-specific
fields, such as `surveyResult`, `webResult`, `webTrace`, `appworldResult`, and
`appworldTrace`.

Errors:

- `404` when the run does not exist.

## Survey Eval

Survey eval asks a simulated persona to complete a survey instrument.

### `GET /api/survey-eval/instruments`

Lists available survey instruments.

Response:

```json
{
  "instruments": [
    {
      "id": "chatgpt_images_market_research_v1",
      "title": "Market research survey",
      "description": "...",
      "questions": [
        {
          "id": "q1",
          "prompt": "How useful was this?",
          "type": "likert",
          "options": [],
          "minValue": 1,
          "maxValue": 5,
          "construct": "usefulness",
          "required": true
        }
      ]
    }
  ]
}
```

### `POST /api/survey-eval`

Starts a survey persona evaluation.

Request body:

```json
{
  "personaId": "Nemotron_01B0D4D4",
  "instrumentId": "chatgpt_images_market_research_v1",
  "personaModel": "anthropic/claude-haiku-4-5"
}
```

`instrumentId` defaults to `chatgpt_images_market_research_v1`.

Response:

```json
{
  "jobId": "survey_abc123"
}
```

Errors:

- `422` when the persona, instrument, or model is invalid.

### `GET /api/survey-eval/jobs/{job_id}`

Polls one survey eval job.

Response:

```json
{
  "jobId": "survey_abc123",
  "applicationType": "survey",
  "taskId": "survey_form",
  "instrumentId": "chatgpt_images_market_research_v1",
  "instrumentTitle": "Market research survey",
  "personaId": "Nemotron_01B0D4D4",
  "personaName": "Persona name",
  "status": "done",
  "phase": "complete",
  "surveyResult": {
    "instrument": {},
    "answers": [],
    "trajectory": [],
    "completion": {
      "numQuestions": 5,
      "numAnswered": 5,
      "meanLikert": 4.2
    }
  },
  "prompts": {},
  "error": null
}
```

Errors:

- `404` when the job does not exist.

## Web Eval

Web eval sends a simulated persona agent to a website task and records the
interaction trace. In BenchFlow mode this maps to `taskType=web`.

### `GET /api/web-eval/tasks`

Lists available web tasks.

Response:

```json
{
  "tasks": [
    {
      "id": "web-ecommerce-platform_product-discovery",
      "title": "Ecommerce product discovery",
      "siteName": "Northstar Home Goods",
      "siteUrl": "http://ecommerce-web:8000/",
      "description": "Browse the site and choose one product.",
      "outputArtifact": "ecommerce_interaction.json",
      "submissionProfile": "ecommerce_interaction"
    }
  ]
}
```

### `POST /api/web-eval`

Starts a web persona evaluation.

Request body:

```json
{
  "personaId": "Nemotron_01B0D4D4",
  "taskId": "web-ecommerce-platform_product-discovery",
  "personaModel": "anthropic/claude-haiku-4-5"
}
```

`taskId` defaults to `web-ecommerce-platform_product-discovery`.

Response:

```json
{
  "jobId": "web_abc123"
}
```

Errors:

- `422` when the persona, task, or model is invalid.

### `GET /api/web-eval/jobs/{job_id}`

Polls one web eval job.

Response:

```json
{
  "jobId": "web_abc123",
  "applicationType": "web",
  "taskId": "web-ecommerce-platform_product-discovery",
  "taskTitle": "Ecommerce product discovery",
  "siteName": "Northstar Home Goods",
  "siteUrl": "http://ecommerce-web:8000/",
  "personaId": "Nemotron_01B0D4D4",
  "personaName": "Persona name",
  "status": "done",
  "phase": "complete",
  "webResult": {
    "selectedProductId": "item-123",
    "overallExperienceRating": 8
  },
  "trace": {
    "events": [],
    "raw": {}
  },
  "prompts": {},
  "error": null
}
```

Errors:

- `404` when the job does not exist.

### `GET /api/web-eval/jobs/{job_id}/screenshots/{filename}`

Fetches a screenshot referenced by a web eval trace.

Path parameters:

- `job_id`: web eval job id.
- `filename`: screenshot filename. Nested paths are accepted by the route but
  are validated by the service.

Response:

- Binary file response.
- `Content-Type` is `image/svg+xml` for `.svg` screenshots and `image/webp` for
  all other screenshot files.

Errors:

- `400` when the filename is invalid.
- `404` when the job or screenshot does not exist.

## AppWorld Eval

AppWorld eval sends a simulated persona agent to an AppWorld API task and
records the API trajectory. In BenchFlow mode this maps to `taskType=appworld`.

### `GET /api/appworld-eval/tasks`

Lists available AppWorld tasks.

Response:

```json
{
  "tasks": [
    {
      "id": "appworld-demo-personal-admin",
      "title": "AppWorld personal admin task",
      "appName": "AppWorld",
      "description": "Complete a multi-app personal administration task through AppWorld-style APIs and report the final state.",
      "outputArtifact": "appworld_result.json",
      "submissionProfile": "appworld_result"
    }
  ]
}
```

### `POST /api/appworld-eval`

Starts an AppWorld persona evaluation.

Request body:

```json
{
  "personaId": "Nemotron_01B0D4D4",
  "taskId": "appworld-demo-personal-admin",
  "personaModel": "anthropic/claude-haiku-4-5"
}
```

`taskId` defaults to `appworld-demo-personal-admin`.

Response:

```json
{
  "jobId": "appworld_abc123"
}
```

Errors:

- `422` when the persona, task, or model is invalid.

### `GET /api/appworld-eval/jobs/{job_id}`

Polls one AppWorld eval job.

Response:

```json
{
  "jobId": "appworld_abc123",
  "applicationType": "appworld",
  "taskId": "appworld-demo-personal-admin",
  "taskTitle": "AppWorld personal admin task",
  "appName": "AppWorld",
  "personaId": "Nemotron_01B0D4D4",
  "personaName": "Persona name",
  "status": "done",
  "phase": "complete",
  "appworldResult": {
    "taskId": "appworld-demo-personal-admin",
    "success": true,
    "score": 1.0,
    "outcome": "Calendar invite and email draft completed.",
    "reason": "The runner completed the AppWorld task.",
    "createdAt": "2026-06-29T00:00:00Z"
  },
  "trace": {
    "events": [
      {
        "step": 1,
        "source": "agent",
        "message": "Listed available AppWorld apps.",
        "actions": [
          {
            "name": "appworld_api_call",
            "arguments": {
              "app": "system",
              "method": "list_apps"
            }
          }
        ]
      }
    ],
    "raw": {}
  },
  "prompts": {},
  "error": null
}
```

Errors:

- `404` when the job does not exist.

## BenchFlow-Compatible Runner API

`backend.service.benchflow_compat_server:app` is a dev/test service used by
MatrAIx to exercise the BenchFlow runtime boundary without a deployed BenchFlow
cluster. It is not mounted on the PersonaEval `/api` app.

Start it with:

```bash
PYTHONPATH=application/persona_eval \
  python -m uvicorn backend.service.benchflow_compat_server:app \
  --host 127.0.0.1 --port 9000
```

### `GET /health`

Returns compat-server liveness.

Response:

```json
{
  "status": "ok"
}
```

### `POST /v1/runs`

Creates a BenchFlow-compatible run.

Request body:

```json
{
  "taskType": "appworld",
  "payload": {
    "persona": {},
    "task": {},
    "config": {},
    "prompts": {}
  }
}
```

Supported `taskType` values:

- `web`
- `appworld`

Response:

```json
{
  "id": "compat_abc123",
  "status": "queued",
  "taskType": "appworld"
}
```

If `BENCHFLOW_COMPAT_WEB_COMMAND` or `BENCHFLOW_COMPAT_APPWORLD_COMMAND` is set,
the compat server runs that command. The command receives:

- `BENCHFLOW_RUN_ID`
- `BENCHFLOW_TASK_TYPE`
- `BENCHFLOW_PAYLOAD_JSON`
- `BENCHFLOW_OUTPUT_DIR`

The command must write `trace.json` plus the expected result artifact into
`BENCHFLOW_OUTPUT_DIR`.

### `GET /v1/runs/{run_id}`

Returns the current run status.

Response:

```json
{
  "id": "compat_abc123",
  "status": "succeeded",
  "taskType": "appworld"
}
```

Terminal statuses are `succeeded` and `failed`.

Errors:

- `404` when the run does not exist.

### `GET /v1/runs/{run_id}/artifacts/{name}`

Returns one JSON artifact for a completed run.

Common artifact names:

- `trace.json`
- `ecommerce_interaction.json`
- `web_result.json`
- `appworld_result.json`
- `screenshots_dir`

Errors:

- `404` when the run or artifact does not exist.
- `409` when the run is not finished.
- `500` when the run failed.

### `GET /mock/{run_id}/{filename}`

Serves deterministic SVG screenshots for mock web runs.

Supported mock filenames:

- `step-1.svg`
- `step-2.svg`

Errors:

- `404` when the run or mock screenshot does not exist.
