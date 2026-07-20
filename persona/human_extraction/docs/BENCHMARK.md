# Persona-extraction throughput & tuning log (Qwen3.6-35B-A3B, vLLM, 1× H200)

Goal: extract structured persona attributes (1,290 dimensions / 43 categories)
from the MatrAIx wiki profiles (~2.13M rows), and figure out (a) whether
Qwen3.6-35B-A3B is good enough, and (b) how long a full 1M-profile run takes and
the best throughput configuration on a single H200 (143 GB).

Scripts:
- `scripts/run_bench_extraction.py` — benchmark harness (prefix-cache toggle, chunk-size
  sweep in one model load, GPU-util monitor, markdown output).
- `scripts/analyze_profile_lengths.py` — profile length distribution (Qwen tokens).
- Raw machine rows: `data/wiki/diagnostics/benchmark_sweep.md`. Per-run outputs:
  `data/wiki/diagnostics/bench_*.jsonl`.

---

## 1. Task shape

- Schema: **1,290 dimensions / 43 categories**. Too large for one prompt, so it
  is chunked. **One source profile → one persona** (profile is never split;
  dimension chunks for a person are merged back into a single record).
- `packed` chunking flattens dims across categories: `chunks = ceil(1290 / dims_per_chunk)`
  (e.g. 50→26, 150→9, 250→6). Per-category chunking (`cat`, ≤50 dims) gives 53.
- Output per generation = one JSON object per dimension: `field_id, value,
  confidence, evidence, description, assignment_type`.

## 2. Profile length distribution (20k random profiles)

| stat | Qwen tokens |
|---|---|
| median | 414 |
| p95 | 2,275 |
| p99 | 5,232 |
| p99.9 | 13,222 |
| max | ~24,800 |

- Only **0.05%** of profiles exceed 16k tokens; **0%** exceed 32k. chars/token ≈ 3.97.
- Handling: `max_model_len=32768` + truncate `profile_text` to **24,000 chars**
  → prompt overflow drops to **0%** (was 3.6% at 16k context). Truncate, don't split.

## 3. Engine fixes required (Qwen3_5Moe / GDN hybrid attention)

- **GDN prefill kernel:** FlashInfer JIT tries to nvcc-compile an sm90 kernel
  with the cluster's CUDA 12.4 (host gcc lacks C++17) and fails per-layer
  (~3 min wasted + OOM risk). **Fix:** `additional_config={"gdn_prefill_backend":"triton"}`
  → "Using Triton/FLA GDN prefill kernel", no JIT errors, faster load.
- **Context overflow:** long profiles blew the 16k window → `VLLMValidationError`.
  Fixed via 32k context + 24k-char cap (above).
- **Prefix caching + Mamba:** vLLM sets Mamba cache mode `align` and warns it's
  *experimental*. Spot-checked outputs — coherent and grounded, no corruption.

## 4. Throughput sweep (20 random profiles, max_tokens=8192, gpu_mem=0.95, max_num_seqs=512)

| config | prefix cache | chunks/prof | s/profile | out tok/s | GPU util | **trunc** | 1M @1 H200 | 1M @8 GPU |
|---|---|---|---|---|---|---|---|---|
| **cat50 (per-category) ← SELECTED** | ON | 53 | 14.22 | 5,960 | 95% | **0%** | **165d** | **~21d** |
| pack50 | ON | 26 | 13.76 | 6,057 | 95% | 0% | 159d | ~20d |
| pack150 | ON | 9 | 13.79 | 5,021 | 97% | 55.6% | 159d | ~20d |
| pack250 | ON | 6 | 11.73 | 3,671 | 98% | 83.3% | 136d | ~17d |
| pack50 | OFF | 26 | 14.35 | 5,917 | 96% | 0% | 166d | ~21d |

**pack26 vs cat53:** per-category (53 chunks) is only **~3.3% slower** than packed
(26 chunks) — 14.22 vs 13.76 s/profile. Doubling the chunk count (≈2× prefill)
barely matters because the job is decode-bound. **Decision: use per-category (53
chunks)** — keeps the semantic category grouping (one chunk per category) for a
negligible ~3% cost, and matches the schema's intended structure.

Baseline (first-10 profiles, per-category 53 chunks, no prefix cache, gpu_mem 0.92,
long outlier profiles): 31.8 s/profile, GPU util ~unknown, out tok/s 2,912,
→ 368d @1GPU. That run was pessimistic (long profiles + redundant prefill).

## 5. Findings

1. **The workload is decode-bound.** With prefix caching + packing + a full
   queue + representative profiles, GPU util pins at **95–98%**. The wall time is
   dominated by **total output tokens per persona (~83k tok** = 1,290 dims ×
   ~50–65 tok each, including short `null`/`unsupported` objects).
2. **Bigger chunks do NOT go faster** — they only **truncate**. pack250 "looks"
   faster (136d) but drops **83%** of outputs at the 8,192 cap (incomplete
   personas). pack150 truncates 56%. **pack50 (≤50 dims/chunk) = 0% truncation.**
3. **Prefix caching helps only ~4% here** (13.76 vs 14.35 s/prof). Because we're
   decode-bound and random profiles are short, the cached dims-prefix prefill is
   a small fraction of the wall time. Still free, so keep it on.
4. **More GPU memory ≠ more speed** for this workload. At gpu_mem 0.95 the KV
   cache is 63 GB / 2.7M tokens (≈max concurrency 83× at 32k), but the GPU is
   compute-bound, not KV-bound — extra memory / higher `max_num_seqs` barely moves it.

