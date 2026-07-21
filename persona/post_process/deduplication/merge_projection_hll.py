#!/usr/bin/env python3
"""Merge projection HLL sketches and recommend target-sized configurations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from persona.post_process.deduplication.hll import estimate_cardinality


def merge(input_dir: Path, config_path: Path, target_rows: int) -> dict[str, object]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    paths = sorted(input_dir.glob("shard_*.npz"))
    if len(paths) != 100:
        raise ValueError(f"expected 100 shard sketches, found {len(paths)}")
    precision = int(config["hll_precision"])
    merged = {
        projection["id"]: np.zeros(1 << precision, dtype=np.uint8)
        for projection in config["projections"]
    }
    rows = kept_rows = 0
    for path in paths:
        with np.load(path) as data:
            rows += int(data["rows"])
            kept_rows += int(data["kept_rows"])
            for projection_id in merged:
                np.maximum(merged[projection_id], data[f"registers__{projection_id}"], out=merged[projection_id])
    projections = []
    for projection in config["projections"]:
        estimate = int(round(estimate_cardinality(merged[projection["id"]])))
        projections.append(
            {
                "id": projection["id"],
                "width": projection["width"],
                "estimated_unique_signatures": estimate,
                "estimated_removed_with_cap_1": max(0, kept_rows - estimate),
                "estimated_keep_share": min(1.0, estimate / kept_rows if kept_rows else 0.0),
                "distance_from_target": abs(estimate - target_rows),
                "fields": [field["id"] for field in projection["fields"]],
            }
        )
    recommendation = min(projections, key=lambda item: item["distance_from_target"])
    return {
        "format": "persona_projection_hll_summary",
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_shards": len(paths),
        "rows": rows,
        "quality_kept_rows": kept_rows,
        "target_rows": target_rows,
        "hll_precision": precision,
        "relative_standard_error": config["relative_standard_error"],
        "projections": projections,
        "closest_projection": recommendation["id"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--target-rows", type=int, default=8_350_000_000)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary = merge(args.input_dir, args.config, args.target_rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()