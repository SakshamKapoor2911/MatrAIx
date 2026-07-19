#!/usr/bin/env python3
"""Profile length distribution (in Qwen tokens) for the wiki profiles.

Samples N random profiles, tokenizes profile_text with the Qwen tokenizer, and
reports the token-length distribution + how many exceed various context limits.
Saves a histogram PNG. CPU-only (safe to run while vLLM holds the GPU).
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

CACHE = "/n/netscratch/lu_lab/Lab/xiaominli/mycache/hf_home"
os.environ.setdefault("HF_HOME", CACHE)
os.environ.setdefault("HF_HUB_CACHE", f"{CACHE}/hub")
os.environ.setdefault("HF_XET_CACHE", f"{CACHE}/xet")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")  # keep this CPU-only

import numpy as np  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

REPO_ROOT = Path("/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx")
DATA_DIR = REPO_ROOT / "persona/human_extraction/data"
DB_PATH = DATA_DIR / "wiki/matraix_wiki_profiles_20260601_v1.sqlite"
OUT_PNG = DATA_DIR / "profile_token_hist.png"
MODEL_ID = "Qwen/Qwen3.6-35B-A3B"

# Approx per-chunk prompt overhead (instructions + up to 50 dimension lines).
# Measured empirically ~5.5k tokens for a full 50-dim chunk; used to compute the
# *effective* profile budget under a given (max_model_len, max_tokens) config.
DIMS_OVERHEAD_TOK = 5500


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000, help="number of profiles to sample")
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--profile-char-cap", type=int, default=24000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    total = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
    print(f"DB has {total:,} profiles; sampling {args.n:,} at random ...", flush=True)
    rows = conn.execute(
        "SELECT profile_text FROM profiles ORDER BY RANDOM() LIMIT ?", (args.n,)
    ).fetchall()
    texts = [r[0] or "" for r in rows]

    tok = AutoTokenizer.from_pretrained(MODEL_ID, cache_dir=f"{CACHE}/hub")

    print("Tokenizing (full text) ...", flush=True)
    full_lens = np.array([len(x) for x in tok(texts, add_special_tokens=False)["input_ids"]])

    print(f"Tokenizing (first {args.profile_char_cap} chars) ...", flush=True)
    capped = [t[: args.profile_char_cap] for t in texts]
    capped_lens = np.array([len(x) for x in tok(capped, add_special_tokens=False)["input_ids"]])

    chars = np.array([len(t) for t in texts])

    def pcts(a):
        return {p: int(np.percentile(a, p)) for p in (50, 90, 95, 99, 99.9)}

    p = pcts(full_lens)
    print("\n" + "=" * 64)
    print("PROFILE LENGTH DISTRIBUTION (Qwen tokens, full profile_text)")
    print("=" * 64)
    print(f"n sampled        : {len(full_lens):,}")
    print(f"chars/token ratio: {chars.sum()/full_lens.sum():.2f}")
    print(f"mean / max       : {full_lens.mean():,.0f} / {full_lens.max():,}")
    print(f"p50/p90/p95/p99/p99.9 : "
          f"{p[50]:,} / {p[90]:,} / {p[95]:,} / {p[99]:,} / {p[99.9]:,}")

    print("\n-- fraction of profiles whose FULL text exceeds a token limit --")
    for lim in (2048, 4096, 8192, 16384, 24576, 32768):
        n = int((full_lens > lim).sum())
        print(f"  > {lim:6,} tok : {n:7,}  ({100*n/len(full_lens):.2f}%)")

    # Effective profile budget = context - output - dims-chunk overhead.
    print("\n-- would OVERFLOW the prompt (profile + ~5.5k dims + max_tokens) --")
    for mml in (16384, 32768):
        budget = mml - args.max_tokens - DIMS_OVERHEAD_TOK
        n = int((full_lens > budget).sum())
        print(f"  max_model_len={mml:5d} -> profile budget ~{budget:6,} tok : "
              f"{n:7,} overflow ({100*n/len(full_lens):.2f}%)")

    print(f"\n-- after truncating profile to {args.profile_char_cap} chars --")
    pc = pcts(capped_lens)
    print(f"  capped p50/p95/p99/max : {pc[50]:,} / {pc[95]:,} / {pc[99]:,} / {capped_lens.max():,}")
    for mml in (16384, 32768):
        budget = mml - args.max_tokens - DIMS_OVERHEAD_TOK
        n = int((capped_lens > budget).sum())
        print(f"  max_model_len={mml:5d} (budget ~{budget:,}) : {n:,} still overflow")

    # ---- Histogram ----
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    ax[0].hist(full_lens, bins=80, color="#4C78A8")
    ax[0].set_title(f"Profile length (Qwen tokens), n={len(full_lens):,}")
    ax[0].set_xlabel("tokens")
    ax[0].set_ylabel("count")
    for lim, c in [(16384, "red"), (32768, "green")]:
        ax[0].axvline(lim, color=c, ls="--", lw=1, label=f"ctx {lim}")
    ax[0].legend()

    clipped = np.clip(full_lens, 0, 40000)
    ax[1].hist(clipped, bins=80, cumulative=True, density=True, color="#F58518")
    ax[1].set_title("Cumulative fraction")
    ax[1].set_xlabel("tokens (clipped at 40k)")
    ax[1].set_ylabel("cum. fraction")
    for lim, c in [(16384, "red"), (32768, "green")]:
        ax[1].axvline(lim, color=c, ls="--", lw=1)
    ax[1].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=120)
    print(f"\nSaved histogram -> {OUT_PNG}")


if __name__ == "__main__":
    main()
