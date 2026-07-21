#!/usr/bin/env python3
"""Build a stable manifest for human-product MinHash extraction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
QUALITY_ROOT = REPO_ROOT / "persona/post_process/quality_filter"
DEFAULT_TASKS = QUALITY_ROOT / "jobs/manifests/full_filter_20260719/human_tasks.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quality-manifest", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    tasks = []
    offset = 0
    with args.quality_manifest.open(encoding="utf-8") as handle:
        for task_index, line in enumerate(handle):
            quality_task = json.loads(line)
            quality_prefix = Path(quality_task["output_prefix"])
            report_path = quality_prefix.with_suffix(".report.json")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            rows = int(report["rows"])
            dataset = str(quality_task["dataset"])
            output = args.output_dir / dataset / f"task_{task_index:04d}.npz"
            tasks.append(
                {
                    "task_index": task_index,
                    "dataset": dataset,
                    "source": quality_task["source"],
                    "quality_bitmap": str(quality_prefix.with_suffix(".reject.bits")),
                    "rows": rows,
                    "global_offset": offset,
                    "output": str(output),
                }
            )
            offset += rows
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(json.dumps(task, sort_keys=True) + "\n" for task in tasks),
        encoding="utf-8",
    )
    print(json.dumps({"tasks": len(tasks), "rows": offset, "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()