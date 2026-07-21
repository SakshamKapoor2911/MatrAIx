#!/usr/bin/env python3
"""Sample persona extraction for a quick quality check.

Runs Qwen/Qwen3.6-35B-A3B (text-only) over ~10 wiki profiles across a
representative set of persona categories, using plain transformers (vLLM 0.8.4
does not support the new qwen3_5_moe architecture). Writes results to
data/sample_extraction_10.jsonl for manual review.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

os.environ.setdefault("HF_HOME", "/n/netscratch/lu_lab/Lab/xiaominli/mycache/hf_home")
os.environ.setdefault("HF_HUB_CACHE", "/n/netscratch/lu_lab/Lab/xiaominli/mycache/hf_home/hub")
os.environ.setdefault("HF_XET_CACHE", "/n/netscratch/lu_lab/Lab/xiaominli/mycache/hf_home/xet")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

import torch
from transformers import AutoModelForImageTextToText, AutoProcessor, AutoTokenizer

REPO_ROOT = Path("/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx")
HERE = REPO_ROOT / "persona/human_extraction"
DATA_DIR = HERE / "data"
DB_PATH = DATA_DIR / "wiki/source/matraix_wiki_profiles_20260601_v1.sqlite"
DIMENSIONS_JSON = REPO_ROOT / "persona/schema/dimensions.json"
OUT_PATH = DATA_DIR / "sample_extraction_10.jsonl"
HF_HUB_CACHE = os.environ["HF_HUB_CACHE"]
HF_TOKEN = os.environ.get("HF_TOKEN_matraix")

MODEL_ID = "Qwen/Qwen3.6-35B-A3B"
N_PROFILES = 10
MAX_DIMS_PER_CHUNK = 50
MAX_NEW_TOKENS = 2048
# Representative, persona-relevant categories for a Wikipedia biography.
REVIEW_CATEGORIES = [
    "Demographic: Core",
    "Demographic: Life Events",
    "Professional: Career",
    "Learning: Academic",
    "Expertise: Domains",
    "Personality: Character",
    "Values & Motivation",
]


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


def main() -> None:
    schema_doc = json.load(open(DIMENSIONS_JSON))
    by_category: dict[str, list] = {}
    for d in schema_doc["dimensions"]:
        by_category.setdefault(d.get("category", "Uncategorized"), []).append(d)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT global_idx, qid, title, profile_text FROM profiles "
        "ORDER BY global_idx LIMIT ?",
        (N_PROFILES,),
    ).fetchall()

    print(f"Loading tokenizer/processor + model {MODEL_ID} ...", flush=True)
    t0 = time.time()
    try:
        tok = AutoProcessor.from_pretrained(MODEL_ID, cache_dir=HF_HUB_CACHE, token=HF_TOKEN)
    except Exception:
        tok = AutoTokenizer.from_pretrained(MODEL_ID, cache_dir=HF_HUB_CACHE, token=HF_TOKEN)
    if getattr(tok, "padding_side", None) is not None:
        tok.padding_side = "left"
    if getattr(tok, "tokenizer", None) is not None:
        tok.tokenizer.padding_side = "left"

    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_ID,
        cache_dir=HF_HUB_CACHE,
        token=HF_TOKEN,
        dtype=torch.bfloat16,
        device_map="cuda",
        trust_remote_code=True,
    )
    model.eval()
    print(f"Model loaded in {time.time() - t0:.0f}s", flush=True)

    def apply_template(user_msg: str) -> str:
        msgs = [{"role": "user", "content": user_msg}]
        for kw in ({"enable_thinking": False}, {}):
            try:
                return tok.apply_chat_template(
                    msgs, tokenize=False, add_generation_prompt=True, **kw
                )
            except TypeError:
                continue
        raise RuntimeError("apply_chat_template failed")

    def tokenizer_for_encoding():
        return getattr(tok, "tokenizer", tok)

    results: dict[int, dict] = {}
    for gid, qid, title, text in rows:
        results[gid] = {
            "global_idx": gid,
            "qid": qid,
            "title": title,
            "profile_text": text,
            "fields": [],
        }

    for cat in REVIEW_CATEGORIES:
        dims_all = by_category.get(cat, [])
        for chunk in chunks(dims_all, MAX_DIMS_PER_CHUNK):
            prompts = [apply_template(build_prompt(r[3], chunk)) for r in rows]
            enc = tokenizer_for_encoding()(
                prompts, return_tensors="pt", padding=True
            ).to(model.device)
            with torch.no_grad():
                out = model.generate(
                    **enc,
                    max_new_tokens=MAX_NEW_TOKENS,
                    do_sample=False,
                )
            gen = out[:, enc["input_ids"].shape[1] :]
            texts = tokenizer_for_encoding().batch_decode(gen, skip_special_tokens=True)
            for (gid, qid, title, _), decoded in zip(rows, texts):
                fields = parse_fields(decoded)
                results[gid]["fields"].extend(fields)
            print(
                f"  [{cat}] chunk={len(chunk)} dims -> {len(rows)} profiles done",
                flush=True,
            )

    with open(OUT_PATH, "w") as fh:
        for gid in sorted(results):
            fh.write(json.dumps(results[gid], ensure_ascii=False) + "\n")
    print(f"Wrote {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
