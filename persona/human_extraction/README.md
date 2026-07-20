# Persona Extraction (Human)

Extract personas from **real human data** (here: MatrAIx wiki person profiles),
in contrast to `synthesis/`, which generates synthetic personas.

> This README doubles as a **runbook**. It captures the environment, the
> CUDA/driver gotchas, and the exact commands needed to reproduce the setup on a
> fresh GPU node.

## Where the 1290-dim outputs are collected

Full extraction outputs (personas in the 1,290-dimension schema) are collected in the HF dataset
repo **`MatrAIx2026/MatrAIx-1290-extractions`** — one folder per dataset, each with an
`extraction_v1/` shard + `manifest.json`. See that repo's `CONTRIBUTING.md` for the folder/record
layout and the required `validate_extraction.py` check before pushing. This repo holds the
**scripts + a small sample**; full outputs are not committed here.

## What's here

Layout (reorganized into folders):

```
human_extraction/
  README.md                 # this runbook
  scripts/                  # runnable python
    run_extraction.py       # PRODUCTION: sharded, resumable, single-card runner
    run_bench_extraction.py # throughput benchmark + chunk/prefix sweep
    analyze_profile_lengths.py  # profile length distribution (tokens)
    score_personas.py       # quality-scoring digest of extracted personas
    legacy/                 # older one-off sample scripts (transformers / early vLLM)
  notebooks/
    extract_personas_wiki.ipynb # end-to-end interactive walkthrough
    explore_wiki_data.ipynb     # dataset exploration (length, metadata)
  jobs/
    extract_shard.job       # SLURM array job (50× H200, 7-day, resumable)
  docs/
    BENCHMARK.md            # throughput sweep + config decision + quality scoring
  data/                     # git-ignored: wiki SQLite, model logs, outputs
```

## Data

- Real Human Survey release:
  `data/matraix_persona_1m_public_release/Real Human Survey/merged_personas_508.jsonl`
  contains survey personas for **508 confirmed real people** in JSONL format,
  with one flattened 1,290-field persona per line. Unanswered survey fields
  remain `null`.
- Source: gated HF dataset `MatrAIx2026/MatrAIx2026`, file
  `wiki/source/matraix_wiki_profiles_20260601_v1.sqlite` (~7.9 GB).
- Requires an HF token; read from env var `HF_TOKEN_matraix` (set in `~/.bashrc`).
- Downloaded into `persona/human_extraction/data/wiki/source/...sqlite` via
  `hf_hub_download(local_dir=DATA_DIR)` — **not** committed to git.
- Single table `profiles` (~2,125,897 rows) with columns:
  `global_idx, task_id, page_id, qid, title, source_url, profile_text,
  input_sha256, source_file, source_row`.

## Model

- `MODEL_ID = "Qwen/Qwen3.6-35B-A3B"`.
- Architecture: `Qwen3_5MoeForConditionalGeneration` (`model_type=qwen3_5_moe`):
  a **multimodal** (vision+video) **hybrid-attention MoE** (linear/SSM + full
  attention, 256 experts, 8 active), 26 safetensors shards ≈ **70 GB** bf16.
- We use it **text-only** (feed `profile_text`, no images).
- `transformers` 5.8.0 supports it; **vLLM must be ≥ 0.24.0** (older vLLM,
  e.g. 0.8.4, does not know `qwen3_5_moe`).

## Environment (env05)

- Conda env: **env05** (`/n/home08/xiaominli/.conda/envs/env05`, Python 3.11).
- Current working stack (after the upgrade in this task):
  - **torch 2.11.0+cu129**, **vLLM 0.24.0** (cu129 build), transformers 5.8.0.
  - `torch.cuda.is_available() == True`, verified matmul on the H200.
- GPU used: NVIDIA **H200** (143 GB) — fits the 35B MoE (~70 GB) with room for
  KV cache.

## ⚠️ CUDA / driver constraint (read before running on a new GPU)

The default PyPI wheel for **vLLM 0.24.0 targets CUDA 13** and pulls
`torch==2.11.0+cu130`. The H200 node used here has driver **575.57.08 = CUDA
12.9 max**, which **cannot run CUDA 13** → `torch.cuda.is_available()` is `False`
and you get: *"The NVIDIA driver on your system is too old (found version
12090)"*.

**Fix / rule of thumb:** match the torch CUDA build to the node's driver.

1. Check the driver's max CUDA:
   ```bash
   nvidia-smi | grep "CUDA Version"     # e.g. "CUDA Version: 12.9"
   ```
2. Pick the matching vLLM CUDA variant (`cu128`/`cu129` for driver 12.8/12.9;
   only use the default `cu130` if the driver supports CUDA 13, i.e. driver
   ≳ 580).
3. Install the matching wheel (example for CUDA 12.9), with caches on netscratch:
   ```bash
   PIP_CACHE_DIR=/n/netscratch/lu_lab/Lab/xiaominli/mycache/pip \
   TMPDIR=/n/netscratch/lu_lab/Lab/xiaominli/mycache/tmp \
   /n/home08/xiaominli/.conda/envs/env05/bin/pip install --force-reinstall \
     "https://github.com/vllm-project/vllm/releases/download/v0.24.0/vllm-0.24.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl" \
     --extra-index-url https://download.pytorch.org/whl/cu129
   ```
   (Use `+cu128` and `/whl/cu128` if you prefer more driver margin.)
