# Application Tasks

Task definitions for **application product research**. These were migrated from
MatrAIx and organized under the PersonaBench `application/` module.

This import contains task folders, task-local environments, tests, and reference
solutions. The shared runtime package, agent implementations, and generated job
recipes are intentionally imported in later PRs.

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

Persona benchmark tasks should live under `persona/bench/` or a later
`persona/tasks/` import, not in this module.

## Docker (`persona-claude-code` tasks)

[`_docker/install-claude-code.sh`](_docker/install-claude-code.sh) pre-bakes
Claude Code + `uv` into the image. Copy it into `environment/` when authoring
survey or chat tasks (see `example-survey_product-feedback` /
`example-chat-*`). Web and computer-use tasks use different base images and do
not use this script.
