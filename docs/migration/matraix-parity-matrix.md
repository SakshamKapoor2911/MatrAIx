# MatrAIx Main Parity Matrix

This document records how `MatrAIx-ai/MatrAIx` `main` maps into the curated
PersonaBench repository layout.

It is intentionally not a byte-for-byte parity target. PersonaBench `main`
should remain a clean, runnable distribution of the MatrAIx codebase. Raw
snapshots, generated jobs, and large persona artifacts stay outside git and are
linked from documentation after upload to external artifact storage.

## Snapshot

| Repository | Ref | Commit |
|---|---|---|
| Source | `MatrAIx-ai/MatrAIx@origin/main` | `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0` |
| Target | `ElegantLin/PersonaBench@origin/main` | `a8cbbd5dbf53588b4a85de1a3d8dda4f87ca0c73` |

## Status Vocabulary

| Status | Meaning |
|---|---|
| `merged-clean` | Curated code is already present in PersonaBench with module-appropriate paths and tests. |
| `partial` | Some useful source material has been imported, but remaining source paths still need a follow-up PR or external handoff. |
| `needs-curated-import` | Source material is useful, but should be imported in a focused PR after path, dependency, and test review. |
| `external-artifact` | Material is too large or generated and should be uploaded outside git, then linked from docs. |
| `archive-only` | Preserve through source PR snapshots or provenance metadata; do not merge into clean `main`. |
| `deferred` | Not required for the current clean-main objective; revisit only if a concrete workflow needs it. |

## Top-Level Source Inventory

| MatrAIx path | Source files | Source size | PersonaBench target | Status | Handling |
|---|---:|---:|---|---|---|
| `.github/` | 8 | 14.5 KiB | `.github/` | `partial` | Safe CODEOWNERS, labeler, pytest, and Ruff workflows are imported. Claude automation remains excluded until secrets and review policy are explicit. |
| Root metadata | 15 | 0.93 MiB | root files | `partial` | Keep PersonaBench branding. Review `LICENSE`, `NOTICE`, `CITATION.cff`, `.python-version`, `uv.lock`, and contributor docs one by one. |
| `adapters/` | 1,483 | 16.4 MiB | `environment/adapters/` | `needs-curated-import` | Do not dump the adapter zoo at repo root. Import adapters in small batches with manifests, dependencies, smoke commands, and external-data notes. |
| `application/` | 88 | 81.1 KiB | `application/` | `merged-clean` | Curated tasks, reporting, and job-generation utilities are already present. Future changes should stay under `application/`. |
| `apps/viewer/` | 64 | 750.0 KiB | `apps/viewer/` | `merged-clean` | Viewer source was imported as repo-local tooling. Generated build output and `node_modules` stay out of git. |
| `configs/jobs/` | 18 | 18.4 KiB | `configs/jobs/` | `partial` | Curated runnable application recipes and the `harbor-smoke-local.yaml` runtime smoke recipe are present. Import only additional recipes whose referenced tasks, agents, and sample datasets exist. |
| `docs/` | 15 | 2.8 MiB | `docs/` | `partial` | Keep architecture and migration docs curated. Large images and legacy planning docs need review before import. |
| `examples/` | 367 | 394.7 KiB | `examples/` or module-local examples | `partial` | The `hello-world` runtime smoke task is imported. Remaining examples need focused review before import. |
| `jobs/` | 509 | 64.3 MiB | external storage | `external-artifact` | Historical run outputs, screenshots, videos, and trajectories do not belong in `main`. Upload selected artifacts and link them from docs. |
| `packages/` | 66 | 303.6 KiB | `packages/` | `partial` | `harbor-langsmith` is imported as an optional package. Import `rewardkit` in a separate PR with its own test and dependency review. |
| `persona/` | 2,098 | 451.2 MiB | `persona/` plus external storage | `partial` | Schema, curation, sample data, tasks, reporting, scripts, and validators are curated. Full generated datasets and attribute-pool outputs stay external. |
| `rfcs/` | 4 | 131.5 KiB | `docs/rfcs/` or `rfcs/` | `deferred` | Import only if the RFC is still part of active contributor guidance. |
| `scripts/` | 4 | 37.2 KiB | module-local scripts | `partial` | Move package publish scripts with packages, adapter validation with adapters, and skill installation docs with contributor tooling. |
| `skills/` | 4 | 39.9 KiB | contributor tooling docs | `deferred` | Preserve as provenance for now. Import only if the repository will support Codex skill-driven task creation. |
| `src/` | 339 | 3.2 MiB | `src/harbor/`, `src/personabench/` | `merged-clean` | Runtime and utility packages are imported under stable namespaces. The old `src/matraix/` namespace should not be restored. |
| `tests/` | 293 | 2.7 MiB | `tests/` | `partial` | Focused tests exist for curated modules. Import additional tests with the packages, examples, or adapters they validate. |

## Remaining PR Plan

The following PRs are the clean-main continuation path approved for migration:

| Order | PR theme | Scope | Explicit exclusions |
|---:|---|---|---|
| 1 | Migration parity audit | This matrix and source-to-target status documentation. | Code imports, guardrail tests. |
| 2 | Safe GitHub metadata | `.github` workflows, PR template updates, CODEOWNERS, labeler config, and CI assumptions that still apply. | Secrets, deploy workflows, branch-protection-breaking behavior. |
| 3 | Minimal examples and smoke recipes | Runtime examples required by curated smoke jobs, likely starting with `examples/tasks/hello-world` and `harbor-smoke-local.yaml`. | Full example job outputs under `examples/jobs/` and `jobs/`. |
| 4 | Optional packages | `packages/rewardkit` and `packages/harbor-langsmith` as isolated optional package PRs, or a single PR if the dependency graph requires both together. | Publishing credentials, generated build artifacts. |
| 5 | Adapter foundation | `environment/adapters/README.md`, adapter manifest format, and a first small adapter batch. | Bulk import of all 1,483 adapter files. |
| 6 | External artifact handoff | Expand artifact inventory and add placeholder HuggingFace slots for persona data, job outputs, and large fixtures. | Uploading binary artifacts into git. |

## Adapter Import Rules

Every adapter PR must include a manifest with:

- source path in `MatrAIx-ai/MatrAIx`
- source commit and source PR when known
- runtime dependencies
- required external datasets or credentials
- smoke command
- owner or original author
- status: `enabled`, `experimental`, or `archived`

Adapters should land under `environment/adapters/<adapter-name>/` unless a
specific adapter is better expressed as an `application/` task or a standalone
optional package.

## External Artifact Rules

Do not commit generated data simply to increase source parity. Anything in the
following categories should be external:

- full persona datasets such as `persona/datasets/bench-dev-2000/`
- attribute-pool generated outputs
- historical `jobs/` outputs
- screenshots, recordings, and trajectories from completed runs
- package manager dependency directories such as `node_modules/`

After upload, record the public artifact location in:

- `migration/matraix/README.md`
- `persona/datasets/README.md`
- task-specific or adapter-specific README files that require the artifact

## Contributor Guidance

Future contributions should preserve the module boundary:

- Persona schema, datasets, curation, tasks, and persona-specific reporting go under `persona/`.
- Application task definitions, application reporting, and application recipe generation go under `application/`.
- Runtime, agents, environments, tools, and external benchmark adapters go under `environment/`.
- Repo-local UI tools go under `apps/`.
- Shared Python utilities go under `src/personabench/`.
- Harbor runtime code remains under `src/harbor/`.
- Historical provenance and source mapping stay under `migration/`.

If a contribution needs a new top-level directory, document why in the PR body
and update `docs/architecture.md` in the same PR.
