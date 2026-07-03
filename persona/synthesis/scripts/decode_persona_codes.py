#!/usr/bin/env python3
"""Decode compact persona code matrices back to JSONL or CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from persona.synthesis.sampler import codes_schema_path  # noqa: E402


def _load_schema(codes_path: Path, schema_path: Path | None = None) -> dict[str, Any]:
    path = schema_path or codes_schema_path(codes_path)
    with path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    if schema.get("format") != "persona_codes":
        raise ValueError(f"Unsupported schema format: {schema.get('format')!r}")
    if schema.get("format_version") != 1:
        raise ValueError(f"Unsupported persona codes version: {schema.get('format_version')!r}")
    return schema


def _iter_decoded_rows(
    codes_path: Path,
    schema: dict[str, Any],
) -> Any:
    rows, cols = schema["shape"]
    matrix = np.memmap(codes_path, dtype=np.dtype(schema["dtype"]), mode="r", shape=(rows, cols))
    columns = schema["columns"]
    values = [col["values"] for col in columns]
    names = [col["id"] for col in columns]
    for row in matrix:
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