4. Verify GPU works before running the model:
   ```bash
   python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
   ```

> If the new GPU node has a **newer driver that supports CUDA 13**, the plain
> `pip install vllm==0.24.0` (cu130) is fine and no cu129 override is needed.

## ⚠️ Cache pitfalls (home FS is only ~95 GB and fills fast)

Everything cache-heavy must live on **netscratch**, never home
(`/n/home08/...`). `~/.bashrc` already sets `HF_HOME` and `HF_TOKEN_matraix`.

- `HF_HOME=/n/netscratch/lu_lab/Lab/xiaominli/mycache/hf_home`
- `HF_HUB_CACHE=$HF_HOME/hub` — model/dataset snapshots.
- **`HF_XET_CACHE=$HF_HOME/xet`** — the Xet chunk cache **ignores `HF_HOME`** and
  otherwise dumps to `~/.cache/huggingface/xet` (this filled home with 13 GB
  from the 7.9 GB SQLite download). Always set it.
- For pip: `PIP_CACHE_DIR` and `TMPDIR` on netscratch (torch/CUDA wheels are
  multi-GB).
- Safe-to-delete home caches if it fills again: `~/.cache/huggingface/xet`,
  `~/.cache/puccinialin` (Rust build cache), `~/.cache/pip`. Do **not** blindly
  delete `~/.cache/huggingface/hub` (may hold models you still use).
- Consider adding to `~/.bashrc`:
  ```bash
  export HF_XET_CACHE="/n/netscratch/lu_lab/Lab/xiaominli/mycache/hf_home/xet"
  export PIP_CACHE_DIR="/n/netscratch/lu_lab/Lab/xiaominli/mycache/pip"
  ```

## How to run

```bash
# 1. (once) confirm GPU + versions
/n/home08/xiaominli/.conda/envs/env05/bin/python -c \
  "import torch,vllm;print(torch.__version__,vllm.__version__,torch.cuda.is_available())"

# 2. throughput benchmark / config sweep (see docs/BENCHMARK.md)
HF_XET_CACHE=/n/netscratch/lu_lab/Lab/xiaominli/mycache/hf_home/xet \
/n/home08/xiaominli/.conda/envs/env05/bin/python \
  persona/human_extraction/scripts/run_bench_extraction.py --random --n-profiles 20

# 3. FULL RUN over all 2.13M profiles — single-card jobs, resumable.
#    seas_gpu caps at 2 days, gpu_h200 at 3 days (NO 7-day GPU queue exists),
#    so we use NUM_SHARDS=200 (~10.6k profiles/shard ≈ 1.75 days) and submit two
#    disjoint halves, one per partition, each 1x H200 per task, 50 concurrent:
cd persona/human_extraction/jobs
mkdir -p sbatch_logs
NUM_SHARDS=200 sbatch -p seas_gpu  --time=2-00:00 --array=0-99%50    extract_shard.job
NUM_SHARDS=200 sbatch -p gpu_h200  --time=2-12:00 --array=100-199%50 extract_shard.job
# each task -> data/wiki/extraction_v1/shard_XXXX.jsonl. Re-run the SAME two lines to
# top up shards that didn't finish (skips already-done global_idx).
```

> Gotchas learned the hard way: `seas_gpu` **rejects** jobs without
> `--gres=gpu:...` (already in the .job); a single `sbatch --array` **is** many
> independent single-card jobs (an "array" is NOT multi-card); `%50` = at most 50
> of them run at once; and the two arrays MUST cover **disjoint** shard ranges or
> they corrupt each other's output files.

The notebook (`notebooks/extract_personas_wiki.ipynb`) mirrors the extraction
steps interactively (config cell pins all caches to netscratch, incl. `HF_XET_CACHE`).
**Selected config** (see `docs/BENCHMARK.md`): per-category ≤50 dims/chunk (53
chunks), `max_tokens=8192`, `gpu_mem=0.95`, `max_num_seqs=512`, prefix caching,
Triton GDN, 24k-char profile cap — ~14.2 s/profile → ~6.1k personas/GPU/day.

## Monitoring the live run & inspecting output

The full run was submitted as **two array jobs** (200 shards total, 50 concurrent
1×H200 jobs per partition): `seas_gpu` = shards 0–99, `gpu_h200` = shards
100–199. With ~100 H200s the whole 2.13M finishes in **~3.5 days**. Job IDs
change on each (re)submission — the commands below find jobs by **name**
(`extract_s`) so they work regardless of ID.

