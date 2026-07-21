# Unified Persona8B Dataset

This pipeline materializes the post-filter, post-dedup persona corpus as a
physical Parquet dataset. Every retained persona is stored in the output; the
dataset does not depend on the original 10B synthetic codes or rejection
bitmaps at read time.

This README is also the operational handoff. For a file-by-file implementation
map, see [`CODE_INDEX.md`](CODE_INDEX.md).

## Published corpus

The accepted 2026-07-20 snapshot contains **8,399,989,719 rows**. This is
10,289 rows below the strict 8,400,000,008-row production target because Wiki
materialization task 73 failed. The snapshot is intentionally published as-is;
it must not be described as a complete 8.4B-row release.

| Source | Successful reports | Rows | Files | Bytes |
|---|---:|---:|---:|---:|
| synthetic | 100 | 8,397,777,004 | 1,700 | 3,158,256,249,011 |
| wiki | 199 | 1,936,153 | 199 | 25,786,429,460 |
| amazon | 256 | 97,915 | 256 | 198,832,257 |
| stackoverflow | 3 | 113,120 | 3 | 317,521,873 |
| prism | 1 | 1,487 | 1 | 8,318,594 |
| gss | 5 | 63,532 | 5 | 11,607,275 |
| real_human_survey | 1 | 508 | 1 | 212,886 |
| **Total** | **565** | **8,399,989,719** | **2,165** | **3,184,579,171,356** |

The omitted Wiki task had 10,630 source rows and would have retained 10,289
rows after applying the quality and deduplication bitmaps. It failed while
converting a numeric-string confidence value such as `"0.7"` to the Arrow
`float32` grounding field. Current code normalizes numeric-string confidence,
but the failed task was not rerun for this snapshot.

The failed task left `wiki-0073-part-0000.parquet.part` but no atomic report.
That partial file was moved outside the upload root. Every accepted Parquet
file has a successful report, and all 2,165 Parquet footers were checked against
the unified Arrow schema before upload metadata was generated.

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

| Stage | Slurm job | Final state |
|---|---:|---|
| Synthetic materialization (100 tasks, max 25 concurrent) | `33386504` | Completed |
| Human materialization (465 tasks, max 50 concurrent) | `33386505` | 464 completed, task 73 failed |
| Real Human Survey | `33386507` | Completed |
| Strict finalization | `33386509` | Cancelled by failed dependency |
| Original Hugging Face upload | `33386510` | Cancelled by failed dependency |
| Accepted partial-snapshot upload | `33714427` | Submitted; initially pending for priority |

Synthetic materialization, 464 of 465 human tasks, and the Real Human Survey
completed. Human task 73 failed; the dependency-bound strict finalizer and
original upload jobs were consequently cancelled without starting. For the
accepted partial release, metadata is generated from the 565 successful atomic
task reports and the 2,165 Parquet files they reference. The stale task-73
`.parquet.part` file is excluded from upload.

The strict finalizer intentionally still requires exactly 8,400,000,008 rows
and will reject this snapshot. The accepted partial release instead has a
separate `manifest.json` with:

```text
release_status: incomplete_accepted_as_is
rows:           8,399,989,719
missing_rows:   10,289
files:          2,165
bytes:          3,184,579,171,356
```

Hugging Face target:

```text
repo: MatrAIx2026/Persona8B
revision: unified-8.4b
```

The dedicated revision prevents this physical Parquet snapshot from being
mixed with the repository's earlier 1B raw-code publication on `main`.

Target URL:

```text
https://huggingface.co/datasets/MatrAIx2026/Persona8B/tree/unified-8.4b
```

Authentication was verified as the `MatrAIx` Hugging Face identity before job
submission. Tokens are provided through the environment and must never be
written into source, manifests, logs, or chat.

## Run and monitor

```bash
cd /n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx

squeue -j 33714427 -o '%.18i %.30j %.14P %.10T %.10M %R'
sacct -j 33714427 -X \
  --format=JobID,JobName,State,ExitCode,Elapsed,Start,End

cat persona/post_process/unified_dataset/results/persona8b_8_4b_20260720/manifest.json

tail -n 100 \
  persona/post_process/unified_dataset/jobs/sbatch_logs/persona8b_upload_partial_33714427.out
tail -n 100 \
  persona/post_process/unified_dataset/jobs/sbatch_logs/persona8b_upload_partial_33714427.err
```

Array tasks write through temporary Parquet files and atomic reports. Failed or
preempted tasks can be resubmitted by array index without changing successful
outputs. The upload command is resumable and stores its local progress metadata
under the materialized folder.

If upload job `33714427` fails or reaches its three-day wall time, resubmit
[`jobs/upload.job`](jobs/upload.job) with the same `OUTPUT`, `REPO_ID`, and
`REVISION`. `hf upload-large-folder` reuses its local cache and skips completed
work. Do not rerun the full materialization pipeline merely to resume upload.

## Production inputs

| Input | Path |
|---|---|
| 10B packed synthetic source | `persona/synthesis/generated/full_dag_10b_20260703/shards/` |
| Final synthetic rejection bitmaps | `persona/post_process/deduplication/results/final_8_4b_20260719/bitmaps/` |
| Synthetic transfer overlay | `persona/post_process/deduplication/results/synthetic_transfer_500_20260720/` |
| Human source manifest | `persona/post_process/deduplication/jobs/manifests/human_minhash_20260719/human_tasks.jsonl` |
| Human quality bitmaps | `persona/post_process/quality_filter/results/full_filter_20260719/` |
| Human deduplication bitmaps | `persona/post_process/deduplication/results/human_minhash_20260719/dedup_threshold_0.95/` |
| Real Human Survey | `persona/human_extraction/data/matraix_persona_1m_public_release/Real Human Survey/merged_personas_508.jsonl` |

## Operational cautions

- Do not describe this accepted snapshot as exactly 8.4B rows.
- Do not upload the quarantined task-73 `.parquet.part` file.
- Do not upload this physical snapshot to `main`; use `unified-8.4b`.
- Do not delete source data, rejection bitmaps, reports, or completed Parquet
  shards while upload is active.
- Do not declare the upload complete until job `33714427` succeeds and the
  dataset files are visible on the Hugging Face revision.