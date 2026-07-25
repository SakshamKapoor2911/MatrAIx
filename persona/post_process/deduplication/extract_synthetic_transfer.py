#!/usr/bin/env python3
"""Export retained synthetic rows and create a source-pool rejection overlay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from persona.synthesis.scripts.decode_persona_codes import _iter_code_chunks, _load_schema


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract(
    source: Path,
    base_bitmap: Path,
    shard: int,
    count: int,
    output: Path,
    overlay: Path,
    manifest: Path,
) -> dict[str, object]:
    schema = _load_schema(source)
    rows, _ = map(int, schema["shape"])
    base_rejected = np.unpackbits(
        np.fromfile(base_bitmap, dtype=np.uint8), bitorder="little", count=rows
    )
    selected_rows = np.flatnonzero(base_rejected == 0)[:count]
    if len(selected_rows) != count:
        raise ValueError(f"requested {count} rows but only found {len(selected_rows)} retained rows")

    names = [column["id"] for column in schema["columns"]]
    values = [column["values"] for column in schema["columns"]]
    output.parent.mkdir(parents=True, exist_ok=True)
    output_part = output.with_suffix(output.suffix + ".part")
    selected_set = set(map(int, selected_rows))
    written = 0
    offset = 0
    with output_part.open("w", encoding="utf-8") as handle:
        for codes in _iter_code_chunks(source, schema):
            for local_index, row in enumerate(codes):
                source_row = offset + local_index
                if source_row not in selected_set:
                    continue
                persona = {
                    name: value_map[int(code)]
                    for name, value_map, code in zip(names, values, row)
                }
                handle.write(json.dumps(persona, ensure_ascii=False) + "\n")
                written += 1
            offset += len(codes)
            if written == count:
                break
    if written != count:
        raise ValueError(f"decoded {written} rows; expected {count}")
    os.replace(output_part, output)

    packed_overlay = np.zeros((rows + 7) // 8, dtype=np.uint8)
    np.bitwise_or.at(
        packed_overlay,
        selected_rows // 8,
        np.left_shift(np.uint8(1), (selected_rows % 8).astype(np.uint8)),
    )
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay_part = overlay.with_suffix(overlay.suffix + ".part")
    packed_overlay.tofile(overlay_part)
    os.replace(overlay_part, overlay)

    result: dict[str, object] = {
        "format": "persona_synthetic_transfer",
        "format_version": 1,
        "source_type": "project_generated_synthetic",
        "source_codes": str(source),
        "source_shard": shard,
        "source_rows": selected_rows.tolist(),
        "personas": count,
        "dimensions_per_persona": len(names),
        "output": str(output),
        "output_sha256": sha256(output),
        "base_bitmap": str(base_bitmap),
        "rejection_overlay": str(overlay),
        "rejection_overlay_sha256": sha256(overlay),
        "overlay_encoding": "numpy.packbits bitorder=little; OR with base bitmap",
        "baseline_synthetic_kept_rows": 8_397_777_504,
        "derived_synthetic_kept_rows": 8_397_777_504 - count,
        "derived_total_kept_rows": 8_400_000_000 - count,
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--base-bitmap", type=Path, required=True)
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            extract(
                args.source,
                args.base_bitmap,
                args.shard,
                args.count,
                args.output,
                args.overlay,
                args.manifest,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()