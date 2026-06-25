# PersonaEval

PersonaEval is a workbench for **testing and evaluating interactive chatbot
applications with simulated persona users**. The current app adapters include a
RecAI / InteRecAgent recommender over real item catalogs (movies, beauty
products, games) and a finance research chatbot backed by OpenBB-style tools.

PersonaEval gives you two surfaces over those applications, in one web app:

- **Chat** — you talk to the selected chatbot turn by turn and inspect its tool
  plan, the ranked candidates, and the raw model action. For interactive
  debugging.
- **PersonaEval** — pick a persona from a catalog of 336, set the run knobs,
  and an LLM "user simulator" drives a full multi-turn conversation against
  the application on its own, then scores the result (overall rating +
  per-dimension + transcript). Fully headless-capable, so it can run inside a
  harness.

The frontend is a React/Vite SPA; the backend is a FastAPI app that also serves
the built SPA, so the whole thing runs at a single origin.

---

## Quickstart (the demo)

**Prerequisites**

- Python environment with the RecAI dependencies — see
  [`RECAI_ENV_NOTES.md`](RECAI_ENV_NOTES.md) for how to provision it.
- Node.js 18+ (to build the frontend).
- This is a git **submodule** consumer: clone with submodules so RecAI is present —
  `git clone --recurse-submodules …`, or in an existing clone run
  `git submodule update --init --recursive`.

**Run it**

```bash
cd applications/persona_eval

# 1) build the frontend (produces frontend/dist, which the backend serves)
cd frontend && npm install && npm run build && cd ..

# 2) start the app (activate your venv first, or pass VENV=/path/to/venv)
./run_demo.sh
```

Open **http://127.0.0.1:8765**. The **catalog browser works immediately** — the
item catalogs ship with the chatbot task at
`applications/tasks/chatbot_chat_api/environment/chatbot_api/data/catalogs/`, so
you can browse all ~9.9k movies / 8.7k games / 8.7k beauty products with no
extra download.

> Reaching it from your laptop over SSH? Either forward the port
> (`ssh -L 8765:127.0.0.1:8765 …`) or start with `HOST=0.0.0.0 ./run_demo.sh`.

## Running live recommendations

Browsing works out of the box; producing *real* recommendations needs two more
things (a fresh clone has neither):

