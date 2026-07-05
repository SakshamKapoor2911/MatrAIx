# Application team — getting started

A step-by-step path from zero to your first multi-persona survey run, then into
the **PersonaEval Cockpit** for interactive task play. No prior Harbor experience
required.

**What you are doing:** loading a synthetic user profile (persona), putting that
user in a product scenario (survey, chat, web, …), and inspecting what they
“said” — all inside a reproducible sandbox.

**Time:** ~30–60 minutes the first time (mostly Docker image build on web/CUA tasks).

---

## What you need

| Requirement | Why |
|-------------|-----|
| **[Docker](https://docs.docker.com/get-docker/)** | Web, CUA, and some smoke recipes use containers |
| **uv** | Python + `harbor` CLI — [install in step 2](#2-install-uv-clone-and-sync) |
| **Node.js 20+** | PersonaEval Cockpit frontend (optional but recommended) |
| **Anthropic API key** | Persona agents (step 6+). [Create one](https://console.anthropic.com/) if needed |
| **OpenAI API key** | Some chat tasks and alternate LLM backends |

Persona pool for local runs: `persona/datasets/bench-dev-sample/` (200 profiles;
smoke persona **`0042`**).

---

## 1. Install Docker and confirm it works

1. Install [Docker Desktop](https://docs.docker.com/get-docker/) (or Docker Engine on Linux).
2. **Start Docker** and wait until it reports “running”.
3. In a terminal:

   ```bash
   docker run --rm hello-world
   ```

   You should see a “Hello from Docker!” message. If this fails, fix Docker before continuing.

---

## 2. Install uv, clone, and sync

**Install [uv](https://docs.astral.sh/uv/)**:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a **new terminal** (or run `source $HOME/.local/bin/env` if the installer says so). Check:

```bash
uv --version
```

On macOS you can also use Homebrew: `brew install uv`.

**Clone the repo and install dependencies:**

```bash
git clone https://github.com/matraix-ai/matraix.git   # or your fork
cd matraix
uv sync
```

Check the CLI:

```bash
uv run harbor --help
```

Repo-wide install details: [../docs/running.md](../docs/running.md).

---

## 3. Smoke test (no API key)

Confirms Docker and Harbor with the upstream **hello-world** task (reference
solution, no LLM call):

```bash
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

First run builds the Docker image (several minutes).

**Success:** the command finishes without error and writes output under
`jobs/harbor-smoke-local/`.

---

## 4. Set your API key

Survey and chat examples use **`persona-claude-code`**, which reads
**`ANTHROPIC_API_KEY`** from your **shell** (not committed to git).

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # replace with your key
```

To keep it across terminal sessions, add the same line to `~/.zshrc` or
`~/.bashrc`, then open a new terminal.

Other agents and keys: [choosing-an-agent.md](choosing-an-agent.md).

---

## 5. Look at a persona (optional but recommended)

A **persona** is a YAML profile — demographics, preferences, communication style,
etc. The agent reads it and tries to answer *as that person*.

```bash
head -40 persona/datasets/bench-dev-sample/persona_0042.yaml
```

You will pass this file path on the command line as `persona_path=...`. Swap
`persona_0042` for any `persona_XXXX.yaml` in the dataset to simulate a different
person.

---

## Harbor vocabulary (Application runs)

| Term | In this guide |
|------|----------------|
| **Task** | The scenario — e.g. [example-survey_product-feedback](tasks/example-survey_product-feedback/) (product brief + survey questions + verifier). Same task for every persona. |
| **Trial** | One full run: **one persona** + **one task** → agent acts → verifier scores. Step 6 is a single trial. |
| **Job** | A batch container: Harbor runs **many trials** from one YAML (step 7). Output lands in `jobs/<job_name>/` with one subfolder per trial. |
| **Agent** | How the LLM is invoked — e.g. `persona-claude-code` (Claude Code CLI with persona injected). |
| **Model** | Which LLM backs the agent — e.g. `anthropic/claude-sonnet-4-6`. Agent and model are independent flags. |
| **Persona** | Which synthetic user profile — `persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml`. |

**Step 6 vs 7:** Step 6 = you **name one persona** on the command line. Step 7 =
`generate_application_job.py` **samples N personas** (with a **seed** for
reproducibility), writes a **job YAML**, then Harbor runs all trials.

**Terminal vs Cockpit:** Steps 6–9 use the terminal (good for CI and smoke).
[Section 10](#10-personaeval-cockpit-play-tasks-visually) uses the Cockpit UI —
same Harbor contracts, better for exploring trajectories and iterating on new tasks.

---

## 6. One persona — you pick who

### Survey (checked-in smoke recipe)

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-survey-local.yaml
```

### Survey / chat (auto mode — recommended)

Generate a job recipe, then run Harbor:

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --persona-ids 0042

export ANTHROPIC_API_KEY="sk-ant-..."
export MATRIX_SURVEY_TASK_PATH=application/tasks/example-survey_product-feedback
uv run harbor run -c configs/jobs/application-task-job-recipe/example-survey-product-feedback-auto-n1.yaml
```

```bash
# Chat (+ sidecar if prompted)
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

The generator prints exact `export` lines. Script reference: [scripts/README.md](scripts/README.md).

### Manual one-liner (any task)

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-survey_product-feedback
```

| Flag | Meaning |
|------|---------|
| `-p` | Task path (the scenario) |
| `-a` | Agent (`persona-claude-code`, `persona-browser-use`, …) |
| `-m` | Model ID for that agent |
| `--ak persona_path=...` | **Which person** — any `persona_XXXX.yaml` under `bench-dev-sample` |

Agent ↔ form mapping: [choosing-an-agent.md](choosing-an-agent.md).

**What happens**

1. Harbor builds the task Docker image the first time (web/CUA only; survey/chat
   in **auto** mode run on the host).
2. The agent reads the persona + task materials.
3. It writes answers to `/app/output/…`.
4. The verifier runs; Harbor writes one trial under `jobs/`.

**Success:** command ends without error; you see a path under `jobs/`.

---

## 7. Batch — sample many personas (job)

Running step 6 ten times by hand does not scale. **`generate_application_job.py`**
samples personas, pins **agent**, **model**, and **seed**, and writes a **job YAML**
under `configs/jobs/application-task-job-recipe/` (gitignored except curated examples).

### Generate your own batch

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --sample-size 10 \
  --seed 42 \
  --dataset persona/datasets/bench-dev-sample
```

**Stratify** when you need balanced representation across a persona field:

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --sample-size 10 \
  --seed 42 \
  --stratify dimensions.age_bracket
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--sample-size` | `1` | How many personas (= how many trials in the job) |
| `--persona-ids` | (none) | Explicit IDs instead of random sampling |
| `--seed` | `42` | Random seed — same seed + pool → same persona IDs |
| `--dataset` | `bench-dev-sample` | Persona pool to sample from |
| `--execution-mode` | `auto` | Same as PersonaEval Cockpit; use `force_docker` to always run in Docker |
| `--stratify` | (none) | Balance across a field, e.g. `dimensions.age_bracket` |
| `--name` | (derived) | Job basename |

Run the generated job (paths are also in the YAML header):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export MATRIX_SURVEY_TASK_PATH=application/tasks/example-survey_product-feedback
uv run harbor run -c configs/jobs/application-task-job-recipe/example-survey-product-feedback-auto-n10.yaml
```

**What a job means here:** one **task**, **N trials** — each trial uses a
different `persona_path` from the YAML. All trials share the same agent and model.

Each trial is one Harbor run. Edit `n_concurrent_trials` in the YAML to run trials
in parallel.

**Cost note:** 10 trials ≈ 10 LLM calls. Use `--sample-size 3` while testing.

---

## 8. Find your output on disk

After a job finishes:

```text
jobs/<job_name>/
├── result.json           # Summary stats
├── job.log
└── <trial_name>/
    ├── results.json      # Reward / verifier outcome
    ├── persona_meta.json # Which persona was used (if persona agent)
    └── artifacts/
        └── app/output/   # The agent's submission JSON
```

Open the submission JSON to read what that simulated user chose.

Refresh batch reporting:

```bash
uv run python application/scripts/report_job.py jobs/<job_name>
```

---

## 9. Browse runs in the viewer

```bash
uv run harbor view jobs --build
```

Opens a local web UI listing jobs and trials — transcripts, artifacts, verifier
logs. Use this to compare personas side by side.

To explore without spending API credits, browse checked-in examples under `jobs/`
if present, or run the no-key smoke recipe from step 3.

Job recipe layout: [../configs/jobs/README.md](../configs/jobs/README.md).

---

## 10. PersonaEval Cockpit — play tasks visually

After smoke passes, use the **Cockpit** to pick tasks, sample personas, launch
Harbor jobs, and inspect trajectories live — without hand-writing job YAML each
time.

### Start the UI

**Terminal A — API**

```bash
VENV=.venv bash application/persona_eval/backend/run_dev.sh
```

**Terminal B — frontend (hot reload)**

```bash
cd application/persona_eval/frontend && npm ci && npm run dev
```

Open **http://localhost:5173** (proxies `/api` → `:8765`).

Check the footer **Preflight** chip before blaming a task. Green = keys, Docker
(when needed), and catalogs look ready.

One-shot (API serves built frontend, no Vite):

```bash
cd application/persona_eval/frontend && npm ci && npm run build
cd ../../.. && application/persona_eval/run_demo.sh
# → http://127.0.0.1:8765
```

More detail: [persona_eval/README.md](persona_eval/README.md),
[persona_eval/REST_API.md](persona_eval/REST_API.md).

### In the Cockpit

1. Open the **PersonaEval** tab.
2. Switch task kind: **Survey** · **Chat** · **Web** · **OS app**.
3. Pick a task card; read instruction/context in the right panel.
4. Sample personas — **Quick pick** (`0042` is the default smoke id), **Random**,
   or **Stratified**.
5. Leave **Mode → auto** (default) and click **Run eval**.
6. Watch live progress; open a trial debrief for trajectory, scorecard, and verifier output.
7. Use **Runs** in the top bar to reopen past jobs.

| Task kind | First-run notes |
|-----------|-----------------|
| Survey | Fast — host auto mode, no task image build |
| Chat | Host auto; toggle **Start sidecar** if the task card shows the sidecar down |
| Web | Docker image build on first run; pick the web agent driver that matches the task stack |
| OS app | Docker or use.computer depending on platform |

Cockpit launches the same Harbor jobs as `generate_application_job.py --execution-mode auto`.
Chat env exports (`MATRIX_CHATBOT_*`) are applied automatically from the UI.

### Register a new task for Cockpit

New tasks must be indexed before they appear in the task picker. See
[task-guide.md § Cockpit registration](task-guide.md#cockpit-registration).

---

## 11. Create a new application task

### 1. Understand task structure

Read [task-guide.md](task-guide.md) — `task.toml`, `instruction.md`, `input/`,
shared runtimes under `environment/task-environments/application/`, `tests/`.

### 2. View other scenario types

Survey is only one **form**. Chat, web, and computer-use need different runtimes
and **different persona agents** (e.g. web uses Playwright or browser-use, not
`persona-claude-code` alone).

Browse the example table in [task-guide.md § Reference scenarios](task-guide.md#reference-scenarios),
run any example with the suggested agent, then inspect with Cockpit or
`harbor view`.

Web stack choice: [web-interaction.md](web-interaction.md).

### 3. Scaffold a new task

Copy the closest **example** task, then put your copy at
**`application/tasks/<your-task-name>`**:

```bash
# survey
cp -R application/tasks/example-survey_product-feedback application/tasks/<your-task-name>

# chat (REST API sidecar)
cp -R application/tasks/example-chat-api_support_chatbot application/tasks/<your-task-name>

# chat (MCP sidecar)
cp -R application/tasks/example-chat-mcp_support_chatbot application/tasks/<your-task-name>

# web — pick one example-web-* stack (see web-interaction.md)
cp -R application/tasks/example-web-playwright_quote-choice application/tasks/<your-task-name>

# computer-use (macOS / iOS / Linux — copy the matching example)
cp -R application/tasks/example-computer-use-macos_calendar-reminder-handoff application/tasks/<your-task-name>
```

### 4. Edit the task

1. **`task.toml`** — metadata (`type`, `domain`, `tags`), timeouts, `[environment].definition`.
2. **`instruction.md`** — scenario and required `/app/output/` format (**persona-facing only** — no agent names).
3. **`input/`** — context, schemas, questionnaire (survey), chatbot config (chat).
4. **`tests/`** — verifier; trajectory / submission fields for metrics.
5. **`reporting.json`** — batch reporting policy.

Runtime Dockerfiles live under `environment/task-environments/application/`
(prefer `shared-*` when the execution model matches).

### 5. Smoke with one persona (terminal)

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/<your-task-name> \
  --execution-mode auto \
  --persona-ids 0042
# Run the printed harbor command + exports
```

Use the agent from [choosing-an-agent.md](choosing-an-agent.md) for your form.

### 6. Iterate in Cockpit

Register the task ([task-guide.md](task-guide.md)), restart the backend, then
play with Quick pick personas before scaling sample size.

### 7. Batch of personas

Same as [step 7](#7-batch--sample-many-personas-job) with your task path.

### 8. View outputs

Cockpit **Runs** tab, or:

```bash
uv run harbor view jobs/<job_name> --build
```

Full task checklist: [tasks/README.md](tasks/README.md).

---

## Cheat sheet

| Goal | Tool | Output |
|------|------|--------|
| Explore / debug visually | PersonaEval Cockpit (Mode **auto**) | `jobs/` |
| Survey / chat (terminal) | `generate_application_job.py --execution-mode auto` | `jobs/<job_name>/` |
| Validate Docker/Harbor only | `harbor-smoke-local.yaml` | smoke task image |
| Batch / CI | `generate_application_job.py` + `harbor run` | job YAML + `jobs/` |
| Browse trajectories | `harbor view` or Cockpit **Runs** | local viewer |
| New scenario | copy `example-*` + register for Cockpit | `application/tasks/<name>/` |

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [task-guide.md](task-guide.md) | Task folder structure and reference scenarios |
| [web-interaction.md](web-interaction.md) | Playwright vs browser-use vs Cocoa vs CUA |
| [choosing-an-agent.md](choosing-an-agent.md) | Agent ↔ form mapping and API keys |
| [tasks/README.md](tasks/README.md) | Contributor checklist and reporting |
| [scripts/README.md](scripts/README.md) | Job generator and reporting scripts |
| [persona_eval/UNIFIED_RUNTIME.md](persona_eval/UNIFIED_RUNTIME.md) | Harbor vs remote execution plane |
