#!/usr/bin/env python3
"""Scan one persona shard and write a non-destructive rejection bitmap."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Iterator, TextIO

import numpy as np

from persona.post_process.quality_filter.conflicts import (
    CompiledRule,
    compile_hard_rules,
    evaluate_hard_conflicts,
)
from persona.synthesis.scripts.decode_persona_codes import _iter_code_chunks, _load_schema


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RULES = Path(__file__).with_name("contradictions.json")
DEFAULT_SCHEMA = REPO_ROOT / "persona/schema/dimensions.json"
JSONL_CHUNK_ROWS = 4096


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def _atomic_paths(output_prefix: Path) -> tuple[Path, Path, Path, Path]:
    bitmap = output_prefix.with_suffix(".reject.bits")
    report = output_prefix.with_suffix(".report.json")
    return bitmap, report, bitmap.with_suffix(bitmap.suffix + ".part"), report.with_suffix(report.suffix + ".part")


def _write_bitmap_chunk(handle: Any, rejected: np.ndarray) -> None:
    handle.write(np.packbits(rejected, bitorder="little").tobytes())


def _scan_code_chunks(
    chunks: Iterable[np.ndarray],
    rules: list[CompiledRule],
    bitmap_part: Path,
) -> tuple[int, int, Counter[str]]:
    rows = rejected_rows = 0
    counts: Counter[str] = Counter()
    with bitmap_part.open("wb") as handle:
        for codes in chunks:
            rejected, chunk_counts = evaluate_hard_conflicts(codes, rules)
            _write_bitmap_chunk(handle, rejected)
            rows += codes.shape[0]
            rejected_rows += int(np.count_nonzero(rejected))
            counts.update(chunk_counts)
    return rows, rejected_rows, counts


def _needed_columns(
    rules_document: dict[str, Any],
    dimensions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    needed: set[str] = set()
    for rule in rules_document.get("conditional_masks", []):
        needed.add(str(rule["target"]))
        needed.update(str(field_id) for field_id in rule.get("condition", {}))
    by_id = {str(dimension["id"]): dimension for dimension in dimensions}
    missing = sorted(needed - set(by_id))
    if missing:
        raise ValueError(f"rules reference fields absent from schema: {missing}")
    return [by_id[field_id] for field_id in sorted(needed)]


def _iter_jsonl_code_chunks(
    source: Path,
    columns: list[dict[str, Any]],
    unknown_values: Counter[str],
) -> Iterator[np.ndarray]:
    column_index = {str(column["id"]): index for index, column in enumerate(columns)}
    value_codes = {
        str(column["id"]): {
            str(value): code for code, value in enumerate(column.get("values", []))
        }
        for column in columns
    }
    batch: list[np.ndarray] = []
    with _open_text(source) as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON: {source}:{line_number}") from error
            fields = row.get("fields")
            if not isinstance(fields, list):
                raise ValueError(f"row lacks fields list: {source}:{line_number}")
            codes = np.full(len(columns), 255, dtype=np.uint8)
            for field in fields:
                if not isinstance(field, dict):
                    continue
                field_id = str(field.get("field_id") or "")
                if field_id not in column_index:
                    continue
                value = field.get("value")
                if value is None or value == "":
                    continue
                code = value_codes[field_id].get(str(value))
                if code is None:
                    unknown_values[f"{field_id}={value}"] += 1
                    continue
                codes[column_index[field_id]] = code
            batch.append(codes)
            if len(batch) == JSONL_CHUNK_ROWS:
                yield np.stack(batch)
                batch.clear()
    if batch:
        yield np.stack(batch)


def scan_shard(
    *,
    dataset: str,
    mode: str,
    source: Path,
    output_prefix: Path,
    rules_path: Path = DEFAULT_RULES,
    schema_path: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    bitmap, report_path, bitmap_part, report_part = _atomic_paths(output_prefix)
    if bitmap.exists() and report_path.exists() and not force:
        return _load_json(report_path)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    bitmap_part.unlink(missing_ok=True)
    report_part.unlink(missing_ok=True)

    rules_document = _load_json(rules_path)
    rules_sha256 = hashlib.sha256(rules_path.read_bytes()).hexdigest()
    unknown_values: Counter[str] = Counter()

    if mode == "codes":
        code_schema = _load_schema(source, schema_path)
        rules = compile_hard_rules(rules_document, code_schema["columns"])
        rows, rejected_rows, counts = _scan_code_chunks(
            _iter_code_chunks(source, code_schema), rules, bitmap_part
        )
        expected_rows = int(code_schema["shape"][0])
        effective_schema = schema_path or Path(f"{source}.schema.json")
    elif mode == "jsonl":
        effective_schema = schema_path or DEFAULT_SCHEMA
        dimensions_document = _load_json(effective_schema)
        columns = _needed_columns(rules_document, dimensions_document["dimensions"])
        rules = compile_hard_rules(rules_document, columns)
        rows, rejected_rows, counts = _scan_code_chunks(
            _iter_jsonl_code_chunks(source, columns, unknown_values), rules, bitmap_part
        )
        expected_rows = None
    else:
        raise ValueError(f"unsupported scan mode: {mode}")

    if len(rules) != len(rules_document["conditional_masks"]):
        raise ValueError(
            f"compiled {len(rules)} of {len(rules_document['conditional_masks'])} rules"
        )
    if expected_rows is not None and rows != expected_rows:
        raise ValueError(f"scanned {rows} rows but schema declares {expected_rows}")

    report = {
        "format": "persona_quality_filter_report",
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset,
        "mode": mode,
        "source": str(source),
        "source_size": source.stat().st_size,
        "schema": str(effective_schema),
        "rules": str(rules_path),
        "rules_sha256": rules_sha256,
        "compiled_rules": len(rules),
        "rows": rows,
        "rejected_rows": rejected_rows,
        "kept_rows": rows - rejected_rows,
        "rejected_share": rejected_rows / rows if rows else 0.0,
        "rule_violation_counts": dict(counts.most_common()),
        "unknown_relevant_values": dict(unknown_values.most_common()),
        "bitmap": str(bitmap),
        "bitmap_encoding": "numpy.packbits bitorder=little; one bit per source row; 1=reject",
    }
    report_part.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(bitmap_part, bitmap)
    os.replace(report_part, report_path)
    return report


def _task_from_manifest(path: Path, task_index: int) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if index == task_index:
                task = json.loads(line)
                if not isinstance(task, dict):
                    raise ValueError(f"manifest task {task_index} is not an object")
                return task
    raise IndexError(f"manifest has no task index {task_index}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--task-index", type=int)
    parser.add_argument("--dataset")
    parser.add_argument("--mode", choices=["codes", "jsonl"])
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output-prefix", type=Path)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.manifest is not None:
        if args.task_index is None:
            parser.error("--manifest requires --task-index")
        task = _task_from_manifest(args.manifest, args.task_index)
        report = scan_shard(
            dataset=str(task["dataset"]),
            mode=str(task["mode"]),
            source=Path(task["source"]),
            output_prefix=Path(task["output_prefix"]),
            rules_path=args.rules,
            schema_path=Path(task["schema"]) if task.get("schema") else None,
            force=args.force,
        )
    else:
        if not all((args.dataset, args.mode, args.source, args.output_prefix)):
            parser.error("direct scans require --dataset, --mode, --source, and --output-prefix")
        report = scan_shard(
            dataset=args.dataset,
            mode=args.mode,
            source=args.source,
            output_prefix=args.output_prefix,
            rules_path=args.rules,
            schema_path=args.schema,
            force=args.force,
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()