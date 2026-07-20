# Unified Persona8B Dataset

This pipeline materializes the post-filter, post-dedup persona corpus as a
physical Parquet dataset. Every retained persona is stored in the output; the
dataset does not depend on the original 10B synthetic codes or rejection
bitmaps at read time.

For continued work, start with [`HANDOFF.md`](HANDOFF.md). For a file-by-file
implementation map, see [`CODE_INDEX.md`](CODE_INDEX.md).

## Production corpus

| Source | Retained rows |
|---|---:|
| synthetic | 8,397,777,004 |
| wiki | 1,946,442 |
| amazon | 97,915 |
| stackoverflow | 113,120 |
| prism | 1,487 |
| gss | 63,532 |
| real_human_survey | 508 |
| **Total** | **8,400,000,008** |

Production output:

```text
results/persona8b_8_4b_20260720/
  data/<source>/**/*.parquet
  reports/*.json
  persona_codes.schema.json
  manifest.json
  README.md
```

The synthetic data is written in files of at most 5M rows. Human source tasks
retain their production shard boundaries.

## Unified columns

- `source`: data product identifier.
- `source_row_index`: stable row index in the source product.
- `source_record_id`: source-specific identifier when available.
- `attributes`: fixed 645-byte vector containing two 4-bit categorical codes
  per byte for the 1,290 schema dimensions.
- `null_bitmap`: optional fixed 162-byte little-endian bitmap. Set bits mark
  null attributes; a null column value means no attributes are null.
- `attribute_overrides`: sparse lossless storage for legacy values absent from
  the current codebook. Overrides take precedence during decoding.
- `has_description`: whether the row has field-level natural-language text.
- `descriptions`: sparse `(field_index, text)` natural-language descriptions.
- `grounding`: sparse field-level evidence, confidence, and assignment type.
- `metadata_json`: source-specific metadata preserved as compact JSON.

Synthetic personas have no natural-language descriptions. Human-extracted
sources may have descriptions and grounding. The Real Human Survey has direct
attributes but no generated descriptions.

## Production run

Submitted 2026-07-20:

| Stage | Slurm job |
|---|---:|
| Synthetic materialization (100 tasks, max 25 concurrent) | `33386504` |
| Human materialization (465 tasks, max 50 concurrent) | `33386505` |
| Real Human Survey | `33386507` |
| Strict finalization | `33386509` |
| Hugging Face upload | `33386510` |

The finalizer runs only after all materialization jobs succeed. It requires the
exact per-source counts above, checks every Parquet schema and row count, and
writes the final byte size to `manifest.json`. Upload then uses the resumable
large-folder API with eight workers.

Hugging Face target:

```text
repo: MatrAIx2026/Persona8B
revision: unified-8.4b
```

The dedicated revision prevents the unified Parquet dataset from being mixed
with the repository's earlier 1B raw-code publication on `main`.

## Run and monitor

```bash
bash persona/post_process/unified_dataset/jobs/launch.sh

squeue -j 33386504,33386505,33386507,33386509,33386510 -r \
  -o '%.18i %.22j %.10T %.10M %R'

cat persona/post_process/unified_dataset/results/persona8b_8_4b_20260720/manifest.json
```

Array tasks write through temporary Parquet files and atomic reports. Failed or
preempted tasks can be resubmitted by array index without changing successful
outputs. The upload command is resumable and stores its local progress metadata
under the materialized folder.