# Unified Persona8B Production Handoff

Last updated: **2026-07-20**

This is the operational handoff for materializing and uploading the complete
post-dedup Persona8B corpus. A new agent should read this file first, then
[`README.md`](README.md) for the dataset contract and [`CODE_INDEX.md`](CODE_INDEX.md)
for the implementation map.

## Goal

Create a real physical copy of all **8,400,000,008 retained personas** as
sharded Parquet. The final dataset must not require the original 10B synthetic
source, rejection bitmaps, or pointer/filter overlays at read time. Upload the
validated result to:

```text
repo: MatrAIx2026/Persona8B
revision: unified-8.4b
```

## Current status

The complete Slurm dependency chain was submitted on 2026-07-20 and then moved
in place to `seas_compute` at the user's request. Job IDs and dependencies were
preserved.

| Stage | Job ID | Tasks | Current state at last update |
|---|---:|---:|---|
| Synthetic materialization | `33386504` | 100, max 25 concurrent | All `PENDING (Priority)` |
| Human materialization | `33386505` | 465, max 50 concurrent | All `PENDING (Priority)` |
| Real Human Survey | `33386507` | 1 | `PENDING (Priority)` |
| Strict finalizer | `33386509` | 1 | `PENDING (Dependency)` |
| Hugging Face upload | `33386510` | 1 | `PENDING (Dependency)` |

At the last check:

```text
completed reports: 0
Parquet files:     0
output bytes:      12,645 (submission metadata/directories only)
manifest.json:     absent
non-empty stderr:  none
```

The scheduler reason is plain `Priority`, not QOS, account, memory, or resource
configuration failure. `seas_compute` was busy when checked. Do not cancel and
resubmit merely because tasks wait several minutes.

### Live production update and recovered incident

After the initial status above, materialization started. Survey task `33386507`
completed successfully with 508 rows. Twenty-five synthetic tasks began running
and produced hundreds of GB of Parquet output.

The first Wiki tasks exposed two source-format variations not covered by the
initial samples:

1. Wiki field lists can be sparse or contain legacy extras instead of exactly
   1,290 objects (observed lengths included 1,242, 1,288, 1,290, and 1,291).
2. Some `confidence` values are numeric strings such as `"0.8"` rather than JSON
   numbers.

The production code was repaired on 2026-07-20:

- Missing current fields are null-filled through `null_bitmap`.
- Unknown and duplicate raw field objects are preserved losslessly in
  `metadata_json._unmapped_fields`.
- Numeric-string confidence values are normalized to float.
- Any non-numeric raw confidence is retained in
  `metadata_json._non_numeric_confidence`.
- Six focused tests pass, including sparse fields and confidence normalization.
- A real task-1 Wiki smoke with 20 rows completed successfully; all 20 rows had
  null bitmaps and overrides, and one retained an unmapped legacy field object.

Eighty human tasks that failed before the repair were requeued in place under
the same array job, preserving the finalizer dependency. Live failed tasks were
zero immediately after requeue. At a later progress check, at least 13 Wiki
tasks had completed successfully after the fix, each with about 10.1K-10.5K
retained rows.

The original jobs were submitted while the shell cwd was
`/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch`, so their current Slurm logs are
actually under:

```text
/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/sbatch_logs/
```

The non-empty human stderr files there with timestamps around 02:43-02:52 are
the known pre-fix failures. Do not treat them as current failures without
checking task state, report existence, and log modification time. `launch.sh`
has since been changed to submit from its own jobs directory, so future runs
will place logs under `unified_dataset/jobs/sbatch_logs/` as documented.

## First commands for the next agent

Run these before changing anything:

