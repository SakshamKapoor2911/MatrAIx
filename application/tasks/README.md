# Application Tasks

Task definitions for **application product research**. These were migrated from
MatrAIx and organized under the PersonaBench `application/` module.

This import contains task folders, task-local environments, tests, and reference
solutions. Runtime and agent wiring live under `environment/runtime/harbor/` and
`environment/agents/personabench/agents/`; curated runnable recipes live under
`configs/jobs/`.

## Naming

- **`example-*`** — reference tasks in the repo (copy from these).
- **`recommender-agent_chat_api`** — clean import of the MatrAIx recommender
  chat task with a task-local HTTP sidecar for smoke runs.
- **Your task** — `application/tasks/<your-task-name>/` (any folder name you choose).

## New Task

Copy the closest `example-*` sibling with the same interaction type, then edit
the scenario, task metadata, and verifier.

1. `cp -R application/tasks/example-survey_product-feedback application/tasks/<your-task-name>`
2. Set `[task].name` to `personabench/application-{slug}`.
3. Update `[metadata]` with `type`, `domain`, and task-specific `tags`.
4. Keep task-local Docker files and fixtures under
   `application/tasks/<your-task-name>/environment/`.
5. Keep verifier entry points under `tests/`.
6. Use `persona/datasets/bench-dev-sample/persona_0042.yaml` for lightweight
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
and chat task images. Harbor builds from each task's own `environment/`
directory, so task Dockerfiles use a task-local copy. After adding or editing a
Claude Code task, run:

```bash
python scripts/sync_docker_snippets.py --write
```

Web and computer-use tasks use different base images and do not use this
script.
