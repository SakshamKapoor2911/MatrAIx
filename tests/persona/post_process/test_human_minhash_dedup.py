from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from persona.post_process.deduplication.merge_human_minhash import merge
from persona.post_process.deduplication.scan_human_minhash import scan


def _row(values: list[str]) -> dict[str, object]:
    return {
        "fields": [
            {"field_id": f"field_{index:02d}", "value": value}
            for index, value in enumerate(values)
        ]
    }


def test_human_exact_and_near_dedup_across_shards(tmp_path: Path) -> None:
    base = [f"value_{index}" for index in range(30)]
    near = base.copy()
    near[-1] = "changed"
    distinct = [f"other_{index}" for index in range(30)]
    rows_by_task = [[_row(base), _row(distinct)], [_row(base), _row(near)]]
    tasks = []
    offset = 0
    for task_index, rows in enumerate(rows_by_task):
        source = tmp_path / f"source_{task_index}.jsonl"
        source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        quality_bitmap = tmp_path / f"quality_{task_index}.bits"
        quality_bitmap.write_bytes(b"\x00")
        task = {
            "task_index": task_index,
            "dataset": "fixture",
            "source": str(source),
            "quality_bitmap": str(quality_bitmap),
            "rows": len(rows),
            "global_offset": offset,
            "output": str(tmp_path / "signatures" / f"task_{task_index:04d}.npz"),
        }
        tasks.append(task)
        scan(task)
        offset += len(rows)
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text("".join(json.dumps(task) + "\n" for task in tasks), encoding="utf-8")

    summary = merge(manifest, tmp_path / "dedup", threshold=0.80, bands=8)

    assert summary["quality_kept_rows"] == 4
    assert summary["dedup_kept_rows"] == 2
    bitmaps = [
        np.unpackbits(
            np.fromfile(tmp_path / "dedup" / "fixture" / f"task_{index:04d}.dedup.reject.bits", dtype=np.uint8),
            bitorder="little",
            count=2,
        ).tolist()
        for index in range(2)
    ]
    assert bitmaps == [[0, 0], [1, 1]]