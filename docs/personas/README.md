# Persona team documentation

Persona work moves in three layers — **collect profiles**, **constrain the
schema graph**, then **evaluate grounding** in bench tasks.

```text
  curation & datasets  →  schema & dimension graph  →  grounding bench tasks
  (sources, packages)     (attributes, validators)      (probe / confounders / score)
```

| Layer | Topic | Start here |
|-------|-------|------------|
| **1 — Data** | Source fetch, normalization, collaborator packages | [curation/existing_data/README.md](../../persona/curation/existing_data/README.md) · `make_package.py` |
| **2 — Schema** | Dimensions, categories, validators | [persona/schema/README.md](../../persona/schema/README.md) · [dimensions.json](../../persona/schema/dimensions.json) |
| **3 — Grounding** | Controlled cohorts, discriminative tasks, alignment scores | [getting-started.md](./getting-started.md) |

Also: [persona/README.md](../../persona/README.md) · [datasets](../../persona/datasets/README.md) · [bench task authoring](../../persona/tasks/README.md) · [research notes](../research/persona-related-work.md)
