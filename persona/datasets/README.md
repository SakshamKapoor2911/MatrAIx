# Persona Datasets

This directory stores small, curated persona datasets that are suitable for git.

Large generated datasets should not be committed directly. Store them externally
or import only a small fixture set for tests and documentation. After upload,
record the HuggingFace or external storage URL in `migration/matraix/README.md`
and link it from the README for the pipeline that produced it.

## Current Datasets

- `bench-dev-sample/`: dev persona pool (200 profiles, 82 dimensions each) for
  schema examples, smoke tests, Playground UI, and curated job recipes.
  Dimension UI groups live in `persona/schema/dimension_categories.json`.

## External Dataset Slots

Expected external persona artifacts include:

- full `bench-dev-2000` persona cohort
- attribute-pool generated candidate pools and normalized outputs
- existing-data curated persona YAML outputs
- Amazon Reviews 2023 user histories, profile databases, inference outputs,
  worker packages, and validation reports
