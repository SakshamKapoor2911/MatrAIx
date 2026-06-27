# MatrAIx Import Plan

This plan guides imports from `MatrAIx-ai/MatrAIx` into PersonaBench.

## Current State

- MatrAIx main at inspection time: `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`.
- PersonaBench migration provenance was merged in PR #125.
- Raw migration PRs are available as screening artifacts, but most should not
  be merged directly.
- The current clean-main source-to-target status is tracked in
  `docs/migration/matraix-parity-matrix.md`.

## Merge Policy

Use the migration PRs as source material. Do not merge snapshot PRs into main
unless the explicit goal is to archive a source tree.

Recommended handling:

- `#2-#60`: main commit stack. Use as provenance and source material. Do not
  merge wholesale if curating into the module layout.
- `#61`: open PR #128 diff. Candidate for a curated Persona import after the
  persona module skeleton is in place.
- `#62-#92`: open or closed source PR snapshots. Screen and curate manually.
- `#93`: full main snapshot. Keep as reference; do not merge together with
  curated imports.
- `#94-#124`: merged PR snapshots. Mostly duplicate source material already in
  main. Screen only.
- `#125`: provenance manifest. Already merged.

## Recommended Import Waves

The migration proceeds on two parallel lines:

1. **Clean Main line:** `main` contains only curated, organized code and docs.
   Raw snapshots remain review artifacts and should not be merged directly.
2. **Unmerged PR Preservation line:** every MatrAIx PR that was not merged into
   MatrAIx `main` remains available as a PersonaBench snapshot PR or a future
   curated port PR. Preserve source PR number, source branch, source commit,
   and original author metadata.

### Wave 0: Architecture and contribution guardrails

Create module READMEs, contribution guidance, and migration logs. This prevents
future imports from landing at repository root.

Status: done in PersonaBench PR #126.

### Wave 1: Persona core

Import schema, dimensions, validators, and curation scripts. Avoid large raw
outputs and generated artifacts.

Primary sources:

- `#48`
- `#52`
- `#98`
- `#99`
- `#103`
- `#108`
- `#109`
- `#112`
- `#116`
- `#119`

Status: schema/curation landed in PersonaBench PR #127, and the persona task
layer landed in PR #134. Full generated persona datasets remain external to
git.

### Wave 2: Application examples

Import runnable scenarios that consume personas. Keep fixtures small and move
application metrics into `application/`.

Primary sources:

- `#43`
- `#45`
- `#56`
- `#62`
- `#66`
- `#68`
- `#70`
- `#71`
- `#73`
- `#74`
- `#76`

Status: task definitions and reporting placeholders imported in PersonaBench
PR #128. Application job generation utilities imported in PR #129.

### Wave 3: Shared utility package

Import pure Python utilities that can run without the full environment runtime.

Status: done in PersonaBench PR #129.

Imported:

- `src/personabench/`
- `application/scripts/generate_application_job.py`
- root `pyproject.toml`

Deferred:

- persona agents
- Harbor/runtime implementation
- checked-in job recipes

### Wave 4: Environment runtime foundation

Import the minimal runtime needed to execute curated application and persona
tasks. Do not bring in every adapter, app, job output, or viewer at once.

Scope:

- runtime primitives needed by `application/tasks/*`
- task execution model
- Docker/use-computer environment glue needed by curated tasks
- small tests or smoke checks proving the runtime imports cleanly

Out of scope:

- generated `jobs/` outputs
- bulk `adapters/`
- `apps/viewer`
- unrelated example jobs

Status: merged in PersonaBench PR #131.

Imported in this wave:

- `src/harbor/` as the environment runtime Python package.
- `harbor`, `hr`, and `hb` console script metadata.
- Runtime package data needed by CLI templates and local environment backends.

Still deferred after runtime foundation:

- `packages/rewardkit/` and `packages/harbor-langsmith/`, unless a later
  verifier or tracing PR proves they are required in `main`.
- `configs/jobs/`, raw `jobs/` outputs, standalone `apps/viewer`, bulk
  adapters, and examples.

