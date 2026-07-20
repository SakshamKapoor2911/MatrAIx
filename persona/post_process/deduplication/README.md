# 🧬 Persona Deduplication

This package separates two operations that should not be conflated:

1. **Deduplication** removes exact or very similar personas according to an
   explicit similarity rule.
2. **Diversity selection** reduces dense regions deterministically until the
   published corpus reaches its target size.

The completed production run retains exactly 8.4 billion personas. Human
products are deduplicated on their own merits first; their final count then
determines the synthetic target:

```text
8,400,000,000 - 2,222,496 = 8,397,777,504
```

The final verification reports `target_met: true`.

## 🧭 Why Synthetic Data Does Not Use MinHash

MinHash estimates Jaccard similarity over sparse sets. The synthetic product is
a dense vector of 1,290 categorical codes, so weighted Hamming similarity is the
natural metric:

```text
S(x, y) = sum_i w_i * I[x_i = y_i] / sum_i w_i
```

A global MinHash index would also replicate several signatures per one of 10
billion rows and create very large low-cardinality buckets. Coordinate
projections are cheaper, preserve categorical semantics, and can be evaluated
directly from nibble-packed codes.

## 1️⃣ Stage 1: Projection Cardinality Pilot

The current CPU pilot scans all 100 synthetic shards once. It evaluates nested
projections containing 6, 7, 8, 9, 10, 11, 12, 14, and 16 fields. Fields are
selected reproducibly by descending graph-prior entropy, round-robin across
schema categories. This prevents one large category from dominating the key.

Each projection is encoded exactly into one `uint64`: every categorical value
uses its four-bit code and projections contain at most 16 fields. A SplitMix64
finalizer feeds a mergeable HyperLogLog sketch with precision 20:

```text
registers per projection: 1,048,576
relative standard error: approximately 0.102%
```

All contradiction-filtered rows are excluded using the existing
`quality_filter` bitmaps. The 100 sketches merge by register-wise maximum. The
result estimates how many distinct projection buckets each width would retain
if the final policy kept one row per bucket.

Projection equality is a diversity bucket, not a claim that two personas meet a
particular full-vector Hamming threshold. The pilot is used to choose an
operational candidate width close to the target without first writing hundreds
of gigabytes of shuffle data.

## 2️⃣ Stage 2: Materialize Candidate Buckets

After choosing the projection width, the production pass emits compact
records containing:

```text
projection_signature : uint64
priority_hash         : uint64
global_row_id         : uint64
```

Records are hash-partitioned, sorted independently, and reduced by projection
signature. `priority_hash` is deterministic and provides an unbiased survivor
within a bucket. The quality-filter bitmap remains authoritative and is ORed
with the deduplication bitmap.

## 3️⃣ Stage 3: Exact Target Selection

Similarity and final corpus size remain separate controls:

- If one survivor per selected projection bucket leaves more than the required
  synthetic rows, retain the globally lowest deterministic priority ranks up
  to the exact target.
- If it leaves fewer rows, use a wider projection or permit additional
  survivors per dense bucket.
- The final boundary is selected by deterministic hash rank, so the output is
  exactly reproducible around the 8.4B publication target.

The output remains non-destructive: one packed rejection bitmap per original
shard preserves source row IDs and avoids rewriting 4.04 TB of codes.

## 👥 Human-Grounded Products

The human-grounded products contain about 2.29 million rows before quality
filtering. They use exact canonical hashes first, then MinHash LSH over
non-null `field_id=value` tokens as candidate generation. Candidate pairs must
pass the configured MinHash signature-agreement threshold. Human rows are not downsampled
merely to satisfy the exact 8.4B total; the synthetic target absorbs the size
adjustment.

Human signatures use 64 permutations and are reusable across thresholds. The
default LSH has eight bands of eight rows. Exact 128-bit canonical hashes are
always merged; LSH candidates default to a conservative minimum estimated
Jaccard similarity of 0.95. This intentionally keeps human-grounded personas
unless they are exact or nearly identical, while synthetic data absorbs almost
all target-size reduction. The merge summary reports the deduplicated human count and derives the
synthetic center target as `8,400,000,000 - human_dedup_kept`.

## 🧪 Running the Pilot

```bash
cd persona/post_process/deduplication/jobs
./submit_projection_pilot.sh
```

The submission creates 100 CPU array tasks and a dependent merge job. Results
are written under `results/projection_pilot_10b_20260719/`.

## 🚀 Production Run: Exactly 8.4B

Date started: 2026-07-19
Date completed: 2026-07-20

This section records the actual inputs, parameters, Slurm jobs, target
decisions, outputs, and operational state for the production run across all six
persona products.

### 📌 Current Operational Pool

