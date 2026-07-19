#!/usr/bin/env python3
"""One-command runner: compose the 1290-dim standardization toolkit end-to-end for a dataset.

The capstone over the toolkit's parts — it wires the reusable pieces together so a new dataset
needs only a small *dataset module* (a ``CROSSWALK`` plus optional ``flatten`` / ``render`` /
``llm_infer``), not a bespoke pipeline:

    crosswalk_engine.apply_crosswalk   # layer 1: observed / exact
    <dataset>.llm_infer                # layer 2: inferred  (pluggable; bring your own endpoint)
    postprocess_engine.normalize       # layer 3: §8 normalize + observed overlay

Two ways to run:
  * **observed-only** (no LLM, no network) — the rule layer + §8 alone. Coded surveys (GSS,
    Afrobarometer) are mostly crosswalk, so this already yields a faithful, valid 1290 extraction
    at zero API cost.
  * **full** — the dataset module also exports ``llm_infer(profile_text, order) -> raw_fields``
    (any OpenAI-compatible endpoint). No API code or credentials live in this repo — you supply
    the inferer.

Every record is ``{user_id, fields:[…×1290], observed}`` — identical to the human_extraction
pipeline. Validate with ``validate_extraction.py`` before upload (the runner prints the command).

Usage:
  python run_pipeline.py --source rows.jsonl --dataset crosswalks/prism.py \
      --schema persona/schema/dimensions.json --out prism/extraction_v1/shard_00.jsonl.gz
  python run_pipeline.py --config configs/prism.json      # same, from a JSON config
  python run_pipeline.py --selftest
"""

import argparse
import gzip
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crosswalk_engine import apply_crosswalk  # noqa: E402
from postprocess_engine import load_schema, normalize  # noqa: E402

_GROUNDED = {"direct", "structured_claim", "summary_inference"}


