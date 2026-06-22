# Application team — getting started

A step-by-step path from zero to your first multi-persona survey run. No prior Harbor experience required.

**What you are doing:** loading a synthetic user profile (persona), putting that user in a product scenario (survey), and inspecting what they “said” — all inside a reproducible Docker sandbox.

**Time:** ~30–60 minutes the first time (mostly Docker image build).

---

## What you need

| Requirement | Why |
|-------------|-----|
| **[Docker](https://docs.docker.com/get-docker/)** | Each run uses a small container (survey, chat, web, …) |
| **uv** | Python + `harbor` CLI for this repo — [install in step 2](#2-install-uv-clone-and-sync) |
| **Anthropic API key** | Only for the persona example (step 6+). [Create one](https://console.anthropic.com/) if needed |

Optional: browse results without re-running — this repo includes example output under `jobs/`.

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

**Install [uv](https://docs.astral.sh/uv/)** (manages Python and project dependencies):

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
git clone https://github.com/matraix-ai/matraix.git
cd matraix
uv sync
```

Check the CLI:

```bash
uv run harbor --help
```

---

## 3. Smoke test (no API key)

Confirms Docker and Harbor with the upstream **hello-world** task (reference solution, no LLM call):

```bash
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

First run builds the Docker image (several minutes).

**Success:** the command finishes without error and writes output under `jobs/harbor-smoke-local/`.

---

## 4. Set your API key

The survey example uses **`persona-claude-code`**, which reads **`ANTHROPIC_API_KEY`** from your **shell** (not committed to git).

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # replace with your key
```

To keep it across terminal sessions, add the same line to `~/.zshrc` or `~/.bashrc`, then open a new terminal.

Other agents and keys: [choosing-an-agent.md](../environments/choosing-an-agent.md) and [`.env.example`](../../.env.example).

---

## 5. Look at a persona (optional but recommended)

A **persona** is a YAML profile — demographics, preferences, communication style, etc. The agent reads it and tries to answer *as that person*.

```bash
# Short preview
head -40 persona/datasets/bench-dev-2000/persona_0042.yaml
```

You will pass this file path on the command line as `persona_path=...`. Swap `persona_0042` for any `persona_XXXX.yaml` in the dataset to simulate a different person.

---

## Harbor vocabulary (Application runs)

| Term | In this guide |
|------|----------------|
| **Task** | The scenario — e.g. [example-survey_product-feedback](../../application/tasks/example-survey_product-feedback/) (product brief + survey questions + verifier). Same task for every persona. |
| **Trial** | One full run: **one persona** + **one task** in Docker → agent acts → verifier scores. Step 6 is a single trial. |
| **Job** | A batch container: Harbor runs **many trials** from one YAML (step 7). Output lands in `jobs/<job_name>/` with one subfolder per trial. |
| **Agent** | How the LLM is invoked — e.g. `persona-claude-code` (Claude Code CLI with persona injected). |
| **Model** | Which LLM backs the agent — e.g. `anthropic/claude-sonnet-4-6`. Agent and model are independent flags. |
| **Persona** | Which synthetic user profile — `persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml`. |

**Step 6 vs 7:** Step 6 = you **name one persona** on the command line. Step 7 = a script **samples N personas** (with a **seed** for reproducibility), writes a **job YAML**, then Harbor runs all trials.

---

## 6. One persona — you pick who

Same survey task as before, but you explicitly choose **agent**, **model**, and **which persona**:

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml \
  -p application/tasks/example-survey_product-feedback
```

| Flag | Meaning |
|------|---------|
| `-p` | Task path (the scenario) |
| `-a` | Agent (`persona-claude-code`, `persona-gemini-cli`, …) |
| `-m` | Model ID for that agent |
| `--ak persona_path=...` | **Which person** — any `persona_XXXX.yaml` under `bench-dev-2000` |

Change `persona_0042` to simulate someone else. Other agents/models: [choosing-an-agent.md](../environments/choosing-an-agent.md).

**What happens**

1. Harbor builds the task Docker image the first time (several minutes).
2. The agent reads the persona + survey materials inside the container.
3. It writes answers to `/app/output/survey_responses.json`.
4. The verifier runs; Harbor writes one trial under `jobs/` (adhoc job name).

**Success:** command ends without error; you see a path under `jobs/`.

**Shortcut:** pre-built runs in `jobs/` if you only want the viewer first (step 9).

---

## 7. Batch — sample many personas (job)

Running step 6 ten times by hand does not scale. **`generate_application_job.py`** samples personas, pins **agent**, **model**, and **seed**, and writes a **job YAML** Harbor runs in one go.

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --sample-size 10 \
  --seed 42 \
  --dataset persona/datasets/bench-dev-2000 \
  --agent-name persona-claude-code \
  --model-name anthropic/claude-sonnet-4-6
```

**Stratify** when you need balanced representation across a persona field (e.g. age brackets):

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --stratify dimensions.age_bracket
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--sample-size` | `1` | How many personas (= how many trials in the job) |
| `--seed` | `42` | Random seed — same seed + pool → same persona IDs (reproducible batch) |
| `--dataset` | `bench-dev-2000` | Persona pool to sample from |
| `--agent-name` | `persona-claude-code` | Agent for every trial |
| `--model-name` | `anthropic/claude-sonnet-4-6` | Model for every trial |
| `--stratify` | (none) | Optional — balance across a field, e.g. `--stratify dimensions.age_bracket` |

Outputs:

- `configs/jobs/application-task-job-recipe/example-survey-product-feedback-n10.yaml` — the **job** (task + list of agents, each with a different `persona_path`)
- `...n10.meta.json` — who was sampled, seed, pool size (for reports and reproducibility)

Run the job:

```bash
uv run harbor run -c configs/jobs/application-task-job-recipe/example-survey-product-feedback-n10.yaml
```

**What a job means here:** one survey **task**, **10 trials** — trial 1 uses `persona_0049`, trial 2 uses `persona_0028`, … (exact IDs are in the YAML header and `.meta.json`). All trials share the same agent and model you passed to the generator.

Each trial is one Docker run. Default `n_concurrent_trials: 1` runs them sequentially; edit the YAML to run more in parallel.

**Cost note:** 10 trials ≈ 10 LLM calls. Use `--sample-size 3` while testing.

**Single persona via job file:** `--sample-size 1` is equivalent to step 6, but with sampling + seed instead of hand-picking `persona_0042`.

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
        └── app/output/survey_responses.json   # The agent’s answers
```

Open `survey_responses.json` to read what that simulated user chose.

---

## 9. Browse runs in the viewer

```bash
uv run harbor view jobs --build
```

Opens a local web UI listing jobs and trials — transcripts, artifacts, verifier logs. Use this to compare personas side by side.

To explore without spending API credits, point the viewer at the checked-in `jobs/` folder (already in the repo).

---

## 10. Create a new application task

### 1. Understand task structure

Read [task-guide.md](./task-guide.md) — `task.toml`, `instruction.md`, `environment/`, `tests/`.

### 2. View other scenario types

Survey is only one **form**. Chat, web, and computer-use need different Docker setups and **different persona agents** (e.g. web uses Playwright or browser automation, not `persona-claude-code` alone).

Browse the example table in [task-guide.md](./task-guide.md#reference-scenarios), run any example with the suggested agent, then inspect with:

```bash
uv run harbor view jobs --build
```

Agent ↔ form mapping: [choosing-an-agent.md](../environments/choosing-an-agent.md).

### 3. Scaffold a new task

Copy the closest **example** task, then put your copy at **`application/tasks/<your-task-name>`** (any folder name — no `example-` prefix required):

```bash
# survey
cp -R application/tasks/example-survey_product-feedback \
      application/tasks/<your-task-name>

# chat (REST API sidecar)
cp -R application/tasks/example-chat-api_support_chatbot \
      application/tasks/<your-task-name>

# chat (MCP sidecar)
cp -R application/tasks/example-chat-mcp_support_chatbot \
      application/tasks/<your-task-name>

# web — pick one example-web-* stack (see web-interaction.md)
cp -R application/tasks/example-web-playwright_books-interest \
      application/tasks/<your-task-name>

# computer-use (macOS / iOS / Linux — copy the matching example)
cp -R application/tasks/example-computer-use-macos_notification-preferences \
      application/tasks/<your-task-name>
```

**Web:** Playwright, browser-use, Cocoa, and CUA use different agents and Docker setups — read [web-interaction.md](./web-interaction.md) before copying an `example-web-*` task.

### 4. Edit the task

1. **`task.toml`** — metadata (`type`, `domain`, `tags`), timeouts, `artifacts` paths.
2. **`instruction.md`** — scenario and required `/app/output/` format.
3. **`environment/`** — Dockerfile; add dependencies or sidecars if needed; put input files here.
4. **`tests/`** — what to verify; what trajectory or submission fields to capture for metrics.

### 5. Try one persona

```bash
uv run harbor run \
  -a <agent-for-your-form> \
  -m <model> \
  --ak persona_path=persona/datasets/bench-dev-2000/persona_0042.yaml \
  -p application/tasks/<your-task-name>
```

Use the agent from [choosing-an-agent.md](../environments/choosing-an-agent.md) for your form.

### 6. Try a batch of personas

Same as step 7 — generate a job YAML, then run it:

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/<your-task-name> \
  --sample-size 10 \
  --seed 42 \
  --agent-name persona-claude-code \
  --model-name anthropic/claude-sonnet-4-6

uv run harbor run -c configs/jobs/application-task-job-recipe/<generated>.yaml
```

### 7. View outputs

```bash
uv run harbor view jobs --build
```

Check per-trial artifacts under `jobs/<job_name>/<trial>/artifacts/`.

### 8. Batch reporting (optional)

To aggregate metrics across many personas for **your** task (tables, distributions, HTML), add a folder under `application/reporting/<your-task-name>/` and write scripts that read `jobs/<job_name>/` (trial results, `persona_meta.json`, verifier output).

See [application/reporting/README.md](../../application/reporting/README.md). Persona **grounding** reports are a separate track under `persona/reporting/`.
