#!/usr/bin/env python3
"""Production persona extraction — sharded, resumable, single-card vLLM.

Each invocation processes ONE contiguous shard of the wiki profiles (by rank in
global_idx order) on one GPU, using the SELECTED config (per-category <=50
dims/chunk = 53 chunks, prefix caching, Triton GDN, 32k ctx, 8192 max_tokens).

Resumable: appends to out/shard_XXXX.jsonl and skips global_idx already present,
so a preempted / re-queued job continues where it left off. Writes one JSON
object per profile: {global_idx, qid, title, fields:[...]}.

Shard math: total profiles are split into --num-shards contiguous blocks (by
global_idx order); this job handles block --shard-id.

Example (single card):
  python run_extraction.py --shard-id 0 --num-shards 50 \
    --out-dir data/wiki/extraction_v1
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import time
from pathlib import Path

CACHE = "/n/netscratch/lu_lab/Lab/xiaominli/mycache/hf_home"
os.environ.setdefault("HF_HOME", CACHE)
os.environ.setdefault("HF_HUB_CACHE", f"{CACHE}/hub")
os.environ.setdefault("HF_XET_CACHE", f"{CACHE}/xet")
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

from vllm import LLM, SamplingParams  # noqa: E402

REPO_ROOT = Path("/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx")
DATA_DIR = REPO_ROOT / "persona/human_extraction/data"
WIKI_DATA_DIR = DATA_DIR / "wiki"
DB_PATH = WIKI_DATA_DIR / "source/matraix_wiki_profiles_20260601_v1.sqlite"
DIMENSIONS_JSON = REPO_ROOT / "persona/schema/dimensions.json"
MODEL_ID = "Qwen/Qwen3.6-35B-A3B"


def build_prompt(profile_text: str, dimensions: list[dict]) -> str:
    lines = [
        "You are extracting persona-attribution fields from a Wikipedia-derived profile.",
        "",
        "Return ONLY JSON with this shape (no markdown, no commentary):",
        '{"fields": [{"field_id": "<one id from DIMENSIONS below>", '
        '"value": "<one allowed value, copied verbatim, or null>", '
        '"confidence": 0.0, '
        '"evidence": "<short quote copied from profile_text>", '
        '"description": "<1-2 sentence detailed description of this person for this attribute>", '
        '"assignment_type": "direct"}]}',
        "",
        "Allowed assignment_type values:",
        "- direct: explicitly stated in the text.",
        "- structured_claim: derived from structured facts in the input.",
        "- summary_inference: reasonable inference from the profile summary.",
        "- unsupported: not supported by the input.",
        "",
        "Rules:",
        "- Emit exactly one object per dimension listed below.",
        "- value MUST be exactly one of that dimension's allowed values (copy it "
        "verbatim), OR null.",
        "- If the profile does not support a dimension, set value to null, "
        'assignment_type to "unsupported", and description to "".',
        "- Every non-null value MUST include a short evidence quote copied from profile_text.",
        "- description: 1-2 concrete sentences that directly describe this specific "
        "person with respect to this attribute, using details from the profile "
        "(facts, numbers, roles, works). Do NOT explain why the value was chosen; "
        "just describe the person. Paraphrase; do not copy the quote verbatim.",
        "- Do not infer private, sensitive, or psychological traits unless directly "
        "stated; when unsure, prefer null/unsupported.",
        "- Return valid JSON only, with no markdown.",
        "",
        "DIMENSIONS (field_id — label — description — allowed values):",
    ]
    for d in dimensions:
        allowed = " | ".join(str(v) for v in d.get("values", [])) or "(free value)"
        desc = str(d.get("description", "")).strip()
        lines.append(f"- {d['id']} — {d.get('label', d['id'])} — {desc} — [{allowed}]")
    lines += ["", "PROFILE:", profile_text]
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
    """Per-category chunks (<= per_chunk dims each) — the SELECTED chunking."""
    out = []
    for cat_dims in by_category.values():
        for i in range(0, len(cat_dims), per_chunk):
            out.append(cat_dims[i : i + per_chunk])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard-id", type=int, required=True)
    ap.add_argument("--num-shards", type=int, required=True)
    ap.add_argument("--out-dir", default=str(WIKI_DATA_DIR / "extraction_v1"))
    ap.add_argument("--batch-profiles", type=int, default=64,
                    help="profiles per vLLM submit / checkpoint granularity")
    ap.add_argument("--max-dims-per-chunk", type=int, default=50)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--max-model-len", type=int, default=32768)
    ap.add_argument("--max-profile-chars", type=int, default=24000)
    ap.add_argument("--gpu-mem", type=float, default=0.95)
    ap.add_argument("--max-num-seqs", type=int, default=512)
    ap.add_argument("--limit", type=int, default=0, help="debug: cap profiles this shard")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"shard_{args.shard_id:04d}.jsonl"

    # --- schema / chunks ---
    schema_doc = json.load(open(DIMENSIONS_JSON))
    by_category: dict[str, list] = {}
    for d in schema_doc["dimensions"]:
        by_category.setdefault(d.get("category", "Uncategorized"), []).append(d)
    chunk_list = cat_chunks(by_category, args.max_dims_per_chunk)

    # --- shard range (contiguous block by global_idx rank) ---
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    total = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
    per = math.ceil(total / args.num_shards)
    offset = args.shard_id * per
    limit = per if not args.limit else min(per, args.limit)
    shard_rows = conn.execute(
        "SELECT global_idx, qid, title, profile_text FROM profiles "
        "ORDER BY global_idx LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()

    # --- resume: skip already-written global_idx ---
    done: set[int] = set()
    if out_path.exists():
        with open(out_path) as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["global_idx"])
                except Exception:
                    pass
    todo = [r for r in shard_rows if r[0] not in done]

    print(f"[shard {args.shard_id}/{args.num_shards}] total={total:,} "
          f"range=[{offset},{offset+limit}) rows={len(shard_rows)} "
          f"already_done={len(done)} todo={len(todo)} chunks/profile={len(chunk_list)}",
          flush=True)
    if not todo:
        print("[shard] nothing to do — complete.", flush=True)
        return

    # --- load model once (SELECTED config) ---
    t0 = time.time()
    llm = LLM(
        model=MODEL_ID,
        dtype="bfloat16",
        gpu_memory_utilization=args.gpu_mem,
        max_model_len=args.max_model_len,
        max_num_seqs=args.max_num_seqs,
        enable_prefix_caching=True,
        trust_remote_code=True,
        limit_mm_per_prompt={"image": 0, "video": 0},
        additional_config={"gdn_prefill_backend": "triton"},
        download_dir=f"{CACHE}/hub",
    )
    sampling = SamplingParams(temperature=0.0, top_p=1.0, max_tokens=args.max_tokens)
    print(f"[shard] model loaded in {time.time()-t0:.0f}s", flush=True)

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
            for gid, qid, title, text in batch:
                prof = (text or "")[: args.max_profile_chars]
                for chunk in chunk_list:
                    convs.append([{"role": "user", "content": build_prompt(prof, chunk)}])
                    idx.append(gid)
            outs = chat(convs)
            merged: dict[int, list] = {gid: [] for gid, *_ in batch}
            for gid, o in zip(idx, outs):
                merged[gid].extend(parse_fields(o.outputs[0].text))
            for gid, qid, title, text in batch:
                out_fh.write(json.dumps(
                    {"global_idx": gid, "qid": qid, "title": title,
                     "fields": merged[gid]}, ensure_ascii=False) + "\n")
            out_fh.flush()
            os.fsync(out_fh.fileno())
            n_done += len(batch)
            rate = n_done / max(1e-9, time.time() - t_gen)
            eta = (len(todo) - n_done) / max(1e-9, rate)
            print(f"[shard {args.shard_id}] {n_done}/{len(todo)} "
                  f"({100*n_done/len(todo):.1f}%)  {rate:.2f} prof/s  "
                  f"ETA {eta/3600:.1f}h", flush=True)

    print(f"[shard {args.shard_id}] DONE {n_done} profiles in "
          f"{(time.time()-t_gen)/3600:.2f}h -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
