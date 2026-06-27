# PersonaBench

PersonaBench is the focused home for persona data, persona schemas, persona
evaluation tasks, and persona-conditioned simulation examples curated from
MatrAIx.

The repository is organized around three contribution modules:

```text
persona/       Persona schemas, datasets, curation pipelines, and persona bench tasks.
application/   Product and research scenarios that consume personas.
environment/   Runtime, agents, job recipes, viewer, and execution infrastructure.
apps/          Repo-local tool frontends paired with runtime APIs.
```

The rule of thumb is simple:

- `persona/` defines who the simulated user is and how persona adherence is
  evaluated.
- `application/` defines what scenario, product, or workflow the simulated user
  interacts with.
- `environment/` defines how the simulation runs, logs, and verifies work.
- `apps/` contains developer-facing tool frontends, currently the viewer UI for
  `harbor view`.

Shared libraries may live under `packages/` when they are genuinely reusable.
Large generated outputs, raw dumps, and migration snapshots should not be
merged into `main`.

## Current Clean-Main State

This branch is intentionally not a byte-for-byte copy of the old MatrAIx
`main`. It keeps the runnable and reviewable parts of MatrAIx under stable
module boundaries:

- `persona/`: persona schema, curation utilities, sample datasets, persona
  grounding tasks, bench tasks, reporting, and validators.
- `application/`: application task definitions, reporting code, and curated
  recipe generation helpers.
- `environment/`: Harbor runtime, persona agents, adapter foundation, SimpleQA
  adapter, curated job recipes, and environment docs.
- `apps/viewer/`: the repo-local viewer frontend for inspecting Harbor jobs.
- `packages/`: optional reusable packages such as `harbor-langsmith` and
  `rewardkit`.

Historical run outputs, generated datasets, large fixtures, screenshots,
recordings, and raw migration snapshots are tracked as external artifacts
instead of being committed to `main`; see
[the artifact handoff checklist](migration/matraix/README.md).

## Quick Start

```bash
uv venv --python 3.12
uv pip install -e .
uv pip install pytest pytest-asyncio
uv pip install -e packages/harbor-langsmith
uv pip install -e packages/rewardkit
uv run pytest tests/ packages/harbor-langsmith/tests/ packages/rewardkit/tests/
uv run ruff check .
```

Run a local smoke job that does not need model credentials:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

Run the curated persona application example after setting the required model
API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-survey-local.yaml
```

More setup, optional package, adapter, viewer, and artifact details are in
[Running PersonaBench](docs/running.md).

## Research Notes

The old MatrAIx literature review lived inside team planning files. Clean main
keeps the useful references as module-specific research notes:

- [Persona related work](docs/research/persona-related-work.md)
- [Application related work](docs/research/application-related-work.md)
- [Environment related work](docs/research/environment-related-work.md)

The source environment review was much thinner than the application and
persona reviews. The environment note records the original environment entries
and cross-links environment-relevant benchmark references that were originally
written in the application review.

Start here:

- [Architecture](docs/architecture.md)
- [Running PersonaBench](docs/running.md)
- [Research notes](docs/research/README.md)
- [Contributing](CONTRIBUTING.md)
- [MatrAIx migration plan](docs/migration/matraix-import-plan.md)
- [MatrAIx merge log](docs/migration/matraix-merge-log.md)
