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

### Step 16: Import optional Rewardkit package

- Branch: `codex/packages-rewardkit`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: restore the Harbor Rewardkit grading toolkit as an optional package
  while keeping package code isolated under `packages/`.
- Imported into:
  - `packages/rewardkit/`
  - `.github/workflows/pytest.yml`
  - `packages/README.md`
  - `pyproject.toml`
  - `tests/environment/test_optional_packages.py`
- Excluded:
  - `packages/matraix/`
  - publish scripts and credentials.
- Compatibility adjustments:
  - Package build backend uses setuptools to match the root PersonaBench
    project.
  - The superseded Apache license classifier was removed while keeping the
    explicit `Apache-2.0` license expression.
  - Rewardkit prompt markdown files are declared as package data.
  - CI installs and runs Rewardkit tests explicitly as optional package tests.
  - Root pytest markers include `unit` and `asyncio` to keep optional package
    test output readable.

### Step 17: Add adapter foundation and SimpleQA adapter

- Branch: `codex/adapters-foundation-simpleqa`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: establish the clean PersonaBench adapter layout and import one
  focused external benchmark adapter without restoring a top-level `adapters/`
  directory.
- Imported into:
  - `environment/adapters/README.md`
  - `environment/adapters/manifest.schema.json`
  - `environment/adapters/simpleqa/`
  - `.github/workflows/pytest.yml`
  - `tests/environment/test_adapters_foundation.py`
- Excluded:
  - `adapters/simpleqa/uv.lock`
  - generated SimpleQA task directories
  - full bulk import of the remaining MatrAIx adapter tree
  - historical `jobs/` outputs
- Compatibility adjustments:
  - SimpleQA generated data defaults to
    `environment/adapters/simpleqa/_generated/simpleqa`.
  - Job recipes point at adapter-local `_generated/` paths instead of top-level
    `datasets/`.
  - The adapter package uses setuptools and declares template package data.
  - Adapter manifests record source path, commit, dependencies, external data,
    smoke commands, and intentionally excluded source paths.

### Step 18: Expand external artifact handoff checklist

- Branch: `codex/external-artifact-handoff`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: give maintainers a concrete upload checklist for large MatrAIx
  artifacts that should stay outside clean `main`.
- Documentation updated:
  - `migration/matraix/README.md`
  - `docs/migration/matraix-parity-matrix.md`
  - `docs/migration/matraix-merge-log.md`
- Recorded artifact groups:
  - tracked `origin/main` persona attribute-pool outputs
  - tracked `origin/main` full generated persona cohort
  - tracked `origin/main` historical `jobs/` outputs
  - tracked binary docs assets and deferred adapter lockfiles/fixtures
  - local side artifacts under the migration workspace, including PRISM,
    curated personas, Amazon reviews, and wiki-collab worker archives
- Policy:
  - Keep published URL cells as `TODO` until each artifact is uploaded.
  - Do not commit these artifacts or dependency directories into
    PersonaBench `main`.
  - After upload, add the actual HuggingFace URLs to the module README that
    consumes each artifact.

### Step 19: Import curated architecture and research docs

- Branch: `codex/docs-architecture-research`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: preserve the useful explanatory architecture diagrams and persona
  related-work notes without importing the old project-management document set.
- Imported into:
  - `docs/assets/matraix-architecture.png`
  - `docs/assets/persona-grounding-flow.png`
  - `docs/research/README.md`
  - `docs/research/persona-related-work.md`
  - `docs/running.md`
  - `docs/architecture.md`
  - `README.md`
- Excluded:
  - `docs/personas/PLAN.md` task assignments and owner placeholders
  - branch-protection setup notes
  - PR management playbooks
  - historical current-state and known-issues notes
  - Superpowers implementation plans
- Compatibility adjustments:
  - The architecture page references the imported images from `docs/assets/`.
  - The related-work section is recast as a research note rather than a team
    planning document.
  - Clean-main run commands are documented against curated recipes and
    adapter-local generated paths.

### Step 20: Expand README and module research reviews

