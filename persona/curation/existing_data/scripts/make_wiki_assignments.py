#!/usr/bin/env python3
"""Create email-friendly range assignments for offline wiki extraction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from persona.curation.existing_data.wiki_collab.core import (
    Assignment,
    load_json,
    load_protocol_manifest,
)


def build_assignments(
    *,
    workers: list[str],
    dataset_id: str,
    dataset_sha256: str,
    protocol_id: str,
    protocol_sha256: str,
    row_count: int,
    chunk_size: int,
) -> list[Assignment]:
    if not workers:
        raise ValueError("at least one worker is required")
    if row_count < 0:
        raise ValueError("row_count must be non-negative")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    assignments: list[Assignment] = []
    start = 0
    assignment_index = 1
    while start < row_count:
        end = min(start + chunk_size, row_count)
        worker_id = workers[(assignment_index - 1) % len(workers)]
        assignments.append(
            Assignment(
                assignment_id=f"A{assignment_index:04d}",
                worker_id=worker_id,
                dataset_id=dataset_id,
                dataset_sha256=dataset_sha256,
                protocol_id=protocol_id,
                protocol_sha256=protocol_sha256,
                range_start=start,
                range_end=end,
            )
        )
        start = end
        assignment_index += 1
    return assignments


def parse_workers(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--protocol-dir", type=Path, required=True)
    parser.add_argument("--workers", required=True, help="Comma-separated worker ids.")
    parser.add_argument("--chunk-size", type=int, default=50_000)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset = load_json(args.dataset_manifest)
    protocol = load_protocol_manifest(args.protocol_dir)
    assignments = build_assignments(
        workers=parse_workers(args.workers),
        dataset_id=dataset["dataset_id"],
        dataset_sha256=dataset["db_sha256"],
        protocol_id=protocol.protocol_id,
        protocol_sha256=protocol.protocol_sha256,
        row_count=int(dataset["row_count"]),
        chunk_size=args.chunk_size,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for assignment in assignments:
            fh.write(json.dumps(assignment.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(assignments)} assignments to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

