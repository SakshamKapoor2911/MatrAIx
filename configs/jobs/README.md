# Job Recipes

This directory contains curated Harbor job recipes that run against files kept
in PersonaBench `main`.

Rules for adding recipes:

- Use paths that exist in this repository.
- Use personas from checked-in sample datasets, or document an external dataset
  dependency in the recipe README.
- Do not commit generated `jobs/` outputs.
- Do not add raw snapshots from the MatrAIx source tree.
- Keep generated or bulk recipes separate from hand-curated examples.

Current curated set:

- `example-job-recipe/`: local application task examples backed by
  `application/tasks/` and `persona/datasets/bench-dev-sample/`, plus
  `harbor-smoke-local.yaml` for a no-API-key runtime smoke check.
- `application-task-job-recipe/`: curated generated application recipe fixtures
  whose personas are copied into `persona/datasets/bench-dev-sample/`.
- `persona-task-grounding-job-recipe/`: curated generated persona grounding
  recipe fixtures backed by the same sample dataset.

Deferred from the MatrAIx source recipes:

- Generated random-sample recipes that reference
  `persona/datasets/bench-dev-2000/` beyond the checked-in sample fixture set,
  because that full dataset is intentionally external to git.