- Branch: `codex/docs-readme-literature-review`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source reference: `origin/main` at `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: answer the README and literature-review gap left by Step 19, which
  imported a condensed persona-only research note but did not yet expose
  application or environment related work.
- Updated:
  - `README.md`
  - `docs/running.md`
  - `docs/research/README.md`
  - `docs/research/persona-related-work.md`
  - `docs/research/application-related-work.md`
  - `docs/research/environment-related-work.md`
  - `docs/migration/matraix-parity-matrix.md`
- Source handling:
  - Application related work is migrated from `docs/applications/PLAN.md` and
    stripped of old task assignments.
  - Environment related work is migrated from `docs/environments/PLAN.md`.
  - The source environment review only had three complete entries; its agent
    environment and telemetry subsections were placeholders. The clean note
    records that source gap and cross-links environment-relevant benchmark
    entries originally written in the application review.
- Compatibility adjustments:
  - README now points to the three module research notes and includes a compact
    quick-start path.
  - Research docs remain notes, not a fresh bibliography or source-verification
    pass.

### Step 21: Import persona existing-data wiki foundation

- Branch: `codex/persona-wiki-amazon-migration`
- Source repository: local `/data2/zonglin/persona_ai/MatrAIx`
- Source branch: `codex/amazon-review-collab-integration`
- Source reference: `87fe1dafb fix: preserve amazon min support fold texts`
- Source base: `MatrAIx-ai/MatrAIx@origin/main`
  `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: start the existing-data curation migration with the Wikipedia/source
  foundation needed before collaboration packaging and Amazon review
  integration.
- Imported into:
  - `persona/curation/existing_data/`
  - `tests/persona/curation/existing_data/`
- Included:
  - external source manifests
  - Wikipedia person-page extraction and cleanup helpers
  - local SQLite wiki profile database builder
  - wiki assignment, validation, and merge helpers needed by the foundation
  - small wiki/sample fixtures and targeted tests
- Excluded:
  - `curated_personas/`
  - raw source dumps, generated outputs, logs, SQLite databases, and worker
    archives
  - Amazon Reviews 2023 pipeline code, which is staged for a follow-up PR
  - Modal/HuggingFace cloud indexer
  - React curation cockpit and built frontend assets
- Compatibility adjustments:
  - Old `personas.existing_data_curation` imports are rewritten to
    `persona.curation.existing_data`.
  - Default schema references point to `persona/schema/dimensions.json`.
  - README is scoped to the files that actually land in this wave, so later
    Amazon and collaborator-package commands are not advertised early.

### Step 22: Import persona collaboration packaging tools

- Branch: `codex/persona-collab-packaging-tools`
- Source repository: local `/data2/zonglin/persona_ai/MatrAIx`
- Source branch: `codex/amazon-review-collab-integration`
- Source reference: `87fe1dafb fix: preserve amazon min support fold texts`
- Source base: `MatrAIx-ai/MatrAIx@origin/main`
  `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: add the owner-to-collaborator loop for existing-data persona
  curation without importing raw snapshots or generated worker outputs.
- Imported into:
  - `persona/curation/existing_data/scripts/`
  - `persona/curation/existing_data/wiki_collab/`
  - `persona/curation/existing_data/worker_kit/`
  - `tests/persona/curation/existing_data/`
- Included:
  - worker-facing `collab_kit/` with schemas, harness, conformance checker,
    CLI adapters, assignment runner, sample inputs, and returned
    `results.jsonl` documentation
  - owner-side package builder, package wrapper template, plain-result merge,
    and audit helpers
  - range worker kit utilities and focused package/runner/merge tests
  - source worktree-only collaborator documentation:
    `wiki_collab/collab_kit/RESULTS_JSONL_README.md`
- Excluded:
  - raw source dumps, local SQLite databases, worker archives, and returned
    generated results
  - Amazon Reviews 2023 data-source scripts and evidence/protocol files, which
    are staged for the next PR
  - Modal/HuggingFace cloud indexer
  - React curation cockpit and built frontend assets
  - Superpowers implementation plans
- Compatibility adjustments:
  - Worker-facing labels, email subjects, and package defaults are renamed from
    MatrAIx to PersonaBench.
  - Repo-root detection is updated for the `persona/curation/existing_data/`
    target layout.
  - Default schema references point to `persona/schema/dimensions.json`.
  - The worker package remains self-contained and excludes local progress,
    archives, caches, and Python bytecode.

### Step 23: Import Amazon Reviews 2023 persona pipeline

- Branch: `codex/persona-amazon-reviews-pipeline`
- Source repository: local `/data2/zonglin/persona_ai/MatrAIx`
- Source branch: `codex/amazon-review-collab-integration`
- Source reference: `87fe1dafb fix: preserve amazon min support fold texts`
- Source base: `MatrAIx-ai/MatrAIx@origin/main`
  `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: add the Amazon Reviews 2023 existing-data path for user-history
  normalization, evidence-profile inference, collaborator packaging,
  validation, and rating-holdout evaluation while keeping raw Amazon data and
  generated outputs outside git.
