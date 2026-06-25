#!/usr/bin/env python3
"""Validate Amazon-review persona inference result archives."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from personas.existing_data_curation.scripts.infer_amazon_review_dimensions import load_schema
from personas.existing_data_curation.wiki_collab.core import Assignment
from personas.existing_data_curation.wiki_collab.results import (
    REQUIRED_PROVENANCE,
    ValidationReport,
    read_result_archive,
    validate_manifest,
)


def fetch_dataset_rows(db_path: Path, indices: Iterable[int]) -> dict[int, dict[str, Any]]:
    wanted = sorted(set(indices))
    if not wanted:
        return {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in wanted)
    rows = conn.execute(
        f"""
        select global_idx, task_id, qid, input_sha256, payload_json
        from profiles
        where global_idx in ({placeholders})
        """,
        wanted,
    ).fetchall()
    conn.close()
    return {int(row["global_idx"]): dict(row) for row in rows}


def validate_amazon_archive(
    archive_path: Path,
    db_path: Path,
    assignment: Assignment,
    expected_prompt_sha256: str,
    schema_path: Path,
) -> ValidationReport:
    report = ValidationReport(str(archive_path))
    try:
        manifest, results, failures = read_result_archive(archive_path)
    except Exception as exc:
        report.errors.append(str(exc))
        return report
    validate_manifest(manifest, assignment, expected_prompt_sha256, report)
    report.failed_rows = len(failures)
    result_indices = _indices_from_rows(results, "result", report)
    failure_indices = _indices_from_rows(failures, "failure", report)
    _validate_range_coverage(assignment, result_indices, failure_indices, report)
    db_rows = fetch_dataset_rows(db_path, result_indices)
    schema_by_id = {dim["id"]: dim for dim in load_schema(schema_path)}
    seen_results: set[int] = set()
    for row in results:
        row_errors = validate_result_row(
            row,
            db_row=db_rows.get(row.get("global_idx")),
            assignment=assignment,
            expected_prompt_sha256=expected_prompt_sha256,
            schema_by_id=schema_by_id,
            seen_indices=seen_results,
        )
        if row_errors:
            report.errors.extend(row_errors)
        else:
            report.valid_rows += 1
    if isinstance(manifest.get("succeeded"), int) and manifest["succeeded"] != len(results):
        report.errors.append(
            f"run_manifest.succeeded={manifest['succeeded']} but results rows={len(results)}"
        )
    if isinstance(manifest.get("failed"), int) and manifest["failed"] != len(failures):
        report.errors.append(
            f"run_manifest.failed={manifest['failed']} but failure rows={len(failures)}"
        )
    return report


def validate_result_row(
    row: dict[str, Any],
    *,
    db_row: dict[str, Any] | None,
    assignment: Assignment,
    expected_prompt_sha256: str,
    schema_by_id: dict[str, dict[str, Any]],
    seen_indices: set[int],
) -> list[str]:
    errors: list[str] = []
    global_idx = row.get("global_idx")
    if not isinstance(global_idx, int):
        return ["global_idx must be an integer"]
    if not assignment.contains(global_idx):
        errors.append(f"global_idx {global_idx} outside assignment range")
    if global_idx in seen_indices:
        errors.append(f"duplicate global_idx {global_idx}")
    seen_indices.add(global_idx)
    if db_row is None:
        errors.append(f"global_idx {global_idx} not found in dataset")
        return errors
    for key in ("task_id", "qid", "input_sha256"):
        if row.get(key) != db_row[key]:
            errors.append(
                f"row {global_idx} {key} mismatch: expected {db_row[key]!r}, got {row.get(key)!r}"
            )
    provenance = row.get("provenance")
    if not isinstance(provenance, dict):
        errors.append(f"row {global_idx} provenance must be an object")
        return errors
    missing_prov = sorted(key for key in REQUIRED_PROVENANCE if not provenance.get(key))
    if missing_prov:
        errors.append(f"row {global_idx} missing provenance fields: {missing_prov}")
    if provenance.get("worker_id") != assignment.worker_id:
        errors.append(f"row {global_idx} worker_id does not match assignment")
    if provenance.get("prompt_sha256") != expected_prompt_sha256:
        errors.append(f"row {global_idx} prompt_sha256 mismatch")
    if provenance.get("protocol_sha256") != assignment.protocol_sha256:
        errors.append(f"row {global_idx} protocol_sha256 mismatch")
    payload = json.loads(db_row["payload_json"])
    valid_review_ids = _review_ids(payload.get("reviews") or [])
    attributes = row.get("inferred_attributes")
    if not isinstance(attributes, list):
        errors.append(f"row {global_idx} inferred_attributes must be a list")
        return errors
    for attr_index, attr in enumerate(attributes):
        errors.extend(
            validate_attribute(
                attr,
                attr_index=attr_index,
                global_idx=global_idx,
                schema_by_id=schema_by_id,
                valid_review_ids=valid_review_ids,
            )
        )
    return errors


def validate_attribute(
    attr: Any,
    *,
    attr_index: int,
    global_idx: int,
    schema_by_id: dict[str, dict[str, Any]],
    valid_review_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(attr, dict):
        return [f"row {global_idx} attribute {attr_index} must be an object"]
    dim_id = attr.get("dimension_id")
    dim = schema_by_id.get(dim_id)
    if dim is None:
        errors.append(f"row {global_idx} attribute {attr_index} unknown dimension_id")
        return errors
    if attr.get("value") not in dim.get("values", []):
        errors.append(f"row {global_idx} attribute {attr_index} value not allowed")
    confidence = attr.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append(f"row {global_idx} attribute {attr_index} confidence out of range")
    evidence_ids = attr.get("evidence_review_ids")
    if not isinstance(evidence_ids, list) or not evidence_ids:
        errors.append(f"row {global_idx} attribute {attr_index} missing evidence_review_ids")
    elif not set(map(str, evidence_ids)).issubset(valid_review_ids):
        errors.append(
            f"row {global_idx} attribute {attr_index} evidence_review_ids not in construction reviews"
        )
    return errors


def _indices_from_rows(rows: list[dict[str, Any]], label: str, report: ValidationReport) -> set[int]:
    indices: set[int] = set()
    for row in rows:
        global_idx = row.get("global_idx")
        if not isinstance(global_idx, int):
            report.errors.append(f"{label} row global_idx must be an integer")
            continue
        if global_idx in indices:
            report.errors.append(f"duplicate {label} global_idx {global_idx}")
        indices.add(global_idx)
    return indices


def _validate_range_coverage(
    assignment: Assignment,
    result_indices: set[int],
    failure_indices: set[int],
    report: ValidationReport,
) -> None:
    expected = set(range(assignment.range_start, assignment.range_end))
    returned = result_indices | failure_indices
    missing = sorted(expected - returned)
    if missing:
        report.errors.append(
            "missing assigned rows not present in results or failures: "
            f"{missing[:20]}{'...' if len(missing) > 20 else ''}"
        )
    overlap = sorted(result_indices & failure_indices)
    if overlap:
        report.errors.append(f"indices present in both results and failures: {overlap[:20]}")


def _review_ids(reviews: list[Any]) -> set[str]:
    ids: set[str] = set()
    for review in reviews:
        if isinstance(review, dict) and review.get("review_id"):
            ids.add(str(review["review_id"]))
    return ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--assignment-json", type=Path, required=True)
    parser.add_argument("--prompt-sha256", required=True)
    parser.add_argument("--schema-path", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assignment = Assignment.from_dict(json.loads(args.assignment_json.read_text(encoding="utf-8")))
    report = validate_amazon_archive(
        archive_path=args.archive,
        db_path=args.db,
        assignment=assignment,
        expected_prompt_sha256=args.prompt_sha256,
        schema_path=args.schema_path,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
