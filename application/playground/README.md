# Playground

Playground is the PersonaBench workbench for evaluating interactive applications
with simulated persona users. This directory is the clean import of the useful
Playground app code from the MatrAIx PR #127 snapshot; the raw snapshot
directory is intentionally not part of `main`.

## Current Status

Included in this clean tree:

- React/Vite frontend under `frontend/`.
- FastAPI backend and service layer under `backend/`.
- Persona simulator package under `packages/playground/src/playground/`.
- Persona catalog sourced from `persona/datasets/bench-dev-sample/`.
- Survey, chatbot, and web evaluation APIs.

Preserved from the earlier clean PersonaBench main:

- `application.playground.backend.service.survey_questionnaire_catalog`
- `application.playground.backend.service.survey_types`

Not included as a raw dump:

- The historical `applications/tasks/chatbot_chat_api` tree.
- The full RecAI / InteRecAgent checkout and large resource bundle.
- Generated run outputs, local resource caches, and raw snapshot folders.

The current clean recommender task sidecar lives at:

```text
environment/task-environments/application/shared-chat-api-recommender/recommender-api/
```

It is suitable for smoke runs and API-contract compatibility. Full native RecAI
recommendations should be restored later as a focused task/runtime PR with
external resources documented separately.

## RecAI Runtime Notes

Playground keeps the chatbot runtime task-backed and lightweight by default.

- The recommender chatbot task lives at
  `application/tasks/recommender-agent_chat_api/`.
- The shared chatbot runtime bridge lives at
  `environment/task-environments/application/shared-chat-api-recommender/recommender-api/`.
- Large native RecAI resource bundles are intentionally not kept in the default
  developer path inside this repo.

If a fuller native RecAI runtime is restored later:

- keep runtime code task-owned and runtime-focused under the shared recommender
  path above
- keep large resources out of git and document their external artifact
  locations
- add a setup script if resources must be materialized locally
- add smoke tests for the API contract and at least one real recommendation turn

The default Playground local workflow uses the project `.venv`, but do not
assume that must always be the only supported environment for a native RecAI
stack. If a separate dependency set is required, document it explicitly and
keep it distinct from the default dev workflow.

For REAL-mode cache-heavy runs, you can redirect Hugging Face and
sentence-transformer caches with:

- `HF_HOME`
- `TRANSFORMERS_CACHE`
- `SENTENCE_TRANSFORMERS_HOME`

## Local credentials

Playground loads secrets from `application/playground/.env.local` (gitignored).
Copy the template and fill in the keys you need:

```bash
cd application/playground
cp .env.local.example .env.local
```

`run_dev.sh` and `run_demo.sh` source this file automatically. Keys exported only
in `~/.zshrc` are not available when the IDE or other non-interactive launchers
start the backend — use `.env.local` for a stable setup.

## Quickstart

From the repository root:

```bash
cd application/playground/frontend
npm ci
npm run build
cd ../../..

PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m uvicorn backend.api.app:app \
  --host 127.0.0.1 --port 8765 --workers 1
```

Open `http://127.0.0.1:8765`.

You can also run the packaged launcher after building the frontend:

```bash
cd application/playground
./run_demo.sh
```

For Vite frontend development, run the API in one terminal and the dev server in
another:

```bash
bash application/playground/backend/run_dev.sh
cd application/playground/frontend && npm run dev
```

## API Surface

All app endpoints are mounted under `/api`.

See [REST_API.md](REST_API.md) for the full endpoint-by-endpoint contract,
including Harbor job launch, trial debrief, and persona-pool APIs.

See [UNIFIED_RUNTIME.md](UNIFIED_RUNTIME.md) for Harbor-backed startup commands
that run the chatbot, survey, web, and OS-app surfaces through one backend.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Backend liveness check. |
| `GET` | `/api/preflight` | Readiness checks for keys, catalogs, and runtime resources. |
| `GET` | `/api/config/options` | Available domains, models, and runtime options. |
| `GET` | `/api/playground/personas` | List persona profiles. |
| `POST` | `/api/harbor/jobs` | Launch a Harbor batch evaluation job. |
| `GET` | `/api/harbor/jobs/{job}` | Poll job status and trial list. |

Interactive OpenAPI docs are available at `/docs` when the backend is running.

## Execution Runtime

Playground runs evaluations through **Harbor** batch jobs (`POST /api/harbor/jobs`).
Set `MATRIX_PLAYGROUND_RUNTIME=harbor` when you want the config surface to
label the active runtime as Harbor-backed (the cockpit always launches Harbor
jobs regardless).

## Validation

Useful local checks:

```bash
PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest packages/playground/src/playground/tests -q

PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest application/playground/backend/tests -q

PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m pytest tests/application/playground -q

.venv/bin/ruff check application/playground tests/application/playground
```

Frontend:

```bash
cd application/playground/frontend
npm ci
npm run build
```

## Layout

```text
backend/        FastAPI app, service layer, backend tests
frontend/       React/Vite SPA
run_demo.sh     Single-origin launcher after frontend build
```

Shared core package:

```text
packages/playground/src/playground/
```

Canonical local persona source:

```text
persona/datasets/bench-dev-sample/
```

Related application tasks live outside this app directory:

```text
application/tasks/example-survey_product-feedback/
application/tasks/recommender-agent_chat_api/
application/tasks/example-web-playwright_quote-choice/
```