- Imported into:
  - `persona/curation/existing_data/`
  - `persona/curation/existing_data/protocols/`
  - `persona/curation/existing_data/samples/`
  - `persona/curation/existing_data/scripts/`
  - `persona/curation/existing_data/wiki_collab/`
  - `persona/curation/existing_data/worker_kit/`
  - `tests/persona/curation/existing_data/`
- Included:
  - Amazon Reviews 2023 manifest, evidence mapping, pool statistics, and small
    sample fixtures
  - Amazon inference protocol prompts and schemas
  - fetch/analyze/retrieve/infer/build-package/validate/evaluate/report helper
    scripts
  - Amazon collaborator profile database and range runner utilities
  - Modal/HuggingFace helper module as optional code; tests use a local Modal
    stub and do not require cloud dependencies
  - focused Amazon tests and a local package smoke path using
    `samples/amazon_reviews_2023/user_histories_sample.jsonl`
- Excluded:
  - raw Amazon Reviews 2023 downloads
  - generated user-history exports, SQLite databases, inference JSONL outputs,
    reports, worker packages, and returned archives
  - Modal/HuggingFace optional dependency metadata, which is staged for a
    follow-up docs/dependency PR
  - React curation cockpit and built frontend assets
  - Superpowers implementation plans
- Compatibility adjustments:
  - Old `personas.existing_data_curation` imports are rewritten to
    `persona.curation.existing_data`.
  - Default schema references point to `persona/schema/dimensions.json`.
  - User-facing worker package titles and default app identifiers are renamed
    from MatrAIx to PersonaBench.
  - `candidate_users_top100.jsonl` remains a candidate-pool sample; the
    package smoke uses the new `user_histories_sample.jsonl` fixture because
    package creation requires rows with embedded `reviews`.

### Step 24: Add optional Amazon Modal/HuggingFace dependency extra

- Branch: `codex/persona-amazon-modal-extra`
- Source repository: local `/data2/zonglin/persona_ai/MatrAIx`
- Source branch: `codex/amazon-review-collab-integration`
- Source reference: `87fe1dafb fix: preserve amazon min support fold texts`
- Purpose: make the optional Amazon Reviews 2023 Modal/HuggingFace helper path
  installable without adding cloud/indexing dependencies to the default
  PersonaBench install.
- Updated:
  - `pyproject.toml`
  - `persona/curation/existing_data/README.md`
  - `docs/migration/matraix-merge-log.md`
- Included:
  - `amazon-modal` optional dependency group for Modal, HuggingFace, Parquet,
    dataset loading, and progress utilities
  - README install note for `modal_amazon_user_index.py`
- Excluded:
  - any raw Amazon data or generated Modal/HuggingFace artifacts
  - default dependency changes for users who do not run the cloud indexing path
  - Superpowers implementation plans

### Step 25: Document persona data pipeline and artifact handoff

- Branch: `codex/persona-data-pipeline-docs`
- Purpose: make the migrated persona data pipeline understandable for future
  contributors and keep large generated artifacts out of `main`.
