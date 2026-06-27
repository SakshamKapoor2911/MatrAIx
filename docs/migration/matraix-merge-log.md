# MatrAIx Merge Log

This log records the curated migration from MatrAIx into PersonaBench.

## 2026-06-27

### Step 1: Merge provenance manifest

- PersonaBench PR: `#125`
- Title: `[matraix-migration] Add provenance manifest`
- Result: merged
- Merge commit: `ee9f9334f1badd9bd84b702817a634b82e778638`
- Previous `origin/main`: `29b951ca3285ec2456ee5dd61020c9d42617255f`
- New `origin/main`: `ee9f9334f1badd9bd84b702817a634b82e778638`
- Files added:
  - `migration/matraix/README.md`
  - `migration/matraix/main_commits.tsv`
  - `migration/matraix/source_pr_commits.tsv`
  - `migration/matraix/source_prs.tsv`
- Notes:
  - This was metadata only.
  - It preserves source commit and source PR authorship before curated imports.
  - No raw MatrAIx code was imported in this step.

### Step 2: Establish architecture guardrails

- Branch: `codex/architecture-guidance`
- Purpose: define module boundaries before importing code.
- Policy:
  - Do not merge raw snapshot directories into `main`.
  - Curate files into `persona/`, `application/`, or `environment/`.
  - Record every import source in this log.
- PersonaBench PR: `#126`
- Result: merged
- Merge commit: `e039ce86b42c0ab91cf27d74a25ee09864b08ee5`

### Step 3: Import curated Persona core assets

- Branch: `codex/persona-core-curated-import`
- PersonaBench PR: `#127`
- Result: merged
- Merge commit: `58c97d4ba29dfaddf6b2fd710982781eb79e86b2`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: bring over Persona-owned schema, curation scripts, and tiny sample
  dataset fixtures without importing raw snapshots or large generated outputs.
- Imported into:
  - `persona/schema/`
  - `persona/curation/attribute_pool/`
  - `persona/datasets/bench-dev-sample/`
- Excluded:
  - full `persona/datasets/bench-dev-2000/`
  - generated attribute-pool `outputs/`
  - raw curation input dumps under the original `persona/attribute_pool/dataset/`
- Compatibility adjustments:
  - Curation scripts now resolve paths relative to
    `persona/curation/attribute_pool/`.
  - Raw/reference inputs live under `sources/`.
  - Generated outputs live under ignored `outputs/`.
  - The schema validator defaults to `persona/schema/dimensions.json`.

### Step 4: Import application task definitions

- Branch: `codex/application-tasks-curated-import`
- PersonaBench PR: `#128`
- Result: merged
- Merge commit: `7b23de31303cdc91b63ae28c70602206ee414b4f`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: bring over application-owned task definitions and the reporting
  placeholder without importing shared runtime code prematurely.
- Imported into:
  - `application/tasks/`
  - `application/reporting/`
- Deferred:
  - `application/scripts/generate_application_job.py`, because it depends on
    the shared `matraix` Python package that has not been curated into
    PersonaBench yet.
  - `configs/jobs/`, agents, `src/matraix/`, and Harbor/runtime wiring.
- Compatibility adjustments:
  - Task registry names use `personabench/application-*`.
  - Local temporary output directories use `/tmp/personabench-*`.
  - Example README persona paths point at
    `persona/datasets/bench-dev-sample/`.

### Step 5: Import shared utility package

- Branch: `codex/shared-utility-package-import`
- PersonaBench PR: `#129`
- Result: merged
- Merge commit: `3909c5baf53a8a104ff0ad4114884d4fcbd91834`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: bring over pure Python utilities needed for persona sampling,
  task catalogs, and application job generation without importing agents or the
  Harbor runtime.
- Imported into:
  - `src/personabench/`
  - `application/scripts/`
  - root `pyproject.toml`
- Deferred:
  - `src/matraix/agents/`
  - Harbor runtime code
  - checked-in `configs/jobs/` recipes
- Compatibility adjustments:
  - Package/import namespace is `personabench`, not `matraix`.
  - Default schema path is `persona/schema/dimensions.json`.
  - Default dataset path is `persona/datasets/bench-dev-sample`.
  - `task_catalog.py` uses the Python standard-library `tomllib`.

### Step 6: Document external artifact handoff and next waves

