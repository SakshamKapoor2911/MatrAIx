#!/usr/bin/env python3
"""Create a rule-only Afrobarometer extraction with exactly 1,290 fields."""

import argparse
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
CURATION = os.path.join(REPO, "persona/curation/existing_data/scripts")
sys.path.insert(0, CURATION)

from postprocess_engine import load_schema, normalize  # noqa: E402


def load_profiles(path):
    profiles = {}
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            try:
                record = json.loads(line)
                profiles[record["uuid"]] = record
            except (json.JSONDecodeError, KeyError) as exc:
                raise SystemExit(f"bad profile JSONL at line {lineno}: {exc}") from exc
    return profiles


def evidence_for(dim, profile_text):
    prefixes = {
        "age_bracket": "Reported age bracket:",
        "gender_identity": "Reported gender:",
        "highest_education": "Highest reported education:",
        "region": "Country:",
        "primary_language": "Primary language:",
        "demo_employment_status": "Reported occupation:",
    }
    prefix = prefixes.get(dim)
    lines = profile_text.splitlines()
    if prefix:
        return next((line for line in lines if line.startswith(prefix)), "")
    if dim == "demo_religion_affiliation":
        return next((line for line in lines if line.startswith("Stated survey-derived value: identifies as ")), "")
    return ""


def build_record(uid, profile, order, allowed):
    fields = normalize([], order, allowed,
                       profile_text=profile["profile_text"],
                       observed=profile.get("observed", {}))
    for field in fields:
        if field["field_id"] in profile.get("observed", {}):
            field["evidence"] = evidence_for(field["field_id"], profile["profile_text"])
            field["description"] = "Mapped exactly from an observed source field."
    return {
        "user_id": uid,
        "source": "afrobarometer_r9",
        "model": None,
        "extraction_method": "rule_based_crosswalk",
        "fields": fields,
        "observed": json.dumps(profile.get("observed", {}), ensure_ascii=False, sort_keys=True),
        "source_inference_flags": json.dumps(profile.get("source_inference_flags", {}),
                                             ensure_ascii=False, sort_keys=True),
    }


def write_parquet(path, profiles, order, allowed, batch_size=100):
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("Parquet output requires pyarrow: pip install pyarrow") from exc
    field_type = pa.struct([
        ("field_id", pa.string()), ("value", pa.string()), ("confidence", pa.float64()),
        ("evidence", pa.string()), ("description", pa.string()),
        ("assignment_type", pa.string()),
    ])
    schema = pa.schema([
        ("user_id", pa.string()), ("source", pa.string()), ("model", pa.string()),
        ("extraction_method", pa.string()), ("fields", pa.list_(field_type)),
        ("observed", pa.string()), ("source_inference_flags", pa.string()),
    ])
    writer = pq.ParquetWriter(path, schema, compression="zstd")
    batch = []
    try:
        for uid, profile in profiles.items():
            batch.append(build_record(uid, profile, order, allowed))
            if len(batch) >= batch_size:
                writer.write_table(pa.Table.from_pylist(batch, schema=schema))
                batch.clear()
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=schema))
    finally:
        writer.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", required=True, help="output from prepare_afrobarometer.py")
    ap.add_argument("--schema", default=os.path.join(REPO, "persona/schema/dimensions.json"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    order, allowed = load_schema(args.schema)
    profiles = load_profiles(args.profiles)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    if args.out.lower().endswith(".parquet"):
        write_parquet(args.out, profiles, order, allowed)
    else:
        with open(args.out, "w", encoding="utf-8") as dst:
            for uid, profile in profiles.items():
                record = build_record(uid, profile, order, allowed)
                record["observed"] = json.loads(record["observed"])
                record["source_inference_flags"] = json.loads(record["source_inference_flags"])
                dst.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"wrote {len(profiles):,} personas ({len(order)} fields each) -> {args.out}")


if __name__ == "__main__":
    main()
