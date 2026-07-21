#!/usr/bin/env python3
"""Full-schema persona extraction benchmark (Qwen/Qwen3.6-35B-A3B via vLLM).

Runs N wiki profiles through the *entire* persona dimension schema (all 43
categories, chunked <= MAX_DIMS_PER_CHUNK) in one big batched vLLM call, so we
get BOTH:
  1. real extraction output for manual quality review, and
  2. an accurate throughput measurement to extrapolate to the full 1M-profile run.

Outputs:
    - data/wiki/diagnostics/bench_extraction_<N>.jsonl: one JSON object per profile
  - prints a throughput report + 1M-profile time estimate.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import threading
import time
from pathlib import Path

CACHE = "/n/netscratch/lu_lab/Lab/xiaominli/mycache/hf_home"
os.environ.setdefault("HF_HOME", CACHE)
os.environ.setdefault("HF_HUB_CACHE", f"{CACHE}/hub")
os.environ.setdefault("HF_XET_CACHE", f"{CACHE}/xet")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

from vllm import LLM, SamplingParams  # noqa: E402

REPO_ROOT = Path("/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx")
DATA_DIR = REPO_ROOT / "persona/human_extraction/data"
DIAGNOSTICS_DIR = DATA_DIR / "wiki/diagnostics"
DB_PATH = DATA_DIR / "wiki/source/matraix_wiki_profiles_20260601_v1.sqlite"
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
    return obj.get("fields", []) if isinstance(obj, dict) else []


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def fmt_hms(s: float) -> str:
    d, r = divmod(s, 86400)
    h, r = divmod(r, 3600)
    m, _ = divmod(r, 60)
    return f"{int(d)}d {int(h)}h {int(m)}m"


def pct(vals, q):
    s = sorted(vals)
    if not s:
        return 0
    i = min(len(s) - 1, int(round(q * (len(s) - 1))))
    return s[i]


class GpuMonitor(threading.Thread):
    """Background sampler of GPU utilization / memory via nvidia-smi."""

    def __init__(self, interval: float = 0.5):
        super().__init__(daemon=True)
        self.interval = interval
        self._alive = True
        self._collect = False
        self.samples: list[tuple[float, float]] = []

    def run(self):
        while self._alive:
            if self._collect:
                try:
                    out = subprocess.check_output(
                        ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
                         "--format=csv,noheader,nounits"],
                        timeout=2,
                    ).decode()
                    u, m = out.strip().splitlines()[0].split(",")
                    self.samples.append((float(u), float(m)))
                except Exception:
                    pass
            time.sleep(self.interval)

    def start_window(self):
        self.samples = []
        self._collect = True

    def stop_window(self):
        self._collect = False
        us = [s[0] for s in self.samples]
        ms = [s[1] for s in self.samples]
        mean_u = sum(us) / len(us) if us else 0.0
        return mean_u, (max(us) if us else 0.0), (max(ms) if ms else 0.0)

    def shutdown(self):
        self._alive = False


def flat_chunks(dims: list[dict], per_chunk: int, by_category: dict, pack: bool):
    """Yield dimension chunks. If pack: flatten across categories (ceil(N/per));
    else keep category boundaries (each category split into <=per_chunk)."""
    if pack:
        for i in range(0, len(dims), per_chunk):
            yield dims[i : i + per_chunk]
    else:
        for cat_dims in by_category.values():
            for i in range(0, len(cat_dims), per_chunk):
                yield cat_dims[i : i + per_chunk]


def run_once(llm, sampling, rows, dims_all, by_category, dims_per_chunk, pack,
             mon: GpuMonitor, args, tag: str):
    """One benchmark pass over all profiles for a given chunking; returns metrics."""

    chunk_list = list(flat_chunks(dims_all, dims_per_chunk, by_category, pack))
    conversations, index = [], []
    for chunk in chunk_list:
        for gid, qid, title, text in rows:
            conversations.append([{"role": "user", "content": build_prompt(text, chunk)}])
            index.append(gid)
    chunks_per_profile = len(chunk_list)
    n_rows = len(rows)

    print(f"\n[{tag}] {n_rows} profiles x {chunks_per_profile} chunks "
          f"= {len(conversations)} generations (pack={pack}, dims/chunk={dims_per_chunk})",
          flush=True)

    mon.start_window()
    tg0 = time.time()
    try:
        outputs = llm.chat(conversations, sampling,
                           chat_template_kwargs={"enable_thinking": False}, use_tqdm=True)
    except TypeError:
        outputs = llm.chat(conversations, sampling, use_tqdm=True)
    gen_s = time.time() - tg0
    util_mean, util_peak, mem_peak = mon.stop_window()

    n_in = n_out = n_trunc = 0
    out_lens = []
    for out in outputs:
        n_in += len(out.prompt_token_ids)
        o = out.outputs[0]
        out_lens.append(len(o.token_ids))
        n_out += len(o.token_ids)
        if o.finish_reason == "length":
            n_trunc += 1

    # Save extracted personas for this run.
    results: dict[int, dict] = {
        gid: {"global_idx": gid, "qid": qid, "title": title,
              "profile_text": text, "fields": []}
        for gid, qid, title, text in rows
    }
    for gid, out in zip(index, outputs):
        results[gid]["fields"].extend(parse_fields(out.outputs[0].text))
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DIAGNOSTICS_DIR / f"bench_{tag}.jsonl"
    with open(out_path, "w") as fh:
        for gid in results:
            fh.write(json.dumps(results[gid], ensure_ascii=False) + "\n")

    s_per_profile = gen_s / n_rows
    est_1gpu = s_per_profile * args.target_profiles
    m = {
        "tag": tag, "pack": pack, "dims_per_chunk": dims_per_chunk,
        "chunks_per_profile": chunks_per_profile, "n_profiles": n_rows,
        "generations": len(conversations), "gen_s": gen_s,
        "in_per_prof": n_in / n_rows, "out_per_prof": n_out / n_rows,
        "out_tps": n_out / gen_s, "tot_tps": (n_in + n_out) / gen_s,
        "out_p50": pct(out_lens, 0.50), "out_p99": pct(out_lens, 0.99),
        "out_max": max(out_lens) if out_lens else 0,
        "trunc_pct": 100 * n_trunc / max(1, len(outputs)),
        "util_mean": util_mean, "util_peak": util_peak, "mem_peak_gb": mem_peak / 1024,
        "s_per_profile": s_per_profile, "est_1gpu_s": est_1gpu,
    }
    print(f"[{tag}] wall={gen_s:.1f}s  s/prof={s_per_profile:.2f}  "
          f"out_tok/s={m['out_tps']:.0f}  tot_tok/s={m['tot_tps']:.0f}  "
          f"GPU util mean/peak={util_mean:.0f}/{util_peak:.0f}%  "
          f"trunc={m['trunc_pct']:.1f}%  1M@1GPU={fmt_hms(est_1gpu)}", flush=True)
    return m


def append_md(md_path: Path, rows: list[dict], header_meta: dict):
    new = not md_path.exists()
    with open(md_path, "a") as fh:
        if new:
            fh.write("# Persona-extraction throughput sweep (Qwen3.6-35B-A3B, 1x H200)\n\n")
        fh.write(f"\n## Run {time.strftime('%Y-%m-%d %H:%M')} — "
                 f"prefix_cache={header_meta['prefix_cache']}, "
                 f"gpu_mem={header_meta['gpu_mem']}, max_num_seqs={header_meta['max_num_seqs']}, "
                 f"max_tokens={header_meta['max_tokens']}, "
                 f"profiles={header_meta['n_profiles']} ({header_meta['sampling']}), "
                 f"model_load={header_meta['load_s']:.0f}s\n\n")
        fh.write("| tag | pack | dims/chunk | chunks/prof | gens | wall s | in tok/prof | "
                 "out tok/prof | out tok/s | tot tok/s | GPU util mean/peak % | trunc % | "
                 "s/profile | 1M @1GPU | 1M @8GPU |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for m in rows:
            fh.write(
                f"| {m['tag']} | {m['pack']} | {m['dims_per_chunk']} | {m['chunks_per_profile']} | "
                f"{m['generations']} | {m['gen_s']:.0f} | {m['in_per_prof']:,.0f} | "
                f"{m['out_per_prof']:,.0f} | {m['out_tps']:,.0f} | {m['tot_tps']:,.0f} | "
                f"{m['util_mean']:.0f}/{m['util_peak']:.0f} | {m['trunc_pct']:.1f} | "
                f"{m['s_per_profile']:.2f} | {fmt_hms(m['est_1gpu_s'])} | "
                f"{fmt_hms(m['est_1gpu_s']/8)} |\n"
            )
    print(f"\nAppended {len(rows)} rows -> {md_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-profiles", type=int, default=20)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--max-model-len", type=int, default=32768)
    ap.add_argument("--max-profile-chars", type=int, default=24000)
    ap.add_argument("--gpu-mem", type=float, default=0.95)
    ap.add_argument("--max-num-seqs", type=int, default=512)
    ap.add_argument("--target-profiles", type=int, default=1_000_000)
    ap.add_argument("--random", action="store_true",
                    help="sample random profiles (representative) instead of first-N")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--prefix-caching", dest="prefix_caching", action="store_true", default=True)
    ap.add_argument("--no-prefix-caching", dest="prefix_caching", action="store_false")
    ap.add_argument("--pack", action="store_true",
                    help="flatten dims across categories (fewer, larger chunks)")
    ap.add_argument("--dims-chunk-sweep", default="50",
                    help="comma list of dims-per-chunk values to sweep in one model load")
    ap.add_argument("--md-out", default=str(DIAGNOSTICS_DIR / "benchmark_sweep.md"))
    args = ap.parse_args()

    schema_doc = json.load(open(DIMENSIONS_JSON))
    by_category: dict[str, list] = {}
    for d in schema_doc["dimensions"]:
        by_category.setdefault(d.get("category", "Uncategorized"), []).append(d)
    dims_all = [d for cat in by_category.values() for d in cat]
    n_dims = len(dims_all)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    if args.random:
        # Deterministic scrambled order (hash of global_idx) so repeated runs /
        # different model loads benchmark the SAME representative profile set.
        query = ("SELECT global_idx, qid, title, profile_text FROM profiles "
                 "ORDER BY ((global_idx + ?) * 2654435761) % 2147483647 LIMIT ?")
        raw_rows = conn.execute(query, (args.seed, args.n_profiles)).fetchall()
    else:
        query = ("SELECT global_idx, qid, title, profile_text FROM profiles "
                 "ORDER BY global_idx LIMIT ?")
        raw_rows = conn.execute(query, (args.n_profiles,)).fetchall()
    rows = [(gid, qid, title, (text or "")[: args.max_profile_chars])
            for gid, qid, title, text in raw_rows]
    sampling_desc = "random" if args.random else "first-N"

    sweep = [int(x) for x in args.dims_chunk_sweep.split(",") if x.strip()]

    print(f"Loading {MODEL_ID} (prefix_caching={args.prefix_caching}, "
          f"gpu_mem={args.gpu_mem}, max_num_seqs={args.max_num_seqs}) ...", flush=True)
    t0 = time.time()
    llm = LLM(
        model=MODEL_ID,
        dtype="bfloat16",
        gpu_memory_utilization=args.gpu_mem,
        max_model_len=args.max_model_len,
        max_num_seqs=args.max_num_seqs,
        enable_prefix_caching=args.prefix_caching,
        trust_remote_code=True,
        limit_mm_per_prompt={"image": 0, "video": 0},
        # Force Triton GDN prefill: FlashInfer JIT fails to nvcc-build a sm90
        # kernel with the system CUDA 12.4 (old host gcc, no C++17).
        additional_config={"gdn_prefill_backend": "triton"},
        download_dir=f"{CACHE}/hub",
    )
    load_s = time.time() - t0
    print(f"Model loaded in {load_s:.0f}s   schema: {n_dims} dims / {len(by_category)} categories",
          flush=True)

    sampling = SamplingParams(temperature=0.0, top_p=1.0, max_tokens=args.max_tokens)

    mon = GpuMonitor(interval=0.5)
    mon.start()

    metrics = []
    for dpc in sweep:
        tag = f"{'pack' if args.pack else 'cat'}{dpc}_{sampling_desc}_pc{int(args.prefix_caching)}"
        metrics.append(run_once(llm, sampling, rows, dims_all, by_category,
                                dpc, args.pack, mon, args, tag))
    mon.shutdown()

    header_meta = {
        "prefix_cache": args.prefix_caching, "gpu_mem": args.gpu_mem,
        "max_num_seqs": args.max_num_seqs, "max_tokens": args.max_tokens,
        "n_profiles": args.n_profiles, "sampling": sampling_desc, "load_s": load_s,
    }
    append_md(Path(args.md_out), metrics, header_meta)


if __name__ == "__main__":
    main()
