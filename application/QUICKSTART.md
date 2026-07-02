# Application Quickstart

Short path for contributors: **visual demo → run an existing task → add a new task**.

Prereqs: Python 3.12, `uv`, Docker, `ANTHROPIC_API_KEY` (and `OPENAI_API_KEY` for chat).
Personas for local runs: `persona/datasets/bench-dev-sample/` (200 profiles, smoke `0042`).

---

## 1. Visual debug / demo (PersonaEval UI)

Best for picking a task, sampling personas, and watching trials live.

**Terminal A — API**

```bash
VENV=.venv bash application/persona_eval/backend/run_dev.sh
```

**Terminal B — frontend (hot reload)**

```bash
cd application/persona_eval/frontend && npm ci && npm run dev
```

Open **http://localhost:5173** (proxies `/api` → `:8765`).

In the cockpit:

1. Choose task type (Survey / Chat / Web / CUA).
2. Pick a task and persona(s).
3. Leave **Mode → auto** (default) and click **Run**.
4. Inspect trials under `jobs/<job_name>/` or use the batch monitor in the UI.

One-shot (API serves built frontend, no Vite):

```bash
cd application/persona_eval/frontend && npm ci && npm run build
cd ../../.. && application/persona_eval/run_demo.sh
# → http://127.0.0.1:8765
```

More detail: [persona_eval/README.md](persona_eval/README.md), [persona_eval/REST_API.md](persona_eval/REST_API.md).

---

## 2. Run an existing task (terminal)

Same contracts as the UI; good for CI and batch runs.

### A. Fastest paths (copy-paste)

```bash
# No API keys — validates Harbor + Docker only
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

**Survey or chat:** use section B below (`generate_application_job.py --execution-mode auto`).

### B. Auto mode (recommended)

Generate a job recipe, then run Harbor:

```bash
# Survey
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --persona-ids 0042

export ANTHROPIC_API_KEY="sk-ant-..."
export MATRIX_SURVEY_INSTRUMENT_ID=product_feedback_v1
uv run harbor run -c configs/jobs/application-task-job-recipe/example-survey_product-feedback-auto-n1.yaml
```

```bash
# Chat (+ sidecar if the UI or script prompts you to start one)
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

The generator prints exact `export` lines. Script reference: [scripts/README.md](scripts/README.md).

### C. Inspect results

```bash
uv run harbor view jobs --build   # trajectory viewer
ls jobs/<job_name>/               # trial artifacts, verifier output
```

Job recipe layout: [../configs/jobs/README.md](../configs/jobs/README.md).  
Repo-wide install and smoke: [../docs/running.md](../docs/running.md).

---

## 3. Create a new task

1. **Copy the closest `example-*` task** (same interaction type):

   ```bash
   cp -R application/tasks/example-survey_product-feedback application/tasks/<your-task>
   ```

2. **Edit task metadata** — `application/tasks/<your-task>/task.toml`:
   - `[task].name` → `personabench/application-<slug>`
   - `[metadata].type` → `survey` | `chat` | `web` | …
   - `[environment].definition` → `application/<your-task>`

3. **Add runtime files** under `environment/task-environments/application/<your-task>/`
   (Dockerfile, `docker-compose.yaml`, fixtures, sidecar API if needed).

4. **Smoke with one persona**:

   ```bash
   uv run python application/scripts/generate_application_job.py \
     --task application/tasks/<your-task> \
     --execution-mode auto \
     --persona-ids 0042
   # then harbor run -c … (see section 2)
   ```

5. **Iterate in the UI** (section 1) before scaling sample size.

Full checklist: [tasks/README.md](tasks/README.md).  
Scenario proposal template: [README.md](README.md#scenario-handoff-template).

---

## Cheat sheet

| Goal | Tool | Output |
|------|------|--------|
| Explore / debug visually | PersonaEval UI (Mode **auto**) | `jobs/` |
| Survey / chat (terminal) | `generate_application_job.py --execution-mode auto` | `jobs/<job_name>/` |
| Validate Docker/Harbor only | `harbor-smoke-local.yaml` | smoke task image |
| Batch / CI | `generate_application_job.py` + `harbor run` | job YAML + `jobs/` |
| Browse trajectories | `harbor view` | local viewer |
| New scenario | copy `example-*` + task env | `application/tasks/<name>/` |

**Task type → run path (Mode auto)**

| Task `type` | What to expect |
|-------------|----------------|
| `survey` | Fast host run — no task Docker image to build |
| `chat` | Host run — start the chat sidecar if prompted |
| `web` / `cua` | Task Docker image from `environment/task-environments/application/<task>/` |
