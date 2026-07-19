# Playground REST API

This document describes the Playground HTTP API exposed by
`backend.api.app:app`. All application endpoints are mounted under `/api`.

Interactive OpenAPI documentation is also available at `/docs` when the backend
is running.

## Conventions

- JSON uses camelCase field names.
- The API does not require authentication in local development.
- Long-running work is launched through `POST /api/harbor/jobs`. Clients poll
  `GET /api/harbor/jobs/{job_name}` until `launch.status` is `completed` or
  `failed`.
- Common Harbor launch statuses are `queued`, `running`, `completed`, and
  `failed`.
- FastAPI may return `422` for malformed requests or failed validation.
- Application handlers return `404` for unknown jobs, trials, personas, cohorts,
  screenshots, recordings, or tasks where applicable.

## Runtime boundary

Playground launches evaluations through Harbor batch jobs. The Playground and
`POST /api/harbor/jobs` share the same artifact layout under `jobs/`.

Execution can stay on the API host or dispatch to a Remote Runner worker:

```bash
MATRIX_EXECUTION_PLANE=harbor    # default — local harbor run
MATRIX_EXECUTION_PLANE=remote    # HTTP dispatch to Remote Runner
REMOTE_RUNNER_API_URL=http://127.0.0.1:9100
REMOTE_RUNNER_API_KEY=...        # optional bearer token for the worker API
```

Survey, chatbot, web, and os-app jobs share the same API regardless of plane.
See [UNIFIED_RUNTIME.md](UNIFIED_RUNTIME.md) for worker setup and remote payload
fields.

Optional per-request override: `"plane": "harbor"` or `"plane": "remote"` on
`POST /api/harbor/jobs`.

## Endpoint index

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Backend liveness. |
| `GET` | `/api/preflight` | Environment and resource readiness checks. |
| `GET` | `/api/chatbot-sidecars` | List chat sidecar statuses. |
| `POST` | `/api/chatbot-sidecars/{application_id}/start` | Start one chat sidecar. |
| `GET` | `/api/config/options` | Editable config knobs, defaults, and runtime facts. |
| `GET` | `/api/playground/personas` | List persona profiles (searchable). |
| `GET` | `/api/playground/personas/{persona_id}` | Read one full persona profile. |
| `GET` | `/api/harbor/jobs` | List Harbor batch jobs. |
| `POST` | `/api/harbor/jobs` | Launch a Harbor batch job. |
| `GET` | `/api/harbor/jobs/{job_name}` | Read one job detail view. |
| `DELETE` | `/api/harbor/jobs/{job_name}` | Delete one job and its artifacts. |
| `GET` | `/api/harbor/jobs/{job_name}/aggregation` | Read refreshed job aggregation JSON. |
| `GET` | `/api/harbor/jobs/{job_name}/live` | Live job/trial progress for the Playground. |
| `GET` | `/api/harbor/jobs/{job_name}/trials/{trial_name}/events` | Incremental trial event stream. |
| `GET` | `/api/harbor/jobs/{job_name}/trials/{trial_name}/debrief` | Post-run debrief for one trial. |
| `GET` | `/api/harbor/jobs/{job_name}/trials/{trial_name}/instruction` | Persona-facing instruction for one trial. |
| `GET` | `/api/harbor/jobs/{job_name}/trials/{trial_name}/trace` | Web trace payload for one trial. |
| `GET` | `/api/harbor/jobs/{job_name}/trials/{trial_name}/screenshots/{filename}` | Fetch one web trace screenshot. |
| `GET` | `/api/harbor/jobs/{job_name}/trials/{trial_name}/recording` | Fetch one os-app screen recording. |
| `GET` | `/api/persona-pool/catalog` | Persona pool dimension catalog. |
| `POST` | `/api/persona-pool/sample` | Sample personas from a pool. |
| `GET` | `/api/persona-pool/personas` | List persona cards from a pool. |
| `GET` | `/api/persona-pool/personas/{persona_id}` | Read one persona card/detail from a pool. |
| `GET` | `/api/persona-pool/cohorts` | List saved persona cohorts. |
| `POST` | `/api/persona-pool/cohorts` | Save a persona cohort. |
| `GET` | `/api/persona-pool/cohorts/{cohort_id}` | Read one saved cohort. |
| `GET` | `/api/tasks/detail` | Task detail for Playground setup (`taskPath` query). |
| `GET` | `/api/survey-eval/instruments` | List task-backed survey questionnaires. |
| `GET` | `/api/survey-eval/harbor-tasks` | List survey Harbor tasks for the Playground. |
| `GET` | `/api/chatbot-eval/tasks` | List chatbot Harbor tasks for the Playground. |
| `GET` | `/api/web-eval/tasks` | List web Harbor tasks for the Playground. |
| `GET` | `/api/os-app-eval/tasks` | List os-app Harbor tasks for the Playground. |

## Health

### `GET /api/health`

Returns a process liveness response.

```json
{
  "status": "ok"
}
```

### `GET /api/preflight`

Returns user-facing readiness checks for credentials, catalogs, optional
sidecars, and eval surfaces.

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

### `GET /api/chatbot-sidecars`

Returns sidecar container status for supported chat applications.

### `POST /api/chatbot-sidecars/{application_id}/start`

Starts the sidecar for one supported `application_id` when it is not already
running. Returns `404` for unknown application ids.

