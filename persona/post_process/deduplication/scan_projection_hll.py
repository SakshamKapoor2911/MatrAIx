#!/usr/bin/env python3
"""Scan one packed synthetic shard into mergeable projection HLL sketches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from persona.post_process.deduplication.hll import update_registers
from persona.synthesis.scripts.decode_persona_codes import _iter_code_chunks, _load_schema


def _load_rejections(path: Path, rows: int) -> np.ndarray:
    packed = np.fromfile(path, dtype=np.uint8)
    rejected = np.unpackbits(packed, bitorder="little", count=rows).astype(np.bool_)
    if len(rejected) != rows:
        raise ValueError(f"rejection bitmap has {len(rejected)} bits, expected {rows}")
    return rejected


def scan(
    source: Path,
    rejection_bitmap: Path,
    config_path: Path,
    out: Path,
) -> dict[str, Any]:
    schema = _load_schema(source)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    rows = int(schema["shape"][0])
    rejected = _load_rejections(rejection_bitmap, rows)
    column_index = {str(column["id"]): index for index, column in enumerate(schema["columns"])}
    precision = int(config["hll_precision"])
    registers = {
        projection["id"]: np.zeros(1 << precision, dtype=np.uint8)
        for projection in config["projections"]
    }
    projection_columns = {
        projection["id"]: [column_index[field["id"]] for field in projection["fields"]]
        for projection in config["projections"]
    }

    offset = 0
    kept_rows = 0
    for codes in _iter_code_chunks(source, schema):
        chunk_rows = codes.shape[0]
        keep = ~rejected[offset : offset + chunk_rows]
        kept_rows += int(np.count_nonzero(keep))
        if np.any(keep):
            kept_codes = codes[keep]
            for projection_id, columns in projection_columns.items():
                signatures = np.zeros(len(kept_codes), dtype=np.uint64)
                for position, column in enumerate(columns):
                    signatures |= kept_codes[:, column].astype(np.uint64) << np.uint64(4 * position)
                update_registers(registers[projection_id], signatures, precision)
        offset += chunk_rows
    if offset != rows:
        raise ValueError(f"scanned {offset} rows, expected {rows}")

    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_suffix(out.suffix + ".part")
    arrays = {f"registers__{key}": value for key, value in registers.items()}
    arrays["rows"] = np.asarray(rows, dtype=np.uint64)
    arrays["kept_rows"] = np.asarray(kept_rows, dtype=np.uint64)
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    os.replace(temporary, out)
    report = {
        "source": str(source),
        "rejection_bitmap": str(rejection_bitmap),
        "config": str(config_path),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "rows": rows,
        "kept_rows": kept_rows,
        "out": str(out),
    }
    report_path = out.with_suffix(".json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--rejection-bitmap", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(scan(args.source, args.rejection_bitmap, args.config, args.out), indent=2))


if __name__ == "__main__":
    main()