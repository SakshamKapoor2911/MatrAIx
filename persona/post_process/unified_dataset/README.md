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
| Initial partial-snapshot upload | `33714427` | Cancelled after 2:31:21 to remove the CLI token argument |
| First secured upload resume | `33777486` | Cancelled after 1:07 for remote legacy-data cleanup |
| Secured upload completion | `33778360` | Completed in 5:36:53 with exit code 0 |

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

Hugging Face locations:

```text
primary mirror: https://huggingface.co/datasets/MatrAIx/Persona8B/tree/main
original upload: https://huggingface.co/datasets/MatrAIx2026/Persona8B/tree/unified-8.4b
```

The dedicated revision prevents this physical Parquet snapshot from being
mixed with the repository's earlier 1B raw-code publication on `main`.
Legacy raw-code shards and manifests inherited by this revision were removed in
Hugging Face commit `3c67684566e1cd146e29a0613d8b6ee66580a4bb`. The revision is
reserved for this physical Parquet snapshot and its release metadata.

Target URL:

```text
https://huggingface.co/datasets/MatrAIx/Persona8B/tree/main
```

Authentication was verified as the `MatrAIx` Hugging Face identity before job
submission. Tokens are provided through the environment and must never be
written into source, manifests, logs, or chat.

## Upload progress log

### 2026-07-21 01:35 EDT

- Current upload job: `33778360` on `seas_compute`, requesting one node, eight
  CPUs, 16 GB memory, and eight Hugging Face upload workers.
- Current scheduler state: `PENDING (Priority)`; the secured resume has not
  started and has no stdout or stderr yet.
- Cleaned remote revision: 826 committed files and 199,975,268 bytes.
- Current Parquet progress: 256 committed files totaling 198,832,257 bytes,
  all under `data/amazon/`.
- Metadata already committed: release README, manifest, code schema, 565 task
  reports, submission metadata, and `.gitattributes`.
- Legacy cleanup: 20 inherited raw-code shards plus old manifests and run notes
  (about 404 GB) were removed from `unified-8.4b` in Hugging Face commit
  `3c67684566e1cd146e29a0613d8b6ee66580a4bb`.
- Initial job `33714427` spent about two hours hashing the full 3.18 TB payload,
  then ran eight concurrent uploads. Its first eight approximately 1.88 GB
  synthetic transfers reached 100% locally but were not committed before that
  job was cancelled, so they are not counted as remote completion. The local
  `upload-large-folder` cache is retained for resume.
- Observed aggregate network throughput during that first synthetic batch was
  approximately 10-15 MB/s. At that rate, 3.18 TB requires roughly 2.5-3.7
  days of transfer time, excluding queue time and retries. The three-day Slurm
  wall time may therefore require at least one resumable resubmission.
- One HTTP 502 was observed and retried automatically; no unrecovered upload
  exception was recorded.
- Credential hardening: `jobs/upload.job` now relies on the `HF_TOKEN`
  environment variable and does not place a token in the process command line.
  The separate token previously used by the initial job should be revoked and
  rotated because it was visible in that process's arguments.

### 2026-07-21 02:55 EDT

- Secured resume job `33778360` started at 02:37 EDT and has run for about 17
  minutes on one node with eight CPUs and eight upload workers.
- The resumable cache avoided repeating the full hash pass: all 2,734 local
  files are already hashed, covering the complete 3.2 TB upload root.
- Hugging Face uploader state reports 373 of 2,165 Parquet files pre-uploaded,
  totaling 16.3 GB. Seven workers are actively pre-uploading and one is waiting.
- The dynamic multipart display shows 119 of 127 files in the current processing
  set and approximately 211/458 GB traversed within that set. These values
  include in-progress/resumed multipart work and are not treated as committed
  repository bytes.
- The authoritative remote revision currently contains 826 committed files and
  199,975,268 bytes. This includes 256 Amazon Parquet files totaling 198,832,257
  bytes plus README, manifest, schema, reports, submission metadata, and
  `.gitattributes`.
- No new synthetic Parquet commit is visible remotely yet. Large LFS/Xet files
  become visible only after their multipart upload and repository commit finish,
  so pre-upload progress can advance substantially before remote committed bytes
  change.
- Current job logs contain no unrecovered exception or new rate-limit failure.
  Continue monitoring both the uploader counters and the remote revision rather
  than estimating progress from remote committed bytes alone.

### 2026-07-22: `MatrAIx/Persona8B` mirror verification

- Dedicated environment credential `HF_TOKEN_persona8b` was verified with the
  `MatrAIx` Hugging Face identity and write access to `MatrAIx/Persona8B`.
- The target `main` revision already contains the complete accepted snapshot, so
  another 3.18 TB network transfer was not submitted.
- All 2,734 local payload files are present remotely with identical paths and
  byte sizes. The only extra remote file is the expected `.gitattributes`.
- All 2,165 Parquet LFS objects were compared by SHA-256 using the local
  `upload-large-folder` cache and remote LFS metadata: 2,165 matches, zero
  missing paths, zero extra data paths, and zero hash mismatches.
- Verified Parquet bytes: 3,184,579,171,356. The remote data subtree contains
  exactly 2,165 files: 1,700 synthetic and 465 human/survey Parquet files.
- Top-level `README.md`, `manifest.json`, `persona_codes.schema.json`, and
  `submission.json` also have byte-identical SHA-256 hashes locally and remotely.
- The target's upload history shows the final `upload-large-folder` commit at
  2026-07-21 12:14 UTC. The target is therefore treated as a complete verified
  mirror rather than retransmitted redundantly.

## Run and monitor

```bash
cd /n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx

squeue -j 33778360 -o '%.18i %.30j %.14P %.10T %.10M %R'
sacct -j 33778360 -X \
  --format=JobID,JobName,State,ExitCode,Elapsed,Start,End

cat persona/post_process/unified_dataset/results/persona8b_8_4b_20260720/manifest.json

tail -n 100 \
  persona/post_process/unified_dataset/jobs/sbatch_logs/persona8b_upload_partial_33778360.out
tail -n 100 \
  persona/post_process/unified_dataset/jobs/sbatch_logs/persona8b_upload_partial_33778360.err
```

Array tasks write through temporary Parquet files and atomic reports. Failed or
preempted tasks can be resubmitted by array index without changing successful
outputs. The upload command is resumable and stores its local progress metadata
under the materialized folder.

Upload job `33778360` completed successfully. If a future mirror repair is
needed, resubmit [`jobs/upload.job`](jobs/upload.job) with the desired `REPO_ID`
and `REVISION`; `hf upload-large-folder` reuses its local cache and server-side
LFS/Xet objects. Do not rerun the materialization pipeline to repair a mirror.

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
- `MatrAIx2026/Persona8B` uses `unified-8.4b`; the verified
  `MatrAIx/Persona8B` mirror intentionally uses `main`.
- Do not delete source data, rejection bitmaps, reports, or completed Parquet
  shards while upload is active.
- Both documented Hugging Face locations are complete and manifest-verified as
  of 2026-07-22.