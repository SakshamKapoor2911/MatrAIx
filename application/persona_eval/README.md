# PersonaEval

PersonaEval is the PersonaBench workbench for evaluating interactive applications
with simulated persona users. This directory is the clean import of the useful
PersonaEval app code from the MatrAIx PR #127 snapshot; the raw snapshot
directory is intentionally not part of `main`.

## Current Status

Included in this clean tree:

- React/Vite frontend under `frontend/`.
- FastAPI backend and service layer under `backend/`.
- Persona simulator package under `persona_eval/`.
- 336 YAML persona profiles under `data/personas/`.
- Survey, chatbot, and web evaluation APIs.
- A small ecommerce web task under
  `application/tasks/web-ecommerce-platform_product-discovery/`.

Preserved from the earlier clean PersonaBench main:

- `application.persona_eval.backend.service.survey_instruments`
- `application.persona_eval.backend.service.survey_types`
- `application.persona_eval.backend.service.recommender_eval`

Not included as a raw dump:

- The historical `applications/tasks/chatbot_chat_api` tree.
- The full RecAI / InteRecAgent checkout and large resource bundle.
- Generated run outputs, local resource caches, and raw snapshot folders.

The current clean recommender task sidecar lives at:

```text
environment/task-environments/application/recommender-agent_chat_api/recommender-api/
```

It is suitable for smoke runs and API-contract compatibility. Full native RecAI
recommendations should be restored later as a focused task/runtime PR with
external resources documented separately.

## Quickstart

From the repository root:

```bash
cd application/persona_eval/frontend
npm ci
npm run build
cd ../../..

PYTHONPATH=.:application/persona_eval:environment/runtime \
  .venv/bin/python -m uvicorn backend.api.app:app \
  --host 127.0.0.1 --port 8765 --workers 1
```

Open `http://127.0.0.1:8765`.

You can also run the packaged launcher after building the frontend:

```bash
cd application/persona_eval
./run_demo.sh
```

For Vite frontend development, run the API in one terminal and the dev server in
another:

```bash
bash application/persona_eval/backend/run_dev.sh
cd application/persona_eval/frontend && npm run dev
```

## API Surface

All app endpoints are mounted under `/api`.

See [REST_API.md](REST_API.md) for the full endpoint-by-endpoint contract,
including request bodies, polling responses, persisted run shapes, and the
dev-only BenchFlow-compatible runner API.

See [UNIFIED_RUNTIME.md](UNIFIED_RUNTIME.md) for the local and BenchFlow-backed
startup commands that run the chatbot, survey, web, and AppWorld surfaces
through one backend.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Backend liveness check. |
| `GET` | `/api/preflight` | Readiness checks for keys, catalogs, and runtime resources. |
| `GET` | `/api/config/options` | Available domains, models, and runtime options. |
| `POST` | `/api/sessions` | Create a manual chat session. |
| `POST` | `/api/sessions/{id}/turns` | Send one manual chat turn. |
| `GET` | `/api/catalog/search` | Search the configured recommendation catalog. |
| `GET` | `/api/persona-eval/personas` | List persona profiles. |
| `POST` | `/api/persona-eval` | Start a chatbot persona evaluation run. |
| `POST` | `/api/survey-eval` | Start a survey persona evaluation run. |
| `POST` | `/api/web-eval` | Start a web persona evaluation run. |

Interactive OpenAPI docs are available at `/docs` when the backend is running.

## Execution Runtime

PersonaEval defaults to the local direct runtime. To send survey, chatbot, and
web runs to BenchFlow-hosted agents instead, start the backend with:

```bash
export MATRIX_PERSONA_EVAL_RUNTIME=benchflow
export BENCHFLOW_API_URL=http://127.0.0.1:9000
# Optional. Leave unset for local/no-auth BenchFlow services.
export BENCHFLOW_API_KEY=...
```

The backend keeps the same API contract (`jobId` + polling endpoints). BenchFlow
is used only behind the runner boundary, and the returned artifacts are
normalized into the existing `surveyResult`, chatbot transcript, and `webResult`
/ `trace` shapes.

For web traces, BenchFlow can either return a local `screenshots_dir` artifact
when the backend shares the runner filesystem, or include per-event
`screenshotUrl` values in `trace.json` for remotely hosted screenshots.

For local development without a deployed BenchFlow service, start the dev-only
compatibility server in a second terminal:

```bash
PYTHONPATH=.:application/persona_eval:environment/runtime \
  python -m uvicorn environment.integrations.persona_eval.benchflow.compat_server:app \
  --host 127.0.0.1 --port 9000
```

By default this serves deterministic mock web artifacts so the MatrAIx
BenchFlow path can be tested end-to-end. To bridge to a real BenchFlow CLI run,
set `BENCHFLOW_COMPAT_WEB_COMMAND`; the command receives
`BENCHFLOW_PAYLOAD_JSON` and `BENCHFLOW_OUTPUT_DIR`, then must write
`trace.json` plus `ecommerce_interaction.json` (or `web_result.json`) into that
output directory.

## Validation

Useful local checks:

```bash
PYTHONPATH=.:application/persona_eval:environment/runtime \
  .venv/bin/python -m pytest application/persona_eval/persona_eval/tests -q

PYTHONPATH=.:application/persona_eval:environment/runtime \
  .venv/bin/python -m pytest application/persona_eval/backend/tests -q

PYTHONPATH=.:application/persona_eval:environment/runtime \
  .venv/bin/python -m pytest tests/application/persona_eval -q

.venv/bin/ruff check application/persona_eval tests/application/persona_eval
```

Frontend:

```bash
cd application/persona_eval/frontend
npm ci
npm run build
```

## Layout

```text
backend/        FastAPI app, service layer, backend tests
frontend/       React/Vite SPA
persona_eval/   Persona simulator, runner, scoring, model clients
data/personas/  Shared PersonaEval persona catalog
run_demo.sh     Single-origin launcher after frontend build
```

Related application tasks live outside this app directory:

```text
application/tasks/persona-survey/
application/tasks/recommender-agent_chat_api/
application/tasks/web-ecommerce-platform_product-discovery/
```
