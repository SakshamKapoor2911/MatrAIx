# Amazon Persona Extraction — Handoff / Runbook

Goal: extract persona attributes for **100,000 Amazon reviewers** (one persona =
one user, built from that user's full review history) using Qwen3.6-35B-A3B on
vLLM. All code is on `main`. The run is **sharded (256 buckets), resumable, and
idempotent** — anyone can pick it up and top it up.

## Current status (2026-07-06)
- Jobs submitted by `xiaominli` on `seas_gpu` are stuck **PENDING (Priority)** —
  256 tasks, 0 running, **0 output yet**. Cause: queue contention, not a bug.
  Requiring **2× A100 on one node** makes them slower to schedule.
- Job IDs (xiaomin's): canary `28585645` (bucket 0), array `28585660` (buckets 1–255).
- A colleague running under **their own account** is the cleanest handoff (fresh
  fairshare/priority). See "Running as a different user" below.

## What one shard does
`shard-id = 0..255` → user_bucket hex `00..ff`. Each task:
1. reads the selection index for its bucket,
2. downloads that bucket's raw reviews from the gated HF dataset,
3. assembles each user's reviews into one `profile_text`,
4. runs the Amazon prompt over all 53 dimension-chunks per user,
5. appends one JSON/user to `data/amazon/extraction_v1/shard_<bkt>.jsonl`.
Resumable: skips `user_id` already written. Re-running the same sbatch line tops
up whatever didn't finish.

## Key files (all on `main`)
- Script:  `persona/human_extraction/scripts/run_extraction_amazon.py`
- Job:     `persona/human_extraction/jobs/extract_shard_amazon.job`
- Monitor: `persona/human_extraction/jobs/monitor_amazon.sh`
- Prompt/notebook (interactive): `persona/human_extraction/notebooks/extract_personas_amazon.ipynb`
- Data-exploration + how the 100K was chosen: `persona/human_extraction/notebooks/explore_amazon_data.ipynb`
- Schema (1,290 dims): `persona/schema/dimensions.json`

## Inputs / outputs
- **Selection index** (which 100K users): `persona/human_extraction/data/amazon/selected_users_100k.parquet`
  columns `user_id, user_bucket, review_count, text_chars, est_tokens`. This is
  git-ignored (regenerate from `explore_amazon_data.ipynb` if missing).
- **Source data** (gated HF): `MatrAIx2026/MatrAIx2026`, path
  `amazon/modal_artifacts/amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000/bucket=XX/category=*/part-*.parquet`.
- **Output**: `persona/human_extraction/data/amazon/extraction_v1/shard_<bkt>.jsonl`
  (git-ignored). One line/user: `{user_id, user_bucket, review_count, fields:[...]}`,
  same field schema as the wiki extractor.

## Prerequisites
- Conda env with vLLM ≥ 0.24.0 (needs the `qwen3_5_moe` arch), torch 2.11 (cu128/cu129),
  transformers, pandas, pyarrow≥17, huggingface_hub. Reference env: `env05`
  (`/n/home08/xiaominli/.conda/envs/env05`, python 3.11).
- **HF token** with access to the gated `MatrAIx2026/MatrAIx2026` dataset. The
  script reads `HF_TOKEN` / `HF_TOKEN_matraix` from env, else parses
  `HF_TOKEN_matraix=...` from `~/.bashrc`. The colleague must supply their own
  token that has been granted access to the gated repo.
- Caches + outputs must live on netscratch (never home). Defaults point at
  `/n/netscratch/lu_lab/Lab/xiaominli/mycache` — change if running as another user.

## Submit (full run)
```bash
cd persona/human_extraction/jobs
mkdir -p sbatch_logs
# smoke test first (bucket 0, 6 users) — confirms the model loads on your GPUs:
sbatch --array=0%1 --export=ALL,LIMIT=6 extract_shard_amazon.job
# full run, 256 buckets, up to 40 concurrent:
sbatch --array=0-255%40 extract_shard_amazon.job
```
Re-run the same `--array=0-255%40` line any time to top up unfinished buckets
(done users are skipped).

## GPU config (edit in extract_shard_amazon.job)
> **Prefer H100 if you have it — it's faster than A100.** Hopper (H100) has
> **native FP8 tensor cores**, so **1× H100 80GB + FP8** is both fast *and*
> near-bf16 quality, and a single-GPU task schedules far more easily than a
> 2-GPU one. Set `--gres=gpu:<your-h100-gres-name>:1` (check `sinfo -o "%P %G"`
> for the exact name, e.g. `nvidia_h100_80gb` / `nvidia_h100`) and pass
> `--export=ALL,TP=1,QUANT=fp8`. If you want full bf16 on H100, use 2× H100
> (`...:2`, `TP=2`, no quant) — H100 also has 80 GB/card like A100, so a single
> card can't hold the ~70 GB model in bf16 *and* the KV cache.

- **Default (A100): 2× A100 80GB, full bf16** (`--gres=gpu:nvidia_a100-sxm4-80gb:2`,
  `-c 32`, `--mem=160G`, `-p seas_gpu`, TP=2). 160 GB holds the ~70 GB model +
  KV cache comfortably. Best quality.
- **Faster to schedule (A100 or H100): 1× GPU + FP8.** Single-GPU slots are far
  easier to grab. Change the job to `--gres=...:1`, `-c 16`, `--mem=96G`, and pass
  `--export=ALL,TP=1,QUANT=fp8`. On A100 (Ampere) FP8 is weight-only Marlin
  (~35 GB weights); on H100 (Hopper) it's **native FP8** (faster, higher quality).
- **More capacity: add a fallback partition.** e.g. `-p seas_gpu,gpu_requeue`
  (gpu_requeue is preemptible — fine, the run is resumable) to grab idle GPUs
  sooner. Match `-t` to the partition's cap (seas_gpu = 2 days).

## Monitor
```bash
bash persona/human_extraction/jobs/monitor_amazon.sh   # queue + progress + error scan
# quick progress:
OUT=persona/human_extraction/data/amazon/extraction_v1
echo "$(cat $OUT/shard_*.jsonl 2>/dev/null | wc -l) / 100000 users, $(ls $OUT/shard_*.jsonl 2>/dev/null | wc -l)/256 shards"
# live log of a running task:
tail -f persona/human_extraction/jobs/sbatch_logs/extract_shard_amazon.job_<JOBID>_<ARRAYID>.out
```

## Running as a different user (colleague)
The defaults are pinned to xiaomin's paths. To run under another account, set
these overrides (env or edit the job) so nothing lands in the wrong home/scratch:
- `HF_HOME`, `HF_HUB_CACHE`, `HF_XET_CACHE`, `VLLM_CACHE_ROOT` → the colleague's
  netscratch (e.g. `/n/netscratch/lu_lab/Lab/<user>/mycache/...`).
- `OUT_DIR` → a writable output dir (can stay in the repo `data/amazon/extraction_v1`
  if the repo is on shared lab storage and group-writable; otherwise point it
  elsewhere and copy back).
- HF token: export `HF_TOKEN=<token-with-gated-access>` in their shell.
- Conda env: either get read access to `env05`, or recreate an equivalent env
  (vLLM ≥ 0.24.0 + torch 2.11 cu129). Setup details are in
  `persona/human_extraction/README.md` (env/driver notes).
- `selected_users_100k.parquet` is git-ignored: copy it over, or regenerate via
  `explore_amazon_data.ipynb` (deterministic, `SEED=20260705`).

## Sanity check after some shards finish
```bash
python - <<'PY'
import json, glob
n=fields=0
for f in glob.glob("persona/human_extraction/data/amazon/extraction_v1/shard_*.jsonl"):
    for line in open(f):
        r=json.loads(line); n+=1; fields+=len(r["fields"])
print(f"users={n:,}  avg_fields/user={fields/max(n,1):.0f}  (expect ~1290)")
PY
```

## Cost / scale
100K users × ~53 chunks ≈ 5.3M prompts — much smaller than the 2.13M-profile wiki
run. Per bucket ≈ 390 users; a single 2×A100 task finishes a bucket in well under
the 2-day cap. With ~40 concurrent, the whole run lands in a day or two once
scheduled.