1. **An OpenAI key** — `export OPENAI_API_KEY=sk-…` (or copy
   [`.env.local.example`](.env.local.example) to `.env.local` and fill it in —
   it's gitignored and auto-loaded).
2. **The recommender resource bundle** — the ~1.2 GB similarity matrices and
   SASRec checkpoints are too big for git, so a script fetches them:

   ```bash
   python applications/tasks/chatbot_chat_api/environment/chatbot_api/scripts/setup_resources.py
   python applications/tasks/chatbot_chat_api/environment/chatbot_api/scripts/setup_resources.py --zip PATH
   ```

   It installs the official RecAI bundle (movie / beauty_product / game) under
   `applications/tasks/chatbot_chat_api/environment/chatbot_api/recai/InteRecAgent/resources/<domain>/`
   and rebuilds the task-owned parquet catalogs.

`GET /api/preflight` (and the chip in the top bar) reports exactly what's ready
vs. missing, in plain language.

---

## API

All endpoints are under `/api` on the same origin. Interactive OpenAPI docs are
served at **`/docs`** when the app is running.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check. |
| GET | `/api/preflight` | Readiness checks (key, engine, catalog, resources) with plain-language detail. |
| GET | `/api/config/options` | Editable run knobs (model, domain, …) + read-only environment facts. |
| **Chat** | | |
| POST | `/api/sessions` | Create a chat session. |
| GET | `/api/sessions` | List sessions. |
| GET | `/api/sessions/{id}` | Get one session (config + turns). |
| PATCH | `/api/sessions/{id}/config` | Update a session's run config. |
| POST | `/api/sessions/{id}/turns` | Send a user turn; returns a `jobId` to poll. |
| GET | `/api/jobs/{id}` | Poll a turn job (status + result). |
| GET | `/api/sessions/{id}/export` | Download a session as JSON. |
| **Catalog** | | |
| GET | `/api/catalog/search` | Search a domain's catalog (`q`, `genre`, `limit`, `domain`). |
| GET | `/api/catalog/items/{id}` | Fetch one catalog item (`domain`). |
| **PersonaEval** | | |
| GET | `/api/persona-eval/personas` | List the persona catalog (`q`, `limit`). |
| GET | `/api/persona-eval/personas/{id}` | One persona's full humanized profile. |
| GET | `/api/persona-eval/goal-contexts` | Selectable conversation styles. |
| POST | `/api/persona-eval` | Start a run (`domain`, `personaId`, `maxTurns`, `goalContextId`); returns a `jobId`. |
| GET | `/api/persona-eval/jobs/{id}` | Poll a running eval (growing transcript + scores). |
| GET | `/api/persona-eval/runs` | List persisted runs. |
| GET | `/api/persona-eval/runs/{id}` | Fetch one persisted run. |

---

## Chatbot Application Task

The chatbot application adapter lives in
`applications/tasks/chatbot_chat_api/environment/chatbot_api/harbor_api/`. It
wraps each chatbot application behind a smaller synchronous REST contract for
persona agents:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Sidecar liveness check. |
| POST | `/v1/session` | Create a recommender chat session. |
| POST | `/v1/messages` | Send one user message and receive one recommender reply. |
| GET | `/v1/conversation?sessionId=...` | Fetch transcript and turns. |
| GET | `/v1/recommendations?sessionId=...` | Fetch recommended item ids across turns. |

The Harbor task is `applications/tasks/chatbot_chat_api/`. It runs the chatbot
application router sidecar, lets the task controller drive the selected
application, and writes `/app/output/transcript.json`,
`/app/output/application_result.json`, and the persona self-report artifacts.

Contract tests:

```bash
PYTHONPATH=applications/persona_eval:applications/tasks/chatbot_chat_api/environment/chatbot_api \
  .venv/bin/python \
  -m pytest applications/tasks/chatbot_chat_api/environment/chatbot_api/harbor_api/tests/test_server.py -q
```

Harbor smoke, once the Harbor runtime is installed:

```bash
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export MATRIX_HARBOR_COMMAND="harbor run"
# Or point to a local Harbor checkout:
# export MATRIX_HARBOR_COMMAND="uv --directory /path/to/harbor run --frozen harbor run"
./run_demo.sh
```

The sidecar uses the real RecAI / InteRecAgent path. The first Docker build is
heavy because it installs RecAI dependencies and downloads the ready-to-run
resource bundle.

---

## Project layout

```
backend/        FastAPI app (api/) + service layer (service/) + tests
frontend/       React/Vite SPA (built to frontend/dist, served by the backend)
persona_eval/   Persona simulator, goal contexts, runner, persona catalog
data/personas/  Shared persona catalog
run_demo.sh     Start the app

../../applications/tasks/chatbot_chat_api/environment/chatbot_api/
  harbor_api/     Chatbot sidecar router and app adapters
  recbot/         Bridge to the in-process RecAI agent
  recai/          Microsoft RecAI submodule
  data/catalogs/  Committed chatbot item catalogs
  scripts/        setup_resources.py for the recommender bundle
```

## Development

```bash
# Backend tests (no RecAI/OpenAI/network needed — the suite fakes the engine)
PYTHONPATH=.:../../applications/tasks/chatbot_chat_api/environment/chatbot_api \
  python -m pytest backend/tests persona_eval/tests -q

# Chatbot task API tests
PYTHONPATH=../../applications/tasks/chatbot_chat_api/environment/chatbot_api \
  python -m pytest ../../applications/tasks/chatbot_chat_api/environment/chatbot_api/harbor_api/tests \
  ../../applications/tasks/chatbot_chat_api/environment/chatbot_api/recbot/tests -q

# Frontend typecheck + build
cd frontend && npm run typecheck && npm run build
```

The backend is a thin FastAPI layer (`backend/api/`) over a small service layer
(`backend/service/`); both are documented in module docstrings. The per-session
`INTERECAGENT_*` environment is derived automatically from each run's config by
`ConfigManager` — you don't set it by hand.
