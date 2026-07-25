#!/usr/bin/env python3
"""Replace Wiki JSONL rows with schema-compatible subscription extractions."""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
from typing import Any

import pyarrow.parquet as pq


ASSIGNMENT_TYPES = {
    "direct",
    "structured_claim",
    "summary_inference",
    "unsupported",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_value(value: str) -> str:
    return " ".join(
        value.replace("\N{EN DASH}", "-").replace("\N{EM DASH}", "-").split()
    ).casefold()


def unsupported_field(field_id: str) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "value": None,
        "confidence": 0.0,
        "evidence": "",
        "description": "",
        "assignment_type": "unsupported",
    }


def convert_fields(
    source_fields: list[dict[str, Any]],
    dimensions: list[dict[str, Any]],
    stats: Counter[str],
) -> list[dict[str, Any]]:
    source_by_id: dict[str, dict[str, Any]] = {}
    for field in source_fields:
        field_id = str(field.get("field_id") or "")
        if field_id in source_by_id:
            raise ValueError(f"duplicate subscription field_id: {field_id}")
        source_by_id[field_id] = field

    canonical_ids = {str(dimension["id"]) for dimension in dimensions}
    stats["dropped_legacy_fields"] += len(set(source_by_id) - canonical_ids)
    converted: list[dict[str, Any]] = []
    for dimension in dimensions:
        field_id = str(dimension["id"])
        source = source_by_id.get(field_id)
        if source is None:
            stats["filled_missing_fields"] += 1
            converted.append(unsupported_field(field_id))
            continue

        value = source.get("value")
        if value is None:
            converted.append(unsupported_field(field_id))
            continue

        allowed_values = [str(item) for item in dimension.get("values", [])]
        value = str(value)
        if allowed_values and value not in allowed_values:
            normalized = normalized_value(value)
            matches = [
                item for item in allowed_values if normalized_value(item) == normalized
            ]
            if len(matches) == 1:
                value = matches[0]
                stats["canonicalized_values"] += 1
            else:
                stats["nulled_incompatible_values"] += 1
                converted.append(unsupported_field(field_id))
                continue

        evidence = str(source.get("evidence") or "").strip()
        assignment_type = str(source.get("assignment_type") or "")
        confidence = source.get("confidence")
        if assignment_type not in ASSIGNMENT_TYPES:
            raise ValueError(
                f"invalid assignment_type {assignment_type!r} for {field_id}"
            )
        if assignment_type == "unsupported" or not evidence:
            stats["nulled_ungrounded_values"] += 1
            converted.append(unsupported_field(field_id))
            continue
        try:
            confidence = float(confidence)
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid confidence for {field_id}") from error
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence out of range for {field_id}: {confidence}")

        stats["preserved_grounded_values"] += 1
        converted.append(
            {
                "field_id": field_id,
                "value": value,
                "confidence": confidence,
                "evidence": evidence,
                "description": "",
                "assignment_type": assignment_type,
            }
        )
    return converted


def load_subscription_rows(
    parquet_path: Path, dimensions: list[dict[str, Any]]
) -> tuple[dict[int, dict[str, Any]], Counter[str], Counter[str]]:
    rows = pq.read_table(parquet_path).to_pylist()
    converted: dict[int, dict[str, Any]] = {}
    stats: Counter[str] = Counter()
    models: Counter[str] = Counter()
    for source in rows:
        global_idx = int(source["global_idx"])
        if global_idx in converted:
            raise ValueError(f"duplicate subscription global_idx: {global_idx}")
        models[str(source.get("model") or "unknown")] += 1
        converted[global_idx] = {
            "global_idx": global_idx,
            "qid": str(source["qid"]),
            "fields": convert_fields(source["fields"], dimensions, stats),
        }
    return converted, stats, models


