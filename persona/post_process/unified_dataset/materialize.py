#!/usr/bin/env python3
"""Materialize physical Parquet shards for the unified Persona8B dataset."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from persona.post_process.unified_dataset.schema import (
    ATTRIBUTE_BYTES,
    ATTRIBUTE_OVERRIDE_TYPE,
    DESCRIPTION_TYPE,
    GROUNDING_TYPE,
    NULL_BITMAP_BYTES,
    UNIFIED_SCHEMA,
    AttributeCodec,
    fixed_binary_array,
)


READ_ROWS = 65_536


def _bitmap(path: Path, rows: int) -> np.ndarray:
    packed = np.fromfile(path, dtype=np.uint8)
    return np.unpackbits(packed, bitorder="little", count=rows).astype(bool)


def _json_lines(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


class DatasetWriter:
    def __init__(
        self,
        output_dir: Path,
        prefix: str,
        rows_per_file: int,
        row_group_size: int,
    ) -> None:
        self.output_dir = output_dir
        self.prefix = prefix
        self.rows_per_file = rows_per_file
        self.row_group_size = row_group_size
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.part = 0
        self.current_rows = 0
        self.total_rows = 0
        self.paths: list[Path] = []
        self.writer: pq.ParquetWriter | None = None

    def _open(self) -> None:
        path = self.output_dir / f"{self.prefix}-part-{self.part:04d}.parquet"
        temporary = path.with_suffix(".parquet.part")
        if temporary.exists():
            temporary.unlink()
        self.paths.append(path)
        self.writer = pq.ParquetWriter(
            temporary,
            UNIFIED_SCHEMA,
            compression="zstd",
            compression_level=3,
            use_dictionary=["source", "source_record_id"],
            write_statistics=True,
        )

    def _close_part(self) -> None:
        if self.writer is None:
            return
        self.writer.close()
        path = self.paths[-1]
        path.with_suffix(".parquet.part").replace(path)
        self.writer = None
        self.current_rows = 0
        self.part += 1

    def write(self, table: pa.Table) -> None:
        if table.schema != UNIFIED_SCHEMA:
            table = table.cast(UNIFIED_SCHEMA)
        offset = 0
        while offset < len(table):
            if self.writer is None:
                self._open()
            available = self.rows_per_file - self.current_rows
            take = min(available, len(table) - offset)
            assert self.writer is not None
            self.writer.write_table(table.slice(offset, take), row_group_size=self.row_group_size)
            self.current_rows += take
            self.total_rows += take
            offset += take
            if self.current_rows == self.rows_per_file:
                self._close_part()

    def close(self) -> dict[str, Any]:
        self._close_part()
        return {
            "rows": self.total_rows,
            "files": len(self.paths),
            "bytes": sum(path.stat().st_size for path in self.paths),
            "paths": [str(path) for path in self.paths],
        }


def _synthetic_table(packed: np.ndarray, source_rows: np.ndarray) -> pa.Table:
    count = len(packed)
    return pa.Table.from_arrays(
        [
            pa.array(["synthetic"] * count, type=pa.string()),
            pa.array(source_rows, type=pa.uint64()),
            pa.nulls(count, type=pa.string()),
            fixed_binary_array(packed, ATTRIBUTE_BYTES),
            pa.nulls(count, type=pa.binary(NULL_BITMAP_BYTES)),
            pa.nulls(count, type=ATTRIBUTE_OVERRIDE_TYPE),
            pa.array(np.zeros(count, dtype=bool)),
            pa.nulls(count, type=DESCRIPTION_TYPE),
            pa.nulls(count, type=GROUNDING_TYPE),
            pa.nulls(count, type=pa.string()),
        ],
        schema=UNIFIED_SCHEMA,
    )


def materialize_synthetic(args: argparse.Namespace) -> dict[str, Any]:
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    rows = int(schema["shape"][0])
    if int(schema["row_bytes"]) != ATTRIBUTE_BYTES:
        raise ValueError("Synthetic row width does not match the unified schema")
    rejected = _bitmap(args.reject_bitmap, rows)
    if args.overlay_bitmap:
        rejected |= _bitmap(args.overlay_bitmap, rows)
    writer = DatasetWriter(args.output_dir, f"synthetic-{args.shard:04d}", args.rows_per_file, args.row_group_size)
    offset = 0
    with gzip.open(args.source, "rb") as handle:
        while offset < rows:
            remaining = rows - offset
            if args.max_source_rows:
                remaining = min(remaining, args.max_source_rows - offset)
                if remaining <= 0:
                    break
            take = min(READ_ROWS, remaining)
            raw = handle.read(take * ATTRIBUTE_BYTES)
            if len(raw) != take * ATTRIBUTE_BYTES:
                raise ValueError(f"Truncated synthetic source at row {offset}")
            matrix = np.frombuffer(raw, dtype=np.uint8).reshape(take, ATTRIBUTE_BYTES)
            keep = ~rejected[offset : offset + take]
            if keep.any():
                source_rows = np.arange(offset, offset + take, dtype=np.uint64)
                source_rows += np.uint64(args.shard * rows)
                writer.write(_synthetic_table(matrix[keep], source_rows[keep]))
            offset += take
            if args.max_source_rows and offset >= args.max_source_rows:
                break
    report = writer.close()
    report.update(
        {
            "source": "synthetic",
            "task": args.shard,
            "source_rows_read": offset,
            "description_rows": 0,
            "grounding_rows": 0,
            "override_rows": 0,
        }
    )
    _write_report(args.report, report)
    return report


def _meaningful_descriptions(fields: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    descriptions = [
        {"field_index": index, "text": field["description"]}
        for index, field in enumerate(fields)
        if field.get("description")
    ]
    return descriptions or None


def _meaningful_grounding(fields: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    grounding = []
    for index, field in enumerate(fields):
        evidence = field.get("evidence")
        confidence = field.get("confidence")
        assignment_type = field.get("assignment_type")
        if field.get("value") is None and not evidence and not confidence:
            continue
        try:
            normalized_confidence = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            normalized_confidence = None
        grounding.append(
            {
                "field_index": index,
                "evidence": evidence or None,
                "confidence": normalized_confidence,
                "assignment_type": assignment_type or None,
            }
        )
    return grounding or None


def _human_table(rows: list[dict[str, Any]]) -> pa.Table:
    return pa.Table.from_pylist(rows, schema=UNIFIED_SCHEMA)


def _human_row(
    record: dict[str, Any],
    codec: AttributeCodec,
    dataset: str,
    source_row_index: int,
) -> dict[str, Any]:
    fields_by_id = {
        field["field_id"]: field
        for field in record["fields"]
        if field.get("field_id") in codec.field_ids
    }
    fields = [fields_by_id.get(field_id, {"field_id": field_id}) for field_id in codec.field_ids]
    attributes, null_bitmap, attribute_overrides = codec.encode_fields(fields)
    descriptions = _meaningful_descriptions(fields)
    if dataset == "wiki":
        record_id = record.get("qid")
    else:
        record_id = record.get("user_id")
    metadata = {key: value for key, value in record.items() if key != "fields"}
    known_ids = set(codec.field_ids)
    seen_ids: set[str] = set()
    unmapped_fields = []
    for field in fields:
        field_id = field.get("field_id")
        if field_id not in known_ids or field_id in seen_ids:
            unmapped_fields.append(field)
        else:
            seen_ids.add(field_id)
    if unmapped_fields:
        metadata["_unmapped_fields"] = unmapped_fields
    non_numeric_confidence = []
    for index, field in enumerate(fields):
        confidence = field.get("confidence")
        if confidence is None:
            continue
        try:
            float(confidence)
        except (TypeError, ValueError):
            non_numeric_confidence.append(
                {"field_index": index, "confidence": confidence}
            )
    if non_numeric_confidence:
        metadata["_non_numeric_confidence"] = non_numeric_confidence
    return {
        "source": dataset,
        "source_row_index": source_row_index,
        "source_record_id": record_id,
        "attributes": attributes,
        "null_bitmap": null_bitmap,
        "attribute_overrides": attribute_overrides,
        "has_description": descriptions is not None,
        "descriptions": descriptions,
        "grounding": _meaningful_grounding(fields),
        "metadata_json": json.dumps(metadata, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
    }


def materialize_human(args: argparse.Namespace) -> dict[str, Any]:
    tasks = [json.loads(line) for line in args.manifest.read_text(encoding="utf-8").splitlines()]
    task = next(item for item in tasks if int(item["task_index"]) == args.task)
    rows = int(task["rows"])
    rejected = _bitmap(Path(task["quality_bitmap"]), rows)
    dedup_path = args.dedup_dir / task["dataset"] / f"task_{args.task:04d}.dedup.reject.bits"
    rejected |= _bitmap(dedup_path, rows)
    codec = AttributeCodec.from_codes_schema(args.schema)
    writer = DatasetWriter(
        args.output_dir / task["dataset"],
        f"{task['dataset']}-{args.task:04d}",
        args.rows_per_file,
        args.row_group_size,
    )
    batch: list[dict[str, Any]] = []
    read_rows = 0
    description_rows = grounding_rows = override_rows = 0
    for local_index, record in enumerate(_json_lines(Path(task["source"]))):
        read_rows += 1
        if not rejected[local_index]:
            row = _human_row(record, codec, task["dataset"], int(task["global_offset"]) + local_index)
            description_rows += int(row["has_description"])
            grounding_rows += int(row["grounding"] is not None)
            override_rows += int(row["attribute_overrides"] is not None)
            batch.append(row)
        if len(batch) >= args.batch_rows:
            writer.write(_human_table(batch))
            batch.clear()
        if args.max_source_rows and read_rows >= args.max_source_rows:
            break
    if not args.max_source_rows and read_rows != rows:
        raise ValueError(f"Expected {rows} source rows, read {read_rows}")
    if batch:
        writer.write(_human_table(batch))
    report = writer.close()
    report.update(
        {
            "source": task["dataset"],
            "task": args.task,
            "source_rows_read": read_rows,
            "description_rows": description_rows,
            "grounding_rows": grounding_rows,
            "override_rows": override_rows,
        }
    )
    _write_report(args.report, report)
    return report


def materialize_survey(args: argparse.Namespace) -> dict[str, Any]:
    codec = AttributeCodec.from_codes_schema(args.schema)
    writer = DatasetWriter(args.output_dir / "real_human_survey", "real-human-survey", args.rows_per_file, args.row_group_size)
    batch = []
    for index, record in enumerate(_json_lines(args.source)):
        attributes, null_bitmap, attribute_overrides = codec.encode_mapping(record)
        batch.append(
            {
                "source": "real_human_survey",
                "source_row_index": index,
                "source_record_id": f"real_human_survey_{index + 1:04d}",
                "attributes": attributes,
                "null_bitmap": null_bitmap,
                "attribute_overrides": attribute_overrides,
                "has_description": False,
                "descriptions": None,
                "grounding": None,
                "metadata_json": None,
            }
        )
    writer.write(_human_table(batch))
    report = writer.close()
    report.update(
        {
            "source": "real_human_survey",
            "task": 0,
            "source_rows_read": len(batch),
            "description_rows": 0,
            "grounding_rows": 0,
            "override_rows": sum(row["attribute_overrides"] is not None for row in batch),
        }
    )
    _write_report(args.report, report)
    return report


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--rows-per-file", type=int, default=1_000_000)
    parser.add_argument("--row-group-size", type=int, default=100_000)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    synthetic = subparsers.add_parser("synthetic")
    _common(synthetic)
    synthetic.add_argument("--source", type=Path, required=True)
    synthetic.add_argument("--reject-bitmap", type=Path, required=True)
    synthetic.add_argument("--overlay-bitmap", type=Path)
    synthetic.add_argument("--shard", type=int, required=True)
    synthetic.add_argument("--max-source-rows", type=int)
    synthetic.set_defaults(function=materialize_synthetic)
    human = subparsers.add_parser("human")
    _common(human)
    human.add_argument("--manifest", type=Path, required=True)
    human.add_argument("--dedup-dir", type=Path, required=True)
    human.add_argument("--task", type=int, required=True)
    human.add_argument("--batch-rows", type=int, default=512)
    human.add_argument("--max-source-rows", type=int)
    human.set_defaults(function=materialize_human)
    survey = subparsers.add_parser("survey")
    _common(survey)
    survey.add_argument("--source", type=Path, required=True)
    survey.set_defaults(function=materialize_survey)
    args = parser.parse_args()
    print(json.dumps(args.function(args), indent=2))


if __name__ == "__main__":
    main()