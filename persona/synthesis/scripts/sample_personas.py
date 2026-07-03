#!/usr/bin/env python3
"""Sample personas from the Persona Full DAG."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from persona.synthesis.sampler import DEFAULT_GRAPH_PATH, sample_to_file_parallel  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path. Omit to benchmark generation without saving samples.",
    )
    parser.add_argument(
        "--format",
        choices=["codes", "jsonl", "csv"],
        default="codes",
        help="Saved output format. Defaults to compact binary codes; use jsonl/csv only for inspection.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes for batch-level parallel generation.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Rows per generated shard. Defaults to a near-even split across workers.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Emit source-proxy and audit-only nodes marked emit:false.",
    )
    parser.add_argument(
        "--compress",
        choices=["gzip"],
        default=None,
        help="Compress codes output (one gzip member per batch). Trades random access for ~1.6x less space.",
    )
    args = parser.parse_args()

    meta = sample_to_file_parallel(
        args.graph,
        n=args.n,
        out=args.out,
        fmt=args.format,
        seed=args.seed,
        emit_only=not args.include_hidden,
        workers=args.workers,
        batch_size=args.batch_size,
        compress=args.compress,
    )
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
