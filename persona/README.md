# Persona Module

This module owns persona data, schema, curation, and persona adherence
evaluation.

Planned layout:

```text
persona/
  schema/       Dimensions, attributes, validators, and schema docs.
  datasets/     Small curated persona sets.
  curation/     Scripts and manifests for building persona data.
  bench/        Persona adherence and grounding tasks.
  reporting/    Persona quality and coverage analysis.
```

Do not place runtime engines, product scenarios, or raw generated job outputs
here. Those belong in `environment/`, `application/`, or external storage.