- Updated:
  - `README.md`
  - `persona/curation/README.md`
  - `persona/curation/existing_data/README.md`
  - `persona/datasets/README.md`
  - `migration/matraix/README.md`
  - `docs/migration/matraix-merge-log.md`
  - `docs/migration/matraix-parity-matrix.md`
- Included:
  - canonical source-to-package curation flow
  - collaborator package and external artifact guidance
  - explicit dataset slots for full persona cohorts, attribute-pool outputs,
    existing-data curated personas, and Amazon Reviews 2023 generated artifacts
- Excluded:
  - uploading artifacts to HuggingFace
  - adding raw/generated data to git
  - Superpowers implementation plans

### Step 26: Import application areas taxonomy

- Branch: `codex/application-areas-taxonomy`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PR: `#24`, `Propose a new Application Areas Taxonomy`
- PersonaBench snapshot PR: `#81`
- Purpose: preserve the application-area taxonomy as a clean research note
  without importing the old planning tree or snapshot wrapper directory.
- Imported into:
  - `docs/research/application-areas-taxonomy.md`
- Updated:
  - `docs/research/README.md`
  - `README.md`
- Excluded:
  - `MatrAIx_PR_024/`
  - old `applications/PLAN.md`, `environments/PLAN.md`, and
    `personas/PLAN.md` planning files from the snapshot.

### Step 27: Import Nemotron selection fixtures and tools

- Branch: `codex/persona-nemotron-selection`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PRs:
  - `#90`, `Add Nemotron domain test user selections`
  - `#92`, `Add Nemotron domain plot renderer`
- PersonaBench snapshot PRs:
  - `#67`
  - `#65`
- Purpose: preserve small Nemotron domain and survey selection fixtures plus
  the reproducible selector/renderer tools without importing generated plots,
  full persona YAML pools, or old application snapshots.
- Imported into:
  - `persona/curation/existing_data/samples/nemotron_domain_selection/`
  - `persona/curation/existing_data/samples/nemotron_survey_selection/`
  - `persona/curation/existing_data/scripts/select_nemotron_survey_users.py`
  - `persona/curation/existing_data/scripts/render_nemotron_domain_selection_plots.py`
- Updated:
  - `persona/curation/existing_data/README.md`
- Excluded:
  - generated Nemotron SVG/PNG/PDF plot outputs
  - full Nemotron curated persona YAML pools
  - `applications/recommendation_chatbot_eval/data/personas/`
  - snapshot wrapper directories.

### Step 28: Import standalone persona survey application task

- Branch: `codex/application-persona-eval-tasks`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PR: `#83`, `Add standalone Harbor-backed survey eval`
- PersonaBench snapshot PR: `#71`
- Purpose: import the standalone Harbor persona-survey task definition without
  pulling in the full `applications/recommendation_chatbot_eval` backend or
  generated data.
- Imported into:
  - `application/tasks/persona-survey/`
- Updated:
  - `tests/environment/test_application_tasks.py`
- Compatibility adjustments:
  - Task registry name uses `personabench/application-persona-survey`.
  - README smoke example points at
    `persona/datasets/bench-dev-sample/persona_0042.yaml`.
- Deferred:
  - `applications/recommendation_chatbot_eval/backend/service/harbor_survey_eval.py`
  - PersonaEval backend tests and runner integration
  - recommender-agent task and sidecar, which depend on the deferred
    recommendation chatbot backend.

### Step 29: Import PersonaEval survey instruments

- Branch: `codex/persona-eval-backend`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PR: `#89`, `[codex] Add real-feature survey instruments`
- PersonaBench snapshot PR: `#68`
- Purpose: preserve the built-in PersonaEval survey instruments as an
  application-owned backend foundation without pulling in API routes, frontend
  code, Harbor runners, or historical experiment outputs.
- Imported into:
  - `application/persona_eval/backend/service/survey_types.py`
  - `application/persona_eval/backend/service/survey_instruments.py`
  - `tests/application/persona_eval/test_survey_instruments.py`
