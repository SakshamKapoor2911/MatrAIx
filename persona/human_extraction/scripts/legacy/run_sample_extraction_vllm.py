#!/usr/bin/env python3
"""Sample persona extraction via vLLM (Qwen/Qwen3.6-35B-A3B) for a quality check.

Runs ~10 wiki profiles across a representative set of persona categories and
writes results to data/sample_extraction_10.jsonl for manual review.
"""

from __future__ import annotations

import json
import os
import sqlite3
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
DB_PATH = DATA_DIR / "wiki/matraix_wiki_profiles_20260601_v1.sqlite"
DIMENSIONS_JSON = REPO_ROOT / "persona/schema/dimensions.json"
OUT_PATH = DATA_DIR / "sample_extraction_10.jsonl"

MODEL_ID = "Qwen/Qwen3.6-35B-A3B"
N_PROFILES = 10
MAX_DIMS_PER_CHUNK = 50
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

    print(f"Loading {MODEL_ID} with vLLM ...", flush=True)
    t0 = time.time()
    llm = LLM(
        model=MODEL_ID,
        dtype="bfloat16",
        gpu_memory_utilization=0.92,
        max_model_len=16384,
        trust_remote_code=True,
        limit_mm_per_prompt={"image": 0, "video": 0},
        download_dir=f"{CACHE}/hub",
    )
    print(f"Model loaded in {time.time() - t0:.0f}s", flush=True)

    sampling = SamplingParams(temperature=0.0, top_p=1.0, max_tokens=3000)

    # Build all (profile, category-chunk) conversations up front, then one batched call.
    conversations = []
    index = []  # (gid, title)
    for cat in REVIEW_CATEGORIES:
        for chunk in chunks(by_category.get(cat, []), MAX_DIMS_PER_CHUNK):
            for gid, qid, title, text in rows:
                conversations.append(
                    [{"role": "user", "content": build_prompt(text, chunk)}]
                )
                index.append((gid, title))

    print(f"Running {len(conversations)} prompts through vLLM ...", flush=True)
    try:
        outputs = llm.chat(
            conversations,
            sampling,
            chat_template_kwargs={"enable_thinking": False},
            use_tqdm=True,
        )
    except TypeError:
        outputs = llm.chat(conversations, sampling, use_tqdm=True)

    results: dict[int, dict] = {}
    for gid, qid, title, text in rows:
        results[gid] = {
            "global_idx": gid,
            "qid": qid,
            "title": title,
            "profile_text": text,
            "fields": [],
        }
    for (gid, title), out in zip(index, outputs):
        results[gid]["fields"].extend(parse_fields(out.outputs[0].text))

    with open(OUT_PATH, "w") as fh:
        for gid in sorted(results):
            fh.write(json.dumps(results[gid], ensure_ascii=False) + "\n")
    print(f"Wrote {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
