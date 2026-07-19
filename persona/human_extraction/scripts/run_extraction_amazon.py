#!/usr/bin/env python3
"""Production Amazon-reviewer persona extraction — sharded, resumable, 1 GPU.

One array task = one user_bucket (hex 00..ff) = one GPU. For its bucket it:
  1. loads the selection index (data/amazon/selected_users_100k.parquet),
  2. downloads that bucket's raw reviews from the gated HF dataset,
  3. assembles each selected user's reviews into a single profile_text,
  4. runs the Amazon persona prompt over all category dimension-chunks, and
  5. appends one JSON object per user to data/amazon/extraction_v1/shard_<bkt>.jsonl.

Persona = one user. Resumable: skips user_id already written, so a preempted /
re-queued task continues where it left off. Output schema matches the wiki
extractor (fields:[{field_id,value,confidence,evidence,description,assignment_type}]).

A100 80GB note: the 35B MoE is ~70 GB in bf16 and will not leave room for the KV
cache on a single 80 GB card, so this script defaults to --quantization fp8
(weight-only FP8 via Marlin on Ampere → ~35 GB weights, plenty of KV headroom).

Example (single card):
  python run_extraction_amazon.py --shard-id 0 --quantization fp8 \
      --out-dir data/amazon/extraction_v1
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

CACHE = "/n/netscratch/lu_lab/Lab/xiaominli/mycache/hf_home"
os.environ.setdefault("HF_HOME", CACHE)
os.environ.setdefault("HF_HUB_CACHE", f"{CACHE}/hub")
os.environ.setdefault("HF_XET_CACHE", f"{CACHE}/xet")
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

import pandas as pd  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402

REPO_ROOT = Path("/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx")
DATA_DIR = REPO_ROOT / "persona/human_extraction/data"
SELECTION = DATA_DIR / "amazon/selected_users_100k.parquet"
DIMENSIONS_JSON = REPO_ROOT / "persona/schema/dimensions.json"
MODEL_ID = "Qwen/Qwen3.6-35B-A3B"

DATASET_REPO = "MatrAIx2026/MatrAIx2026"
UBUK = ("amazon/modal_artifacts/"
        "amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000")

REVIEW_TMPL = ("[{date}] {category} | {parent_asin} | rating={rating:.0f}/5 | "
               "verified={verified}\nTitle: {title}\n{text}")


def hf_token() -> str | None:
    tok = os.environ.get("HF_TOKEN") or os.environ.get("HF_TOKEN_matraix")
    if tok:
        return tok
    bashrc = Path(os.path.expanduser("~/.bashrc"))
    if bashrc.exists():
        for line in bashrc.read_text().splitlines():
            m = re.search(r"HF_TOKEN_matraix=['\"]?([^'\"\s]+)", line)
            if m:
                return m.group(1)
    return None


def assemble_profile(g: pd.DataFrame, max_chars: int) -> str:
    """Concatenate one user's reviews (chronological) into a profile_text."""
    g = g.sort_values("timestamp")
    parts = [REVIEW_TMPL.format(
                date=r.date, category=r.category, parent_asin=r.parent_asin,
                rating=float(r.rating), verified=bool(r.verified_purchase),
                title=(r.title or ""), text=(r.text or ""))
             for r in g.itertuples()]
    header = (f"Amazon reviewer profile — {len(g)} reviews across "
              f"{g.category.nunique()} categories.\n\n")
    return (header + "\n\n".join(parts))[:max_chars]