## Config

### `GET /api/config/options`

Returns the available config knobs, canonical defaults, and fixed runtime
environment metadata used by the Playground.

## Personas

### `GET /api/playground/personas`

Query parameters:

- `q` — optional substring search
- `limit` — optional result cap
- `domain` — accepted for backwards compatibility; no domain-specific blurb is
  returned

### `GET /api/playground/personas/{persona_id}`

Returns the full persona record (`id`, `name`, `source`, `context`).

## Harbor batch jobs

Harbor jobs are the canonical launch path. Artifacts are written under
`jobs/{job_name}/`.

### `GET /api/harbor/jobs`

Returns a list of job summaries (`jobName`, trial counts, status, timestamps).

### `POST /api/harbor/jobs`

Launch a multi-trial Harbor job from one application task.

Request body:

```json
{
  "taskPath": "application/tasks/example-survey_product-feedback",
  "sampleSize": 3,
  "seed": 42,
  "personaPool": "persona/datasets/bench-dev-sample",
  "personaIds": ["0042"],
  "mode": "auto",
  "plane": "harbor",
  "personaModel": "anthropic/claude-haiku-4-5",
  "nConcurrentTrials": 2
}
```

Common optional fields:

| Field | Purpose |
|---|---|
| `agentName` | Override resolved Harbor agent |
| `jobName` | Explicit job basename; if omitted, defaults to `pg-{task_slug}-{8 hex chars}` |
| `cohortId` | Launch from a saved persona cohort |
| `personaSources` / `personaFilters` | Pool sampling filters |
| `chatDomain`, `chatApplicationId`, `chatApplicationContext`, `chatMaxTurns` | Chatbot / user-sim tasks |
| `osAppSubmissionProfile`, `osAppBackend` | os-app / CUA tasks |

`mode` must be one of `auto`, `force_docker`, or `smoke`.
`plane` must be `harbor` or `remote`.

Response:

```json
{
  "jobName": "pg-example-survey-product-feedback-abc123",
  "configPath": "configs/jobs/application-task-job-recipe/pg-example-survey-product-feedback-abc123.yaml",
  "jobsDir": "jobs",
  "agentName": "persona-json-survey",
  "taskType": "survey",
  "trialProfile": "json_survey",
  "mode": "auto",
  "plane": "harbor"
}
```

Poll `GET /api/harbor/jobs/{job_name}` until `launch.status` is terminal.

### `GET /api/harbor/jobs/{job_name}`

Returns the job detail view: launch metadata, generated config path, trial list,
and per-trial result summaries when available.

### `DELETE /api/harbor/jobs/{job_name}`

Deletes the job directory and generated config when present.

### `GET /api/harbor/jobs/{job_name}/aggregation`

Returns `jobs/{job_name}/aggregation.json`, refreshing it when needed.

### `GET /api/harbor/jobs/{job_name}/live`

Returns live progress for the Playground: launch status, trial phases, and basic
persona labels.

### Trial inspection routes

| Route | Purpose |
|---|---|
| `GET .../trials/{trial_name}/events?after=0` | Incremental event stream |
| `GET .../trials/{trial_name}/debrief` | Structured post-run debrief |
| `GET .../trials/{trial_name}/instruction` | Persona-facing instruction text |
| `GET .../trials/{trial_name}/trace` | Web trajectory / trace JSON |
| `GET .../trials/{trial_name}/screenshots/{filename}` | Binary screenshot |
| `GET .../trials/{trial_name}/recording` | Binary screen recording (mp4) |

## Persona pool

Used by the Playground setup rails for sampling and cohort management.

### `GET /api/persona-pool/catalog?pool=...`

Returns dimension metadata for one persona pool.

### `POST /api/persona-pool/sample`

Samples personas from a pool with optional filters and stratification.

### `GET /api/persona-pool/personas`

Lists persona cards. Supports `limit`, `offset`, `seed`, `personaIds`, `detail`,
and `all`.

### `GET /api/persona-pool/personas/{persona_id}?pool=...`

Returns one persona card or detail record from the requested pool.

### `GET /api/persona-pool/cohorts`

Lists saved cohorts.

### `POST /api/persona-pool/cohorts`

Saves a cohort from explicit persona ids or a sampled/filtered selection.

### `GET /api/persona-pool/cohorts/{cohort_id}`

Returns one saved cohort definition.

## Task catalogs

Read-only catalogs for Playground task pickers. Each route returns a `tasks` array
with task metadata plus optional profile markdown when available.

| Route | Surface |
|---|---|
| `GET /api/tasks/detail?taskPath=...` | One task detail record (includes `personaStrategy` from `persona_strategy.json`) |
| `GET /api/survey-eval/instruments` | Survey questionnaires |
| `GET /api/survey-eval/harbor-tasks` | Survey Harbor tasks |
| `GET /api/chatbot-eval/tasks` | Chatbot Harbor tasks |
| `GET /api/web-eval/tasks` | Web Harbor tasks |
| `GET /api/os-app-eval/tasks` | os-app Harbor tasks |

## Related docs

- [UNIFIED_RUNTIME.md](UNIFIED_RUNTIME.md) — Harbor vs remote execution planes
- [QUICKSTART.md](../QUICKSTART.md) — terminal smoke and Playground setup
- OpenAPI `/docs` — generated from FastAPI models in `backend/api/schemas.py`
