# Persona Curation

This directory contains scripts and notes for constructing persona schemas and
persona datasets.

Generated large outputs are not committed to git. Keep raw source dumps,
intermediate profile databases, model inference outputs, worker packages, and
returned result archives outside `main` unless a maintainer explicitly approves
a storage plan.

## Current Pipelines

- `attribute_pool/`: schema and attribute-pool curation notes from MatrAIx.
  Large generated candidate pools remain external.
- `existing_data/`: source manifests, Wikipedia profile extraction, worker
  packaging, result validation/merge, and Amazon Reviews 2023 persona
  inference/packaging utilities.

## Contribution Rules

Use this sequence for new persona data work:

```text
source fetch/index -> clean/normalize -> local DB or JSONL histories
  -> persona inference/assignment -> validation/QA
  -> collaborator package or merged dataset -> external artifact upload
```

Small fixtures for tests and docs may live in git. Full datasets should be
uploaded externally and linked from `migration/matraix/README.md` plus the
pipeline README that consumes them.
