# Application Tasks

Task definitions for **application product research**. These were migrated from
MatrAIx and organized under the PersonaBench `application/` module.

This import contains application task folders, tests, and reference solutions.
Runtime build contexts live under `environment/task-environments/application/`.
Runtime and agent wiring live under `environment/runtime/harbor/` and
`environment/agents/personabench/agents/`; curated runnable recipes live under
`configs/jobs/`.

## Naming

- **`example-*`** — reference tasks in the repo (copy from these). For surveys, only
  **`example-survey_product-feedback`** is the reference; other `survey_*` folders are
  real application benchmark tasks.
- **`survey_*`** — application survey tasks (json_survey / complete_json).
- **`recommender-agent_chat_api`** — clean import of the MatrAIx recommender
  chat task with an environment-side HTTP sidecar for smoke runs.
- **`web-ecommerce-platform_product-discovery`** — deterministic ecommerce web
  task used by the PersonaEval web cockpit.
- **Your task** — `application/tasks/<your-task-name>/` (any folder name you choose).

## New Task

Copy the closest `example-*` sibling with the same interaction type, then edit
the scenario, task metadata, and verifier.

1. `cp -R application/tasks/example-survey_product-feedback application/tasks/<your-task-name>`
2. Set `[task].name` to `personabench/application-{slug}`.
3. Update `[metadata]` with `type`, `domain`, and task-specific `tags`.
4. Put Docker files and runtime fixtures under
   `environment/task-environments/application/<your-task-name>/`.
5. Set `[environment].definition = "application/<your-task-name>"`.
6. Keep verifier entry points under `tests/`.
7. Use `persona/datasets/bench-dev-sample/persona_0042.yaml` for lightweight
   smoke examples until a larger persona dataset is restored externally.

## Metadata

| Field | Meaning |
|-------|---------|
| **type** | Interaction form (`survey`, `chat`, `web`, `desktop`, `mobile`, …) |
| **domain** | Vertical: `software` · `finance` · `healthcare` · `commerce-retail` |
| **tags** | Task-specific labels; do not repeat `type` or `domain`. |

Persona benchmark and grounding tasks should live under `persona/tasks/`, not
in this module.

## Interface

[`interface/`](interface/) records the shared application-task protocol for
survey, chatbot, and web/computer-use tasks. Use it to decide where a new task
belongs and which artifacts its verifier should expect.

## Docker (`persona-claude-code` tasks)

[`../../environment/docker-snippets/install-claude-code.sh`](../../environment/docker-snippets/install-claude-code.sh)
is the canonical install script that pre-bakes Claude Code + `uv` into survey
and chat task images. Harbor resolves `[environment].definition` to
`environment/task-environments/<definition>` and packages that directory as the
task archive's `environment/` folder. After adding or editing a Claude Code
task, run:

```bash
python scripts/sync_docker_snippets.py --write
```

Web and computer-use tasks use different base images and do not use this
script.
