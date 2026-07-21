# Unified Persona8B Code Index

All code written for the physical 8.4B Persona8B materialization pipeline lives
under:

```text
persona/post_process/unified_dataset/
```

Tests live under:

```text
tests/persona/post_process/
```

## Python implementation

| File | Responsibility |
|---|---|
| [`schema.py`](schema.py) | Defines the unified Arrow schema, 1,290-field categorical codec, packed attribute representation, null bitmap, and lossless off-schema overrides. |
| [`materialize.py`](materialize.py) | Streams retained synthetic, human-extracted, and Real Human Survey personas into physical Parquet shards. Applies all quality, deduplication, and transfer-exclusion bitmaps. |
| [`finalize.py`](finalize.py) | Enforces exact per-source and global row counts, verifies every Parquet schema and row count, calculates final byte size, and writes `manifest.json`, the dataset card, and the codebook. |
| [`status.py`](status.py) | Reports Slurm states, completed task reports, rows, bytes, description coverage, and final-manifest readiness. |
| [`monitor_events.py`](monitor_events.py) | Event-driven live monitor for reports, Slurm logs, finalization, and upload completion; uses Linux inotify without polling sleeps. |
| [`__init__.py`](__init__.py) | Declares the Python package. |

## Slurm and upload jobs

All production job definitions are in [`jobs/`](jobs/).

| File | Responsibility |
|---|---|
| [`jobs/launch.sh`](jobs/launch.sh) | Submits the complete dependency chain and records all job IDs in `submission.json`. |
| [`jobs/materialize_synthetic.job`](jobs/materialize_synthetic.job) | Runs a 100-task synthetic array. Each task reads one 100M-row compressed source shard and writes only retained physical rows. |
| [`jobs/materialize_human.job`](jobs/materialize_human.job) | Runs a 465-task array over Wiki, Amazon, Stack Overflow, PRISM, and GSS source shards. Applies quality and human MinHash-dedup rejection bitmaps. |
| [`jobs/materialize_survey.job`](jobs/materialize_survey.job) | Converts the 508 Real Human Survey rows into the same Parquet schema. |
| [`jobs/finalize.job`](jobs/finalize.job) | Runs strict final validation after all materialization tasks succeed. |
| [`jobs/upload.job`](jobs/upload.job) | Creates the `unified-8.4b` Hugging Face revision and performs a resumable eight-worker upload to `MatrAIx2026/Persona8B`. |

The current submitted production jobs are:

| Stage | Job ID |
|---|---:|
| Synthetic materialization | `33386504` |
| Human materialization | `33386505` |
| Real Human Survey | `33386507` |
| Finalization | `33386509` |
| Hugging Face upload | `33386510` |

## Tests

| File | Coverage |
|---|---|
| [`tests/persona/post_process/test_unified_dataset_schema.py`](../../../tests/persona/post_process/test_unified_dataset_schema.py) | Packed attribute width, null preservation, off-schema override preservation, and fixed-size Arrow binary construction. |

Run the focused tests with:

```bash
/n/home08/xiaominli/.conda/envs/env05/bin/python -m pytest -q \
  tests/persona/post_process/test_unified_dataset_schema.py
```

## Production inputs

The materializer reads the following immutable or validated artifacts:

| Input | Path |
|---|---|
| 10B packed synthetic source | `persona/synthesis/generated/full_dag_10b_20260703/shards/` |
| Final synthetic rejection bitmaps | `persona/post_process/deduplication/results/final_8_4b_20260719/bitmaps/` |
| 500-row synthetic transfer overlay | `persona/post_process/deduplication/results/synthetic_transfer_500_20260720/` |
| Human source manifest | `persona/post_process/deduplication/jobs/manifests/human_minhash_20260719/human_tasks.jsonl` |
| Human quality bitmaps | `persona/post_process/quality_filter/results/full_filter_20260719/` |
| Human deduplication bitmaps | `persona/post_process/deduplication/results/human_minhash_20260719/dedup_threshold_0.95/` |
| Real Human Survey | `persona/human_extraction/data/matraix_persona_1m_public_release/Real Human Survey/merged_personas_508.jsonl` |

## Output

The complete physical dataset is written under:

```text
persona/post_process/unified_dataset/results/persona8b_8_4b_20260720/
```

Expected structure:

```text
data/
  synthetic/shard_XXXX/*.parquet
  wiki/*.parquet
  amazon/*.parquet
  stackoverflow/*.parquet
  prism/*.parquet
  gss/*.parquet
  real_human_survey/*.parquet
reports/*.json
persona_codes.schema.json
manifest.json
README.md
submission.json
```

`manifest.json` is created only after all **8,400,000,008** rows pass strict
validation. Its `bytes` field is the authoritative final dataset size.

## Execution flow

```text
launch.sh
  -> synthetic array (100 tasks)
  -> human array (465 tasks)
  -> Real Human Survey task
  -> finalize.py after all materialization succeeds
  -> upload.job after strict finalization succeeds
```

The final Hugging Face destination is:

```text
https://huggingface.co/datasets/MatrAIx2026/Persona8B/tree/unified-8.4b
```