```bash
cd /n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx

squeue -j 33386504,33386505,33386507,33386509,33386510 -r \
  -o '%.18i %.22j %.14P %.10T %.10M %R'

PYTHONPATH=$PWD /n/home08/xiaominli/.conda/envs/env05/bin/python \
  persona/post_process/unified_dataset/status.py

# Long-running event-driven monitor; exits only after upload completes:
PYTHONPATH=$PWD /n/home08/xiaominli/.conda/envs/env05/bin/python \
  persona/post_process/unified_dataset/monitor_events.py

find persona/post_process/unified_dataset/jobs/sbatch_logs \
  -type f -name 'persona8b_*.err' -size +0c -print

# Current production submission used this log directory:
find /n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/sbatch_logs \
  -type f -name 'persona8b_*.err' -size +0c -print
```

If materialization has begun, also run:

```bash
ROOT=persona/post_process/unified_dataset/results/persona8b_8_4b_20260720
find "$ROOT/reports" -name '*.json' | wc -l
find "$ROOT/data" -name '*.parquet' | wc -l
du -sh "$ROOT"
```

## Non-negotiable row accounting

The strict finalizer encodes these production counts:

| Source | Required rows |
|---|---:|
| synthetic | 8,397,777,004 |
| wiki | 1,946,442 |
| amazon | 97,915 |
| stackoverflow | 113,120 |
| prism | 1,487 |
| gss | 63,532 |
| real_human_survey | 508 |
| **Total** | **8,400,000,008** |

Do not change these counts without reconciling against
`persona/post_process/deduplication/README.md` and the production summaries.
The synthetic count includes the 500-row post-dedup transfer exclusion. Shard 0
must apply both the baseline rejection bitmap and the transfer overlay.

## Format decision and rationale

All rows share one Arrow schema. The central representation is compact but
fully physical:

- `attributes`: 645 fixed bytes, two 4-bit categorical values per byte.
- `null_bitmap`: optional 162 fixed bytes for missing human/survey values.
- `attribute_overrides`: sparse exact storage for values absent from the
  current codebook, such as legacy `age_bracket="65+"`.
- `source`, `source_row_index`, and `source_record_id`: provenance columns.
- `has_description` and `descriptions`: explicit natural-language feature and
  sparse field-level text.
- `grounding`: sparse evidence, confidence, and assignment type.
- `metadata_json`: lossless source-specific metadata.

The compact categorical representation is necessary. Expanding 8.4B rows into
1,290 string columns would produce an impractically large dataset. Each retained
persona is still a complete physical row; decoding requires only the included
`persona_codes.schema.json`, not any original source data.

## Description behavior

- Synthetic rows have no natural-language descriptions.
- Human-extracted rows may have field-level descriptions and grounding.
- Real Human Survey rows have direct attributes but no generated descriptions.
- `has_description` is a first-class Boolean column so consumers can filter or
  stratify by NL availability.

Smoke inspection found description coverage varies by source, as expected.
For example, a 20-row Amazon smoke sample had descriptions on all 20 rows. The
pipeline records exact per-source `description_rows`, `grounding_rows`, and
`override_rows` in task reports and the final manifest.

## Validation already completed

Focused tests:

```text
tests/persona/post_process/test_unified_dataset_schema.py
3 passed
```

The smoke dataset is under:

```text
persona/post_process/unified_dataset/results/smoke_20260720/
```

Validated smoke outputs:

| Source | Rows written | Result |
|---|---:|---|
| synthetic | 7,945 retained from first 10,000 source rows | Passed bitmap filtering and packed-byte write |
| amazon | 20 | Passed descriptions, grounding, metadata, and legacy override handling |
| real_human_survey | 508 | Passed flattened-to-codebook conversion and null handling |

All three smoke Parquet files have exactly one Arrow schema. Smoke inspection
also proved the override column is necessary: one Amazon row and two Survey rows
contained values outside the current synthetic codebook and were preserved
losslessly.

## Expected size

The synthetic smoke Parquet compressed to about 377 bytes per retained row.
This implies roughly **3.17 TB** for the synthetic body. Human descriptions,
grounding, metadata, Parquet footers, and compression variation lead to a
working estimate of **3.2-3.7 TB** for the final dataset.

This estimate is not authoritative. After all tasks finish, `finalize.py` sums
the actual Parquet file sizes and writes the exact byte count to:

