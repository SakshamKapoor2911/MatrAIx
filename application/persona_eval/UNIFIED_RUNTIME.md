# PersonaEval Runtime Runbook

PersonaEval launches evaluations through **Harbor batch jobs**. The Cockpit and
`POST /api/harbor/jobs` always use the same artifact layout under `jobs/`.

## Execution planes

| Plane | Meaning |
|-------|---------|
| `harbor` (default) | API machine or local dev runs `harbor run` directly |
| `remote` | API dispatches `taskType=harbor_job` to a **Remote Runner** HTTP worker |

Configure the default plane:

```bash
export MATRIX_EXECUTION_PLANE=harbor   # or remote
```

Optional per-request override: `"plane": "harbor"` or `"plane": "remote"` on
`POST /api/harbor/jobs`.

## Option A: Local Harbor (default)

**Terminal A — API**

```bash
bash application/persona_eval/backend/run_dev.sh
```

**Terminal B — frontend**

```bash
cd application/persona_eval/frontend && npm run dev
```

Open http://localhost:5173 and launch with **Mode → auto**.

## Option B: Remote Runner worker

Use this when the API should not execute `harbor run` locally.

**Terminal A — Remote Runner**

```bash
PYTHONPATH=.:environment/runtime:packages/persona-eval/src:application/persona_eval:src \
  uvicorn persona_eval.remote_runner.server:app \
  --host 127.0.0.1 --port 9100
```

**Terminal B — PersonaEval API**

```bash
export REMOTE_RUNNER_API_URL=http://127.0.0.1:9100
export MATRIX_EXECUTION_PLANE=remote
bash application/persona_eval/backend/run_dev.sh
```

The worker must have access to the same repository checkout (tasks, personas,
`jobs/` output directory). Production deployments typically mount a shared
`jobs/` path or sync artifacts after each run.

### Remote Runner API

- `GET /health`
- `POST /v1/runs` with `{"taskType": "harbor_job", "payload": {...}}`
- `GET /v1/runs/{id}`
- `GET /v1/runs/{id}/artifacts/{name}`

Primary payload fields for `harbor_job`:

- `jobName`
- `configYaml` — generated Harbor job recipe
- `repoRoot`
- `jobsDir`
- `env` — optional `PYTHONPATH` plus `MATRIX_*` task exports only (no API keys)

API keys and other secrets must be configured on the **worker** process, not
sent from the PersonaEval API host.

Optional dev-only `taskType=web` returns a deterministic mock when
`REMOTE_RUNNER_WEB_COMMAND` is not set.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `MATRIX_EXECUTION_PLANE` | Default `harbor` or `remote` |
| `REMOTE_RUNNER_API_URL` | Remote runner base URL (required for `remote`) |
| `REMOTE_RUNNER_API_KEY` | Optional bearer token |
| `REMOTE_RUNNER_INLINE` | Run jobs inline in the API process (tests) |
| `REMOTE_RUNNER_HARBOR_COMMAND` | Override `harbor` CLI command on the worker |

## Task types

Harbor resolves execution per task `metadata.type`:

- `survey` / `chatbot` → host-native agents in `auto` mode
- `web` / `os-app` → docker or `use-computer` backends

See [QUICKSTART.md](../QUICKSTART.md) for terminal `harbor run` examples.