The exact-8.4B run below is the audited production baseline. After that run,
500 retained synthetic rows were exported to the local public-release staging
area and excluded from subsequent use of the source synthetic pool. Therefore,
the current operational counts are:

```text
baseline synthetic kept:  8,397,777,504
post-dedup exclusions:               500
current synthetic kept:   8,397,777,004
human kept:                   2,222,496
current total kept:        8,399,999,500
```

The exclusion is represented non-destructively by
`results/synthetic_transfer_500_20260720/shard_0000.transfer.reject.bits`.
Consumers of the current pool must OR this overlay with the baseline shard-0
bitmap. The packed source and the audited 8.4B baseline remain immutable.

### ✅ Audited 8.4B Baseline Outcome

The run started with 10,002,288,277 rows and retained exactly 8,400,000,000.
The stages below are non-overlapping: each rejected row is charged to the first
stage that rejects it.

| Stage | Input scope | Rejected at stage | Remaining in scope |
| --- | ---: | ---: | ---: |
| Original corpus | 10,002,288,277 | - | 10,002,288,277 |
| Quality filter | 10,002,288,277 | 239,310 | 10,002,048,967 |
| Human MinHash deduplication | 2,264,093 human | 41,597 | 2,222,496 human |
| Synthetic projection-bucket deduplication | 9,999,784,874 synthetic | 252,936,392 | 9,746,848,482 synthetic buckets |
| Synthetic deterministic target cutoff | 9,746,848,482 synthetic | 1,349,070,978 | 8,397,777,504 synthetic |
| Final human + synthetic corpus | - | - | **8,400,000,000** |

The accounting closes exactly:

```text
239,310 quality rejects
+ 41,597 human duplicate rejects
+ 252,936,392 synthetic projection-bucket duplicate rejects
+ 1,349,070,978 synthetic target-cutoff rejects
= 1,602,288,277 total rejects

10,002,288,277 original rows - 1,602,288,277 rejects
= 8,400,000,000 final rows
```

The total rejected share is approximately 16.0192%. Most removals are
diversity selection for the publication target, not quality violations.

### 🧹 Quality-Filter Accounting

| Product | Original rows | Quality rejected | Quality kept |
| --- | ---: | ---: | ---: |
| Synthetic | 10,000,000,000 | 215,126 | 9,999,784,874 |
| Wiki | 1,997,743 | 23,900 | 1,973,843 |
| Amazon | 100,000 | 56 | 99,944 |
| Stack Overflow | 113,335 | 215 | 113,120 |
| PRISM | 1,500 | 13 | 1,487 |
| GSS | 75,699 | 0 | 75,699 |
| **Total** | **10,002,288,277** | **239,310** | **10,002,048,967** |

### 👥 Human Deduplication Accounting

Human deduplication runs only after quality filtering. Exact canonical-hash
matches always merge; MinHash LSH candidates merge only after meeting the 0.95
signature-agreement threshold.

| Product | Quality kept | Dedup rejected | Dedup kept |
| --- | ---: | ---: | ---: |
| Wiki | 1,973,843 | 27,401 | 1,946,442 |
| Amazon | 99,944 | 2,029 | 97,915 |
| Stack Overflow | 113,120 | 0 | 113,120 |
| PRISM | 1,487 | 0 | 1,487 |
| GSS | 75,699 | 12,167 | 63,532 |
| **Total** | **2,264,093** | **41,597** | **2,222,496** |

The merge performed 15,513 exact unions and 26,084 verified LSH unions after
checking 1,590,404,648 candidate pairs.

### 🎯 How the Exact 8.4B Target Is Enforced

1. Human deduplication fixes `human_kept = 2,222,496`.
2. The synthetic target is derived, not estimated:
  `8,400,000,000 - 2,222,496 = 8,397,777,504`.
3. The selected `entropy_rr_14` projection maps each quality-kept synthetic row
  into a categorical diversity bucket. The 256 reducers retain the minimum
  `(priority_hash, global_row_id)` representative per projection signature,
  producing exactly 9,746,848,482 unique buckets.
4. Each representative has a deterministic 64-bit priority derived from its
  global row ID. A 65,536-bin histogram over the high 16 priority bits locates
  the global target boundary without sorting all 9.75 billion survivors.
5. All earlier bins contribute 8,397,699,801 rows. The boundary bin contributes
  exactly 77,703 additional rows after sorting it by
  `(priority_hash, global_row_id)`.
6. The resulting cutoff is applied to every source shard. Bitmap tasks combine
  `quality rejection OR projection duplicate OR above-cutoff rejection`.
7. The finalizer sums all 100 synthetic shard reports and the human summary. It
  raises an error unless the total is exactly 8,400,000,000.

The recorded boundary is:

```text
priority_bin:       56,284
cutoff_priority:    15,842,686,571,127,085,373
cutoff_global_row:  9,440,273,893
synthetic_kept:     8,397,777,504
human_kept:             2,222,496
total_kept:         8,400,000,000
target_met:         true
```

### Goal and Input

Produce a non-destructive set of rejection bitmaps for:

- 10 billion Full-DAG synthetic personas;
- Wiki, Amazon, Stack Overflow, PRISM, and GSS human-grounded personas.

The implementation uses 8,400,000,000 as a deterministic center target. Human
rows are deduplicated on their own merits, then the synthetic target is set to:

```text
synthetic_target = 8,400,000,000 - human_dedup_kept
```

Deduplication starts after the completed contradiction filter:

```text
quality run: full_filter_20260719
quality rows: 10,002,288,277
quality rejected: 239,310
quality kept: 10,002,048,967
quality shard reports: 565 / 565
quality-filtered human rows: 2,264,093
```

Input summary:

```text
persona/post_process/quality_filter/results/full_filter_20260719/summary.json
```

The pre-dedup preliminary synthetic center target was 8,397,735,907. The
completed human MinHash merge raised the final synthetic target to
8,397,777,504 because 41,597 human duplicates were removed.

### 🔄 Production Pipeline

```text
quality-filter bitmaps
  |-- human JSONL
  |     -> 64-permutation MinHash + 128-bit exact hash (465 CPU tasks)
  |     -> exact groups + 8x8 LSH candidates + threshold verification
  |     -> human dedup bitmaps and human_dedup_kept
  |
  `-- synthetic packed codes
        -> projection HLL calibration (100 CPU tasks)
        -> choose narrowest projection safely above synthetic_target
        -> materialize 24-byte records (100 CPU tasks)
        -> hash partition and reduce (256 CPU tasks)
        -> one deterministic survivor per projection bucket
        -> exact global priority cutoff
        -> final synthetic bitmaps (100 CPU tasks)
        -> verify synthetic_kept + human_kept = 8,400,000,000
```

The HLL calibration and human MinHash extraction ran concurrently. A dependent
launcher submitted the final synthetic stages after both merge summaries were
available.

### Human Production Parameters

```text
exact hash: xxHash3 128-bit over sorted canonical tokens
MinHash permutations: 64
MinHash seed: 20260719
LSH bands: 8
rows per band: 8
similarity threshold: 0.95
minimum signature agreement: ceil(0.95 * 64) = 61
signature concurrency: 50
```

Exact-hash matches always merge. LSH only generates candidates; candidates must
have at least 61 equal MinHash components. The 64-component signatures are
retained, so thresholds can be changed without rescanning the source JSONL.

Canonical inventory:

| Product | Tasks |
| --- | ---: |
| Wiki | 200 |
| Amazon | 256 |
| Stack Overflow | 3 |
| PRISM | 1 |
| GSS | 5 |
| Total | 465 |

Historical jobs from the 2026-07-19 in-progress snapshot:

| Stage | Slurm job | State |
| --- | ---: | --- |
| Signature extraction | `33280584` | Completed; 465/465 outputs |
| Exact + LSH merge | `33280596` | Cancelled before start when threshold changed from 0.85 to 0.95 |
| Conservative exact + LSH merge | `33292549` | Completed; threshold 0.95 |

Manifest and outputs:

```text
jobs/manifests/human_minhash_20260719/human_tasks.jsonl
results/human_minhash_20260719/signatures/
results/human_minhash_20260719/dedup_threshold_0.95/
```

Historical note: the human submission record was created with threshold 0.85
and while the publication target was 8.3B. Its merge job was cancelled before
execution. The signatures are threshold-independent and are reused by job
`33292549` at threshold 0.95. The final launcher computes the target directly as
`8400000000 - human_dedup_kept`.

### Synthetic Calibration Run

```text
projection widths: 6, 7, 8, 9, 10, 11, 12, 14, 16
HLL precision: 20
registers: 1,048,576 per projection
relative standard error: approximately 0.102%
array tasks: 100
concurrency: 20
```

Calibration jobs, now completed:

| Stage | Slurm job | State |
| --- | ---: | --- |
| HLL shard scans | `33276594` | Completed; 100/100 sketches |
| HLL merge | `33276611` | Completed |

Results:

```text
results/projection_pilot_10b_20260719/sketches/
results/projection_pilot_10b_20260719/summary.json
```

The final launcher chooses the narrowest projection whose estimated unique
bucket count is at least 0.5% above the required synthetic target. The margin
protects against HLL estimation error and ensures the exact cutoff stage has
enough projection survivors.

### Synthetic Production Reduction

The materialization stage writes one 24-byte record per quality-kept row:

```text
projection_signature : uint64
priority_hash         : uint64
global_row_id         : uint64
```

The materialized intermediate occupies approximately 224 GB. Records are assigned to
256 partitions by a SplitMix64 hash of the projection signature. Each reducer:

1. sorts by signature, priority hash, and global row ID;
2. keeps one deterministic survivor per signature;
3. writes duplicate local row IDs grouped by source shard;
4. writes survivor priority/local-row records grouped by source shard;
5. writes a 65,536-bin histogram over the high 16 priority bits.

The cutoff stage merges the histograms, identifies the single boundary bin, and
sorts only rows in that bin by `(priority_hash, global_row_id)`. Final bitmap
tasks combine:

```text
quality rejection
OR projection-bucket duplicate rejection
OR rows above the deterministic target cutoff
```

Completed output:

```text
results/final_8_4b_20260719/
  submission.json
  materialized/
  reduced/
  cutoff.json
  bitmaps/
  summary.json