### Wave 5: Persona agents

Import persona-enabled agents only after the runtime foundation is present.

Candidate agents:

- `persona-claude-code`
- `persona-computer-1`
- `persona-browser-use`
- `persona-cocoa`
- other persona adapters that can import cleanly against the runtime foundation

Status: scoped in branch `codex/environment-persona-agents`.

Imported in this wave:

- `src/personabench/agents/persona/`
- `src/personabench/agents/installed/browser_use.py`
- `src/personabench/agents/installed/cocoa.py`
- Harbor `AgentFactory` registrations for persona agent names and the
  browser-use/cocoa installed adapters.

Still deferred:

- Checked-in job recipes that exercise these agents.
- Historical job outputs.
- Standalone `apps/viewer`.
- Bulk adapter and example directories.

### Wave 6: Curated job recipes

Import only job recipes that can run against the curated runtime and sample
datasets. Keep generated jobs and historical outputs outside git.

Status: scoped in branch `codex/configs-job-recipes`.

Imported in this wave:

- Curated `configs/jobs/example-job-recipe/appSim-*.yaml` recipes that point at
  `application/tasks/` and `persona/datasets/bench-dev-sample/`.

Still deferred:

- `harbor-smoke-local.yaml`, because it points at unimported
  `examples/tasks/hello-world`.
- `personaBench-*` and persona grounding recipes, because they should be
  regenerated against curated sample or external PersonaBench datasets instead
  of copied from source snapshots.
- Generated random-sample recipes that reference the external
  `persona/datasets/bench-dev-2000/` dataset.
- All historical `jobs/` outputs.

### Wave 7: PersonaBench task layer

Import persona grounding tasks, grounding specs, reporting, and script entry
points without importing full generated persona pools.

Status: scoped in branch `codex/persona-bench-tasks`.

Imported in this wave:

- `persona/tasks/`
- `persona/reporting/`
- `persona/scripts/`
- `persona/validators/`
- `src/personabench/persona_grounding.py`
- `src/personabench/persona_consistency.py`
- `src/personabench/persona_generator.py`
- focused unit tests under `tests/unit/personabench/`

Still deferred:

- Full `persona/datasets/bench-dev-2000/` and generated cohorts.
- Generated `configs/jobs/persona-task-grounding-job-recipe/*.yaml` outputs.
- Annotation tooling not required to run the curated task layer.

Primary sources:

- `#45`
- `#46`
- `#47`
- `#51`
- `#57`
- `#61`
- `#121`

### Wave 8: Optional viewer and tooling

Decision: keep the React frontend under `apps/viewer`, because Harbor's
`view` CLI already resolves that source path and the backend API lives in
`src/harbor/viewer/`. Document `apps/` as repo-local tooling, not a fourth
business module.

Status: scoped in branch `codex/viewer-tooling`.

Imported in this wave:

- `apps/viewer/`
- `tests/unit/viewer/`

Still deferred:

- built `apps/viewer/build/` output
- `node_modules/`
- any unrelated adapters or example snapshots

### Wave 9: Data curation and larger datasets

Import scripts, manifests, and small samples. Put large outputs in external
storage or Git LFS only after a maintainer decision.

Primary sources:

- `#64`
- `#65`
- `#67`
- `#72`
- `#75`
- `#77`
- `#78`
- `#79`
- `#80`
- `#83`
- `#84`
- `#87`
- `#88`
- `#104-#110`

## Open PR Preservation

Do not close or overwrite PersonaBench snapshot PRs until their source PR has
either been explicitly rejected or ported into a curated PR.

Current handling policy:

- Keep raw snapshot PRs open or clearly labeled as archive/do-not-merge.
- For each useful MatrAIx open PR, create a new curated port PR against
  PersonaBench `main`.
- Use titles like
  `[port matraix#128][persona] Add annotation package tool`.
- In each curated port PR body, record:
  - source repository
  - source PR number
  - source branch
  - source commit
  - original author
  - files intentionally excluded
- Never merge a raw full-tree snapshot into clean `main`.
