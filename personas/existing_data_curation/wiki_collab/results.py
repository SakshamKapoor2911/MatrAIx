#!/usr/bin/env python3
"""Validation helpers for returned wiki collaboration results."""

from __future__ import annotations

from dataclasses import dataclass, field
import gzip
import io
import json
import sqlite3
import tarfile
from pathlib import Path
from typing import Any, Iterable, Iterator

from .core import Assignment


REQUIRED_ARCHIVE_MEMBERS = {
    "results.jsonl.gz",
    "failures.jsonl.gz",
    "run_manifest.json",
}

REQUIRED_PROVENANCE = {
    "worker_id",
    "backend",
    "provider",
    "requested_model",
    "model_source",
    "model_confidence",
    "prompt_sha256",
    "protocol_sha256",
    "runner_version",
    "effort",
}

VALID_ASSIGNMENT_TYPES = {
    "direct",
    "structured_claim",
    "summary_inference",
    "unsupported",
}


@dataclass
class ValidationReport:
    archive_path: str
    valid_rows: int = 0
    failed_rows: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_path": self.archive_path,
            "accepted": self.accepted,
            "valid_rows": self.valid_rows,
            "failed_rows": self.failed_rows,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _read_tar_member(tar: tarfile.TarFile, name: str) -> bytes:
    member = tar.getmember(name)
    if not member.isfile():
        raise ValueError(f"{name} is not a regular file")
    fh = tar.extractfile(member)
    if fh is None:
        raise ValueError(f"could not read {name}")
    return fh.read()


def read_result_archive(archive_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    with tarfile.open(archive_path, "r:gz") as tar:
        names = {member.name for member in tar.getmembers()}
        missing = REQUIRED_ARCHIVE_MEMBERS - names
        if missing:
            raise ValueError(f"archive missing required members: {sorted(missing)}")
        manifest = json.loads(_read_tar_member(tar, "run_manifest.json").decode("utf-8"))
        result_bytes = _read_tar_member(tar, "results.jsonl.gz")
        failure_bytes = _read_tar_member(tar, "failures.jsonl.gz")
    results = list(_jsonl_gzip_bytes(result_bytes, "results.jsonl.gz"))
    failures = list(_jsonl_gzip_bytes(failure_bytes, "failures.jsonl.gz"))
    return manifest, results, failures


def _jsonl_gzip_bytes(data: bytes, label: str) -> Iterator[dict[str, Any]]:
    with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as gz:
        for line_no, raw in enumerate(gz, 1):
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{label}:{line_no}: invalid JSON: {exc}") from exc


def iter_archive_results(archive_path: Path) -> Iterator[dict[str, Any]]:
    _, results, _ = read_result_archive(archive_path)
    yield from results


def validate_manifest(
    manifest: dict[str, Any],
    assignment: Assignment,
    expected_prompt_sha256: str,
    report: ValidationReport,
) -> None:
    expected = {
        "worker_id": assignment.worker_id,
        "dataset_id": assignment.dataset_id,
        "dataset_sha256": assignment.dataset_sha256,
        "protocol_id": assignment.protocol_id,
        "protocol_sha256": assignment.protocol_sha256,
        "range_start": assignment.range_start,
        "range_end": assignment.range_end,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            report.errors.append(
                f"run_manifest.{key} mismatch: expected {value!r}, got {manifest.get(key)!r}"
            )
    if not manifest.get("backend"):
        report.errors.append("run_manifest.backend is required")
    if not manifest.get("runner_version"):
        report.errors.append("run_manifest.runner_version is required")
    if "reported_models" not in manifest:
        report.errors.append("run_manifest.reported_models is required")
    if not manifest.get("effort"):
        report.errors.append("run_manifest.effort is required")
    if expected_prompt_sha256 and not isinstance(expected_prompt_sha256, str):
        report.errors.append("expected prompt hash must be a string")


def validate_result_row(
    row: dict[str, Any],
    *,
    db_row: dict[str, Any] | None,
    assignment: Assignment,
    expected_prompt_sha256: str,
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
    if not provenance.get("effort"):
        errors.append(f"row {global_idx} effort is required")
    fields = row.get("fields")
    if not isinstance(fields, list):
        errors.append(f"row {global_idx} fields must be a list")
        return errors
    for field_index, field in enumerate(fields):
        if not isinstance(field, dict):
            errors.append(f"row {global_idx} field {field_index} must be an object")
            continue
        for key in ("field_id", "value", "confidence", "evidence", "assignment_type"):
            if key not in field:
                errors.append(f"row {global_idx} field {field_index} missing {key}")
        confidence = field.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            errors.append(f"row {global_idx} field {field_index} confidence out of range")
        if field.get("assignment_type") not in VALID_ASSIGNMENT_TYPES:
            errors.append(f"row {global_idx} field {field_index} invalid assignment_type")
    return errors


def fetch_dataset_rows(db_path: Path, indices: Iterable[int]) -> dict[int, dict[str, Any]]:
    wanted = sorted(set(indices))
    if not wanted:
        return {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in wanted)
    rows = conn.execute(
        f"select global_idx, task_id, qid, input_sha256 from profiles where global_idx in ({placeholders})",
        wanted,
    ).fetchall()
    conn.close()
    return {int(row["global_idx"]): dict(row) for row in rows}


def validate_archive(
    archive_path: Path,
    db_path: Path,
    assignment: Assignment,
    expected_prompt_sha256: str,
) -> ValidationReport:
    report = ValidationReport(str(archive_path))
    try:
        manifest, results, failures = read_result_archive(archive_path)
    except Exception as exc:
        report.errors.append(str(exc))
        return report
    validate_manifest(manifest, assignment, expected_prompt_sha256, report)
    report.failed_rows = len(failures)
    db_rows = fetch_dataset_rows(db_path, [int(row.get("global_idx", -1)) for row in results if isinstance(row.get("global_idx"), int)])
    seen_indices: set[int] = set()
    for row in results:
        row_errors = validate_result_row(
            row,
            db_row=db_rows.get(row.get("global_idx")),
            assignment=assignment,
            expected_prompt_sha256=expected_prompt_sha256,
            seen_indices=seen_indices,
        )
        if row_errors:
            report.errors.extend(row_errors)
        else:
            report.valid_rows += 1
    manifest_success = manifest.get("succeeded")
    if isinstance(manifest_success, int) and manifest_success != len(results):
        report.errors.append(
            f"run_manifest.succeeded={manifest_success} but results rows={len(results)}"
        )
    return report