- Updated:
  - `application/README.md`
- Compatibility adjustments:
  - The source instrument registry imported `SurveyInstrument` and
    `SurveyQuestion` from the old monolithic `harbor_survey_eval.py` runner.
    PersonaBench splits those lightweight dataclasses into `survey_types.py` so
    survey schema code can land before runner/API migration.
  - The import path now follows the clean `application/persona_eval/` layout
    instead of the source `applications/persona_eval/` tree.
- Deferred:
  - `applications/persona_eval/backend/api/`
  - `applications/persona_eval/backend/service/harbor_survey_eval.py`
  - `applications/persona_eval/frontend/`
  - experiment configs, traces, caches, and generated outputs.

### Step 30: Ignore editor-local VS Code workspace settings

- Branch: `codex/ignore-vscode-workspace`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PR: `#129`, `Ignore VS Code workspace settings`
- PersonaBench snapshot PR: `#82`
- Purpose: keep contributor-local VS Code workspace settings out of clean
  `main`.
- Updated:
  - `.gitignore`
- Source handling:
  - The source PR also deleted `.vscode/settings.json`.
  - PersonaBench did not have a tracked `.vscode/settings.json`, so the clean
    migration only enables the `.vscode/` ignore rule.

### Step 31: Import additional persona benchmark related-work notes

- Branch: `codex/persona-related-work-benchmark-notes`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PRs:
  - `#77`, `Add personalization and social-interaction benchmarks`
  - `#84`, `Add behavior and private-user-data benchmarks`
- PersonaBench snapshot PRs:
  - `#111`
  - `#113`
- Purpose: preserve useful persona benchmark references from the old
  `personas/PLAN.md` without restoring the old plan file, owner roster, or
  task-assignment format.
- Updated:
  - `docs/research/persona-related-work.md`
- Imported references:
  - LaMP
  - PersonalLLM
  - BehaviorChain / Digital Twins
  - PersonaBench private-user-data benchmark
- Source handling:
  - SOTOPIA was also present in source PR `#77`, but it is already covered in
    `docs/research/environment-related-work.md`, so it is not duplicated here.
  - Owner-line edits from source PR `#77` are intentionally excluded.

### Step 32: Import industry-to-attribute mapping note

- Branch: `codex/persona-industry-attribute-map`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PR: `#74`, `Add Summary of Industry-Related Persona Attributes from
  Attribute Schema`
- PersonaBench snapshot PR: `#110`
- Purpose: preserve the domain-to-attribute mapping for movie, beauty, game,
  finance, health, and coding scenarios without restoring the old `personas/`
  planning folder.
- Imported into:
  - `persona/curation/attribute_pool/docs/industry_related_persona_attributes.md`
- Updated:
  - `persona/curation/attribute_pool/README.md`
- Compatibility adjustments:
  - The old filename with spaces is replaced by a stable snake_case doc name.
  - The source table is reformatted into maintainable per-domain sections.

### Step 33: Import behavior-grounded persona research plan

- Branch: `codex/behavior-grounded-persona-plan`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PRs:
  - `#43`, `Add behavior-grounded persona research plan`
  - `#47`, `Rename behavior grounded persona plan file`
- PersonaBench snapshot PRs:
  - `#101`
  - `#102`
- Purpose: preserve the research direction for behavior-grounded personas
  without restoring the old `personas/` planning folder.
- Imported into:
  - `docs/research/behavior-grounded-personas.md`
- Updated:
  - `docs/research/README.md`
- Compatibility adjustments:
  - The old plan file is converted into a research note.
  - The source rename PR is absorbed by using a stable docs path from the
    start.

### Step 34: Import coding persona dimensions v2

- Branch: `codex/persona-schema-coding-v2`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PR: `#82`, `Add coding persona dimensions v2`
- PersonaBench snapshot PR: `#112`
- Purpose: bring the merged MatrAIx v2 persona dimension catalog into the
  clean `persona/schema` module without restoring raw snapshot outputs.
