# Persona Attribute Candidate Pool

This folder contains the persona attribute aggregation, normalization, and
LLM-assisted deduplication pipeline imported from MatrAIx.

This curated import keeps source docs and scripts in git, but intentionally
does not import the large generated `outputs/` tree.

## Included

- `docs/`: method notes and theoretical-basis documents.
  - `industry_related_persona_attributes.md` maps common application domains
    to useful schema attributes for cohort selection.
- `scripts/`: pipeline scripts for aggregation, normalization, deduplication,
  graph preparation, and final merge construction.
- `sources/`: small source notes that explain the input datasets. Large raw
  inputs should be restored locally or through external dataset storage, not
  committed directly.
- `OUTPUTS.md`: policy for large generated artifacts that were excluded.

## Excluded Outputs

The MatrAIx source tree included generated CSV/JSONL/graph outputs. Some were
larger than 50 MB, and one normalized JSONL was roughly 70 MB. Those artifacts
should live outside normal git history unless a maintainer approves a storage
plan.

See `OUTPUTS.md` for examples and options.

## Current Counts

- High-quality candidate attributes before deduplication: 9,935
- Step 3 canonical attributes before LLM merge: 9,504
- LLM-adjudicated candidate pairs: 7,000
- High-confidence merge edges: 429
- Final merged attributes: 9,123
- Final graph edges: 5,039

Only high-confidence `duplicate_of` / `alias_of` merge decisions are collapsed. Correlated, inverse, broader/narrower, conflict, review, and rejected pairs remain separate attributes and are represented as graph edges or review rows.

## Reproducibility

Scripts used to generate these artifacts are in `scripts/`. Method notes and theoretical-basis documents are in `docs/`.

In PersonaBench, curation scripts resolve paths relative to this
`attribute_pool/` directory:

- raw/reference inputs: `sources/`
- generated/intermediate outputs: `outputs/`
- scripts: `scripts/`

`outputs/` is ignored by git. If a future PR needs to publish generated data,
include a manifest plus a small fixture in git, then store the full artifact in
approved external storage or Git LFS after maintainer approval.

This work belongs to the Persona layer because it defines persona schema attributes, source grounding, deduplication logic, and graph relations. Application scenarios consume this attribute pool but should not own it.
