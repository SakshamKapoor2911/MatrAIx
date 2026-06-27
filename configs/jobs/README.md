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
  `application/tasks/` and `persona/datasets/bench-dev-sample/`.

Deferred from the MatrAIx source recipes:

- `harbor-smoke-local.yaml`, because it points at `examples/tasks/hello-world`,
  which is not part of the curated PersonaBench main tree.
- `personaBench-example-survey-local.yaml` and persona grounding recipes,
  because they should be regenerated against curated sample or external
  PersonaBench datasets instead of copied from the source tree.
- Generated random-sample recipes that reference
  `persona/datasets/bench-dev-2000/`, because that full dataset is intentionally
  external to git.