- Updated:
  - `persona/schema/dimensions.json`
  - `persona/schema/README.md`
  - `persona/curation/existing_data/wiki_collab/collab_kit/README.md`
- Imported schema:
  - `schemaVersion`: `2.0`
  - `targetDimensions`: `1412`
  - Delta from the previous clean schema: 73 new dimensions, no removed
    dimension IDs.
- Source handling:
  - Older closed Attribute Schema snapshots (`#83`, `#84`, `#88`) contain the
    same v1 schema plus superseded v2 drafts and generated intermediate files.
  - Raw attribute-pool outputs, raw datasets, parquet catalogs, curated persona
    dumps, and application UI/backend files from the snapshot branch are
    intentionally excluded from this schema-only PR.

### Step 35: Import AutoPersona research proposal

- Branch: `codex/autopersona-research-note`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PRs:
  - `#36`, `Attribute Schema`
  - `#50`, `Attribute Schema`
  - `#51`, `Persona Attributes Schema`
- PersonaBench snapshot PRs:
  - `#88`
  - `#84`
  - `#83`
- Purpose: preserve the AutoPersona causal schema-learning proposal without
  restoring raw attribute schema workspaces, generated outputs, or old planning
  folders.
- Imported into:
  - `docs/research/autopersona.md`
- Updated:
  - `docs/research/README.md`
- Source handling:
  - The AutoPersona document is identical across the three source snapshots.
  - Attribute-pool scripts, manifests, and v2 schema material from these
    snapshots were already handled by the clean persona curation/schema
    migrations.
  - Raw dataset files, html/pdf references, candidate-pool outputs, graph
    files, and intermediate dedup artifacts remain excluded from `main`.

### Step 36: Import application domain catalog and scenario template

- Branch: `codex/application-domain-template-docs`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PRs:
  - `#46`, `docs: add application-domains brainstorming catalog`
  - `#49`, `docs: re-propose Application Template (runnable handoff to
    Environment team)`
- PersonaBench snapshot PRs:
  - `#86`
  - `#85`
- Purpose: preserve the detailed application-domain benchmark catalog and the
  scenario handoff template without restoring the old team planning layout.
- Imported into:
  - `docs/research/application-domain-benchmark-catalog.md`
- Updated:
  - `docs/research/README.md`
  - `application/README.md`
- Source handling:
  - The old `applications/application_domains_brainstorming.md` is renamed and
    linked from the research docs.
  - The source application README is adapted into a concise scenario handoff
    template under the clean `application/` module.
  - Old `applications/PLAN.md`, team rosters, old root README changes,
    duplicated persona schema/data files, and raw curation folders are excluded.

### Step 37: Import Amazon top reviewer selector

- Branch: `codex/amazon-top-reviewer-selector`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PR: `#125`, `Add Amazon top 10K reviewer inference queue`
- PersonaBench snapshot PR: `#64`
- Purpose: preserve the reproducible reviewer-queue selection logic without
  committing generated top-10K CSV/JSONL/ID artifacts to clean `main`.
- Imported into:
  - `persona/curation/existing_data/scripts/select_amazon_top_reviewers.py`
- Updated:
  - `persona/curation/existing_data/README.md`
  - `migration/matraix/README.md`
- Source handling:
  - The selector now writes into ignored `outputs/` by default.
  - Generated top-reviewer queue files from the source snapshot are listed in
    the external artifact checklist for HuggingFace upload.
  - Existing Amazon HF export, inference, packaging, and validation tools remain
    the downstream path for producing worker packages.

### Step 38: Import persona source fetcher and repair provenance paths

- Branch: `codex/persona-source-fetcher`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PR: `#53`, `[codex] Add Wikipedia persona seed pipeline`
- PersonaBench snapshot PR: `#79`
- Purpose: preserve the reusable source-fetch registry that backs the persona
  schema provenance while keeping raw downloads and old direct-LLM wiki
  assignment scripts out of clean `main`.
- Imported into:
  - `persona/curation/existing_data/scripts/fetch_sources.py`
