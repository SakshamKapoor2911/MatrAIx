#!/usr/bin/env python3
"""Conformance checker — the one contract both sides agree on.

The owner runs this on the tasks they send AND on the results they receive; the
worker runs it on the results they produce before sending. If it passes on both
sides, the formats are guaranteed to line up. Pure stdlib, no dependencies.

    python3 conformance.py --results results.jsonl --dimensions dimensions.json
    python3 conformance.py --results results.jsonl --dimensions dimensions.json \
            --tasks tasks.jsonl            # also check coverage vs the assigned tasks

Exit code 0 = conformant, 1 = violations found (printed), 2 = bad invocation.
Importable: check_results(results, dimensions, tasks=None) -> (errors, warnings).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ASSIGNMENT_TYPES = {"direct", "structured_claim", "summary_inference", "unsupported"}
RESULT_REQUIRED = ("global_idx", "fields")
FIELD_REQUIRED = ("field_id", "value", "confidence", "evidence", "assignment_type")
# Provenance the returned log should carry (which model/version/effort produced it).
RUN_PROVENANCE = ("model", "effort", "runner_version")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{ln}: invalid JSON: {exc}") from exc
    return rows


def _dim_index(dimensions: list[dict[str, Any]]) -> dict[str, set[str]]:
    """id -> set of allowed values (empty set = open value)."""
    index: dict[str, set[str]] = {}
    for d in dimensions:
        index[str(d["id"])] = {str(v) for v in d.get("values", [])}
    return index


def check_results(
    results: list[dict[str, Any]],
    dimensions: list[dict[str, Any]] | None = None,
    tasks: list[dict[str, Any]] | None = None,
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Empty errors == conformant."""
    errors: list[str] = []
    warnings: list[str] = []
    dim_values = _dim_index(dimensions) if dimensions is not None else None

    seen_idx: set[Any] = set()
    for i, rec in enumerate(results):
        where = f"result[{i}]"
        if not isinstance(rec, dict):
            errors.append(f"{where}: not a JSON object")
            continue
        for key in RESULT_REQUIRED:
            if key not in rec:
                errors.append(f"{where}: missing required key '{key}'")
        gi = rec.get("global_idx")
        if not isinstance(gi, int):
            errors.append(f"{where}: global_idx must be an integer, got {gi!r}")
        else:
            if gi in seen_idx:
                errors.append(f"{where}: duplicate global_idx {gi}")
            seen_idx.add(gi)

        run = rec.get("run")
        if not isinstance(run, dict):
            warnings.append(f"{where}: missing 'run' provenance (model/effort/runner_version)")
        else:
            missing_prov = [k for k in RUN_PROVENANCE if not run.get(k)]
            if missing_prov:
                warnings.append(f"{where}: run provenance missing {missing_prov}")

        fields = rec.get("fields")
        if not isinstance(fields, list):
            errors.append(f"{where}: 'fields' must be a list")
            continue

        seen_fids: set[str] = set()
        for j, field in enumerate(fields):
            fw = f"{where}.fields[{j}]"
            if not isinstance(field, dict):
                errors.append(f"{fw}: not a JSON object")
                continue
            for key in FIELD_REQUIRED:
                if key not in field:
                    errors.append(f"{fw}: missing required key '{key}'")
            fid = field.get("field_id")
            if not isinstance(fid, str) or not fid:
                errors.append(f"{fw}: field_id must be a non-empty string")
            else:
                if fid in seen_fids:
                    errors.append(f"{fw}: duplicate field_id '{fid}' in this record")
                seen_fids.add(fid)
                if dim_values is not None and fid not in dim_values:
                    errors.append(f"{fw}: field_id '{fid}' is not in the dimensions spec")

            value = field.get("value")
            if value is not None and not isinstance(value, str):
                errors.append(f"{fw}: value must be a string or null, got {type(value).__name__}")
            if (
                dim_values is not None
                and isinstance(fid, str)
                and fid in dim_values
                and dim_values[fid]
                and isinstance(value, str)
                and value not in dim_values[fid]
            ):
                errors.append(f"{fw}: value {value!r} not in allowed values for '{fid}'")

            conf = field.get("confidence")
            if not isinstance(conf, (int, float)) or isinstance(conf, bool) or not 0 <= conf <= 1:
                errors.append(f"{fw}: confidence must be a number in [0,1], got {conf!r}")

            atype = field.get("assignment_type")
            if atype not in ASSIGNMENT_TYPES:
                errors.append(f"{fw}: assignment_type {atype!r} not in {sorted(ASSIGNMENT_TYPES)}")

            evidence = field.get("evidence")
            if not isinstance(evidence, str):
                errors.append(f"{fw}: evidence must be a string")
            elif value is not None and not evidence.strip():
                errors.append(f"{fw}: value is set but evidence is empty")

            if atype == "unsupported" and value is not None:
                warnings.append(f"{fw}: assignment_type 'unsupported' but value is not null")

    if tasks is not None:
        task_idx = {t.get("global_idx") for t in tasks if isinstance(t.get("global_idx"), int)}
        result_idx = {
            r.get("global_idx") for r in results if isinstance(r.get("global_idx"), int)
        }
        missing = sorted(i for i in task_idx - result_idx)
        extra = sorted(i for i in result_idx - task_idx)
        if missing:
            warnings.append(
                f"coverage: {len(missing)} assigned global_idx have no result "
                f"(e.g. {missing[:5]})"
            )
        if extra:
            errors.append(
                f"coverage: {len(extra)} result global_idx are not in the assigned tasks "
                f"(e.g. {extra[:5]})"
            )

    return errors, warnings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, required=True, help="results.jsonl to check")
    ap.add_argument("--dimensions", type=Path, default=None, help="dimensions.json spec (recommended)")
    ap.add_argument("--tasks", type=Path, default=None, help="tasks.jsonl, to also check coverage")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = load_jsonl(args.results)
    dimensions = json.loads(args.dimensions.read_text(encoding="utf-8")) if args.dimensions else None
    tasks = load_jsonl(args.tasks) if args.tasks else None
    errors, warnings = check_results(results, dimensions, tasks)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    n_fields = sum(len(r.get("fields", [])) for r in results if isinstance(r, dict))
    if errors:
        print(f"\nFAIL: {len(results)} records, {n_fields} fields — {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"\nPASS: {len(results)} records, {n_fields} fields conform to the contract"
          f" ({len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
