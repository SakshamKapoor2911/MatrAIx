# Human Extraction Data Layout

This directory contains large, git-ignored inputs, checkpoints, and generated
persona artifacts. Only this README and `.gitignore` are tracked.

```text
data/
  wiki/
    source/                  Downloaded Wiki profile SQLite input.
    extraction_v1/           Wiki Qwen extraction shards and checkpoints.
    diagnostics/             Benchmark outputs, plots, logs, and environment records.
    subscription_pr51/       Downloaded strong-model Wiki batch and rich source revision.
    replacements/            Applied replacement manifests and rollback backups.
  amazon/                    Amazon cohort, extraction, and publication snapshots.
  prism/
    hf_main/                 Validated PRISM extraction from Existing_Data main.
  gss/
    hf_main/                 Validated GSS extraction from Existing_Data main.
  stackoverflow/
    hf_pr55/                 Revision-pinned download of Existing_Data PR #55.
  matraix_persona_1m_public_release/
    Real Human Survey/       108 public survey-submitted personas.
```

## MatrAIx Persona 1M Public Release

`matraix_persona_1m_public_release/` is a revision-pinned snapshot of the public
Hugging Face dataset `MatrAIx2026/MatrAIx_Persona_1M_Public_Release` at commit
`46e9c31ba34d21bea7d690e5159624e1006d66e4`.

The snapshot currently contains 108 files under `Real Human Survey/`.
`Extracted Persona Data/` and `Synthetic Persona Data/` are empty placeholders
in the pinned upstream revision. A local derived file,
`Synthetic Persona Data/synthetic_personas_500.jsonl`, adds 500 explicitly
synthetic personas exported from the accepted 10B synthetic pool. Validation
confirmed that all 108 survey files are valid JSON,
are continuously numbered `Human0001.json` through `Human0108.json`, and contain
the same 1,290 dimension IDs in a consistent order. These are flat dimension
maps rather than the human-extraction pipeline's `fields` list representation.
`SHA256SUMS` records one checksum per survey file, and `SNAPSHOT.json` records
the source repository, immutable revision, and local derived addition.

The 500 transferred synthetic rows remain identified as synthetic. They are
logically removed from their source pool by OR-ing
`post_process/deduplication/results/synthetic_transfer_500_20260720/`
`shard_0000.transfer.reject.bits` with the accepted shard-0 rejection bitmap.
The original packed source remains immutable; the transfer manifest records the
source row IDs, checksums, and derived corpus count of 8,399,999,500.

## Wiki

- `wiki/source/matraix_wiki_profiles_20260601_v1.sqlite` is the 2,125,897-row
  input profile database.
- `wiki/extraction_v1/shard_XXXX.jsonl` contains the 200 output shards. These
  files are resumable checkpoints as well as production outputs.
- `wiki/matraix_wiki_profiles_20260601_v1.sqlite` is a compatibility symlink to
  the file under `wiki/source/`.

Rows 0-1199 in `wiki/extraction_v1/shard_0000.jsonl` were replaced with the
subscription/API extraction from `MatrAIx2026/Existing_Data` PR #51. The local
source area contains both:

- `subscription_pr51/`: the current flattened PR head at
  `6c2de679838741eb7530bb1200a7fcb115a3457f`;
- `subscription_pr51/rich_0647ae3f/`: the immutable rich extraction used for
  conversion, SHA-256
  `836d01fb31b94fd27592916ffdb1879f83babfb0f25408c9352e4aca546379d6`.

The rich artifact was used because it retains confidence, evidence, and
assignment type. The current PR head keeps only sparse values. The applied
conversion and original Qwen rollback data are under
`wiki/replacements/subscription_pr51_batch_1/`:

- `replacement_manifest.json` records source/schema hashes, model counts,
  conversion statistics, and shard hashes before and after replacement.
- `original_qwen_rows_0000000_0001199.jsonl.gz` contains the 1,200 original
  rows; its SHA-256 is
  `559b19ee490e8fe17c5b0bbd92afaf021f906c9dd5cb2d7271bfe16593c12923`.

## Amazon

The Amazon extraction is complete. The directory contains the frozen 100K
cohort, completed H200 continuation shards, smoke outputs, and Hugging Face
publication snapshots. `extraction_resume_20260717/EXTRACTION_COMPLETE.json`
records completion of all 167 continuation buckets and a 100,000-user global
total.

Independent validation combines the latest 167 continuation buckets with the
89 completed source buckets retained in the frozen snapshot. All 256 bucket
sets exactly match the authoritative 100K selection; every row is valid JSON,
uses `prompt_variant=medium_b`, has the correct bucket, and contains exactly
1,290 fields. `hf_snapshot_20260719/` remains a 91,307-user in-progress snapshot
and must not be treated as the final full publication artifact.

## Stack Overflow

`stackoverflow/hf_pr55/` contains the raw and PR #53-compatible 2023-2025
Stack Overflow survey persona artifacts downloaded from the pinned
`refs/pr/55` revision of `MatrAIx2026/Existing_Data`.

## PRISM

`prism/hf_main/` contains the source README, manifest, and one gzip JSONL shard
for 1,500 PRISM Alignment participants. The download resolved
`MatrAIx2026/Existing_Data` `main` to commit
`83f8eb3420b12ebccfa97771a8dccceccb1e3cad`.

Full-stream validation confirmed the compressed HF LFS SHA-256, the
manifest-pinned uncompressed SHA-256, 1,500 rows and unique users, and exactly
1,290 consistently ordered field IDs per row.

## GSS

`gss/hf_main/` contains the source README, manifest, and five gzip JSONL shards
for 75,699 General Social Survey respondents. It comes from the same pinned HF
commit as PRISM.

Full-stream validation confirmed every compressed and uncompressed SHA-256,
the manifest's per-shard counts (15,140, 15,140, 15,140, 15,140, and 15,139),
75,699 globally unique users, and exactly 1,290 consistently ordered field IDs
per row.

Historical `bench_*`, `sweep_*`, environment backup, and log files are grouped
under `wiki/diagnostics/`.