def build_amazon_prompt(profile_text: str, dimensions: list[dict]) -> str:
    """Amazon-reviewer persona-extraction prompt (see extract_personas_amazon.ipynb)."""
    lines = [
        "You are building a persona for a single Amazon shopper from their "
        "complete product-review history.",
        "",
        "The input is a chronological list of that ONE person's reviews. Each "
        "review has a date, product category, product id (ASIN), star rating, a "
        "verified-purchase flag, a title, and body text. Infer who this shopper "
        "is from the WHOLE history together:",
        "- WHAT they buy: product categories and specific items reveal interests, "
        "hobbies, life stage, household, budget, and needs.",
        "- HOW they write: tone, length, detail, sentiment, and vocabulary reveal "
        "personality, values, and writing style.",
        "- WHAT they say: facts a reviewer states about themselves (\"as a "
        "nurse\", \"for my kids\", \"at 65 I...\") are the strongest signal.",
        "",
        "Return ONLY JSON with this shape (no markdown, no commentary):",
        '{"fields": [{"field_id": "<one id from DIMENSIONS below>", '
        '"value": "<one allowed value, copied verbatim, or null>", '
        '"confidence": 0.0, '
        '"evidence": "<short quote copied verbatim from one review>", '
        '"description": "<1-2 sentence description of this shopper for this attribute>", '
        '"assignment_type": "direct"}]}',
        "",
        "assignment_type values (Amazon context):",
        "- direct: the reviewer explicitly states it about themselves in a review.",
        "- structured_claim: strongly implied by concrete purchase facts (e.g. "
        "repeatedly buying baby products -> has a young child).",
        "- summary_inference: a softer inference from the overall pattern, tone, "
        "or writing style across many reviews.",
        "- unsupported: not supported by the reviews.",
        "",
        "Rules:",
        "- Emit exactly one object per dimension listed below.",
        "- value MUST be exactly one of that dimension's allowed values (copied "
        "verbatim), OR null.",
        "- Judge the history as a whole; prefer attributes backed by MULTIPLE "
        "reviews over a single purchase (one-off items may be gifts for others).",
        "- If the reviews do not support a dimension, set value to null, "
        'assignment_type to "unsupported", and description to "".',
        "- Every non-null value MUST include a short evidence quote copied "
        "verbatim from one of the reviews.",
        "- description: 1-2 concrete sentences describing THIS shopper for this "
        "attribute using details from their reviews (categories, products, "
        "statements). Describe the person; do not justify the label.",
        "- Be conservative with sensitive attributes (age, gender, health, "
        "ethnicity, religion, income): assign only when clearly stated or very "
        "strongly implied; otherwise null/unsupported.",
        "- Return valid JSON only, with no markdown.",
        "",
        "DIMENSIONS (field_id — label — description — allowed values):",
    ]
    for d in dimensions:
        allowed = " | ".join(str(v) for v in d.get("values", [])) or "(free value)"
        desc = str(d.get("description", "")).strip()
        lines.append(f"- {d['id']} — {d.get('label', d['id'])} — {desc} — [{allowed}]")
    lines += ["", "REVIEWER HISTORY:", profile_text]
    return "\n".join(lines)


def parse_fields(text: str) -> list[dict]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return []
    try:
        obj = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(obj, dict):
        return []
    fields = obj.get("fields")
    return fields if isinstance(fields, list) else []


def cat_chunks(by_category: dict, per_chunk: int):
    out = []
    for cat_dims in by_category.values():
        for i in range(0, len(cat_dims), per_chunk):
            out.append(cat_dims[i : i + per_chunk])
    return out


