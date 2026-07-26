#!/usr/bin/env python3
"""Prepare ConvAI2 personas for deterministic MatrAIx crosswalk extraction."""

import argparse
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
CURATION = os.path.join(REPO, "persona/curation/existing_data/scripts")
sys.path.insert(0, CURATION)

from crosswalk_engine import apply_crosswalk, load_allowed  # noqa: E402
from crosswalks.convai2 import CROSSWALK, extract_assignments  # noqa: E402


def records(table, allowed, limit=0):
    rows = table.to_pylist()
    if limit:
        rows = rows[:limit]
    for row in rows:
        text = str(row.get("persona_description") or "").strip()
        observed, provenance, unmapped = apply_crosswalk(row, CROSSWALK, allowed)
        matches = extract_assignments(text)
        yield {
            "uuid": row["uuid"],
            "profile_text": text,
            "observed": observed,
            "observed_evidence": {dim: matches[dim][1] for dim in observed},
            "observed_provenance": provenance,
            "crosswalk_unmapped": unmapped,
            "source": row.get("source", "AlekseyKorshuk/persona-chat"),
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="ConvAI2 personas.parquet")
    ap.add_argument(
        "--schema", default=os.path.join(REPO, "persona/schema/dimensions.json")
    )
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("pyarrow is required: pip install pyarrow") from exc

    table = pq.read_table(args.input)
    required = {"uuid", "persona_description"}
    missing = required - set(table.column_names)
    if missing:
        raise SystemExit(f"input is missing required columns: {sorted(missing)}")
    allowed = load_allowed(args.schema)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    count = 0
    with open(args.out, "w", encoding="utf-8") as fh:
        for record in records(table, allowed, args.limit):
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    print(f"prepared {count:,} profiles -> {args.out}")


if __name__ == "__main__":
    main()