```text
persona/post_process/unified_dataset/results/persona8b_8_4b_20260720/manifest.json
```

Report that exact value to the user after finalization.

## Output and atomicity

Production root:

```text
persona/post_process/unified_dataset/results/persona8b_8_4b_20260720/
```

Tasks write `*.parquet.part`, close the writer, then atomically rename to
`*.parquet`. Each task writes its JSON report atomically only after successful
completion. Therefore:

- A report means that task completed.
- A `.parquet.part` file means the task was interrupted.
- Completed Parquet files and reports should not be deleted during retry.
- Job scripts remove stale `.parquet.part` files for their own output prefix.

Synthetic output files contain at most 5M rows. Human inputs retain their task
boundaries and normally produce one output file each.

## Failure diagnosis and recovery

### Find failed array indices

```bash
sacct -X -j 33386504,33386505,33386507,33386509,33386510 \
  --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS
```

Inspect logs:

```bash
grep -RIl . persona/post_process/unified_dataset/jobs/sbatch_logs/*.err
tail -n 100 persona/post_process/unified_dataset/jobs/sbatch_logs/<log>.err
```

For the current job IDs, substitute
`/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/sbatch_logs/` because of the
submission-cwd detail documented above.

### Retry synthetic indices

Prefer Slurm requeue if the array task is still known and requeueable:

```bash
scontrol requeue 33386504_<INDEX>
```

If a new array submission is required, preserve the same exported paths used by
[`jobs/launch.sh`](jobs/launch.sh). Do not rerun the entire 100-task array merely
for one failure.

### Retry human indices

```bash
scontrol requeue 33386505_<INDEX>
```

The human array index is the `task_index` in:

```text
persona/post_process/deduplication/jobs/manifests/human_minhash_20260719/human_tasks.jsonl
```

### Finalizer failure

Do not bypass a finalizer count or schema error. Compare task reports against
the required counts, locate missing/duplicate report prefixes, repair only the
failed tasks, then resubmit `jobs/finalize.job` with the same `OUTPUT` and
`SCHEMA` environment variables.

### Upload failure

Upload uses `hf upload-large-folder`, which persists resumable metadata under
the local output. Rerunning the upload job should reuse completed hashing and
uploads.

Before retrying, verify authentication without printing the token:

```bash
source ~/.bashrc
export HF_TOKEN="${HF_TOKEN_matraix:-${HF_TOKEN:-}}"
hf auth whoami
```

Expected identity at submission time:

```text
MatrAIx
orgs: MatrAIx2026
```

Never write the token into source files, manifests, logs, or chat. The upload
job receives the environment through Slurm export and creates the
`unified-8.4b` branch idempotently before upload.

## Final acceptance checklist

The next agent should not declare the task complete until all are true:

1. `33386504`, `33386505`, and `33386507` completed successfully.
2. Exactly 566 materialization reports exist: 100 synthetic, 465 human, and 1
   Survey report.
3. `33386509` completed and `manifest.json` exists.
4. Manifest source counts equal the table in this document.
5. Manifest total equals exactly `8,400,000,008`.
6. Every Parquet file has the unified Arrow schema.
7. Final exact bytes and human-readable size are reported to the user.
8. `33386510` completed successfully.
9. The dataset is visible at the `unified-8.4b` Hugging Face revision.
10. Repository documentation is updated from "in progress" to "complete" with
    exact size, file count, description coverage, upload URL, and completion
    date.

## What not to do

- Do not use the original 10B count as the final retained count.
- Do not omit the 500-row synthetic transfer overlay.
- Do not silently map legacy `65+` to one current age band.
- Do not expand all attributes to strings for 8.4B rows.
- Do not upload to `main`; use `unified-8.4b` unless the user explicitly changes
  the destination strategy.
- Do not delete source data, dedup bitmaps, smoke output, or completed production
  shards while the pipeline is active.
- Do not mark the task finished while jobs are merely queued or running.