- Updated:
  - `persona/schema/dimensions.json`
  - `persona/curation/existing_data/README.md`
- Source handling:
  - `fetch_sources.py` is adapted for the clean PersonaBench path and writes to
    ignored `raw/` by default.
  - Schema `fetch_script` provenance entries now point to the clean
    `persona/curation/existing_data/scripts/fetch_sources.py` path.
  - The old `assign_wikipedia_persona_fields.py` Claude CLI flow and prompt are
    excluded because the current wiki/Amazon collaboration package uses the
    tested `wiki_collab/collab_kit` contract instead.

### Step 39: Import recommender chat API task

- Branch: `codex/application-recommender-chat-task`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PRs:
  - `#72`, `app: add Harbor recommender chat task`
- PersonaBench snapshot PR:
  - `#76`
- Purpose: preserve the recommender chat application task contract without
  importing the full historical recommendation evaluation app, generated
  catalogs, or persona fixture bundle into clean `main`.
- Imported into:
  - `application/tasks/recommender-agent_chat_api/`
- Updated:
  - `application/tasks/README.md`
  - `src/personabench/task_catalog.py`
- Source handling:
  - The task name is normalized from `matraix/...` to
    `personabench/application-recommender-agent-chat-api`.
  - The source compose file referenced the full
    `applications/recommendation_chatbot_eval` app. The clean task instead
    includes a task-local REST sidecar that implements the same smoke-test HTTP
    contract.
  - Full RecAI/backend/frontend migration remains separate application tooling
    work; generated recommender catalog/persona fixture files stay external.

### Step 40: Import recommender PersonaEval artifact helpers

- Branch: `codex/application-recommender-eval-artifacts`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PRs:
  - `#75`, `v1 evaluation flow`
  - `#76`, `Add Harbor-backed recommender persona eval`
- PersonaBench snapshot PRs:
  - `#74`
  - `#73`
- Purpose: preserve the pure Python artifact/result contract for recommender
  persona evaluation without importing the full historical backend, frontend,
  generated data, or raw app snapshot.
- Imported into:
  - `application/persona_eval/backend/service/recommender_eval.py`
- Updated:
  - `application/persona_eval/README.md`
- Source handling:
  - Result dataclasses, prompt construction, Harbor persona YAML writing, and
    artifact mapping are adapted to the clean `application/persona_eval/`
    module.
  - Legacy `MATRIX_*` environment variable wiring, API endpoints, subprocess
    Harbor runner integration, and frontend UI remain deferred until the
    application tooling surface is migrated cleanly.

### Step 41: Import application task interface docs

- Branch: `codex/application-task-interface-docs`
- Source repository: `MatrAIx-ai/MatrAIx`
- Source PR:
  - `#86`, `Generalize Type 2 chatbot applications`
- PersonaBench snapshot PR:
  - `#70`
- Purpose: preserve the survey/chatbot/web application task protocol layer
  without importing the full generalized PersonaEval backend, frontend, or
  generated application data.
- Imported into:
  - `application/tasks/interface/`
- Updated:
  - `application/tasks/README.md`
- Source handling:
  - The source `applications/tasks/application_interface/` docs are adapted to
    the clean `application/tasks/` layout.
  - Canonical paths now point at existing PersonaBench tasks:
    `persona-survey`, `recommender-agent_chat_api`, and
    `example-web-playwright_books-interest`.
  - The full `applications/persona_eval` app stack from this source PR remains
    deferred for separate curated application tooling work.

### Step 42: Import parity items 1, 2, 3, and 5 from MatrAIx main

