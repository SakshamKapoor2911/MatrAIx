# Application team documentation

> Part of [PersonaBench](../README.md). The Application module owns **persona-affiliated
> product simulation scenarios**.

## New here?

**[QUICKSTART.md](QUICKSTART.md)** — install Docker, set an API key, run one survey
with a persona, scale to a batch, play tasks in the **PersonaEval Cockpit**, create
a new task. Written for contributors who are not full-time engineers.

This directory is the upgraded home of the MatrAIx
[`docs/applications`](https://github.com/JianhengHou/MatrAIx/tree/dev/harbor-based-work/docs/applications)
guides, adapted to the PersonaBench layout (shared runtimes, **Mode → auto**,
`bench-dev-sample` personas, PersonaEval Cockpit).

## Guides

| Doc | Purpose |
|-----|---------|
| [QUICKSTART.md](QUICKSTART.md) | Zero → first run → batch → Cockpit → new task |
| [task-guide.md](task-guide.md) | Application task folder structure and reference scenarios |
| [web-interaction.md](web-interaction.md) | Playwright vs browser-use vs Cocoa vs CUA for live-web tasks |
| [choosing-an-agent.md](choosing-an-agent.md) | Agent ↔ form mapping, models, and API keys |
| [tasks/README.md](tasks/README.md) | Contributor checklist, reporting, interface contracts |
| [scripts/README.md](scripts/README.md) | `generate_application_job.py`, `report_job.py` |
| [persona_eval/README.md](persona_eval/README.md) | PersonaEval API, preflight, remote runner |

## Paths in this repository

| Kind | Path |
|------|------|
| Executable tasks | `application/tasks/` |
| Team docs | `application/` (this directory) |
| Shared runtimes | `environment/task-environments/application/` |
| Job recipes | `configs/jobs/example-job-recipe/`, `configs/jobs/application-task-job-recipe/` |
| PersonaEval app | `application/persona_eval/` |
| Verifiers | `packages/rewardkit/` + per-task `tests/` |

**Convention:** Harbor task format; `instruction.md` = scenario for the simulated
user; persona lives in the agent layer (`-a persona-*` + `persona_path`). Agent
choice belongs in README / Cockpit / job YAML — not in `instruction.md`.

---

## Goal

Collect realistic scenarios where persona-affiliated agents evaluate products,
workflows, assistants, and research questions — and make sure each scenario runs
end-to-end inside Harbor and PersonaEval.

Each application should define:

- target domain
- task setting
- relevant persona types
- required environment
- interaction protocol
- evaluation metrics
- expected output format
- example runs
- known limitations

## Scenario handoff template

Use this format when proposing a new runnable application scenario:

```text
Scenario name:
Task type:                # survey / chatbot / web / app
Domain / vertical:
Product or system under test:
Task specification:       # what happens in the episode and what must be done
Environment needs:        # surface, tools, initial state, data, credentials
Persona inputs:           # referenced cohort or dimensions, not copied data
User goal and context:    # motivation, prior knowledge, constraints
Metrics:                  # task success, fidelity, friction, safety, etc.
Outputs:                  # trajectory, telemetry, reports, artifacts
```

Example:

```text
Scenario name: Retail order-support refund handling
Task type: chatbot
Domain / vertical: Commerce & Retail / order support
Product or system under test: retail order-support chatbot
Task specification: simulated shoppers request a return or refund over
  multi-turn chat; the bot must handle each request under the return policy.
Environment needs: chat API connector, orders fixture, return policy document,
  and deterministic task start state.
Persona inputs: price sensitivity, age, shopping habits, tech savviness.
User goal and context: ordered earbuds arrived late and the user wants a refund.
Metrics: persona adherence, turns to resolution, frustration, policy compliance.
Outputs: conversation trajectory and per-metric score report.
```

For broader domain inspiration, see
[`docs/research/application-domain-benchmark-catalog.md`](../docs/research/application-domain-benchmark-catalog.md).

## Current layout

```text
application/
  persona_eval/ PersonaEval app, API, simulator, and frontend workbench.
  reporting/   Application result summaries.
  scripts/     Application job generation helpers.
  tasks/       Runnable survey, chat, web, and product tasks.
  QUICKSTART.md, task-guide.md, web-interaction.md, choosing-an-agent.md
```

Applications should depend on persona inputs by reference. They should not copy
large persona datasets into application folders.

Keep new application contributions scoped to application-owned task, script,
reporting, or PersonaEval folders. Do not commit generated job outputs under
`jobs/`.

## Contributing

- new task scenarios under `application/tasks/`
- domain-specific benchmarks
- evaluation metrics (`packages/rewardkit/`, `reporting.json`)
- analysis templates (`application/reporting/`)

See [../CONTRIBUTING.md](../CONTRIBUTING.md) if present in your checkout.
