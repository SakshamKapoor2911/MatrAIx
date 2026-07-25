# Amazon 100K Extraction — Koutian to Xiaomin Continuation (2026-07-17)

> **Completion update (2026-07-19):** the continuation finished successfully.
> `EXTRACTION_COMPLETE.json` reports 61,781 newly completed users and 100,000
> global users. Independent validation against the authoritative selection
> confirmed 256/256 exact bucket sets, 100,000 unique users, zero missing or
> extra users, valid JSON, `medium_b`, and exactly 1,290 fields per row. The
> existing 91,307-user frozen snapshot predates completion and still needs to be
> rebuilt before publishing the full 100K package.

This document records Xiaomin Li's takeover of the Amazon reviewer persona
extraction after Koutian Wu's GPU allocation ended. It supersedes
`../AMAZON_EXTRACTION_HANDOFF.md` for current status. The older document was
Xiaomin's original 2026-07-06 handoff to Koutian, when the extraction was still
0% complete.

> **Update (2026-07-17): core blocker resolved.** Koutian uploaded the exact
> production selection index to HF PR #53 and identified PR #264 as the
> authoritative `medium_b` implementation. Xiaomin verified the selection hash,
> all 103 manifest bucket counts, and the exact 61,781-user remainder. A one-user
> H200 FP8 smoke test is queued as Slurm job `32247994`; the bulk continuation
> will launch only after that smoke output passes contract checks.

## Current verified status

Source of truth: Hugging Face dataset PR #53 for
`MatrAIx2026/MatrAIx2026`:

- Revision: `refs/pr/53`
- Output prefix: `amazon/extraction_v1/qwen36/final_20260715/`
- Manifest: `amazon/extraction_v1/qwen36/final_20260715/manifest.json`
- Completed users: **38,219 / 100,000 (38.2%)**
- Remaining users reported by the manifest/handoff: **61,781**
- Buckets represented: 103
- Complete buckets: 89
- Partial buckets: 14
- Untouched buckets: 153

The completed output consists of:

- `casper_h100_medium_b/`: H100, FP8, tensor parallel size 1
- `derecho_a100_medium_b/`: A100, bf16, tensor parallel size 4

Both tranches use model `Qwen/Qwen3.6-35B-A3B`, prompt variant `medium_b`,
and the schema sanitizer introduced in repository PR #174. Each row contains
`prompt_variant: "medium_b"` and exactly 1,290 sanitized field IDs.

## Remaining buckets reported by Koutian

Partial buckets (`have / selected` from the HF manifest):

```text
0f 368/372
10 240/403
13 216/405
16 208/367
1e 360/382
22 72/400
29 344/409
2f 264/381
32 280/395
36 256/411
3d 184/395
3f 192/373
47 306/372
4d 259/401
```

Untouched buckets:

```text
30
68-ff
```

In decimal Slurm array IDs, these are:

```text
Partial: 15,16,19,22,30,34,41,47,50,54,61,63,71,77
Untouched: 48,104-255
```

These ranges must not be submitted until the exact selection index described
below is available and validated.

## What Xiaomin has prepared

An isolated runtime worktree has been created so the current main worktree and
Wiki extraction are not disturbed:

```text
/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx-amazon-resume
```

Local runtime commit:

```text
0ce88e733 Prepare exact medium_b Amazon resume runtime for H200
```

Prepared and validated components:

1. PR #174 schema-validation runner as the base.
2. Exact `medium_b` prompt copied from PR #177's comparison implementation.
   A byte-for-byte prompt comparison passes.
3. Output metadata includes `prompt_variant: "medium_b"`.
4. Single-H200 Slurm job:
   `persona/human_extraction/jobs/extract_shard_amazon_h200.job`.
5. Planned GPU configuration: 1 x H200, bf16, TP=1, `max_model_len=32768`.
6. Scheduler test passed for `seas_gpu`.
7. All 14 partial HF shards were downloaded into:

```text
/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx/
persona/human_extraction/data/amazon/extraction_resume_20260717
```

These seed files allow resume-skip by `user_id` after the correct selection
index is supplied.

No Amazon GPU continuation job has been launched yet. This is intentional: the
exact selected-user cohort is currently unavailable.

## Resolved issue: exact selection index

