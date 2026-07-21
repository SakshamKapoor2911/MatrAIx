#!/usr/bin/env python3
"""Cluster human personas by exact hash and MinHash LSH similarity."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np

from persona.post_process.deduplication.hll import splitmix64


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = np.arange(size, dtype=np.int64)
        self.rank = np.zeros(size, dtype=np.uint8)

    def find(self, item: int) -> int:
        root = item
        while self.parent[root] != root:
            root = int(self.parent[root])
        while self.parent[item] != item:
            parent = int(self.parent[item])
            self.parent[item] = root
            item = parent
        return root

    def union(self, left: int, right: int) -> bool:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return False
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1
        return True


def _manifest(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _band_keys(signatures: np.ndarray, start: int, rows_per_band: int) -> np.ndarray:
    keys = np.zeros(len(signatures), dtype=np.uint64)
    for position in range(rows_per_band):
        salt = np.uint64(0x9E3779B97F4A7C15 * (start + position + 1) & 0xFFFFFFFFFFFFFFFF)
        keys ^= splitmix64(signatures[:, start + position] ^ salt)
    return keys


def merge(
    manifest_path: Path,
    output_dir: Path,
    threshold: float,
    bands: int,
    total_target: int = 8_400_000_000,
) -> dict[str, Any]:
    tasks = _manifest(manifest_path)
    loaded = []
    task_ids = []
    for task in tasks:
        path = Path(task["output"])
        if not path.is_file():
            raise FileNotFoundError(path)
        data = np.load(path)
        loaded.append(data)
        task_ids.append(np.full(len(data["global_rows"]), int(task["task_index"]), dtype=np.uint16))
    signatures = np.concatenate([data["signatures"] for data in loaded])
    global_rows = np.concatenate([data["global_rows"] for data in loaded])
    source_rows = np.concatenate([data["source_rows"] for data in loaded])
    exact_hi = np.concatenate([data["exact_hi"] for data in loaded])
    exact_lo = np.concatenate([data["exact_lo"] for data in loaded])
    task_index = np.concatenate(task_ids)
    for data in loaded:
        data.close()

    count, num_perm = signatures.shape
    if num_perm % bands:
        raise ValueError(f"{num_perm} permutations are not divisible by {bands} bands")
    rows_per_band = num_perm // bands
    minimum_agreement = math.ceil(threshold * num_perm)
    union_find = UnionFind(count)
    exact_unions = lsh_unions = 0
    candidate_pairs = 0

    exact_order = np.lexsort((exact_lo, exact_hi))
    sorted_hi = exact_hi[exact_order]
    sorted_lo = exact_lo[exact_order]
    boundaries = np.flatnonzero(
        (sorted_hi[1:] != sorted_hi[:-1]) | (sorted_lo[1:] != sorted_lo[:-1])
    ) + 1
    starts = np.r_[0, boundaries]
    stops = np.r_[boundaries, count]
    for start, stop in zip(starts, stops):
        if stop - start < 2:
            continue
        representative = int(exact_order[start])
        for position in range(start + 1, stop):
            exact_unions += int(union_find.union(representative, int(exact_order[position])))

    for band in range(bands):
        start_column = band * rows_per_band
        keys = _band_keys(signatures, start_column, rows_per_band)
        order = np.argsort(keys, kind="stable")
        sorted_keys = keys[order]
        boundaries = np.flatnonzero(sorted_keys[1:] != sorted_keys[:-1]) + 1
        starts = np.r_[0, boundaries]
        stops = np.r_[boundaries, count]
        for start, stop in zip(starts, stops):
            group_size = stop - start
            if group_size < 2:
                continue
            members = order[start:stop]
            for left_position in range(group_size - 1):
                left = int(members[left_position])
                left_root = union_find.find(left)
                for right_position in range(left_position + 1, group_size):
                    right = int(members[right_position])
                    if left_root == union_find.find(right):
                        continue
                    candidate_pairs += 1
                    agreement = int(np.count_nonzero(signatures[left] == signatures[right]))
                    if agreement >= minimum_agreement:
                        lsh_unions += int(union_find.union(left, right))
                        left_root = union_find.find(left)

    roots = np.fromiter((union_find.find(index) for index in range(count)), dtype=np.int64, count=count)
    survivor_by_root: dict[int, int] = {}
    for index, root in enumerate(roots):
        previous = survivor_by_root.get(int(root))
        if previous is None or global_rows[index] < global_rows[previous]:
            survivor_by_root[int(root)] = index
    rejected = np.fromiter(
        (survivor_by_root[int(root)] != index for index, root in enumerate(roots)),
        dtype=np.bool_,
        count=count,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_counts: Counter[str] = Counter()
    dataset_rejected: Counter[str] = Counter()
    for task in tasks:
        index = int(task["task_index"])
        selected = task_index == index
        bitmap = np.zeros(int(task["rows"]), dtype=np.bool_)
        bitmap[source_rows[selected]] = rejected[selected]
        destination = output_dir / str(task["dataset"]) / f"task_{index:04d}.dedup.reject.bits"
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        temporary.write_bytes(np.packbits(bitmap, bitorder="little").tobytes())
        os.replace(temporary, destination)
        dataset_counts[str(task["dataset"])] += int(np.count_nonzero(selected))
        dataset_rejected[str(task["dataset"])] += int(np.count_nonzero(rejected[selected]))

    dedup_rejected_rows = int(np.count_nonzero(rejected))
    dedup_kept_rows = count - dedup_rejected_rows
    summary = {
        "format": "persona_human_minhash_dedup_summary",
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "num_perm": num_perm,
        "bands": bands,
        "rows_per_band": rows_per_band,
        "minimum_signature_agreement": minimum_agreement,
        "quality_kept_rows": count,
        "dedup_rejected_rows": dedup_rejected_rows,
        "dedup_kept_rows": dedup_kept_rows,
        "final_total_target": total_target,
        "required_synthetic_rows": total_target - dedup_kept_rows,
        "exact_unions": exact_unions,
        "lsh_unions": lsh_unions,
        "candidate_pairs_verified": candidate_pairs,
        "datasets": {
            dataset: {
                "quality_kept_rows": dataset_counts[dataset],
                "dedup_rejected_rows": dataset_rejected[dataset],
                "dedup_kept_rows": dataset_counts[dataset] - dataset_rejected[dataset],
            }
            for dataset in sorted(dataset_counts)
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.95)
    parser.add_argument("--bands", type=int, default=8)
    parser.add_argument("--total-target", type=int, default=8_400_000_000)
    args = parser.parse_args()
    print(
        json.dumps(
            merge(args.manifest, args.output_dir, args.threshold, args.bands, args.total_target),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()