def load_bucket_reviews(bucket: str, token: str | None) -> pd.DataFrame:
    """All reviews in one user_bucket (across every category file)."""
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi(token=token)
    files = [f for f in api.list_repo_files(DATASET_REPO, repo_type="dataset")
             if f.startswith(f"{UBUK}/bucket={bucket}/") and f.endswith(".parquet")]
    dfs = [pd.read_parquet(hf_hub_download(DATASET_REPO, f, repo_type="dataset",
                                           token=token)) for f in files]
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard-id", type=int, required=True,
                    help="0..255 -> user_bucket hex 00..ff")
    ap.add_argument("--out-dir", default=str(DATA_DIR / "amazon/extraction_v1"))
    ap.add_argument("--batch-profiles", type=int, default=32,
                    help="profiles per vLLM submit / checkpoint granularity")
    ap.add_argument("--max-dims-per-chunk", type=int, default=50)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--max-model-len", type=int, default=32768)
    ap.add_argument("--max-profile-chars", type=int, default=48000)
    ap.add_argument("--gpu-mem", type=float, default=0.90)
    ap.add_argument("--max-num-seqs", type=int, default=64)
    ap.add_argument("--tensor-parallel", type=int, default=1,
                    help="GPUs per task (2 => bf16 fits across 2x A100 80GB, no quant)")
    ap.add_argument("--quantization", default="fp8",
                    help="fp8 (fits single A100 80GB) | none (bf16, needs 2x A100)")
    ap.add_argument("--limit", type=int, default=0, help="debug: cap users this shard")
    args = ap.parse_args()

    bucket = f"{args.shard_id:02x}"
    token = hf_token()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"shard_{bucket}.jsonl"

    # --- schema / chunks ---
    schema_doc = json.load(open(DIMENSIONS_JSON))
    by_category: dict[str, list] = {}
    for d in schema_doc["dimensions"]:
        by_category.setdefault(d.get("category", "Uncategorized"), []).append(d)
    chunk_list = cat_chunks(by_category, args.max_dims_per_chunk)

    # --- selection for this bucket ---
    sel = pd.read_parquet(SELECTION)
    sel_b = sel[sel.user_bucket == bucket]
    want = set(sel_b.user_id)
    review_count = dict(zip(sel_b.user_id, sel_b.review_count))
    if args.limit:
        want = set(list(want)[: args.limit])

    # --- resume: skip already-written user_id ---
    done: set[str] = set()
    if out_path.exists():
        with open(out_path) as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["user_id"])
                except Exception:
                    pass
    todo_ids = [u for u in want if u not in done]

    print(f"[shard {args.shard_id} bucket={bucket}] selected={len(sel_b):,} "
          f"want={len(want):,} done={len(done):,} todo={len(todo_ids):,} "
          f"chunks/user={len(chunk_list)}", flush=True)
    if not todo_ids:
        print("[shard] nothing to do — complete.", flush=True)
        return

    # --- load this bucket's reviews and assemble profiles ---
    t0 = time.time()
    rev = load_bucket_reviews(bucket, token)
    rev = rev[rev.user_id.isin(set(todo_ids))]
    profiles = {uid: assemble_profile(g, args.max_profile_chars)
                for uid, g in rev.groupby("user_id", sort=False)}
    todo = [u for u in todo_ids if u in profiles]
    print(f"[shard] loaded {len(rev):,} reviews, assembled {len(profiles):,} "
          f"profiles in {time.time()-t0:.0f}s", flush=True)

    # --- load model once ---
    t0 = time.time()
    llm_kwargs = dict(
        model=MODEL_ID,
        dtype="bfloat16",
        tensor_parallel_size=args.tensor_parallel,
        gpu_memory_utilization=args.gpu_mem,
        max_model_len=args.max_model_len,
        max_num_seqs=args.max_num_seqs,
        enable_prefix_caching=True,
        trust_remote_code=True,
        download_dir=f"{CACHE}/hub",
    )
    if args.quantization and args.quantization.lower() != "none":
        llm_kwargs["quantization"] = args.quantization
    llm = LLM(**llm_kwargs)
    sampling = SamplingParams(temperature=0.0, top_p=1.0, max_tokens=args.max_tokens)
    print(f"[shard] model loaded in {time.time()-t0:.0f}s "
          f"(tp={args.tensor_parallel}, quant={args.quantization})", flush=True)

    def chat(convs):
        try:
            return llm.chat(convs, sampling,
                            chat_template_kwargs={"enable_thinking": False}, use_tqdm=False)
        except TypeError:
            return llm.chat(convs, sampling, use_tqdm=False)

    # --- stream in batches; checkpoint after each ---
    n_done = 0
    t_gen = time.time()
    with open(out_path, "a") as out_fh:
        for bstart in range(0, len(todo), args.batch_profiles):
            batch = todo[bstart : bstart + args.batch_profiles]
            convs, idx = [], []
            for uid in batch:
                prof = profiles[uid]
                for chunk in chunk_list:
                    convs.append([{"role": "user", "content": build_amazon_prompt(prof, chunk)}])
                    idx.append(uid)
            outs = chat(convs)
            merged: dict[str, list] = {uid: [] for uid in batch}
            for uid, o in zip(idx, outs):
                merged[uid].extend(parse_fields(o.outputs[0].text))
            for uid in batch:
                out_fh.write(json.dumps(
                    {"user_id": uid, "user_bucket": bucket,
                     "review_count": int(review_count.get(uid, 0)),
                     "fields": merged[uid]}, ensure_ascii=False) + "\n")
            out_fh.flush()
            os.fsync(out_fh.fileno())
            n_done += len(batch)
            rate = n_done / max(1e-9, time.time() - t_gen)
            eta = (len(todo) - n_done) / max(1e-9, rate)
            print(f"[shard {args.shard_id}] {n_done}/{len(todo)} "
                  f"({100*n_done/len(todo):.1f}%)  {rate:.2f} user/s  "
                  f"ETA {eta/3600:.1f}h", flush=True)

    print(f"[shard {args.shard_id}] DONE {n_done} users in "
          f"{(time.time()-t_gen)/3600:.2f}h -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
