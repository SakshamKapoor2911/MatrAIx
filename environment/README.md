# Environment Module

This module owns execution infrastructure. Runtime Python code currently lives
under `environment/runtime/harbor/`. Persona-conditioned runtime agents live
under `environment/agents/personabench/agents/`. The installed Python import
names remain `harbor.*` and `personabench.agents.*` so existing jobs, recipes,
and console scripts keep working.

Current layout:

```text
environment/
  README.md           Module boundary and contribution guidance.
  adapters/           Curated external benchmark adapters.
  agents/
    personabench/
      agents/         PersonaBench-owned installed and persona agents.
  runtime/
    harbor/
      agents/         Base and installed agent wrappers.
      cli/            Harbor CLI entrypoints and templates.
      environments/   Runtime backends, including local Docker and optional cloud backends.
      models/         Task, trial, job, metric, registry, and trajectory models.
      trial/          Trial execution loop.
      verifier/       Verification orchestration.
      viewer/         Runtime viewer backend used by the `harbor view` CLI.
configs/jobs/
  application-task-job-recipe/ Curated application job fixtures.
  example-job-recipe/          Local smoke and example recipes.
  persona-task-grounding-job-recipe/ Curated persona grounding job fixtures.
apps/viewer/
  React frontend source paired with `environment/runtime/harbor/viewer/`.
```

The runtime foundation exposes the `harbor`, `hr`, and `hb` console scripts
through the root package metadata. Cloud runtime providers remain optional
extras in `pyproject.toml`. Python packaging uses explicit package-dir mappings
so `harbor` resolves from `environment/runtime/harbor/`,
`personabench.agents` resolves from `environment/agents/personabench/agents/`,
and top-level `personabench` utilities continue resolving from `src/personabench/`.

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
