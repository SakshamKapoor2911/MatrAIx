#!/usr/bin/env python3
"""Extract reusable MinHash signatures for one human persona shard."""

from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
from typing import Any, TextIO

from datasketch import MinHash
import numpy as np
import xxhash


NUM_PERM = 64
SEED = 20260719
NULL_VALUES = {"", "null", "none", "unknown", "unsupported", "prefer not to say"}


def _open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def _load_rejections(path: Path, rows: int) -> np.ndarray:
    return np.unpackbits(np.fromfile(path, dtype=np.uint8), bitorder="little", count=rows).astype(np.bool_)


def _tokens(row: dict[str, Any]) -> list[bytes]:
    fields = row.get("fields")
    if not isinstance(fields, list):
        return []
    tokens = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        field_id = str(field.get("field_id") or "").strip()
        value = str(field.get("value") or "").strip()
        if not field_id or value.lower() in NULL_VALUES:
            continue
        tokens.append(f"{field_id}={value}".encode("utf-8"))
    tokens.sort()
    return tokens


def scan(task: dict[str, Any], num_perm: int = NUM_PERM) -> dict[str, Any]:
    source = Path(task["source"])
    rows = int(task["rows"])
    offset = int(task["global_offset"])
    output = Path(task["output"])
    rejected = _load_rejections(Path(task["quality_bitmap"]), rows)
    if len(rejected) != rows:
        raise ValueError(f"quality bitmap does not cover {rows} rows")

    source_rows: list[int] = []
    global_rows: list[int] = []
    exact_hi: list[int] = []
    exact_lo: list[int] = []
    signatures: list[np.ndarray] = []
    with _open_text(source) as handle:
        for row_index, line in enumerate(handle):
            if row_index >= rows:
                raise ValueError(f"source has more than declared {rows} rows")
            if rejected[row_index]:
                continue
            row = json.loads(line)
            tokens = _tokens(row)
            minhash = MinHash(num_perm=num_perm, seed=SEED)
            if tokens:
                minhash.update_batch(tokens)
            digest = xxhash.xxh3_128(b"\x00".join(tokens)).digest()
            hi, lo = np.frombuffer(digest, dtype=">u8")
            source_rows.append(row_index)
            global_rows.append(offset + row_index)
            exact_hi.append(int(hi))
            exact_lo.append(int(lo))
            signatures.append(minhash.hashvalues.copy())
        scanned_rows = row_index + 1 if rows else 0
    if scanned_rows != rows:
        raise ValueError(f"source has {scanned_rows} rows, expected {rows}")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    with temporary.open("wb") as handle:
        np.savez_compressed(
            handle,
            source_rows=np.asarray(source_rows, dtype=np.uint32),
            global_rows=np.asarray(global_rows, dtype=np.uint64),
            exact_hi=np.asarray(exact_hi, dtype=np.uint64),
            exact_lo=np.asarray(exact_lo, dtype=np.uint64),
            signatures=np.stack(signatures).astype(np.uint64) if signatures else np.empty((0, num_perm), dtype=np.uint64),
            rows=np.asarray(rows, dtype=np.uint64),
        )
    os.replace(temporary, output)
    report = {
        "dataset": task["dataset"],
        "source": str(source),
        "rows": rows,
        "quality_kept_rows": len(source_rows),
        "num_perm": num_perm,
        "seed": SEED,
        "output": str(output),
    }
    output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _task(path: Path, index: int) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        for current, line in enumerate(handle):
            if current == index:
                return json.loads(line)
    raise IndexError(index)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--task-index", type=int, required=True)
    parser.add_argument("--num-perm", type=int, default=NUM_PERM)
    args = parser.parse_args()
    print(json.dumps(scan(_task(args.manifest, args.task_index), args.num_perm), indent=2))


if __name__ == "__main__":
    main()