- Branch: `codex/matraix-parity-1235`
- Source repository: local `/data2/zonglin/MatrAIx`
- Source base: `MatrAIx-ai/MatrAIx@main`
- Source commit: `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Purpose: close the functional gaps identified in the main-vs-PersonaBench
  audit for viewer helpers, curated job recipes, Harbor runtime examples, and
  selective Harbor runtime tests.
- Imported into:
  - `apps/viewer/app/lib/`
  - `configs/jobs/application-task-job-recipe/`
  - `configs/jobs/example-job-recipe/personaBench-example-survey-local.yaml`
  - `configs/jobs/persona-task-grounding-job-recipe/`
  - `examples/tasks/`
  - `tests/unit/models/`
  - `tests/unit/agents/computer_1/`
  - `tests/unit/agents/test_base_agent_model_info.py`
  - `tests/unit/agents/test_factory.py`
  - `tests/unit/agents/test_oracle.py`
- Updated:
  - `.gitignore`
  - `configs/jobs/README.md`
  - `docs/migration/matraix-parity-matrix.md`
  - `persona/datasets/README.md`
  - `persona/datasets/bench-dev-sample/`
  - `tests/environment/test_examples_smoke.py`
  - `tests/environment/test_job_recipes.py`
  - `tests/unit/viewer/test_frontend_source_parity.py`
- Source handling:
  - Viewer `app/lib/` was restored because current frontend source imports
    `~/lib/*`; without those files the viewer cannot typecheck or build.
  - Generated application and persona grounding recipes are checked in as
    curated fixtures, not broad generated-output directories.
  - Recipe persona paths are adapted from `persona/datasets/bench-dev-2000/`
    to `persona/datasets/bench-dev-sample/`.
  - `bench-dev-sample/` is expanded from 2 to 14 checked-in personas, only to
    cover smoke tests and the curated recipe fixtures. The full
    `bench-dev-2000` cohort remains external.
  - All source `examples/tasks/` runtime examples are imported. Source
    `examples/jobs/`, `examples/configs/`, `examples/agents/`,
    `examples/metrics/`, and `examples/prompts/` remain excluded.
  - Selected Harbor model/task/agent tests are imported. Legacy
    `registry.json` tests are excluded because clean main does not restore the
    old root registry file.
  - Computer-1 provider tests now skip cleanly unless optional vendor SDKs from
    the `computer-1` extra are installed.
- Verification:
  - `.venv/bin/python -m pytest tests/` passed with 654 passed, 2 skipped.
  - `.venv/bin/ruff check .` passed.
  - `npm ci` in `apps/viewer/` completed, but `npm run typecheck` could not run
    on this machine because Node v18.19.1 is below the Node 20+ requirement and
    Rollup's optional native dependency was unavailable under that install.

### Step 43: Fix viewer Node/npm environment reproducibility

- Branch: `codex/viewer-node20-environment`
- Purpose: make the imported viewer frontend reproducible on Linux CI and
  local development machines after Step 42 restored the frontend helper
  modules.
- Updated:
  - `.github/workflows/viewer.yml`
  - `apps/viewer/.node-version`
  - `apps/viewer/.nvmrc`
  - `apps/viewer/package.json`
  - `apps/viewer/package-lock.json`
  - `apps/viewer/README.md`
  - `apps/viewer/CLAUDE.md`
  - `docs/running.md`
  - `tests/unit/viewer/test_frontend_environment.py`
- Source handling:
  - The viewer now declares Node.js 20.19.0 as its tested local runtime and
    CI uses the same version file before running `npm ci` and
    `npm run typecheck`.
  - The viewer docs now use the npm lockfile workflow instead of the stale
    Bun-only commands.
  - The npm lockfile preserves Linux x64 native optional package entries for
    esbuild, Rollup, Tailwind oxide, and lightningcss. This keeps Linux
    `npm ci` installs from missing the native package required by Rollup and
    Vite.
- Verification:
  - `PATH=/tmp/personabench-node-v20.19.0/bin:$PATH npm ci` passed in
    `apps/viewer/`.
  - `PATH=/tmp/personabench-node-v20.19.0/bin:$PATH npm run typecheck` passed
    in `apps/viewer/`.
  - `PATH=/tmp/personabench-node-v20.19.0/bin:$PATH npm run build` passed in
    `apps/viewer/`.
  - `.venv/bin/python -m pytest tests/` passed with 658 passed, 2 skipped.
  - `.venv/bin/ruff check .` passed.
