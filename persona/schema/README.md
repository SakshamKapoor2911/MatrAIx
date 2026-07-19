# Persona Schema

This directory contains the persona dimension catalog and schema validation
tools.

## Files

- `dimensions.json`: unified persona dimension catalog imported from MatrAIx.
  The current catalog uses schema version `2.0` and contains 1412
  dimensions, including the coding persona dimensions from MatrAIx PR #82.
- `validators/schema_validator.py`: validates required dimension fields and
  checks that deprecated fields are absent.
- `render_persona_schema_taxonomy.py`: renders the taxonomy tree of the schema.
- `persona_schema_taxonomy.png` / `.pdf`: generated taxonomy tree figure for the
  paper appendix.

## Taxonomy Tree Figure

`persona_schema_taxonomy.png` / `.pdf` is a clean three-level horizontal bracket
tree of the schema for the paper appendix, aligned to the official taxonomy
table (9 groups / 1290 attributes):

- Left column: the 9 top-level groups, with attribute totals.
- Middle column: the aspects (schema-prefix mid level, e.g. `Demographic`,
  `Developer`).
- Right column: the 43 fine-grained categories, with attribute counts.

Regenerate it from the repository root:

```bash
uv run --extra viz python persona/schema/render_persona_schema_taxonomy.py
```

Notes:

- Latent/helper graph nodes (18 nodes with no `category`, e.g. `latent_*` /
  `phase*_*`) are excluded, since they are internal modeling variables rather
  than persona attributes; the figure covers exactly the 1,290 real attributes.
- The individual `Developer: *` categories are shown separately, so the appendix
  figure is a more detailed view of the schema.
- Do not hand-edit the generated figures; regenerate them with the script and
  commit both the script change and the figures.

## Validate

Run from the repository root:

```bash
python3 persona/schema/validators/schema_validator.py
```

The validator also accepts an explicit path:

```bash
python3 persona/schema/validators/schema_validator.py persona/schema/dimensions.json
```
