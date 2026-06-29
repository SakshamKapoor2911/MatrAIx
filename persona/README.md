# Persona Module

This module owns persona data, schema, curation, and persona adherence
evaluation.

Current layout:

```text
persona/
  schema/       Dimensions, attributes, validators, and schema docs.
  datasets/     Small curated persona sets and sample fixtures.
  curation/     Scripts and manifests for building persona data.
  tasks/        Persona grounding tasks and task-local verifiers.
  scripts/      Persona pool and grounding job generation.
  validators/   Schema validation utilities.
  reporting/    Persona grounding job rollups.
```

Do not place runtime engines, product scenarios, or raw generated job outputs
here. Those belong in `environment/`, `application/`, or external storage.

## Data Pipeline

PersonaBench keeps runnable persona curation code in git and keeps
large/generated data outside `main`.

Canonical flow:

```text
fetch or index source data
  -> normalize and clean records
  -> build local profile DB or JSONL histories
  -> infer or assign persona dimensions
  -> validate outputs
  -> create collaborator package
  -> merge returned results
  -> upload generated artifacts externally
```

Start with [persona curation](curation/README.md) and the
[existing-data pipeline](curation/existing_data/README.md). Large artifact
upload slots are tracked in
[migration/matraix/README.md](../migration/matraix/README.md).

## Imported from MatrAIx

The first curated import brought in:

- `schema/dimensions.json`
- `schema/validators/schema_validator.py`
- `curation/attribute_pool/` docs and pipeline scripts
- two sample personas under `datasets/bench-dev-sample/`
- `tasks/`, `scripts/`, `validators/`, and `reporting/` for the curated
  persona grounding task layer

Large MatrAIx generated outputs were intentionally excluded. See
`docs/migration/matraix-merge-log.md`.