def load_dataset_module(path):
    """Import a dataset module by file path; must export CROSSWALK (+ optional flatten/render/llm_infer)."""
    spec = importlib.util.spec_from_file_location("dataset_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "CROSSWALK"):
        raise ValueError(f"{path}: a dataset module must define CROSSWALK")
    return mod


def build_record(
    row, crosswalk, order, allowed, *, render=None, flatten=None, llm_infer=None
):
    """Compose the three faithful layers for one source ``row`` -> one 1290-dim record.

    With ``llm_infer=None`` this is observed-only (crosswalk + §8): the stated dims come through
    ``direct``, every other dim is null/``unsupported`` — still a complete, faithful record.
    """
    row = flatten(row) if flatten else row
    observed, _prov, _unmapped = apply_crosswalk(row, crosswalk, allowed)  # layer 1
    profile_text, raw_fields = None, []
    if llm_infer is not None:  # layer 2 (optional)
        if render is None:
            raise ValueError(
                "llm_infer given but the dataset module has no render(); need profile_text"
            )
        profile_text = render(row)
        raw_fields = llm_infer(profile_text, order)
    fields = normalize(  # layer 3: §8 + observed overlay
        raw_fields, order, allowed, profile_text=profile_text, observed=observed
    )
    uid = row.get("user_id") or row.get("id") or row.get("uuid")
    return {"user_id": uid, "fields": fields, "observed": observed}


def _read_jsonl(path):
    op = gzip.open(path, "rt") if path.endswith(".gz") else open(path)
    with op as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _open_out(path):
    return gzip.open(path, "wt") if path.endswith(".gz") else open(path, "w")


def run(source, dataset, schema, out, observed_only=False):
    """Stream ``source`` rows through the pipeline and write ``out``; returns the record count."""
    order, allowed = load_schema(schema)
    mod = load_dataset_module(dataset)
    flatten = getattr(mod, "flatten", None)
    render = getattr(mod, "render", None)
    llm_infer = None if observed_only else getattr(mod, "llm_infer", None)

    n, grounded = 0, 0
    if os.path.dirname(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
    with _open_out(out) as fh:
        for row in _read_jsonl(source):
            rec = build_record(
                row,
                mod.CROSSWALK,
                order,
                allowed,
                render=render,
                flatten=flatten,
                llm_infer=llm_infer,
            )
            fh.write(json.dumps(rec) + "\n")
            n += 1
            grounded += sum(
                1
                for f in rec["fields"]
                if f["assignment_type"] in _GROUNDED
                and f["value"] not in (None, "", "null")
            )

    mode = (
        "observed-only (crosswalk + §8)"
        if llm_infer is None
        else "full (crosswalk + LLM + §8)"
    )
    print(
        f"✓ wrote {n:,} records -> {out}   [{mode}]   ~{grounded / max(1, n):.1f} grounded dims/persona"
    )
    print("Validate before upload:")
    print("  python persona/human_extraction/scripts/validate_extraction.py \\")
    print(f"      --input {out} --schema {schema}")
    return n


def _selftest():
    order = ["age_bracket", "gender_identity", "trait_openness", "urbanicity"]
    allowed = {
        "age_bracket": {"25-34"},
        "gender_identity": {"Man", "Woman"},
        "trait_openness": {"High", "Low"},
        "urbanicity": {"Urban", "Rural"},
    }
    crosswalk = {
        "age_bracket": {
            "src": "age",
            "map": {"25-34 years old": "25-34"},
            "prov": "observed",
        },
        "gender_identity": {
            "src": "gender",
            "map": {"female": "Woman"},
            "prov": "observed",
        },
    }
    row = {
        "id": "u1",
        "age": "25-34 years old",
        "gender": "female",
        "text": "She loves trying new things.",
    }

    def render(r):
        return r["text"]

    # (a) observed-only: stated dims -> direct; everything else null (no inference, no network)
    rec = build_record(row, crosswalk, order, allowed, render=render)
    assert rec["user_id"] == "u1"
    assert len(rec["fields"]) == len(order)
    byid = {f["field_id"]: f for f in rec["fields"]}
    assert (
        byid["age_bracket"]["value"] == "25-34"
        and byid["age_bracket"]["assignment_type"] == "direct"
    )
    assert byid["gender_identity"]["value"] == "Woman"
    assert (
        byid["trait_openness"]["value"] is None and byid["urbanicity"]["value"] is None
    )
    assert rec["observed"] == {"age_bracket": "25-34", "gender_identity": "Woman"}

    # (b) full: a grounded inference is kept; the observed overlay still wins its dim
    def good_llm(profile_text, order):
        return [
            {
                "field_id": "trait_openness",
                "value": "High",
                "confidence": 0.7,
                "evidence": "loves trying new things",
                "description": "",
                "assignment_type": "summary_inference",
            }
        ]

    rec2 = build_record(
        row, crosswalk, order, allowed, render=render, llm_infer=good_llm
    )
    b2 = {f["field_id"]: f for f in rec2["fields"]}
    assert b2["trait_openness"]["value"] == "High" and b2["trait_openness"]["evidence"]
    assert b2["age_bracket"]["assignment_type"] == "direct"

    # (c) faithfulness: an argument-from-absence inference is demoted by §8, never emitted
    def bad_llm(profile_text, order):
        return [
            {
                "field_id": "urbanicity",
                "value": "Urban",
                "confidence": 0.9,
                "evidence": "no mention of where she lives",
                "description": "",
                "assignment_type": "summary_inference",
            }
        ]

    rec3 = build_record(
        row, crosswalk, order, allowed, render=render, llm_infer=bad_llm
    )
    b3 = {f["field_id"]: f for f in rec3["fields"]}
    assert b3["urbanicity"]["assignment_type"] == "unsupported", b3["urbanicity"]
    assert b3["urbanicity"]["evidence"] == ""

    print(
        f"run_pipeline self-test: end-to-end compose verified ({len(order)} dims; observed-only + full + §8) ✅"
    )


def main():
    ap = argparse.ArgumentParser(
        description="One-command 1290-dim standardization runner."
    )
    ap.add_argument(
        "--config", help="JSON config with source/dataset/schema/out[/observed_only]"
    )
    ap.add_argument("--source", help="source rows (.jsonl/.gz), one row per line")
    ap.add_argument(
        "--dataset", help="path to the dataset module (exports CROSSWALK, …)"
    )
    ap.add_argument("--schema", help="path to dimensions.json")
    ap.add_argument("--out", help="output shard (.jsonl/.gz)")
    ap.add_argument(
        "--observed-only", action="store_true", help="rule layer + §8 only (no LLM)"
    )
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return
    cfg = {}
    if args.config:
        cfg = json.load(open(args.config))
    source = args.source or cfg.get("source")
    dataset = args.dataset or cfg.get("dataset")
    schema = args.schema or cfg.get("schema")
    out = args.out or cfg.get("out")
    observed_only = args.observed_only or cfg.get("observed_only", False)
    if not all([source, dataset, schema, out]):
        ap.error(
            "need --source, --dataset, --schema, --out (or a --config providing them)"
        )
    run(source, dataset, schema, out, observed_only=observed_only)


if __name__ == "__main__":
    sys.exit(main())