def validate_converted_row(
    row: dict[str, Any], dimensions: list[dict[str, Any]]
) -> None:
    if list(row) != ["global_idx", "qid", "title", "fields"]:
        raise ValueError(f"invalid row keys for global_idx={row.get('global_idx')}")
    fields = row["fields"]
    expected_ids = [str(dimension["id"]) for dimension in dimensions]
    if [field.get("field_id") for field in fields] != expected_ids:
        raise ValueError(f"invalid field order for global_idx={row['global_idx']}")
    for field, dimension in zip(fields, dimensions):
        if list(field) != [
            "field_id",
            "value",
            "confidence",
            "evidence",
            "description",
            "assignment_type",
        ]:
            raise ValueError(f"invalid field keys for {field.get('field_id')}")
        value = field["value"]
        allowed = {str(item) for item in dimension.get("values", [])}
        if value is not None and allowed and str(value) not in allowed:
            raise ValueError(f"off-schema value for {field['field_id']}: {value!r}")
        if value is not None and not str(field["evidence"]).strip():
            raise ValueError(f"ungrounded value for {field['field_id']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subscription-parquet", type=Path, required=True)
    parser.add_argument("--target-shard", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    schema_document = json.loads(args.schema.read_text())
    dimensions = schema_document["dimensions"]
    subscription, stats, models = load_subscription_rows(
        args.subscription_parquet, dimensions
    )
    expected_indices = list(range(min(subscription), max(subscription) + 1))
    if sorted(subscription) != expected_indices:
        raise ValueError("subscription global_idx coverage is not contiguous")

    original_rows: list[dict[str, Any]] = []
    target_count = 0
    with args.target_shard.open() as handle:
        for line in handle:
            row = json.loads(line)
            target_count += 1
            global_idx = int(row["global_idx"])
            replacement = subscription.get(global_idx)
            if replacement is None:
                continue
            if str(row["qid"]) != replacement["qid"]:
                raise ValueError(
                    f"qid mismatch at {global_idx}: {row['qid']} != "
                    f"{replacement['qid']}"
                )
            replacement["title"] = row["title"]
            replacement_row = {
                "global_idx": replacement["global_idx"],
                "qid": replacement["qid"],
                "title": replacement["title"],
                "fields": replacement["fields"],
            }
            validate_converted_row(replacement_row, dimensions)
            subscription[global_idx] = replacement_row
            original_rows.append(row)

    if len(original_rows) != len(subscription):
        raise ValueError(
            f"target matched {len(original_rows)} of {len(subscription)} replacements"
        )

    report = {
        "status": "validated_dry_run" if not args.apply else "applied",
        "source_revision": args.source_revision,
        "source_parquet": str(args.subscription_parquet),
        "source_parquet_sha256": sha256_file(args.subscription_parquet),
        "schema": str(args.schema),
        "schema_sha256": sha256_file(args.schema),
        "target_shard": str(args.target_shard),
        "target_shard_rows": target_count,
        "target_sha256_before": sha256_file(args.target_shard),
        "replaced_rows": len(subscription),
        "global_idx_range": [min(subscription), max(subscription)],
        "models": dict(sorted(models.items())),
        "conversion_stats": dict(sorted(stats.items())),
        "description_policy": "empty because the subscription prompt did not emit descriptions",
    }
    print(json.dumps(report, indent=2))
    if not args.apply:
        return

    args.audit_dir.mkdir(parents=True, exist_ok=True)
    backup_path = args.audit_dir / "original_qwen_rows_0000000_0001199.jsonl.gz"
    if backup_path.exists():
        raise FileExistsError(f"backup already exists: {backup_path}")
    with gzip.open(backup_path, "wt", encoding="utf-8") as backup:
        for row in original_rows:
            backup.write(json.dumps(row, ensure_ascii=False) + "\n")

    temporary = args.target_shard.with_suffix(args.target_shard.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    output_rows = 0
    try:
        with args.target_shard.open() as source, temporary.open("w") as output:
            for line in source:
                row = json.loads(line)
                replacement = subscription.get(int(row["global_idx"]))
                if replacement is None:
                    output.write(line)
                else:
                    output.write(json.dumps(replacement, ensure_ascii=False) + "\n")
                output_rows += 1
        if output_rows != target_count:
            raise ValueError(f"row count changed: {target_count} -> {output_rows}")
        shutil.copymode(args.target_shard, temporary)
        temporary.replace(args.target_shard)
    finally:
        if temporary.exists():
            temporary.unlink()

    report["target_sha256_after"] = sha256_file(args.target_shard)
    report["backup"] = str(backup_path)
    report["backup_sha256"] = sha256_file(backup_path)
    report_path = args.audit_dir / "replacement_manifest.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()