- Branch: `codex/document-external-artifacts`
- Purpose: record large MatrAIx artifacts that should be uploaded to external
  storage, and update the clean-main migration plan.
- Documentation updated:
  - `migration/matraix/README.md`
  - `docs/migration/matraix-import-plan.md`
- Policy:
  - Large generated outputs, raw datasets, and historical job artifacts stay
    out of PersonaBench `main`.
  - HuggingFace or other approved external storage should hold the large
    artifacts referenced by module READMEs.
  - Raw snapshot PRs remain preservation artifacts, not clean-main merge
    candidates.

### Step 7: Import environment runtime foundation

- Branch: `codex/environment-runtime-foundation`
- PersonaBench PR: `#131`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: bring over the Harbor runtime package needed to execute curated
  PersonaBench application and persona tasks, without importing raw snapshots
  or historical job outputs.
- Imported into:
  - `src/harbor/`
  - root `pyproject.toml`
  - `tests/environment/`
- Excluded:
  - `src/matraix/agents/`
  - `packages/rewardkit/`
  - `packages/harbor-langsmith/`
  - `configs/jobs/`
  - `jobs/`
  - standalone `apps/viewer`
  - bulk `adapters/` and `examples/`
- Compatibility adjustments:
  - The root project remains `personabench`; the imported runtime keeps the
    `harbor` Python namespace and CLI entrypoints.
  - Harbor version discovery now falls back from the upstream `harbor`
    distribution name to the PersonaBench distribution name.
  - Runtime package data is declared explicitly so CLI templates are included
    in built distributions.
  - `AgentFactory` no longer points at deferred `matraix.agents` import paths;
    persona agent registrations are reserved for the follow-up
    `environment/persona-agents` PR.

### Step 8: Import PersonaBench-owned persona agents

- Branch: `codex/environment-persona-agents`
- PersonaBench PR: `#132`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: bring over persona-conditioned Harbor agents after the runtime
  foundation is present, without restoring the old `matraix` package namespace.
- Imported into:
  - `src/personabench/agents/`
  - `tests/environment/test_persona_agents.py`
- Updated:
  - `src/harbor/agents/factory.py`
  - root `pyproject.toml`
- Excluded:
  - `configs/jobs/`
  - `jobs/`
  - standalone `apps/viewer`
  - bulk `adapters/` and `examples/`
- Compatibility adjustments:
  - Agent import paths now use `personabench.agents.*`.
  - Persona and installed agent package initializers use lazy exports so
    importing the lightweight persona loader does not require Harbor runtime
    dependencies.
  - Persona prompt templates are included as package data.

### Step 9: Import curated application job recipes

- Branch: `codex/configs-job-recipes`
- PersonaBench PR: `#133`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: add small Harbor job recipes that exercise curated application
  tasks and sample personas, without importing generated historical outputs or
  recipes that depend on absent full datasets.
- Imported into:
  - `configs/jobs/`
  - `tests/environment/test_job_recipes.py`
- Excluded:
  - `configs/jobs/example-job-recipe/harbor-smoke-local.yaml`
  - `configs/jobs/example-job-recipe/personaBench-example-survey-local.yaml`
  - `configs/jobs/application-task-job-recipe/`
  - `configs/jobs/persona-task-grounding-job-recipe/`
  - `jobs/`
- Compatibility adjustments:
  - Recipe persona paths point at
    `persona/datasets/bench-dev-sample/persona_0042.yaml`.
  - Recipe documentation records what remains deferred and why.

### Step 10: Import PersonaBench task layer

- Branch: `codex/persona-bench-tasks`
- PersonaBench PR: `#134`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: bring over the curated persona grounding task, reporting, scripts,
  validators, and pure persona generation utilities without importing the full
  generated persona pool or generated job recipes.
- Imported into:
  - `persona/tasks/`
  - `persona/reporting/`
  - `persona/scripts/`
  - `persona/validators/`
  - `src/personabench/persona_grounding.py`
  - `src/personabench/persona_consistency.py`
  - `src/personabench/persona_generator.py`
  - `tests/unit/personabench/`
- Excluded:
  - full `persona/datasets/bench-dev-2000/`
  - generated `persona/datasets/_generated/` cohorts and dev pools
  - generated `configs/jobs/persona-task-grounding-job-recipe/*.yaml`
  - historical `jobs/` outputs
