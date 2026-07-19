#!/usr/bin/env python3
"""Prepare Afrobarometer rows for the deterministic 1,290-field crosswalk.

Emits JSONL records with the extractor's required ``uuid``, ``profile_text`` and
validated ``observed`` fields. Synthetic names and inferred seniority/domain are
excluded from evidence.  The output also retains source metadata for auditing.
"""

import argparse
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
CURATION = os.path.join(REPO, "persona/curation/existing_data/scripts")
sys.path.insert(0, CURATION)

from crosswalk_engine import apply_crosswalk, load_allowed  # noqa: E402
from crosswalks.afrobarometer import CROSSWALK  # noqa: E402


def _present(value):
    return value is not None and str(value).strip() not in {"", "nan"}


def render_profile(row):
    """Render only source-supported facts, without the synthetic person name."""
    labels = [
        ("age_bracket", "Reported age bracket"),
        ("gender", "Reported gender"),
        ("country", "Country"),
        ("location", "Location and settlement type"),
        ("education_level", "Highest reported education"),
        ("professional_background", "Reported occupation"),
        ("primary_language", "Primary language"),
        ("tech_affinity", "Source technology-affinity category"),
    ]
    lines = [f"{label}: {row[key]}" for key, label in labels if _present(row.get(key))]
    if _present(row.get("values")):
        try:
            values = json.loads(row["values"])
        except (TypeError, json.JSONDecodeError):
            values = [row["values"]]
        lines.extend(f"Stated survey-derived value: {value}" for value in values if _present(value))
    return "\n".join(lines)


def records(table, allowed, limit=0):
    rows = table.to_pylist()
    if limit:
        rows = rows[:limit]
    for row in rows:
        observed, provenance, unmapped = apply_crosswalk(row, CROSSWALK, allowed)
        yield {
            "uuid": row["uuid"],
            "profile_text": render_profile(row),
            "observed": observed,
            "observed_provenance": provenance,
            "crosswalk_unmapped": unmapped,
            "source": row.get("source", "afrobarometer_r9"),
            "source_inference_flags": json.loads(row.get("_inference_flags") or "{}"),
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="afrobarometer_round9.parquet")
    ap.add_argument("--schema", default=os.path.join(REPO, "persona/schema/dimensions.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("pyarrow is required: pip install pyarrow") from exc

    allowed = load_allowed(args.schema)
    table = pq.read_table(args.input)
    required = {"uuid", "age_bracket", "gender", "country", "location"}
    missing = required - set(table.column_names)
    if missing:
        raise SystemExit(f"input is missing required columns: {sorted(missing)}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    count = 0
    with open(args.out, "w", encoding="utf-8") as fh:
        for record in records(table, allowed, args.limit):
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    print(f"prepared {count:,} profiles -> {args.out}")


if __name__ == "__main__":
    main()
