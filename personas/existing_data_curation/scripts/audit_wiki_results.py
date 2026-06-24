#!/usr/bin/env python3
"""Audit returned wiki extraction archives across workers, models, and ranges."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from personas.existing_data_curation.wiki_collab.core import Assignment, load_jsonl
from personas.existing_data_curation.wiki_collab.results import (
    read_result_archive,
    validate_archive,
)


def _assignment_key_from_manifest(manifest: dict[str, Any]) -> tuple[str, str, int, int]:
    return (
        str(manifest.get("worker_id")),
        str(manifest.get("protocol_id")),
        int(manifest.get("range_start")),
        int(manifest.get("range_end")),
    )


def _assignment_key(assignment: Assignment) -> tuple[str, str, int, int]:
    return (
        assignment.worker_id,
        assignment.protocol_id,
        assignment.range_start,
        assignment.range_end,
    )


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def _confidence_bucket(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "invalid"
    if value >= 0.9:
        return "0.90-1.00"
    if value >= 0.7:
        return "0.70-0.89"
    if value >= 0.5:
        return "0.50-0.69"
    if value >= 0:
        return "0.00-0.49"
    return "invalid"


def audit_archives(
    *,
    archives: list[Path],
    db_path: Path,
    assignments: list[Assignment],
    expected_prompt_sha256: str,
) -> dict[str, Any]:
    assignment_by_key = {_assignment_key(assignment): assignment for assignment in assignments}
    assigned_indices: set[int] = set()
    for assignment in assignments:
        assigned_indices.update(range(assignment.range_start, assignment.range_end))

    covered_indices: set[int] = set()
    duplicate_indices: list[int] = []
    backend_counts: Counter[str] = Counter()
    worker_counts: Counter[str] = Counter()
    requested_model_counts: Counter[str] = Counter()
    reported_model_counts: Counter[str] = Counter()
    effort_counts: Counter[str] = Counter()
    field_counts: Counter[str] = Counter()
    assignment_type_counts: Counter[str] = Counter()
    confidence_buckets: Counter[str] = Counter()
    archive_reports: list[dict[str, Any]] = []
    total_valid_rows = 0
    total_failed_rows = 0
    total_returned_rows = 0

    for archive in archives:
        archive_report: dict[str, Any] = {
            "archive_path": str(archive),
            "accepted": False,
            "valid_rows": 0,
            "failed_rows": 0,
            "errors": [],
            "warnings": [],
        }
        try:
            manifest, results, failures = read_result_archive(archive)
            assignment = assignment_by_key.get(_assignment_key_from_manifest(manifest))
            if assignment is None:
                archive_report["errors"].append("no matching assignment for archive manifest")
            else:
                validation = validate_archive(
                    archive,
                    db_path,
                    assignment,
                    expected_prompt_sha256,
                )
                archive_report.update(validation.to_dict())
                total_valid_rows += validation.valid_rows
                total_failed_rows += validation.failed_rows
            archive_report.update(
                {
                    "worker_id": manifest.get("worker_id"),
                    "backend": manifest.get("backend"),
                    "requested_model": manifest.get("requested_model"),
                    "effort": manifest.get("effort"),
                    "range_start": manifest.get("range_start"),
                    "range_end": manifest.get("range_end"),
                    "returned_rows": len(results),
                    "failure_rows": len(failures),
                }
            )
            total_returned_rows += len(results)
            for row in results:
                global_idx = row.get("global_idx")
                if isinstance(global_idx, int):
                    if global_idx in covered_indices:
                        duplicate_indices.append(global_idx)
                    covered_indices.add(global_idx)
                provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
                backend_counts[str(provenance.get("backend") or manifest.get("backend") or "unknown")] += 1
                worker_counts[str(provenance.get("worker_id") or manifest.get("worker_id") or "unknown")] += 1
                requested_model_counts[
                    str(provenance.get("requested_model") or manifest.get("requested_model") or "unknown")
                ] += 1
                reported_model_counts[str(provenance.get("reported_model") or "unknown")] += 1
                effort_counts[str(provenance.get("effort") or manifest.get("effort") or "unknown")] += 1
                fields = row.get("fields") if isinstance(row.get("fields"), list) else []
                for field in fields:
                    if not isinstance(field, dict):
                        continue
                    field_counts[str(field.get("field_id") or "unknown")] += 1
                    assignment_type_counts[str(field.get("assignment_type") or "unknown")] += 1
                    confidence_buckets[_confidence_bucket(field.get("confidence"))] += 1
        except Exception as exc:
            archive_report["errors"].append(str(exc))
        archive_reports.append(archive_report)

    missing_indices = sorted(assigned_indices - covered_indices)
    duplicate_indices_sorted = sorted(set(duplicate_indices))
    accepted_archives = sum(1 for item in archive_reports if item.get("accepted"))
    return {
        "summary": {
            "archive_count": len(archive_reports),
            "accepted_archives": accepted_archives,
            "rejected_archives": len(archive_reports) - accepted_archives,
            "returned_rows": total_returned_rows,
            "valid_rows": total_valid_rows,
            "failed_rows": total_failed_rows,
            "duplicate_rows": len(duplicate_indices),
            "backend_counts": _counter_dict(backend_counts),
            "worker_counts": _counter_dict(worker_counts),
            "requested_model_counts": _counter_dict(requested_model_counts),
            "reported_model_counts": _counter_dict(reported_model_counts),
            "effort_counts": _counter_dict(effort_counts),
            "field_counts": _counter_dict(field_counts),
            "assignment_type_counts": _counter_dict(assignment_type_counts),
            "confidence_buckets": _counter_dict(confidence_buckets),
        },
        "coverage": {
            "assigned_rows": len(assigned_indices),
            "covered_rows": len(covered_indices & assigned_indices),
            "missing_assigned_rows": len(missing_indices),
            "missing_indices_sample": missing_indices[:100],
            "duplicate_indices_sample": duplicate_indices_sorted[:100],
        },
        "archives": archive_reports,
    }


def load_assignments(path: Path) -> list[Assignment]:
    return [Assignment.from_dict(row) for row in load_jsonl(path)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", action="append", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--prompt-sha256", required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit_archives(
        archives=args.archive,
        db_path=args.db,
        assignments=load_assignments(args.assignments),
        expected_prompt_sha256=args.prompt_sha256,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return 0 if report["summary"]["rejected_archives"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