- Compatibility adjustments:
  - Task registry names use `personabench/persona-bench-*`.
  - Default schema paths use `persona/schema/dimensions.json`.
  - Local generated datasets go under ignored `persona/datasets/_generated/`.
  - Persona grounding verifier env now prefers `PERSONABENCH_PROBE_*` while
    retaining `MATRAIX_PROBE_*` fallback for migrated task compatibility.

### Step 11: Import viewer frontend tooling

- Branch: `codex/viewer-tooling`
- PersonaBench PR: `#135`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: bring over the frontend source for `harbor view` now that the
  viewer backend API is already present in `src/harbor/viewer/`.
- Imported into:
  - `apps/viewer/`
  - `apps/README.md`
  - `tests/unit/viewer/`
- Excluded:
  - `apps/viewer/build/`
  - `apps/viewer/node_modules/`
  - generated static viewer assets under `src/harbor/viewer/static/`
- Compatibility adjustments:
  - Viewer UI and CLI display text use PersonaBench branding.
  - The private frontend package name is `personabench-viewer`.
  - Architecture docs define `apps/` as repo-local tooling, not a fourth
    business module.

### Step 12: Add clean-main parity matrix

- Branch: `codex/migration-parity-audit`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: record the remaining source-to-target gaps before importing GitHub
  metadata, examples, optional packages, adapters, and external artifact
  references.
- Documentation added:
  - `docs/migration/matraix-parity-matrix.md`
- Policy:
  - PersonaBench `main` targets clean functional parity, not byte-for-byte
    source-tree parity.
  - Large generated artifacts and historical run outputs stay external to git.
  - Remaining imports should land as focused curated PRs with source mapping,
    explicit exclusions, and validation notes.

### Step 13: Import safe GitHub metadata and CI

- Branch: `codex/github-metadata-ci`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: restore repository metadata that supports clean-main review and CI
  without copying workflows that depend on MatrAIx organization teams,
  unavailable secrets, or unimported test paths.
- Imported or adapted into:
  - `.github/CODEOWNERS`
  - `.github/labeler.yml`
  - `.github/workflows/pr-labeler.yml`
  - `.github/workflows/pytest.yml`
  - `.github/workflows/ruff.yml`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `src/personabench/agents/installed/__init__.py`
  - `src/personabench/agents/persona/__init__.py`
- Excluded:
  - Claude automation workflows that require `ANTHROPIC_API_KEY`.
  - Source pytest ignores and smoke jobs that reference unimported MatrAIx
    tests, examples, jobs, or `uv.lock`.
  - Source type-check workflow until PersonaBench has an agreed type-check
    scope.
  - Ruff format check until the already-imported source files are formatted in
    a dedicated cleanup PR.
- Compatibility adjustments:
  - Lazy persona-agent package exports use literal `__all__` declarations so
    the restored Ruff workflow passes without changing import behavior.

### Step 14: Import minimal examples smoke path

- Branch: `codex/examples-smoke`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: restore the smallest no-API-key runtime smoke path without importing
  the full examples tree or generated job outputs.
- Imported into:
  - `examples/tasks/hello-world/`
  - `configs/jobs/example-job-recipe/harbor-smoke-local.yaml`
  - `examples/README.md`
  - `examples/tasks/README.md`
  - `tests/environment/test_examples_smoke.py`
- Excluded:
  - `examples/jobs/`
  - `examples/configs/`
  - `examples/agents/`
  - `examples/metrics/`
  - `examples/prompts/`
  - all historical `jobs/` outputs
- Compatibility adjustments:
  - Job recipe docs now list `harbor-smoke-local.yaml` as the preferred
    no-API-key runtime smoke recipe.

### Step 15: Import optional Harbor LangSmith package

- Branch: `codex/packages-harbor-langsmith`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: restore the LangSmith Harbor job plugin as an optional package
  without reintroducing the legacy `matraix` package namespace.
- Imported into:
  - `packages/harbor-langsmith/`
  - `packages/README.md`
  - `.github/workflows/pytest.yml`
  - `tests/environment/test_optional_packages.py`
- Excluded:
  - `packages/matraix/`
  - `packages/rewardkit/`, which remains a separate follow-up package PR.
  - publish scripts and credentials.
- Compatibility adjustments:
  - Package dependency targets the PersonaBench distribution while keeping the
    `harbor` Python namespace used by the runtime.
  - Package build backend uses setuptools to match the root PersonaBench
    project.
