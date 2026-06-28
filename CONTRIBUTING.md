# Contributing to PersonaBench

PersonaBench accepts focused PRs. A PR can touch more than one module, but it
must explain the boundary crossing in the PR body.

## Modules

| Module | Owns | Does not own |
| --- | --- | --- |
| `persona/` | Persona schema, attributes, curated datasets, persona curation scripts, persona adherence tasks | Runtime drivers, product scenarios, checked-in job outputs |
| `application/` | Survey/chat/web/product scenarios, application metrics, application task fixtures | Persona source datasets, runtime engines |
| `environment/` | Harbor/runtime code, persona agent adapters, job recipes, viewer backend, execution backends | Persona schema decisions, application-specific research claims |
| `apps/` | Repo-local tool frontends such as the `harbor view` UI | Generated builds, datasets, task definitions |
| `packages/` | Reusable libraries used by multiple modules | One-off scripts or generated outputs |

## PR Expectations

Every PR should include:

- The module or modules it touches.
- The source issue or migration source, when applicable.
- A short explanation of why the change belongs in that module.
- Test or validation commands that were run.
- Any generated data policy decision, especially for large files.

## What Not To Merge

Do not merge raw migration snapshot directories such as:

- `MatrAIx/`
- `MatrAIx_PR_*`
- `MatrAIx_CLOSED_PR_*`
- `MatrAIx_MERGED_PR_*`

Those are screening artifacts. Curate the useful code into the module layout
instead.

Do not check in large generated job output by default. Prefer small fixtures
under the owning module, or external storage for large datasets and run logs.

## Migration Workflow

When importing from MatrAIx:

1. Find the source PR or commit in `migration/matraix/`.
2. Decide which module owns the useful content.
3. Move only the curated files into that module.
4. Add or update module docs.
5. Run the narrowest useful validation.
6. Record the import in `docs/migration/matraix-merge-log.md`.
