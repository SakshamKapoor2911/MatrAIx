# Environment Module

This module owns execution infrastructure. Runtime Python code currently lives
under `src/harbor/` because the imported MatrAIx runtime is a Python package
with console scripts and package data.

Current layout:

```text
environment/
  README.md    Module boundary and contribution guidance.
src/harbor/
  agents/      Base and installed agent wrappers.
  cli/         Harbor CLI entrypoints and templates.
  environments/ Runtime backends, including local Docker and optional cloud backends.
  models/      Task, trial, job, metric, registry, and trajectory models.
  trial/       Trial execution loop.
  verifier/    Verification orchestration.
  viewer/      Runtime viewer backend used by the `harbor view` CLI.
```

Planned environment-owned directories:

```text
environment/
  agents/      Persona-conditioned agents and model wrappers.
  jobs/        Curated job recipe schemas and reusable templates.
  viewer/      Result inspection UI, if it remains in this repository.
  adapters/    Optional external benchmark adapters.
```

The runtime foundation exposes the `harbor`, `hr`, and `hb` console scripts
through the root package metadata. Cloud runtime providers remain optional
extras in `pyproject.toml`.

Persona agent implementations live here because they are runtime mechanisms.
Persona schemas and datasets live in `persona/`.

Do not add raw generated job outputs, full application snapshots, or benchmark
adapter dumps here. Import those as curated PRs with a README explaining the
owner, execution path, and intentionally excluded artifacts.

Deferred from the runtime foundation import:

- Persona-specific agents from `src/matraix/agents/`.
  `AgentName` keeps the persona identifiers for config compatibility, but
  `AgentFactory` will not register those names until the agents are imported
  under a PersonaBench-owned namespace.
- Checked-in `configs/jobs/` recipes.
- Historical `jobs/` outputs.
- Standalone `apps/viewer` and other UI/tooling packages.
- Bulk adapter and example directories.
