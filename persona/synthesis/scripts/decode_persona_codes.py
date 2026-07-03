#!/usr/bin/env python3
"""Decode compact persona code matrices back to JSONL or CSV."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from persona.synthesis.sampler import codes_schema_path  # noqa: E402
from persona.synthesis.sampler.sampler import _unpack_nibbles  # noqa: E402

_DECODE_CHUNK_ROWS = 8192


def _load_schema(codes_path: Path, schema_path: Path | None = None) -> dict[str, Any]:
    path = schema_path or codes_schema_path(codes_path)
    with path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    if schema.get("format") != "persona_codes":
        raise ValueError(f"Unsupported schema format: {schema.get('format')!r}")
    if schema.get("format_version") not in (1, 2):
        raise ValueError(f"Unsupported persona codes version: {schema.get('format_version')!r}")
    return schema


def _iter_code_chunks(codes_path: Path, schema: dict[str, Any]) -> Any:
    """Yield decoded integer-code chunks of shape (rows_chunk, cols)."""
    rows, cols = schema["shape"]
    packing = schema.get("packing", "none")
    compression = schema.get("compression", "none")
    if packing == "nibble":
        row_bytes = schema.get("row_bytes", (cols + 1) // 2)
        row_dtype = np.uint8
    elif packing == "none":
        row_dtype = np.dtype(schema["dtype"])
        row_bytes = cols * row_dtype.itemsize
    else:
        raise ValueError(f"Unsupported codes packing: {packing!r}")

    def as_codes(raw: np.ndarray) -> np.ndarray:
        if packing == "nibble":
            return _unpack_nibbles(raw, cols)
        return raw.view(row_dtype).reshape(-1, cols)

    if compression == "gzip":
        with gzip.open(codes_path, "rb") as f:
            remaining = rows
            while remaining > 0:
                take = min(remaining, _DECODE_CHUNK_ROWS)
                blob = f.read(take * row_bytes)
                if len(blob) != take * row_bytes:
                    raise ValueError(f"Truncated codes stream in {codes_path}")
                yield as_codes(np.frombuffer(blob, dtype=np.uint8).reshape(take, row_bytes))
                remaining -= take
    elif compression == "none":
        raw = np.memmap(codes_path, dtype=np.uint8, mode="r", shape=(rows, row_bytes))
        for start in range(0, rows, _DECODE_CHUNK_ROWS):
            yield as_codes(np.asarray(raw[start : min(start + _DECODE_CHUNK_ROWS, rows)]))
    else:
        raise ValueError(f"Unsupported codes compression: {compression!r}")


def _iter_decoded_rows(
    codes_path: Path,
    schema: dict[str, Any],
) -> Any:
    columns = schema["columns"]
    values = [col["values"] for col in columns]
    names = [col["id"] for col in columns]
    for chunk in _iter_code_chunks(codes_path, schema):
        for row in chunk:
            yield {name: value_map[int(code)] for name, value_map, code in zip(names, values, row)}


def decode_codes_to_file(
    codes_path: str | Path,
    out: str | Path,
    *,
    fmt: str = "jsonl",
    schema_path: str | Path | None = None,
) -> dict[str, Any]:
    if fmt not in {"jsonl", "csv"}:
        raise ValueError(f"Unsupported decode format: {fmt}")

    codes = Path(codes_path)
    dest = Path(out)
    schema = _load_schema(codes, Path(schema_path) if schema_path is not None else None)
    rows, cols = schema["shape"]
    dest.parent.mkdir(parents=True, exist_ok=True)

    with dest.open("w", encoding="utf-8", newline="") as f:
        decoded_rows = _iter_decoded_rows(codes, schema)
        if fmt == "jsonl":
            for row in decoded_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        else:
            fieldnames = [col["id"] for col in schema["columns"]]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(decoded_rows)

    return {
        "codes": str(codes),
        "schema": str(Path(schema_path) if schema_path is not None else codes_schema_path(codes)),
        "out": str(dest),
        "format": fmt,
        "samples": rows,
        "columns": cols,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codes", type=Path, required=True)
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    args = parser.parse_args()

    meta = decode_codes_to_file(
        args.codes,
        args.out,
        fmt=args.format,
        schema_path=args.schema,
    )
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
