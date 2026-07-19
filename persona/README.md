# Persona Module

This module owns persona data, schema, curation, and persona adherence
evaluation.

**Persona team guides:** [docs/personas/README.md](../docs/personas/README.md) (data → schema → grounding)

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

## Major Persona Data Products

The persona module currently has three large data products: a fully synthetic
10B-persona attribute space, Wiki-grounded personas for about 2.1M public
profiles, and a fixed 100K Amazon-reviewer cohort. Large payloads are stored on
scratch or Hugging Face; git tracks the schema, production code, manifests, and
run records.

| Data product | Scale | Source / method | Canonical format | Status / public artifact |
|---|---:|---|---|---|
| Full-DAG synthetic personas | 10,000,000,000 | Probabilistic graph sampling | Nibble-packed `codes.gz` + schema + manifest | Full local run complete; [1B subset on Hugging Face](https://huggingface.co/datasets/MatrAIx2026/Persona8B) |
| Wiki personas | 2,125,897 target profiles | Qwen3.6 extraction from English Wikipedia-derived profiles | Sharded JSONL with 1,290 structured fields | Production run substantially complete; [10,630-row public shard](https://huggingface.co/datasets/HFXM/MatrAIx-Wiki-Personas) |
| Amazon Review personas | 100,000 fixed reviewers | Qwen3.6 extraction from chronological review histories | Sharded JSONL with 1,290 sanitized fields | Production merge in progress; [deterministic 10K public subset](https://huggingface.co/datasets/HFXM/MatrAIx-Amazon-Review-Personas-10K) |

Descriptions and evidence in the human-extraction datasets are model-generated
and can contain errors. They are grounded signals for persona research, not
verified personal facts.

### 1. Full-DAG Synthetic Personas (10B)

This dataset samples the full 1,290-dimension persona space from
[`synthesis/graph/full_dag.json`](synthesis/graph/full_dag.json). It does not use
an LLM for generation: the sampler follows graph priors, dependencies, helper
nodes, and consistency constraints, then emits one categorical code per schema
dimension.

Production flow:

```text
dimensions.json + full_dag.json
  -> validate emitted graph nodes against the schema
  -> sample 100 independent shards on CPU
  -> encode 100M personas/shard as nibble-packed integer codes
  -> gzip each code shard
  -> write a schema sidecar and manifest per shard
  -> decode or render selected rows lazily for downstream use
```

Completed run (`full_dag_10b_20260703`):

- **10B rows**, 1,290 attributes/row.
- **100 shards x 100M rows**.
- CPU-only Slurm array on `seas_compute`: `0-99%20`, 48 CPUs/task.
- Canonical payload: `*.codes.gz`; rendered natural language is not stored for
  all 10B rows.
- Compressed codes size: **4.0397 TB** (about 404 bytes/persona).
- Local output (git-ignored):
  `persona/synthesis/generated/full_dag_10b_20260703/`.
- Decode/render selected data with
  [`synthesis/scripts/decode_persona_codes.py`](synthesis/scripts/decode_persona_codes.py)
  and [`synthesis/scripts/render_personas.py`](synthesis/scripts/render_personas.py).

The first 1B rows (shards `0000-0009`) were uploaded to
[`MatrAIx2026/Persona8B`](https://huggingface.co/datasets/MatrAIx2026/Persona8B)
with schema sidecars, manifests, checksums, and the production run record. See
[`RUN_FULL_DAG_10B_20260703.md`](synthesis/jobs/graph_10b_generation/RUN_FULL_DAG_10B_20260703.md)
and
[`HF_UPLOAD_PERSONA8B_1B_20260704.md`](synthesis/jobs/graph_10b_generation/HF_UPLOAD_PERSONA8B_1B_20260704.md).

### 2. Wiki-Grounded Personas (~2.1M)

The Wiki pipeline maps one public-person profile to one persona. The source is a
gated copy of `MatrAIx2026/MatrAIx2026`, stored locally as a read-only SQLite
database with **2,125,897 profiles**. The extraction uses
`Qwen/Qwen3.6-35B-A3B` through vLLM.

Production flow:

```text
Wikipedia-derived profile SQLite
  -> inspect profile/token length distribution
  -> keep one full profile per person (24K-character safety cap)
  -> split the 1,290 dimensions into 53 category-local prompt chunks
  -> run deterministic Qwen3.6 extraction on H200 GPUs
  -> parse and merge all chunks for the same person
  -> append one resumable JSONL record per profile
  -> validate allowed values, evidence, descriptions, and shard coverage
```

The run uses 200 contiguous shards (normally about 10,630 profiles/shard) across
`seas_gpu` and `gpu_h200`. Each task uses one H200; checkpointing is by
`global_idx`, so timed-out or failed shards can be safely topped up.

Each output row has this structure:

```json
{
  "global_idx": 0,
  "qid": "Q41746",
  "title": "Achilles",
  "fields": [
    {
      "field_id": "age_bracket",
      "value": "65+",
      "confidence": 0.8,
      "evidence": "verbatim profile quote",
      "description": "1-2 sentence person-specific description",
      "assignment_type": "direct"
    }
  ]
}
```

Every row contains approximately 1,290 field objects; unsupported dimensions
normally have `value: null`. The local uncompressed output is roughly 0.5 TB and
is git-ignored under `human_extraction/data/extraction_v1/`. A complete public
sample shard (10,630 rows, gzip-compressed) plus its legacy schema is available
at
[`HFXM/MatrAIx-Wiki-Personas`](https://huggingface.co/datasets/HFXM/MatrAIx-Wiki-Personas).

Implementation and operational details are in
[`human_extraction/README.md`](human_extraction/README.md),
[`human_extraction/scripts/run_extraction.py`](human_extraction/scripts/run_extraction.py),
and [`human_extraction/docs/BENCHMARK.md`](human_extraction/docs/BENCHMARK.md).

### 3. Amazon Review Personas (100K)

The Amazon pipeline defines a fixed cohort of **100,000 unique reviewers** from
the Amazon Reviews 2018-2023 artifacts in `MatrAIx2026/MatrAIx2026`. One persona
is built from one reviewer's chronological review history, including product
category, title, text, rating, date, and verified-purchase context.

Selection and extraction flow:

```text
per-user review statistics (256 hash buckets)
  -> explore review counts, characters, and true Qwen token lengths
  -> remove histories that are too short or exceed the model input budget
  -> freeze a 100K user_id/user_bucket selection parquet
  -> assemble one chronological profile_text per reviewer
  -> run Qwen3.6 with the conservative medium_b prompt
  -> sanitize every model field against dimensions.json before persistence
  -> resume/deduplicate by user_id within each bucket shard
  -> merge cross-cluster tranches and verify all 256 buckets
```

The authoritative cohort is pinned by SHA-256:

```text
8a0084628f32a06f8f823126f819ef1abcc8387978b44f79eb4f923cb5e8ce12
```

The first 38,219 users were produced on H100 (FP8, TP=1) and A100 (bf16,
TP=4). The continuation uses one H200 per worker (FP8, TP=1), the exact
`medium_b` prompt, PR #174 schema sanitization, per-task local compile caches,
resumable partial buckets, and a self-healing supervisor that validates and
retries incomplete buckets.

Each JSONL row contains `user_id`, `user_bucket`, `review_count`,
`prompt_variant`, and 1,290 sanitized `fields`. The sanitizer drops hallucinated
field IDs, canonicalizes allowed values, fills missing dimensions as
unsupported, and requires grounded evidence for non-null values.

The deterministic public 10K subset contains exactly 10,000 unique users and is
available at
[`HFXM/MatrAIx-Amazon-Review-Personas-10K`](https://huggingface.co/datasets/HFXM/MatrAIx-Amazon-Review-Personas-10K).
It includes gzip JSONL data, the exact dimensions schema, a manifest, and
checksums. Current continuation details are tracked in
[`human_extraction/docs/HANDOFF_KOUTIAN_TO_XIAOMIN_20260717.md`](human_extraction/docs/HANDOFF_KOUTIAN_TO_XIAOMIN_20260717.md).

## Imported from MatrAIx

The first curated import brought in:

- `schema/dimensions.json`
- `schema/validators/schema_validator.py`
- `curation/attribute_pool/` docs and pipeline scripts
- 200 dev personas under `datasets/bench-dev-sample/` (82 dimensions, version 1.0)
- `tasks/`, `scripts/`, `validators/`, and `reporting/` for the curated
  persona grounding task layer

Large MatrAIx generated outputs were intentionally excluded. See
`docs/migration/matraix-merge-log.md`.