Koutian's continuation PR #241 originally referred to a shared file named:

```text
selected_users_100k.parquet
```

The exact file has now been uploaded to HF dataset PR #53:

```text
amazon/extraction_v1/qwen36/final_20260715/selected_users_100k.parquet
amazon/extraction_v1/qwen36/final_20260715/selected_users_100k.sha256
```

Verified production SHA-256:

```text
8a0084628f32a06f8f823126f819ef1abcc8387978b44f79eb4f923cb5e8ce12
```

Local verified copy:

```text
persona/human_extraction/data/amazon/selected_users_100k_koutian.parquet
```

Validation results: 100,000 rows, 100,000 unique `user_id`, 256 buckets; every
one of the 103 represented bucket counts matches the HF PR #53 manifest; all 14
seeded partial-shard user IDs are members of this selection; exact remainder is
61,781.

Xiaomin has a local file at:

```text
persona/human_extraction/data/amazon/selected_users_100k.parquet
```

Its SHA-256 is:

```text
44010ae855e3db95367941782f2069504b547d99002625073a513961f5e707b2
```

This local file is **not** the selection index used for Koutian's 38,219-row
run. Evidence:

| Bucket | HF completed users | Local selected users | HF/local overlap |
|---|---:|---:|---:|
| `00` | 385 | 385 | 385 |
| `10` | 240 | 394 | 19 |
| `47` | 306 | 398 | 11 |
| `4d` | 259 | 392 | 17 |

The mismatch is substantial, not a count-only formatting issue. Using Xiaomin's
local parquet would extract a different cohort for untouched buckets and would
not produce the intended 100K dataset.

## Requested from Koutian — status

The original request and current resolution status are recorded below.

### 1. Exact selection parquet — resolved

Uploaded to HF PR #53 and verified as described above. It contains:

```text
user_id
user_bucket
review_count
```

SHA-256 verified.

### 2. Exact production runner snapshot or commit — resolved for continuation

Koutian identified the required public code as:

- PR #174: portability and schema sanitizer
- PR #264: authoritative `medium_b` production implementation

The isolated runtime now applies PR #264 directly on top of PR #174. It writes
the same `prompt_variant: "medium_b"` field as the existing HF rows.

### 3. Schema revision/checksum

Provide the commit or SHA-256 of `persona/schema/dimensions.json` used during the
run. The completed rows contain 1,290 unique field IDs, but an explicit schema
fingerprint should accompany the dataset.

### 4. Final runtime flags

Confirm the final flags used for both tranches, especially:

```text
max_model_len
max_tokens
max_dims_per_chunk
batch_profiles
max_num_seqs
gpu_memory_utilization
quantization
tensor_parallel_size
```

The manifest records H100 FP8 TP=1 and A100 bf16 TP=4, but not every generation
parameter.

## Validation and launch plan after receipt

After receiving the exact selection file, Xiaomin will:

1. Verify its SHA-256 and total unique users = 100,000.
2. Recompute per-bucket selected counts and assert they match HF PR #53's
   manifest for all 103 represented buckets.
3. Verify every seeded partial-shard `user_id` is in the supplied selection.
4. Regenerate the exact remaining total and assert it equals 61,781.
5. Run a one-user H200 smoke test in a separate output directory.
6. Inspect the smoke row for:
   - `prompt_variant == "medium_b"`
   - exactly 1,290 unique schema field IDs
   - schema-valid enum values
   - unsupported normalization
   - evidence grounding
7. Submit disjoint H200 arrays for the 14 partial and 153 untouched buckets.
8. Monitor failures and resume by `user_id`.
9. Deduplicate per shard, generate a new manifest, and upload the continuation as
   a Hugging Face dataset PR for coordinated merge with PR #53.

## Relevant links

- Repository continuation PR #241:
  <https://github.com/MatrAIx-ai/MatrAIx/pull/241>
- Request for the exact selection file:
  <https://github.com/MatrAIx-ai/MatrAIx/pull/241#issuecomment-5000525738>
- HF dataset repository:
  <https://huggingface.co/datasets/MatrAIx2026/MatrAIx2026>
- Original Xiaomin-to-Koutian handoff:
  `persona/human_extraction/AMAZON_EXTRACTION_HANDOFF.md`
