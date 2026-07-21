#!/usr/bin/env python3
"""Prepare shard-local calibration candidates for the Persona 1M build."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np

from persona.post_process.coreset_1m.build_coreset import (
    discover_synthetic_candidates,
    load_codebook,
    load_targets,
    named_columns,
    scan_candidates,
    source_paths,
)


def write_cache(
    output: Path,
    rows: np.ndarray,
    columns: dict[str, np.ndarray],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    with temporary.open("wb") as handle:
        np.savez_compressed(
            handle,
            source_rows=rows,
            **{f"field__{name}": values for name, values in columns.items()},
        )
    os.replace(temporary, output)


def prepare_human(input_root: Path, codebook: Path, targets_path: Path, source: str, output: Path) -> None:
    field_ids, values = load_codebook(codebook)
    targets, _ = load_targets(targets_path, field_ids, values)
    field_indices = [field_ids.index(name) for name in targets]
    rows, decoded = scan_candidates(source_paths(input_root / "data", source), field_indices)
    write_cache(output, rows, named_columns(decoded, field_ids, field_indices))


def prepare_synthetic(
    input_root: Path,
    codebook: Path,
    targets_path: Path,
    shard: int,
    output: Path,
) -> None:
    field_ids, values = load_codebook(codebook)
    targets, _ = load_targets(targets_path, field_ids, values)
    field_indices = [field_ids.index(name) for name in targets]
    row_groups = discover_synthetic_candidates(input_root / "data")
    path = list(row_groups)[shard]
    rows, decoded = scan_candidates([path], field_indices, row_groups={path: row_groups[path]})
    write_cache(output, rows, named_columns(decoded, field_ids, field_indices))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--codebook", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    human = subparsers.add_parser("human")
    human.add_argument("--source", required=True)
    synthetic = subparsers.add_parser("synthetic")
    synthetic.add_argument("--shard", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "human":
        prepare_human(args.input_root, args.codebook, args.targets, args.source, args.output)
    else:
        prepare_synthetic(args.input_root, args.codebook, args.targets, args.shard, args.output)


if __name__ == "__main__":
    main()