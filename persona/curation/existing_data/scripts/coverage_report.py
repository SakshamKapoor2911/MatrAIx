#!/usr/bin/env python3
"""Coverage & quality report for 1290-dim persona extractions.

Reads one or more dataset shards and reports how much of the schema each fills — per-persona
non-null + **grounded** (direct/structured/summary) attributions, assignment_type mix, per-category
coverage, and completeness. With multiple inputs it prints a comparison table (e.g. real vs
synthetic), and it emits a one-line summary you can drop straight into the collection index.

No LLM, no network — pure analysis. Usage:
  python coverage_report.py --input prism.jsonl.gz --schema persona/schema/dimensions.json
  python coverage_report.py --input a.jsonl b.jsonl --schema dims.json --labels prism gss
"""

import argparse
import collections
import gzip
import json
import sys

GROUNDED_AT = {"direct", "structured_claim", "summary_inference"}


def _open(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def _read(path):
    for line in _open(path):
        line = line.strip()
        if line:
            yield json.loads(line)


def load_schema(schema_path):
    dims = json.load(open(schema_path))["dimensions"]
    allowed = {d["id"]: set(d.get("values") or []) for d in dims}
    categories = {d["id"]: d.get("category", "?") for d in dims}
    return allowed, categories


def summarize(records, allowed, categories):
    """Compute coverage/quality metrics over an iterable of extraction records."""
    n_dims = len(allowed)
    n = 0
    nonnull = 0
    grounded = 0
    at = collections.Counter()
    cat_grounded = collections.Counter()
    complete = 0
    for rec in records:
        n += 1
        seen = 0
        for f in rec.get("fields", []):
            fid = f.get("field_id")
            if fid not in allowed:
                continue
            seen += 1
            at[f.get("assignment_type")] += 1
            if f.get("value") not in (None, "null", ""):
                nonnull += 1
                if f.get("assignment_type") in GROUNDED_AT:
                    grounded += 1
                    cat_grounded[categories.get(fid, "?")] += 1
        if seen >= n_dims:
            complete += 1
    d = max(1, n)
    return {
        "personas": n,
        "avg_nonnull": nonnull / d,
        "avg_grounded": grounded / d,
        "at_mix": dict(at),
        "top_categories": cat_grounded.most_common(8),
        "complete_pct": 100 * complete / d,
        "n_dims": n_dims,
    }


def _print_report(label, s):
    print(f"\n=== {label} ===")
    print(
        f"  personas: {s['personas']:,}   complete (all {s['n_dims']} dims): {s['complete_pct']:.1f}%"
    )
    print(
        f"  avg non-null/persona: {s['avg_nonnull']:.1f}   avg grounded/persona: {s['avg_grounded']:.1f}"
    )
    print(f"  assignment_type mix: {s['at_mix']}")
    print(
        "  top grounded categories: "
        + ", ".join(f"{c} ({n})" for c, n in s["top_categories"][:6])
    )
    print(
        f"  >>> index snippet: {s['personas']:,} personas · ~{s['avg_grounded']:.0f} grounded dims/persona"
    )


def _selftest():
    allowed = {"a": {"x"}, "b": {"y"}, "c": {"z"}}
    categories = {"a": "Demo", "b": "Demo", "c": "Values"}
    records = [
        {
            "fields": [
                {"field_id": "a", "value": "x", "assignment_type": "direct"},
                {"field_id": "b", "value": "y", "assignment_type": "summary_inference"},
                {"field_id": "c", "value": None, "assignment_type": "unsupported"},
            ]
        },
        {
            "fields": [
                {"field_id": "a", "value": "x", "assignment_type": "direct"},
                {
                    "field_id": "b",
                    "value": "bad",
                    "assignment_type": "unsupported",
                },  # demoted, unsupported
                {"field_id": "c", "value": "z", "assignment_type": "structured_claim"},
            ]
        },
    ]
    s = summarize(records, allowed, categories)
    assert s["personas"] == 2, s
    assert abs(s["avg_grounded"] - 2.0) < 1e-9, (
        s
    )  # p1: a,b grounded; p2: a,c grounded -> (2+2)/2
    assert s["complete_pct"] == 100.0, s  # both records cover all 3 dims
    assert dict(s["top_categories"]).get("Demo") == 3, s  # a×2 + b×1 grounded in Demo
    print("coverage_report self-test: metrics verified ✅")


def main():
    ap = argparse.ArgumentParser(
        description="Coverage/quality report for 1290-dim extractions."
    )
    ap.add_argument(
        "--input", nargs="*", default=[], help="one or more shard files (.jsonl/.gz)"
    )
    ap.add_argument("--schema", help="path to dimensions.json")
    ap.add_argument("--labels", nargs="*", default=[], help="optional labels per input")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
        return
    if not args.input or not args.schema:
        ap.error("--input and --schema are required (or use --selftest)")
    allowed, categories = load_schema(args.schema)
    summaries = []
    for i, path in enumerate(args.input):
        label = args.labels[i] if i < len(args.labels) else path.split("/")[-1]
        s = summarize(_read(path), allowed, categories)
        summaries.append((label, s))
        _print_report(label, s)
    if len(summaries) > 1:
        print("\n=== comparison ===")
        print(
            f"  {'dataset':20} {'personas':>10} {'grounded/persona':>18} {'complete%':>10}"
        )
        for label, s in summaries:
            print(
                f"  {label:20} {s['personas']:>10,} {s['avg_grounded']:>18.1f} {s['complete_pct']:>9.1f}%"
            )


if __name__ == "__main__":
    sys.exit(main())
