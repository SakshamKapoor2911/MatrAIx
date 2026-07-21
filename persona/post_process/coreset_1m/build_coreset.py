#!/usr/bin/env python3
"""Build and audit the calibrated MatrAIx Persona 1M public release."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Iterator

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from persona.post_process.coreset_1m.calibration import (
    calibrate_inclusion_weights,
    deterministic_priority_sample,
)
from persona.post_process.unified_dataset.schema import ATTRIBUTE_COUNT, UNIFIED_SCHEMA


SOURCE_COUNTS = {
    "synthetic": 400_000,
    "wiki": 323_438,
    "amazon": 97_915,
    "stackoverflow": 113_120,
    "prism": 1_487,
    "gss": 63_532,
    "real_human_survey": 508,
}
HUMAN_SOURCES = tuple(source for source in SOURCE_COUNTS if source != "synthetic")
CORESET_SCHEMA = UNIFIED_SCHEMA.append(pa.field("populated_attribute_count", pa.uint16(), nullable=False)).append(
    pa.field("description_count", pa.uint16(), nullable=False)
)


def load_codebook(path: Path) -> tuple[list[str], list[list[str]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    columns = payload["columns"]
    return [column["id"] for column in columns], [column["values"] for column in columns]


def load_targets(path: Path, field_ids: list[str], values: list[list[str]]) -> tuple[dict[str, dict[int, float]], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    targets: dict[str, dict[int, float]] = {}
    for field_id, definition in payload["dimensions"].items():
        index = field_ids.index(field_id)
        codebook = {value: code for code, value in enumerate(values[index])}
        targets[field_id] = {codebook[value]: float(share) for value, share in definition["shares"].items()}
    return targets, payload


def _fixed_binary_matrix(array: pa.Array, width: int) -> np.ndarray:
    buffer = array.buffers()[1]
    if buffer is None:
        return np.zeros((len(array), width), dtype=np.uint8)
    return np.frombuffer(buffer, dtype=np.uint8, count=len(array) * width, offset=array.offset * width).reshape(len(array), width)


def decode_calibration_batch(batch: pa.RecordBatch, field_indices: list[int]) -> np.ndarray:
    """Decode selected packed fields, returning -1 for nulls or overrides."""
    attributes = _fixed_binary_matrix(batch.column("attributes"), 645)
    decoded = np.empty((len(batch), len(field_indices)), dtype=np.int16)
    for output_index, field_index in enumerate(field_indices):
        packed = attributes[:, field_index // 2]
        decoded[:, output_index] = (packed >> (4 if field_index % 2 else 0)) & 0x0F

    null_array = batch.column("null_bitmap")
    null_data = _fixed_binary_matrix(null_array, 162)
    validity_buffer = null_array.buffers()[0]
    if validity_buffer is None:
        has_bitmap = np.ones(len(batch), dtype=bool)
    else:
        validity = np.frombuffer(validity_buffer, dtype=np.uint8)
        has_bitmap = np.unpackbits(validity, bitorder="little")[null_array.offset : null_array.offset + len(batch)].astype(bool)
    for output_index, field_index in enumerate(field_indices):
        is_null = has_bitmap & (((null_data[:, field_index // 8] >> (field_index % 8)) & 1) == 1)
        decoded[is_null, output_index] = -1

    overrides = batch.column("attribute_overrides").to_pylist()
    output_by_field = {field_index: output_index for output_index, field_index in enumerate(field_indices)}
    for row_index, row_overrides in enumerate(overrides):
        for override in row_overrides or ():
            output_index = output_by_field.get(override["field_index"])
            if output_index is not None:
                decoded[row_index, output_index] = -1
    return decoded


def iter_batches(paths: list[Path], columns: list[str], *, row_groups: dict[Path, int] | None = None) -> Iterator[tuple[Path, int | None, pa.RecordBatch]]:
    for path in paths:
        parquet = pq.ParquetFile(path)
        groups = [row_groups[path]] if row_groups and path in row_groups else range(parquet.num_row_groups)
        for row_group in groups:
            for batch in parquet.iter_batches(row_groups=[row_group], batch_size=65_536, columns=columns):
                yield path, row_group, batch


def scan_candidates(
    paths: list[Path], field_indices: list[int], *, row_groups: dict[Path, int] | None = None
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    source_rows = []
    decoded_parts = []
    columns = ["source_row_index", "attributes", "null_bitmap", "attribute_overrides"]
    for _, _, batch in iter_batches(paths, columns, row_groups=row_groups):
        source_rows.append(batch.column("source_row_index").to_numpy(zero_copy_only=False))
        decoded_parts.append(decode_calibration_batch(batch, field_indices))
    rows = np.concatenate(source_rows).astype(np.uint64, copy=False)
    decoded = np.concatenate(decoded_parts)
    return rows, {str(index): decoded[:, offset] for offset, index in enumerate(field_indices)}


def named_columns(decoded: dict[str, np.ndarray], field_ids: list[str], field_indices: list[int]) -> dict[str, np.ndarray]:
    return {field_ids[index]: decoded[str(index)] for index in field_indices}


def select_rows(
    source: str,
    rows: np.ndarray,
    columns: dict[str, np.ndarray],
    targets: dict[str, dict[int, float]],
    sample_size: int,
    seed: int,
) -> np.ndarray:
    weights = calibrate_inclusion_weights(columns, targets, sample_size)
    stable_ids = (f"{source}:{int(row)}" for row in rows)
    selected_offsets = deterministic_priority_sample(stable_ids, weights, sample_size, seed)
    return rows[selected_offsets]


def counts_for_selection(columns: dict[str, np.ndarray], rows: np.ndarray, selected_rows: set[int]) -> dict[str, Counter[int]]:
    mask = np.fromiter((int(row) in selected_rows for row in rows), dtype=bool, count=len(rows))
    result: dict[str, Counter[int]] = {}
    for name, values in columns.items():
        known = values[mask]
        result[name] = Counter(int(value) for value in known if value >= 0)
    return result


def calibration_audit(
    targets: dict[str, dict[int, float]],
    values: list[list[str]],
    field_ids: list[str],
    field_indices: list[int],
    human_counts: dict[str, Counter[int]],
    synthetic_counts: dict[str, Counter[int]],
) -> dict[str, Any]:
    audit = {}
    for field_index in field_indices:
        name = field_ids[field_index]
        combined = Counter(human_counts[name])
        combined.update(synthetic_counts[name])
        known = sum(combined.values())
        categories = {}
        for code, target_share in targets[name].items():
            achieved = combined[code] / known if known else None
            categories[values[field_index][code]] = {
                "target": target_share,
                "achieved": achieved,
                "absolute_error": abs(achieved - target_share) if achieved is not None else None,
                "rows": combined[code],
            }
        audit[name] = {
            "known_rows": known,
            "missing_rows": 1_000_000 - known,
            "categories": categories,
            "max_absolute_error": max(item["absolute_error"] for item in categories.values()),
        }
    return audit


def residual_targets(
    targets: dict[str, dict[int, float]], human_counts: dict[str, Counter[int]], synthetic_size: int
) -> tuple[dict[str, dict[int, float]], dict[str, dict[str, float]]]:
    residuals = {}
    diagnostics = {}
    for name, target in targets.items():
        known_human = sum(human_counts[name].values())
        known_total = known_human + synthetic_size
        raw = {code: share * known_total - human_counts[name][code] for code, share in target.items()}
        clipped = {code: max(0.0, count) for code, count in raw.items()}
        total = sum(clipped.values())
        residuals[name] = {code: count / total for code, count in clipped.items()}
        diagnostics[name] = {
            "known_human": known_human,
            "negative_residual_mass": float(-sum(min(0.0, count) for count in raw.values())),
        }
    return residuals, diagnostics


def augment_table(table: pa.Table) -> pa.Table:
    null_bitmaps = table.column("null_bitmap").to_pylist()
    populated = [ATTRIBUTE_COUNT if bitmap is None else ATTRIBUTE_COUNT - sum(byte.bit_count() for byte in bitmap) for bitmap in null_bitmaps]
    descriptions = table.column("descriptions")
    description_count = pc.fill_null(pc.list_value_length(descriptions), 0).cast(pa.uint16())
    return table.append_column("populated_attribute_count", pa.array(populated, type=pa.uint16())).append_column(
        "description_count", description_count
    ).cast(CORESET_SCHEMA)


class CoresetWriter:
    def __init__(self, output_dir: Path, rows_per_file: int = 100_000) -> None:
        self.output_dir = output_dir
        self.rows_per_file = rows_per_file
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.part = 0
        self.rows = 0
        self.current_rows = 0
        self.writer: pq.ParquetWriter | None = None
        self.paths: list[Path] = []

    def _open(self) -> None:
        path = self.output_dir / f"persona-1m-{self.part:04d}.parquet"
        self.paths.append(path)
        self.writer = pq.ParquetWriter(path.with_suffix(".parquet.part"), CORESET_SCHEMA, compression="zstd", compression_level=3)

    def write(self, table: pa.Table) -> None:
        table = augment_table(table)
        offset = 0
        while offset < len(table):
            if self.writer is None:
                self._open()
            take = min(self.rows_per_file - self.current_rows, len(table) - offset)
            assert self.writer is not None
            self.writer.write_table(table.slice(offset, take), row_group_size=50_000)
            self.current_rows += take
            self.rows += take
            offset += take
            if self.current_rows == self.rows_per_file:
                self._close()

    def _close(self) -> None:
        if self.writer is None:
            return
        self.writer.close()
        path = self.paths[-1]
        path.with_suffix(".parquet.part").replace(path)
        self.writer = None
        self.current_rows = 0
        self.part += 1

    def close(self) -> None:
        self._close()


def _filter_table(table: pa.Table, selected: set[int] | None) -> pa.Table:
    if selected is None:
        return table
    rows = table.column("source_row_index").to_numpy(zero_copy_only=False)
    mask = pa.array(np.fromiter((int(row) in selected for row in rows), dtype=bool, count=len(rows)))
    return table.filter(mask)


def materialize_source(writer: CoresetWriter, paths: list[Path], selected: set[int] | None) -> Counter[str]:
    stats: Counter[str] = Counter()
    for path in paths:
        parquet = pq.ParquetFile(path)
        for batch in parquet.iter_batches(batch_size=16_384):
            table = _filter_table(pa.Table.from_batches([batch], schema=UNIFIED_SCHEMA), selected)
            if len(table):
                writer.write(table)
                stats["rows"] += len(table)
                stats["description_rows"] += int(pc.sum(table.column("has_description")).as_py())
    return stats


def materialize_synthetic_candidates(
    writer: CoresetWriter, row_groups: dict[Path, int], selected: set[int]
) -> Counter[str]:
    stats: Counter[str] = Counter()
    for path, row_group in row_groups.items():
        table = pq.ParquetFile(path).read_row_group(row_group)
        filtered = _filter_table(table, selected)
        if len(filtered):
            writer.write(filtered)
            stats["rows"] += len(filtered)
    return stats


def discover_synthetic_candidates(
    data_root: Path, *, shard_count: int, seed: int
) -> dict[Path, int]:
    if not 1 <= shard_count <= 100:
        raise ValueError("shard_count must be between 1 and 100")
    rng = np.random.default_rng(seed)
    result = {}
    for shard in sorted(rng.choice(100, size=shard_count, replace=False).tolist()):
        files = sorted((data_root / "synthetic" / f"shard_{shard:04d}").glob("*.parquet"))
        if not files:
            raise FileNotFoundError(f"Synthetic shard {shard:04d} is not materialized")
        path = files[int(rng.integers(len(files)))]
        result[path] = int(rng.integers(pq.ParquetFile(path).num_row_groups))
    return result


def source_paths(data_root: Path, source: str) -> list[Path]:
    paths = sorted((data_root / source).rglob("*.parquet"))
    if not paths:
        raise FileNotFoundError(f"No unified Parquet files found for {source}")
    return paths


def parquet_row_count(paths: list[Path]) -> int:
    return sum(pq.read_metadata(path).num_rows for path in paths)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def build(args: argparse.Namespace) -> dict[str, Any]:
    field_ids, values = load_codebook(args.codebook)
    targets, target_payload = load_targets(args.targets, field_ids, values)
    field_indices = [field_ids.index(name) for name in targets]
    all_paths = {source: source_paths(args.input_root / "data", source) for source in HUMAN_SOURCES}
    for source in HUMAN_SOURCES:
        available = parquet_row_count(all_paths[source])
        if available < SOURCE_COUNTS[source]:
            raise ValueError(f"{source}: need {SOURCE_COUNTS[source]:,} rows, found {available:,}")

    candidate_rows: dict[str, np.ndarray] = {}
    candidate_columns: dict[str, dict[str, np.ndarray]] = {}
    for source in HUMAN_SOURCES:
        rows, decoded = scan_candidates(all_paths[source], field_indices)
        candidate_rows[source] = rows
        candidate_columns[source] = named_columns(decoded, field_ids, field_indices)

    wiki_selected = select_rows(
        "wiki", candidate_rows["wiki"], candidate_columns["wiki"], targets, SOURCE_COUNTS["wiki"], args.seed
    )
    selected_by_source = {"wiki": set(map(int, wiki_selected))}
    human_counts = {name: Counter() for name in targets}
    for source in HUMAN_SOURCES:
        selected = selected_by_source.get(source, set(map(int, candidate_rows[source])))
        source_counts = counts_for_selection(candidate_columns[source], candidate_rows[source], selected)
        for name in targets:
            human_counts[name].update(source_counts[name])

    synthetic_targets, residual_diagnostics = residual_targets(targets, human_counts, SOURCE_COUNTS["synthetic"])
    synthetic_row_groups = discover_synthetic_candidates(
        args.input_root / "data",
        shard_count=args.synthetic_candidate_shards,
        seed=args.seed,
    )
    synthetic_rows, synthetic_decoded = scan_candidates(
        list(synthetic_row_groups), field_indices, row_groups=synthetic_row_groups
    )
    synthetic_columns = named_columns(synthetic_decoded, field_ids, field_indices)
    synthetic_selected_array = select_rows(
        "synthetic", synthetic_rows, synthetic_columns, synthetic_targets, SOURCE_COUNTS["synthetic"], args.seed + 1
    )
    selected_by_source["synthetic"] = set(map(int, synthetic_selected_array))
    synthetic_counts = counts_for_selection(
        synthetic_columns, synthetic_rows, selected_by_source["synthetic"]
    )

    if args.output.exists():
        shutil.rmtree(args.output)
    writer = CoresetWriter(args.output / "data")
    source_stats = {}
    for source in HUMAN_SOURCES:
        selected = selected_by_source.get(source)
        source_stats[source] = dict(materialize_source(writer, all_paths[source], selected))
    source_stats["synthetic"] = dict(
        materialize_synthetic_candidates(writer, synthetic_row_groups, selected_by_source["synthetic"])
    )
    writer.close()
    actual_counts = {source: int(stats.get("rows", 0)) for source, stats in source_stats.items()}
    if actual_counts != SOURCE_COUNTS or writer.rows != 1_000_000:
        raise ValueError(f"Final source counts are incorrect: {actual_counts}; total={writer.rows}")

    shutil.copy2(args.codebook, args.output / "persona_codes.schema.json")
    shutil.copy2(args.targets, args.output / "calibration_targets.json")
    parquet_files = []
    for path in writer.paths:
        parquet_files.append({
            "path": str(path.relative_to(args.output)),
            "rows": pq.read_metadata(path).num_rows,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    audit = {
        "targets": target_payload,
        "residual_diagnostics": residual_diagnostics,
        "calibration": calibration_audit(
            targets, values, field_ids, field_indices, human_counts, synthetic_counts
        ),
        "source_stats": source_stats,
        "synthetic_candidate_rows": len(synthetic_rows),
        "synthetic_candidate_row_groups": [
            {
                "path": str(path.relative_to(args.input_root)),
                "row_group": row_group,
                "rows": pq.ParquetFile(path).metadata.row_group(row_group).num_rows,
            }
            for path, row_group in synthetic_row_groups.items()
        ],
    }
    (args.output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "format": "matraix_persona_1m_coreset",
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "rows": writer.rows,
        "sources": actual_counts,
        "human_grounded_rows": 600_000,
        "synthetic_rows": 400_000,
        "files": parquet_files,
        "bytes": sum(item["bytes"] for item in parquet_files),
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--codebook", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--synthetic-candidate-shards", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260720)
    args = parser.parse_args()
    print(json.dumps(build(args), indent=2))


if __name__ == "__main__":
    main()