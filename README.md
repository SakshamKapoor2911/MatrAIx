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

Start here:

- [Architecture](docs/architecture.md)
- [Contributing](CONTRIBUTING.md)
- [MatrAIx migration plan](docs/migration/matraix-import-plan.md)
- [MatrAIx merge log](docs/migration/matraix-merge-log.md)