```bash
USER=xiaominli
OUT=/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx/persona/human_extraction/data/wiki/extraction_v1

# queue state (use -r to EXPAND array tasks; squeue/sacct FOLD pending ones into
# one _[...] row — that's why you 'only see a couple' rows)
squeue -u $USER -r -n extract_shard.job -o "%.14i %.9P %.7T %b %R"
squeue -u $USER -h -r -n extract_shard.job -t RUNNING -o "%P" | sort | uniq -c   # running per partition
squeue -u $USER -h -r -n extract_shard.job -t PENDING | wc -l                    # tasks left to start

# progress: profiles written vs 2,125,897 total
d=$(cat $OUT/shard_*.jsonl 2>/dev/null | wc -l)
echo "$d / 2,125,897 ($(awk "BEGIN{printf \"%.2f\",100*$d/2125897}\")%) across $(ls $OUT/shard_*.jsonl 2>/dev/null|wc -l) shards"

# check a shard's live log (model load ~5 min, then '[shard N] X/Y (..%) ETA ..h')
tail -f jobs/sbatch_logs/extract_shard.job_*_<ARRAY_ID>.out

# scan all shard logs for real failures
grep -aliE "Traceback|CUDA error|out of memory" jobs/sbatch_logs/*.err
```

**Output format** — `data/wiki/extraction_v1/shard_XXXX.jsonl`, one JSON object per
profile: `{global_idx, qid, title, fields: [ {field_id, value, confidence,
evidence, description, assignment_type}, ... ]}` (~1290 field objects/profile).
Quality caveats + recommended post-processing (negatives / `assignment_type`) are
in `docs/BENCHMARK.md` §8. Inspect/score with `scripts/score_personas.py`.

### Subscription/API replacement for rows 0-1199

Local `shard_0000.jsonl` rows with `global_idx` 0-1199 were replaced with the
rich extraction artifact from `MatrAIx2026/Existing_Data` PR #51, immutable
commit `0647ae3fd6bfba403e9c63a0c9350b35be806b05`. Identity was verified by
exact `global_idx + qid` match before replacement.

Use `scripts/replace_wiki_subscription_rows.py` to reproduce the conversion. It
projects the PR's older 1,339-dimension contract onto the current 1,290 schema,
validates values and grounding, backs up the original Qwen rows, writes through
a temporary file, and atomically replaces the shard. The newer flattened PR
head is retained for reference but is not suitable as a replacement source
because it omits confidence, evidence, and assignment type.

**Resuming after preemption / time-out:** just re-run the same two `sbatch`
lines — `run_extraction.py` reads each `shard_XXXX.jsonl`, skips `global_idx`
already present, and continues. Safe to run repeatedly.

**As of the initial submission (2026-07-05):** `seas_gpu` job `28288908`
(shards 0–99) + `gpu_h200` job `28288957` (shards 100–199).

## Extraction prompt & output

Prompt is extended from the dataset owner's default method in
`../curation/existing_data/wiki_collab/collab_kit/solver.py` (`build_prompt`).

Output is **structured**: per profile, one object per dimension (attribute) with:

| field | meaning |
|---|---|
| `field_id` | attribute id (from `../schema/dimensions.json`) |
| `value` | one allowed value verbatim, or `null` |
| `description` | **1–2 sentence direct, detailed description of the person** for this attribute (e.g. `python_proficiency=high` → "Has authored over two million lines of code…"). Describes the person, does **not** justify the value. |
| `evidence` | short verbatim quote from `profile_text` (grounding) |
| `confidence` | number in `[0, 1]` |
| `assignment_type` | `direct \| structured_claim \| summary_inference \| unsupported` |

The persona dimension schema (`../schema/dimensions.json`) has **1,290**
attributes across **43** categories; prompts are chunked by `category`
(≤ 50 dims/chunk) so the whole schema isn't fed at once.

## Change log

- Created `human_extraction/` folder + notebook + extraction scripts.
- Pinned all caches (HF hub, **HF Xet**, pip, tmp) to netscratch; data downloads
  into git-ignored `data/`.
- Ported/extended the wiki extraction prompt from `wiki_collab` `solver.py`;
  added a `description` field (direct 1–2 sentence description of the person).
- Upgraded env05: vLLM 0.8.4 → **0.24.0 (cu129)**, torch 2.6.0+cu124 →
  **2.11.0+cu129**, to support `qwen3_5_moe` on a CUDA-12.9 driver.
- Freed ~48 GB on home (removed 5 unused conda envs + stale HF model cache).

## Known issues / notes

- The default vLLM 0.24 PyPI wheel (cu130) is unusable on this driver — see the
  CUDA constraint section. On a **new GPU**, re-check `nvidia-smi` and reinstall
  the matching cuXXX vLLM wheel if the driver differs.
- `pip freeze` in env05 errors (`TypeError: ... got 'NoneType'`) due to one
  package with broken version metadata; use `pip list` instead. This also
  surfaces as a non-fatal `Exit 2` at the end of some pip installs — the actual
  packages still install (verify with an import).
- First vLLM run JIT-compiles the GDN/linear-attention kernel and captures CUDA
  graphs — expect a slow first load with 0% GPU util before inference starts.

## Next steps

- Loop over all categories (chunked) × all profiles, batched through vLLM.
- Validate each `value` against its dimension's allowed set; write results to
  JSONL conforming to
  `../curation/existing_data/wiki_collab/collab_kit/schemas/result.output.schema.json`.
- Checkpoint by `(global_idx, category)` for resumable long runs.
