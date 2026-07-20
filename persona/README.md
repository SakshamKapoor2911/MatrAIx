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
  post_process/ Cached cross-dataset statistics and paper figures.
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

The persona module currently has seven major data products. After quality
filtering, cross-product deduplication, deterministic synthetic diversity
selection, the current synthetic-pool exclusions, and inclusion of the 508-person
Real Human Survey cohort, the operational corpus contains **8,400,000,008
personas (about 8.4B)**. Large payloads are stored on scratch or Hugging Face;
git tracks the schema, production code, manifests, and run records.

| Data product | Current retained scale | Source / method | Canonical format | Status / public artifact |
|---|---:|---|---|---|
| Full-DAG synthetic personas | 8,397,777,004 | Probabilistic graph sampling; quality filtering and deterministic diversity selection from 10B generated rows | Nibble-packed `codes.gz` source + rejection bitmaps + schema + manifests | Current operational pool; audited pre-exclusion baseline retained 8,397,777,504 synthetic rows |
| Wiki personas | 1,946,442 | Qwen3.6 extraction with 1,200 subscription/API upgrades | Sharded JSONL with structured persona fields | Retained from 1,997,743 extracted rows after quality filtering and deduplication |
| Amazon Review personas | 97,915 | Qwen3.6 extraction from chronological review histories | 256 bucketed JSONL shards with 1,290 sanitized fields | Retained from the validated 100K cohort; [deterministic 10K public subset](https://huggingface.co/datasets/HFXM/MatrAIx-Amazon-Review-Personas-10K) |
| Stack Overflow survey personas | 113,120 | Qwen3.6 extraction from 2023-2025 Stack Overflow survey records | Raw sparse JSONL + PR #53-compatible JSONL with 1,290 fields | Retained from 113,335 responses; data in [Existing_Data PR #55](https://huggingface.co/datasets/MatrAIx2026/Existing_Data/discussions/55) |
| PRISM Alignment personas | 1,487 | Exact demographic crosswalk + Qwen3-235B-A22B extraction | One gzip JSONL shard with 1,290 fields + observed overlay | Retained from 1,500 participants; validated on [Existing_Data main](https://huggingface.co/datasets/MatrAIx2026/Existing_Data/tree/main/prism) |
| GSS personas | 63,532 | Rule-based crosswalk from NORC GSS 1972-2024 | Five gzip JSONL shards with 1,290 fields + observed overlay | Retained from 75,699 respondents; validated on [Existing_Data main](https://huggingface.co/datasets/MatrAIx2026/Existing_Data/tree/main/gss) |
| Real Human Survey personas | 508 confirmed real people | Direct real-person survey records | One JSONL file with 1,290 schema-ordered fields | Complete and validated locally |

Descriptions and evidence in LLM-extracted datasets are model-generated and can
contain errors. Rule-based survey mappings preserve coded responses but still
depend on crosswalk correctness. These are grounded signals for persona
research, not independently verified personal facts.

Cross-dataset paper statistics, cached tables, and figures are in
[`post_process/dataset_statistics/`](post_process/dataset_statistics/). The
streaming profiler reads the large artifacts only when they change; the
notebook reads the compact cache and can be rerun quickly.

### 1. Full-DAG Synthetic Personas (8,397,777,004 Retained)

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

Initial generation run (`full_dag_10b_20260703`):

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

The 10B rows are the immutable pre-deduplication source, not the final corpus
size. The audited deduplication baseline retained 8,397,777,504 synthetic rows
alongside 2,222,496 human-grounded rows for an exact 8.4B total. Subsequent
operational exclusions removed 500 additional synthetic rows, leaving the
current synthetic pool at **8,397,777,004**. With the 2,222,496 retained
human-grounded personas and 508 Real Human Survey personas, the current corpus
contains **8,400,000,008 personas**. The non-destructive rejection bitmaps,
accounting, and exact selection procedure are documented in
[`post_process/deduplication/README.md`](post_process/deduplication/README.md).

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
is git-ignored under `human_extraction/data/wiki/extraction_v1/`. A complete public
sample shard (10,630 rows, gzip-compressed) plus its legacy schema is available
at
[`HFXM/MatrAIx-Wiki-Personas`](https://huggingface.co/datasets/HFXM/MatrAIx-Wiki-Personas).

Implementation and operational details are in
[`human_extraction/README.md`](human_extraction/README.md),
[`human_extraction/scripts/run_extraction.py`](human_extraction/scripts/run_extraction.py),
and [`human_extraction/docs/BENCHMARK.md`](human_extraction/docs/BENCHMARK.md).

The first **1,200 rows** (`global_idx` 0-1199) in local `shard_0000.jsonl` have
been upgraded with the stronger subscription/API extraction from
[`Existing_Data` PR #51](https://huggingface.co/datasets/MatrAIx2026/Existing_Data/discussions/51).
The replacement uses immutable commit
`0647ae3fd6bfba403e9c63a0c9350b35be806b05`, whose rich Parquet retains
per-field confidence, evidence, and assignment type. The current PR head is not
used as the conversion source because its flattened persona-card Parquet drops
that grounding metadata.

The 1,200 source identities match the local Qwen rows exactly by
`global_idx + qid`. Their model mix is 660 Claude Opus 4.8, 420 GPT-5.5, 89
GPT-5.4-mini, 30 DeepSeek variants, and one mixed-model row. Conversion to the
current 1,290-field contract:

- preserves 189,458 grounded claims;
- canonicalizes 998 unambiguous legacy dash variants;
- nulls 587 legacy `age_bracket=65+` values because they cannot be uniquely
  mapped to `65-74`, `75-84`, or `85+`;
- drops removed legacy IDs and fills absent current IDs as `unsupported`;
- emits an empty `description` because the subscription prompt did not produce
  that field.

The original Qwen rows are retained in a gzip rollback backup, with hashes and
model provenance in a replacement manifest under
`human_extraction/data/wiki/replacements/subscription_pr51_batch_1/`. The
validated, atomic conversion is implemented by
[`human_extraction/scripts/replace_wiki_subscription_rows.py`](human_extraction/scripts/replace_wiki_subscription_rows.py).

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

The full extraction completed on 2026-07-19. The final supervisor validated all
167 continuation buckets with zero missing users, extra users, or invalid JSON
lines. An independent 256-bucket validation then combined the latest 167 local
continuation buckets with the 89 completed source buckets and checked them
against the authoritative selection parquet. Results: **100,000 rows, 100,000
globally unique users, zero missing or extra users**, correct bucket assignment,
`prompt_variant=medium_b`, and exactly 1,290 fields on every row. The older
91,307-user `hf_snapshot_20260719` directory is an in-progress frozen snapshot,
not the final 100K publication package.

### 4. Stack Overflow Survey Personas (113,335)

This dataset maps one response from the public
[Stack Overflow Developer Survey](https://survey.stackoverflow.co/) to one
persona. It covers **113,335 responses** across three survey years:

| Survey year | Personas | Raw SHA-256 | PR #53-compatible SHA-256 |
|---|---:|---|---|
| 2023 | 55,593 | `cbd5fe1877390bfe5221a1e3cbd4904f634aff90b1fc966499aeb56a5f096f21` | `15c56d4fb77a1d44c4cf6efd11694bae7d3387412e4c1ec031c52e3266b323c3` |
| 2024 | 34,658 | `182f09dbc10e8310bb207c4c2d417deb3afa6edb911f3af545ad1236c8dce653` | `de26e460eb20be4d2d270934bd4ad1bbeab891b7fb479f47641eb5c1dc0557c4` |
| 2025 | 23,084 | `e7d7aecc412c31f37f693040a7bf2c7e836b779b0d32b9523a91ed0f4a503994` | `7b88c9c11aa2dd5abe0b1f60a91496e5c45908bc48839c07edbcbfb0a947ac49` |

The direct extraction used `Qwen/Qwen3.6-35B-A3B` through vLLM and identifies
itself as `stackoverflow_vllm_v2`. The raw files retain supported fields only.
The translated files follow the Amazon PR #53 record contract: each row has
`user_id`, deterministic `user_bucket`, `review_count`, `prompt_variant`, and
exactly 1,290 schema-ordered `fields`. Missing dimensions are represented as
explicit `unsupported` fields. All 113,335 rows passed full-stream validation
with zero rejected rows. The reported extraction cost was 1,886 RTX6000 PRO
GPU-hours.

The authoritative artifacts are in
[`MatrAIx2026/Existing_Data` PR #55](https://huggingface.co/datasets/MatrAIx2026/Existing_Data/discussions/55)
under `StackExchange_Persona/extraction_v1/qwen36/`. The PR contains the three
raw JSONL files, three translated JSONL files, a conversion manifest, and a
conversion report. It is not yet on the dataset's `main` revision because PR
#55 currently has a `.gitattributes` merge conflict. A revision-pinned local
copy is stored under the git-ignored path
`human_extraction/data/stackoverflow/hf_pr55/`.

Repository PR #152 is already merged and provides the Stack Overflow
collaboration and reproduction code. The main entry points are
[`existing_data_curation/scripts/export_hf_stackoverflow_user_histories.py`](existing_data_curation/scripts/export_hf_stackoverflow_user_histories.py),
[`existing_data_curation/scripts/make_stackoverflow_collab_package.py`](existing_data_curation/scripts/make_stackoverflow_collab_package.py), and
[`existing_data_curation/wiki_collab/stackoverflow_collab.py`](existing_data_curation/wiki_collab/stackoverflow_collab.py).
The source-specific default prompt and field contract are in
[`existing_data_curation/wiki_collab/collab_kit/solver.py`](existing_data_curation/wiki_collab/collab_kit/solver.py),
with source and evidence mappings in
[`existing_data_curation/configs/stackexchange_persona.json`](existing_data_curation/configs/stackexchange_persona.json)
and
[`existing_data_curation/configs/stackoverflow_evidence_mapping.json`](existing_data_curation/configs/stackoverflow_evidence_mapping.json).

### 5. PRISM Alignment Personas (1,500)

This product maps all **1,500 real participants** in the
[PRISM Alignment Corpus](https://huggingface.co/datasets/HannahRoseKirk/prism-alignment)
to the 1,290-dimension schema. One persona represents one survey respondent. It
uses two layers:

1. A rule-based observed overlay maps nine demographics directly from survey
  responses to allowed schema values.
2. `Qwen3-235B-A22B` extracts evidence-grounded attributes from demographics,
  verbatim self-description, and stated AI preferences in 53 category-local
  prompt chunks.

Post-processing demotes ungrounded or absence-based claims to `unsupported`,
nulls off-schema values, and gives exact observed values precedence. Every row
has `user_id`, 1,290 ordered `fields`, and an `observed` mapping. The completed
v1.1 shard has about 178.1 grounded attributions and 8.7 exact demographics per
persona. Human-written PRISM survey text is CC-BY-4.0; downstream use must also
follow the source dataset card.

The gzip shard, manifest, and source README are on
[`MatrAIx2026/Existing_Data`](https://huggingface.co/datasets/MatrAIx2026/Existing_Data/tree/main/prism)
and are downloaded locally under the git-ignored path
`human_extraction/data/prism/hf_main/`. The local copy resolves HF `main` at
commit `83f8eb3420b12ebccfa97771a8dccceccb1e3cad`. Its 1,500 unique users,
1,290-field ordering, compressed SHA-256, and manifest-pinned uncompressed
SHA-256 have been verified.

Reproduction details are in
[`human_extraction/PRISM_EXTRACTION_HANDOFF.md`](human_extraction/PRISM_EXTRACTION_HANDOFF.md).
The main implementation files are
[`human_extraction/scripts/render_prism_profiles.py`](human_extraction/scripts/render_prism_profiles.py),
[`human_extraction/scripts/run_extraction_api.py`](human_extraction/scripts/run_extraction_api.py),
and
[`human_extraction/scripts/postprocess.py`](human_extraction/scripts/postprocess.py).
The exact observed-layer crosswalk is also available in
[`curation/existing_data/scripts/crosswalks/prism.py`](curation/existing_data/scripts/crosswalks/prism.py).

### 6. General Social Survey Personas (75,699)

This product standardizes **75,699 respondents** from the NORC General Social
Survey 1972-2024 cumulative release 3. It uses no LLM. A declarative crosswalk
maps 18 coded survey variables into the exact observed layer; normalization
emits each observed value as `direct` with confidence 1.0 and fills every other
schema dimension as `null` / `unsupported`.

The result has five gzip JSONL shards. Every row contains `user_id`, 1,290
ordered `fields`, and `observed`; the average respondent has about 14.6 direct
dimensions. All **75,699 user IDs are unique**, and the manifest reports zero
validation errors or warnings. Use is subject to the
[NORC GSS data terms](https://gss.norc.org/us/en/gss/get-the-data.html).

The artifacts are on
[`MatrAIx2026/Existing_Data`](https://huggingface.co/datasets/MatrAIx2026/Existing_Data/tree/main/gss)
and are downloaded locally under `human_extraction/data/gss/hf_main/`, from HF
commit `83f8eb3420b12ebccfa97771a8dccceccb1e3cad`. All five compressed HF LFS
hashes, manifest-pinned uncompressed hashes, per-shard row counts, global user
uniqueness, and 1,290-field ordering have been verified.

The available rule-based machinery is implemented in
[`curation/existing_data/scripts/crosswalk_engine.py`](curation/existing_data/scripts/crosswalk_engine.py),
with the PRISM mapping as a worked crosswalk example. The artifact manifest
identifies its source-specific GSS mapping as `cw_gss_raw`, but that crosswalk is
not currently tracked on this branch; retain the downloaded manifest with the
data until that reproducibility gap is closed.

### 7. Real Human Survey Personas (508)

This dataset contains survey personas for **508 confirmed real people**. The
canonical local artifact is
`human_extraction/data/matraix_persona_1m_public_release/Real Human Survey/merged_personas_508.jsonl`.
It contains one flattened persona per line, with all 1,290 schema fields in a
consistent order. Unanswered survey fields remain `null`.

The artifact has been validated for row count, JSON structure, field count, and
field ordering. Additional data notes are in
[`human_extraction/README.md`](human_extraction/README.md).

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
