# Application module

> Part of [Playground](../README.md). We own **persona-affiliated product
> simulation scenarios** — surveys, chatbots, live web, and computer-use tasks.

Welcome. If you are joining to design scenarios, run demos, or ship a new task,
you are in the right place.

---

## Start here

| You want to… | Go to |
|--------------|-------|
| Run your first persona survey (terminal) | **[QUICKSTART.md](QUICKSTART.md)** |
| Play tasks in the UI | QUICKSTART **[§10 — Playground](QUICKSTART.md#10-playground--play-tasks-visually)** |
| Add a new task | [tasks/README.md](tasks/README.md) + [task-guide.md](task-guide.md) |
| Pick agent + API keys | [choosing-an-agent.md](choosing-an-agent.md) |
| Understand how runs execute | [environment/README.md](../environment/README.md) |
| Use the HTTP API | [playground/REST_API.md](playground/REST_API.md) |

**Time budget:** ~30–60 minutes for a first end-to-end pass (Docker image builds
 dominate on web/CUA tasks).

---

## What Application delivers

Each runnable scenario under `application/tasks/` defines:

- a **persona-facing** scenario (`instruction.md` — no agent names)
- task metadata (`task.toml` — type, domain, environment definition)
- a **verifier** (`tests/` — shape, coverage, quality signals)
- optional **batch reporting** (`reporting.json` — summaries and LLM judges)

Persona profiles live in `persona/datasets/`. Tasks reference them via
`persona_path=` at job launch — never copy persona YAML into application folders.

```text
application/
  tasks/              Executable scenarios (survey, chat, web, os-app)
  task-spec/          Shared contracts per interaction type
  playground/       Playground UI, FastAPI backend, remote runner client
  scripts/            generate_application_job.py, report_job.py
  QUICKSTART.md       Contributor walkthrough (terminal → batch → UI)
  task-guide.md       Folder layout and reference tasks
  choosing-an-agent.md
  web-interaction.md
```

Shared Docker / sidecar stacks: `environment/task-environments/application/`.

---

## Task types at a glance

| Type | Reference task | Agent (typical) | Docs |
|------|------------------|-----------------|------|
| Survey | `example-survey_product-feedback` | `persona-claude-code` | [task-spec/survey/](task-spec/survey/) |
| Chatbot | `chat_recai` | `persona-claude-code` | [task-spec/chatbot/](task-spec/chatbot/) |
| Web | `example-web-playwright_quote-choice` | `persona-openhands-sdk` | [web-interaction.md](web-interaction.md) |
| OS / computer-use | `example-computer-use-ios_photo-access-review` | `persona-computer-1` | [task-spec/os-app/](task-spec/os-app/) |

Copy the closest **`example-*`** sibling when adding a task. See
[tasks/README.md](tasks/README.md) for the full checklist.

---

## Conventions (please follow)

1. **`instruction.md` is persona-facing only** — scenario + output format. Put
   agent names and smoke commands in the task **README** under *Suggested setup
   (non-binding)*.
2. **Harbor task names** use one slash: `application/{slug}`.
3. **Generated job YAML** uses hyphenated slugs from folder names
   (`example-survey-product-feedback-auto-n1.yaml`, not underscores).
4. **Do not commit** bulk `jobs/` output — curated demo jobs in `jobs/` are
   maintained intentionally; your local runs stay local unless asked otherwise.

---

## Scenario proposal template

Use this when opening an Issue or design doc before coding:

```text
Scenario name:
Task type:                # survey / chatbot / web / os-app
Domain / vertical:
Product or system under test:
Task specification:       # episode + required artifacts
Environment needs:        # sidecar, browser, credentials
Persona inputs:           # cohort or dimensions (by reference)
User goal and context:
Metrics:                  # success, fidelity, friction, …
Outputs:                  # trajectory, telemetry, reports
Known limitations:
```

Domain inspiration:
[application-domain-benchmark-catalog.md](../docs/research/application-domain-benchmark-catalog.md).

---

## Batch reporting

Reporting is task-owned, not a separate app folder:

| Piece | Location |
|-------|----------|
| Policy | `application/tasks/<name>/reporting.json` |
| Rollup script | `application/scripts/report_job.py` → `jobs/<job>/aggregation.json` |
| Playground / API | optional LLM judges when `PLAYGROUND_REPORTING_ENABLE_LLM=1` |

---

## Guides index

| Doc | Purpose |
|-----|---------|
| [QUICKSTART.md](QUICKSTART.md) | Zero → first run → batch → Playground → new task |
| [task-guide.md](task-guide.md) | Task folder structure |
| [task-spec/README.md](task-spec/README.md) | Hub — links to per-type specs and shared reporting docs |
| [web-interaction.md](web-interaction.md) | Playwright vs browser-use vs Cocoa vs CUA |
| [choosing-an-agent.md](choosing-an-agent.md) | Agent ↔ form ↔ API keys |
| [tasks/README.md](tasks/README.md) | Contributor checklist |
| [scripts/README.md](scripts/README.md) | Job generation scripts |
| [playground/README.md](playground/README.md) | Playground app |
| [playground/UNIFIED_RUNTIME.md](playground/UNIFIED_RUNTIME.md) | Local vs remote execution |

---

## Contributing

- New scenarios → `application/tasks/`
- Metrics / judges → `reporting.json` + `packages/rewardkit/`
- UI / API → `application/playground/`

Workflow and PR rules: [CONTRIBUTING.md](../CONTRIBUTING.md).

Open Environment roadmap items (task review agent, multi-agent env, benchmark
import) live in [environment/README.md](../environment/README.md#roadmap--open-work).
