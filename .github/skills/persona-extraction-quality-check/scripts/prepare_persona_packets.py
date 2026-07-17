#!/usr/bin/env python3
"""Prepare one source/extraction quality-review packet per persona.

Uses only the Python standard library. It supports a source CSV plus extracted
JSONL files, directories of JSONL shards, or ZIP archives containing JSONL.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

MISSING_TOKENS = {"", "na", "n/a", "none", "nan", "null", "<na>"}
RESPONSE_KEYS = ("response_id", "ResponseId", "source_response_id")
ROW_KEYS = ("row_index", "source_row")


@dataclass(frozen=True)
class RecordOrigin:
    container: str
    member: str | None
    line_number: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Exact source CSV or a directory containing one unambiguous filtered CSV.",
    )
    parser.add_argument(
        "--extraction",
        type=Path,
        action="append",
        required=True,
        help="Extraction JSONL, ZIP, or directory. Repeat for multiple inputs.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--rubric", type=Path, default=None)
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--seed", type=int, default=20260717)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--sample-size", type=int, default=None)
    selection.add_argument("--all", action="store_true")
    selection.add_argument(
        "--ids-file",
        type=Path,
        help="Text file containing response IDs, row indexes, or persona IDs, one per line.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--hash-inputs",
        action="store_true",
        help="Compute full SHA-256 for source and extraction containers (slower for large ZIPs).",
    )
    return parser.parse_args()


def repo_root() -> Path:
    # <repo>/.github/skills/<skill>/scripts/this_file.py
    return Path(__file__).resolve().parents[4]


def resolve_source_csv(path: Path, year: int | None) -> Path:
    path = path.resolve()
    if path.is_file():
        if path.suffix.lower() != ".csv":
            raise ValueError(f"Source must be CSV for this packetizer: {path}")
        return path
    if not path.is_dir():
        raise FileNotFoundError(f"Source path does not exist: {path}")

    patterns: list[str] = []
    if year is not None:
        patterns.extend(
            [
                f"results_{year}_completeness_60.csv",
                f"results_{year}_completeness_60_attention.csv",
            ]
        )
    patterns.extend(["results_*_completeness_60.csv", "results_*_completeness_60_attention.csv"])

    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(path.glob(pattern))
    candidates = sorted(set(p.resolve() for p in candidates if p.is_file()))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(
            f"No filtered completeness source CSV found in {path}; pass the exact CSV with --source."
        )
    rendered = "\n".join(f"- {candidate}" for candidate in candidates)
    raise ValueError(
        "Multiple plausible source CSVs found; pass the exact file used for extraction:\n" + rendered
    )


def iter_jsonl_files(path: Path) -> Iterator[Path]:
    if path.is_file() and path.suffix.lower() == ".jsonl":
        yield path.resolve()
        return
    if path.is_dir():
        for child in sorted(path.rglob("*.jsonl")):
            if child.is_file():
                yield child.resolve()
        return
    raise ValueError(f"Not a JSONL file or directory: {path}")


def iter_extraction_records(paths: list[Path]) -> Iterator[tuple[dict[str, Any], RecordOrigin]]:
    for input_path in paths:
        path = input_path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"Extraction path does not exist: {path}")
        if path.is_file() and path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                members = sorted(
                    (
                        info
                        for info in archive.infolist()
                        if info.filename.lower().endswith(".jsonl")
                    ),
                    key=lambda info: info.filename,
                )
                if not members:
                    raise ValueError(f"ZIP contains no JSONL files: {path}")
                for member in members:
                    with archive.open(member) as handle:
                        for line_number, raw_line in enumerate(handle, start=1):
                            if not raw_line.strip():
                                continue
                            try:
                                record = json.loads(raw_line)
                            except json.JSONDecodeError as error:
                                raise ValueError(
                                    f"Invalid JSON at {path}!{member.filename}:{line_number}: {error}"
                                ) from error
                            if not isinstance(record, dict):
                                raise ValueError(
                                    f"Record is not an object at {path}!{member.filename}:{line_number}"
                                )
                            yield record, RecordOrigin(str(path), member.filename, line_number)
            continue

        files = list(iter_jsonl_files(path))
        if not files:
            raise ValueError(f"No JSONL files found under {path}")
        for jsonl_path in files:
            with jsonl_path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise ValueError(
                            f"Invalid JSON at {jsonl_path}:{line_number}: {error}"
                        ) from error
                    if not isinstance(record, dict):
                        raise ValueError(f"Record is not an object at {jsonl_path}:{line_number}")
                    yield record, RecordOrigin(str(jsonl_path), None, line_number)


def first_present(record: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return None


def normalize_response_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_row_index(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid row index: {value!r}") from error


def fields_from_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    fields = record.get("fields")
    if fields is None and isinstance(record.get("persona"), dict):
        fields = record["persona"].get("fields")
    if not isinstance(fields, list) or any(not isinstance(field, dict) for field in fields):
        raise ValueError("Extraction record must contain a list of field objects at 'fields'.")
    return fields


def extraction_identity(record: dict[str, Any]) -> tuple[str | None, int | None, str | None]:
    response_id = normalize_response_id(first_present(record, RESPONSE_KEYS))
    row_index = normalize_row_index(first_present(record, ROW_KEYS))
    year_value = record.get("year")
    year = normalize_response_id(year_value)
    return response_id, row_index, year


def identity_key(record: dict[str, Any]) -> str:
    response_id, row_index, year = extraction_identity(record)
    prefix = year or "unknown-year"
    if response_id is not None:
        return f"{prefix}:response:{response_id}"
    if row_index is not None:
        return f"{prefix}:row:{row_index}"
    for key in ("global_idx", "uuid", "qid", "task_id"):
        value = record.get(key)
        if value is not None and str(value).strip():
            return f"{prefix}:{key}:{str(value).strip()}"
    raise ValueError("Extraction record has no stable identity field.")


def sanitize_component(value: str, limit: int = 120) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return (clean or "persona")[:limit]


def load_source_rows(source_csv: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    rows: list[dict[str, str]] = []
    by_response: dict[str, int] = {}
    with source_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Source CSV has no header: {source_csv}")
        for row_index, raw_row in enumerate(reader):
            row = {str(key): "" if value is None else str(value) for key, value in raw_row.items()}
            rows.append(row)
            response_id = normalize_response_id(row.get("ResponseId"))
            if response_id is not None:
                if response_id in by_response:
                    raise ValueError(f"Duplicate ResponseId {response_id!r} in {source_csv}")
                by_response[response_id] = row_index
    if not rows:
        raise ValueError(f"Source CSV has no data rows: {source_csv}")
    return rows, by_response


def resolve_source_row(
    record: dict[str, Any], source_rows: list[dict[str, str]], by_response: dict[str, int]
) -> tuple[int, dict[str, str], str | None]:
    response_id, row_index, _ = extraction_identity(record)
    response_row_index = by_response.get(response_id) if response_id is not None else None

    if response_id is not None and response_row_index is None:
        raise ValueError(f"Extraction response_id {response_id!r} has no source CSV match.")
    if row_index is not None and not 0 <= row_index < len(source_rows):
        raise ValueError(f"Extraction row_index {row_index} is outside source CSV range.")
    if response_row_index is not None and row_index is not None and response_row_index != row_index:
        raise ValueError(
            f"Identity mismatch: response_id {response_id!r} is source row {response_row_index}, "
            f"but extraction row_index is {row_index}."
        )

    selected_index = response_row_index if response_row_index is not None else row_index
    if selected_index is None:
        raise ValueError("Cannot pair extraction to source: neither response_id nor row_index is usable.")
    source_row = source_rows[selected_index]
    source_response_id = normalize_response_id(source_row.get("ResponseId"))
    if response_id is not None and source_response_id != response_id:
        raise ValueError(
            f"Identity mismatch after join: extraction {response_id!r}, source {source_response_id!r}."
        )
    return selected_index, source_row, source_response_id


def present_source_profile(source_row: dict[str, str]) -> list[dict[str, str]]:
    profile: list[dict[str, str]] = []
    for column, raw_value in source_row.items():
        value = raw_value.strip()
        if value.lower() in MISSING_TOKENS:
            continue
        profile.append({"column": column, "value": raw_value})
    return profile


def load_dimensions(schema_path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    dimensions = payload.get("dimensions") if isinstance(payload, dict) else None
    if not isinstance(dimensions, list):
        raise ValueError(f"Schema has no dimensions list: {schema_path}")
    result: dict[str, dict[str, Any]] = {}
    for dimension in dimensions:
        if isinstance(dimension, dict) and isinstance(dimension.get("id"), str):
            result[dimension["id"]] = dimension
    return result


def file_fingerprint(path: Path, full_hash: bool) -> dict[str, Any]:
    stat = path.stat()
    result: dict[str, Any] = {
        "path": str(path.resolve()),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    if full_hash:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        result["sha256"] = digest.hexdigest()
    return result


def load_requested_ids(path: Path) -> set[str]:
    ids = {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if not ids:
        raise ValueError(f"IDs file is empty: {path}")
    return ids


def record_matches_ids(record: dict[str, Any], requested: set[str]) -> bool:
    response_id, row_index, _ = extraction_identity(record)
    candidates = {identity_key(record)}
    if response_id is not None:
        candidates.add(response_id)
    if row_index is not None:
        candidates.add(str(row_index))
    return not candidates.isdisjoint(requested)


def select_records(
    records: Iterator[tuple[dict[str, Any], RecordOrigin]],
    sample_size: int | None,
    seed: int,
    requested_ids: set[str] | None,
) -> tuple[list[tuple[dict[str, Any], RecordOrigin]], int]:
    rng = random.Random(seed)
    selected: list[tuple[dict[str, Any], RecordOrigin]] = []
    seen_keys: set[str] = set()
    total = 0

    for record, origin in records:
        key = identity_key(record)
        if key in seen_keys:
            raise ValueError(f"Duplicate extraction identity {key!r} at {origin}")
        seen_keys.add(key)
        total += 1

        if requested_ids is not None:
            if record_matches_ids(record, requested_ids):
                selected.append((record, origin))
            continue

        if sample_size is None:
            selected.append((record, origin))
            continue
        if len(selected) < sample_size:
            selected.append((record, origin))
            continue
        replacement = rng.randrange(total)
        if replacement < sample_size:
            selected[replacement] = (record, origin)

    if requested_ids is not None:
        matched: set[str] = set()
        for record, _ in selected:
            response_id, row_index, _ = extraction_identity(record)
            matched.add(identity_key(record))
            if response_id is not None:
                matched.add(response_id)
            if row_index is not None:
                matched.add(str(row_index))
        missing = sorted(requested_ids - matched)
        if missing:
            raise ValueError(f"Requested IDs not found ({len(missing)}): {missing[:20]}")
    return selected, total


def main() -> int:
    args = parse_args()
    root = repo_root()
    source_csv = resolve_source_csv(args.source, args.year)
    schema_path = (args.schema or (root / "persona/schema/dimensions.json")).resolve()
    rubric_path = (
        args.rubric
        or (root / "persona/human_extraction/docs/EXTRACTION_QUALITY_RUBRIC.md")
    ).resolve()
    if not schema_path.is_file():
        raise FileNotFoundError(f"Dimension schema not found: {schema_path}")
    if not rubric_path.is_file():
        raise FileNotFoundError(f"Canonical rubric not found: {rubric_path}")

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        if not args.overwrite:
            raise FileExistsError(f"Output directory is not empty: {output}; use --overwrite.")
        shutil.rmtree(output)
    packets_dir = output / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)

    source_rows, by_response = load_source_rows(source_csv)
    dimensions = load_dimensions(schema_path)
    requested_ids = load_requested_ids(args.ids_file) if args.ids_file else None
    sample_size = None if args.all or requested_ids is not None else (args.sample_size or 100)
    if sample_size is not None and sample_size <= 0:
        raise ValueError("--sample-size must be positive")

    extraction_paths = [path.resolve() for path in args.extraction]
    selected, total_extractions = select_records(
        iter_extraction_records(extraction_paths), sample_size, args.seed, requested_ids
    )
    if not selected:
        raise ValueError("No extraction records selected.")

    def sort_key(item: tuple[dict[str, Any], RecordOrigin]) -> tuple[int, str]:
        response_id, row_index, _ = extraction_identity(item[0])
        return (row_index if row_index is not None else sys.maxsize, response_id or "")

    selected.sort(key=sort_key)
    manifest_path = output / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as manifest:
        for sequence, (record, origin) in enumerate(selected, start=1):
            source_index, source_row, source_response_id = resolve_source_row(
                record, source_rows, by_response
            )
            response_id, row_index, record_year = extraction_identity(record)
            year = record_year or (str(args.year) if args.year is not None else "unknown-year")
            id_value = response_id or str(row_index if row_index is not None else source_index)
            persona_id = f"stackoverflow-{year}-response-{id_value}"
            fields = fields_from_record(record)
            emitted_ids = [str(field.get("field_id")) for field in fields]
            emitted_schema = [dimensions[field_id] for field_id in emitted_ids if field_id in dimensions]
            missing_schema_ids = sorted(set(emitted_ids) - dimensions.keys())
            metadata = {key: value for key, value in record.items() if key not in {"fields", "persona"}}
            packet = {
                "packet_version": "1.0",
                "persona_id": persona_id,
                "identity": {
                    "year": year,
                    "response_id": source_response_id or response_id,
                    "row_index": source_index,
                },
                "source": {
                    "path": str(source_csv),
                    "row_index": source_index,
                    "response_id": source_response_id,
                    "source_profile": present_source_profile(source_row),
                },
                "extracted_persona": {
                    "origin": {
                        "container": origin.container,
                        "member": origin.member,
                        "line_number": origin.line_number,
                    },
                    "metadata": metadata,
                    "fields": fields,
                },
                "emitted_dimension_schema": emitted_schema,
                "missing_schema_field_ids": missing_schema_ids,
                "rubric_path": str(rubric_path),
            }
            filename = f"{sequence:06d}__{sanitize_component(persona_id)}.json"
            packet_path = packets_dir / filename
            packet_path.write_text(
                json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            manifest_record = {
                "sequence": sequence,
                "persona_id": persona_id,
                "response_id": source_response_id or response_id,
                "row_index": source_index,
                "packet_path": str(packet_path),
                "extracted_field_count": len(fields),
                "source_present_field_count": len(packet["source"]["source_profile"]),
                "missing_schema_field_ids": missing_schema_ids,
            }
            manifest.write(json.dumps(manifest_record, ensure_ascii=False) + "\n")

    rubric_sha = hashlib.sha256(rubric_path.read_bytes()).hexdigest()
    config = {
        "packet_version": "1.0",
        "source": file_fingerprint(source_csv, args.hash_inputs),
        "extractions": [
            file_fingerprint(path, args.hash_inputs)
            if path.is_file()
            else {"path": str(path), "type": "directory"}
            for path in extraction_paths
        ],
        "schema_path": str(schema_path),
        "rubric_path": str(rubric_path),
        "rubric_sha256": rubric_sha,
        "seed": args.seed,
        "selection": (
            "all" if args.all else "ids" if requested_ids is not None else "sample"
        ),
        "requested_sample_size": sample_size,
        "total_extraction_records": total_extractions,
        "selected_personas": len(selected),
    }
    (output / "run_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "source_csv": str(source_csv),
                "total_extraction_records": total_extractions,
                "selected_personas": len(selected),
                "manifest": str(manifest_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # noqa: BLE001 - CLI should fail with a concise message.
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