```

### ⚙️ Automatic Final Chain

```text
original launcher job: 33282038 (cancelled before execution)
replacement launcher job: 33292644 (submitted the final chain)
dependency: afterok:33276611:33292549
```

Completed final chain:

| Stage | Slurm job | Tasks | Concurrency | Result |
| --- | ---: | ---: | ---: | --- |
| Materialize projection records | `33322094` | 100 | 20 | Completed |
| Reduce signature partitions | `33322095` | 256 | 32 | Completed |
| Select exact cutoff | `33322096` | 1 | 1 | Completed in 16m 37s |
| Build final synthetic bitmaps | `33322097` | 100 | 50 | Completed; 100/100 |
| Verify final count | `33322107` | 1 | 1 | Completed; `target_met: true` |

The launcher reached all `sbatch` calls, but its final `jq` serialization failed
because the shell variable name `reduce` collided with the jq `reduce` keyword.
Consequently, `submission.json` is empty; the authoritative assigned job IDs
are recorded in the table above and in Slurm accounting. This metadata failure
did not affect the submitted dependency chain or any data outputs.

### 📦 Authoritative Result Files

```text
results/human_minhash_20260719/dedup_threshold_0.95/summary.json
results/projection_pilot_10b_20260719/summary.json
results/final_8_4b_20260719/cutoff.json
results/final_8_4b_20260719/bitmaps/shard_0000.reject.bits ... shard_0099.reject.bits
results/final_8_4b_20260719/bitmaps/shard_0000.reject.json ... shard_0099.reject.json
results/final_8_4b_20260719/summary.json
results/synthetic_transfer_500_20260720/manifest.json
results/synthetic_transfer_500_20260720/shard_0000.transfer.reject.bits
```

`final_8_4b_20260719/summary.json` verifies the immutable baseline. The transfer
manifest and overlay define the current 8,399,999,500-row operational pool.

### ✅ Baseline Acceptance Criteria

The run is accepted only if:

1. ✅ All 465 human signature tasks completed successfully.
2. ✅ All 100 synthetic HLL sketches merged under one configuration hash.
3. ✅ All 100 materializers and 256 reducers completed successfully.
4. ✅ All 100 synthetic shards have rejection bitmaps and row-count reports.
5. ✅ The human merge records threshold 0.95 and candidate counts.
6. ✅ No canonical source shard was modified; outputs are rejection bitmaps.
7. ✅ The final count is exactly 8,400,000,000.
8. ✅ Final `target_met` is `true`.

The later 500-row exclusion does not alter this historical acceptance result;
it defines a derived operational pool whose expected total is 8,399,999,500.

### 🔍 Verification Commands

```bash
cat results/final_8_4b_20260719/summary.json
find results/final_8_4b_20260719/bitmaps \
  -name 'shard_*.reject.bits' | wc -l
find results/final_8_4b_20260719/bitmaps \
  -name 'shard_*.reject.json' | wc -l
sacct -j 33322094,33322095,33322096,33322097,33322107 \
  --format=JobID,JobName,State,Elapsed,ExitCode
```

Expected bitmap and report counts are both 100. The completed chain had zero
non-empty task error logs.

### Restart and Threshold Changes

Signature and sketch stages are shard-local. Existing completed outputs are
retained and their jobs skip valid output files when resubmitted.

To test another human threshold, reuse the existing signature files and rerun
only `merge_human_minhash.py` with a different `--threshold`. Do not regenerate
the 465 signatures.

If the selected synthetic projection produces fewer exact buckets than the
required target despite the HLL safety margin, select the next wider projection
and rerun materialization. Reducer and bitmap outputs must not be mixed across
projection configurations.

### Semantic Boundary

For human products, MinHash estimates Jaccard similarity over populated
categorical claims. For synthetic data, projection equality is a diversity
bucket, not proof of high full-vector weighted-Hamming similarity. The final
synthetic priority cutoff is diversity selection layered after projection
deduplication and is reported separately from semantic duplicate removal.