## 6. Recommended production config

```
max_model_len   = 32768
max_tokens      = 8192          # power-of-2; p99 output ~5.6k, <0.2% truncation
gpu_mem         = 0.95
max_num_seqs    = 512
enable_prefix_caching = True    # ~4% free
gdn_prefill_backend   = "triton"
chunking        = per-category, <=50 dims/chunk  (53 chunks/profile, 0% truncation)  [SELECTED]
profile cap     = 24000 chars   (affects ~0.03% of profiles)
```

Realistic estimate at this config (representative profiles):
- **~14.2 s/profile → 1M ≈ 165 days on one H200; ≈ 21 days on 8 GPUs; ≈ 41 days on 4.**
- Embarrassingly parallel: shard profiles across N GPUs → wall time / N.
- (packed 26-chunk is ~3% faster — 159d — if you ever want to trade the category
  grouping for a touch more speed.)

## 7. Ways to go materially faster (future)

The only lever left is **reducing output tokens per persona** (decode-bound):
- Don't emit full objects for `unsupported`/`null` dimensions — only return the
  dims that actually apply (median ~320/1290 non-null). Could cut output ~2–3×.
- Drop or shorten the `description` field (largest per-dim cost) if not needed.
- Smaller/faster model for the "does this dim apply?" pass, big model only for hits.
- More GPUs (linear scaling).

## 8. Quality (manual scoring of 20 personas, selected cat50 config)

Scored `data/wiki/diagnostics/bench_cat50_random_pc1.jsonl` (20 random profiles) — see
`scripts/score_personas.py`.

**Automated validity:** avg **1,286 / 1,290** fields present (18/20 at 100%
coverage; 2 missed one chunk → ~99.7% chunk parse rate); **97.5%** of non-null
values are in the dimension's allowed set; **90.6%** evidence present; **91.5%**
description present. ~524 non-null/persona, of which ~182 are substantive
positives (direct/structured/summary) and the rest are `None`/absence values.

**Manual read (grounded vs source profile):**
- ✅ **Positive attributions accurate & grounded.** e.g. G. L. Hersey → Arts &
  Humanities / Retired (emeritus) / Army veteran; Maruthanayagam Pillai → South
  Asia / Muslim convert / married (even cross-checked the language list to mark
  Croatian=None); Labrović → born 1999 → Millennial/25-34; Curtius →
  Education/Teaching. Evidence is verbatim; descriptions concrete and specific.
- ⚠️ **`assignment_type` unreliable for negatives:** `fam_*/ind_*=None` often
  mislabeled `[direct] conf=1.0` with the opening sentence as "evidence"; 4,110
  fields returned `assignment_type=null`.
- ⚠️ **Occasional bucket slip:** Hersey born 1927 → `generation=Boomer` (should
  be Silent Gen).
- ⚠️ Non-null count inflated by `None`/absence values.

**Verdict: ~4/5 — Qwen3.6-35B-A3B is capable and production-usable.** Recommended
post-processing: when `value` is `None`/absence → force
`assignment_type=unsupported` and drop the echoed evidence; treat `confidence`/
`assignment_type` as weak signals. Positive-attribution value+evidence+description
are trustworthy.

## 9. Scaling to the full 2.13M (data-parallel, 50× H200)

The 2,125,897 profiles have **no category/partition** — only `global_idx`
(0…2.13M) and arbitrary `source_file` shards → **embarrassingly parallel**. Run
**data-parallel** (one full model per H200, NOT tensor-parallel).

- Throughput: **~6,085 personas / GPU / day** (14.2 s/profile).
- Wall-time caps: `seas_gpu` = **2 days**, `gpu_h200` = **3 days** (there is **no
  7-day GPU queue**). A 50-shard split (42.5k/shard ≈ 7 days) does NOT fit, so we
  use **200 shards** (~10.6k/shard ≈ 1.75 days) to fit one 2-day run.
- Scripts:
  - `scripts/run_extraction.py` — sharded, **resumable** single-card runner (contiguous
    `global_idx` block, appends `out/shard_XXXX.jsonl`, skips done global_idx).
  - `jobs/extract_shard.job` — SLURM array, one task = one **1×H200** job
    (`--gres=gpu:nvidia_h200:1` required or seas_gpu rejects it). Submit as two
    disjoint halves, one per partition, 50 concurrent each:
    ```
    cd persona/human_extraction/jobs && mkdir -p sbatch_logs
    NUM_SHARDS=200 sbatch -p seas_gpu --time=2-00:00 --array=0-99%50    extract_shard.job
    NUM_SHARDS=200 sbatch -p gpu_h200 --time=2-12:00 --array=100-199%50 extract_shard.job
    ```
    → ~100 H200s, full 2.13M in **~3.5 days**. Re-run the same two lines to top up
    unfinished shards. **Monitoring commands + output format: see README.md
    "Monitoring the live run".** (initial submit 2026-07-05: seas_gpu 28288908,
    gpu_h200 28288957.)
- No HF token needed at runtime (local sqlite + cached model). Caches pinned to
  netscratch (`VLLM_CACHE_ROOT` too).
- An "array" is many **independent single-card** jobs (NOT multi-card); pending
  tasks fold into one `_[...]` row in squeue/sacct — use `squeue -r` to expand.
- Bigger lever for more samples/GPU-hour: reduce output tokens (skip full
  `null`/`unsupported` objects) → potential 2–3×.
