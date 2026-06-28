# Environment Module

This module owns execution infrastructure. Runtime Python code currently lives
under `src/harbor/` because the imported MatrAIx runtime is a Python package
with console scripts and package data.

Current layout:

```text
environment/
  README.md    Module boundary and contribution guidance.
  adapters/    Curated external benchmark adapters.
configs/jobs/
  application-task-job-recipe/ Curated application job fixtures.
  example-job-recipe/          Local smoke and example recipes.
  persona-task-grounding-job-recipe/ Curated persona grounding job fixtures.
src/harbor/
  agents/      Base and installed agent wrappers.
  cli/         Harbor CLI entrypoints and templates.
  environments/ Runtime backends, including local Docker and optional cloud backends.
  models/      Task, trial, job, metric, registry, and trajectory models.
  trial/       Trial execution loop.
  verifier/    Verification orchestration.
  viewer/      Runtime viewer backend used by the `harbor view` CLI.
src/personabench/agents/
  installed/   PersonaBench-owned installed-agent adapters.
  persona/     Persona-conditioned Harbor agents and prompt templates.
apps/viewer/
  React frontend source paired with `src/harbor/viewer/`.
```

The runtime foundation exposes the `harbor`, `hr`, and `hb` console scripts
through the root package metadata. Cloud runtime providers remain optional
extras in `pyproject.toml`.

Persona agent implementations live here because they are runtime mechanisms.
Persona schemas and datasets live in `persona/`.

Do not add raw generated job outputs, full application snapshots, or benchmark
adapter dumps here. Import those as curated PRs with a README explaining the
owner, execution path, and intentionally excluded artifacts.

External benchmark adapters live under `environment/adapters/<adapter-name>/`
with a manifest, adapter-local package metadata, and ignored `_generated/`
output. Do not restore a top-level `adapters/` directory or write generated
datasets to shared root paths.

Still excluded from clean `main`:

- Historical `jobs/` outputs, recordings, screenshots, and trajectories.
- Bulk adapter directories beyond focused, manifest-backed imports.
- Generated adapter datasets and downloaded benchmark corpora.
- Raw MatrAIx snapshots or dependency lockfiles that are not required by a
  curated adapter PR.
