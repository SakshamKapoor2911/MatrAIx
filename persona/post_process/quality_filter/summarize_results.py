#!/usr/bin/env python3
"""Validate all shard reports and aggregate quality-filter results by dataset."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable


def _tasks(paths: Iterable[Path]) -> list[dict[str, Any]]:
    tasks = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                task = json.loads(line)
                if not isinstance(task, dict):
                    raise ValueError(f"non-object task in {path}")
                tasks.append(task)
    return tasks


def summarize(manifests: list[Path]) -> dict[str, Any]:
    tasks = _tasks(manifests)
    missing: list[str] = []
    datasets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "shards": 0,
            "rows": 0,
            "rejected_rows": 0,
            "kept_rows": 0,
            "rule_violation_counts": Counter(),
            "unknown_relevant_values": Counter(),
        }
    )
    rules_hashes: set[str] = set()

    for task in tasks:
        report_path = Path(task["output_prefix"]).with_suffix(".report.json")
        if not report_path.is_file():
            missing.append(str(report_path))
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        dataset = str(task["dataset"])
        aggregate = datasets[dataset]
        aggregate["shards"] += 1
        for key in ("rows", "rejected_rows", "kept_rows"):
            aggregate[key] += int(report[key])
        aggregate["rule_violation_counts"].update(report["rule_violation_counts"])
        aggregate["unknown_relevant_values"].update(report["unknown_relevant_values"])
        rules_hashes.add(str(report["rules_sha256"]))

    if missing:
        raise RuntimeError(f"missing {len(missing)} shard reports; first: {missing[:5]}")
    if len(rules_hashes) != 1:
        raise RuntimeError(f"shards used inconsistent rule versions: {sorted(rules_hashes)}")

    total_rows = total_rejected = 0
    serializable_datasets = {}
    for dataset, aggregate in sorted(datasets.items()):
        rows = aggregate["rows"]
        rejected = aggregate["rejected_rows"]
        total_rows += rows
        total_rejected += rejected
        serializable_datasets[dataset] = {
            **{key: aggregate[key] for key in ("shards", "rows", "rejected_rows", "kept_rows")},
            "rejected_share": rejected / rows if rows else 0.0,
            "rule_violation_counts": dict(aggregate["rule_violation_counts"].most_common()),
            "unknown_relevant_values": dict(aggregate["unknown_relevant_values"].most_common()),
        }

    return {
        "format": "persona_quality_filter_summary",
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifests": [str(path) for path in manifests],
        "tasks": len(tasks),
        "rules_sha256": next(iter(rules_hashes)),
        "rows": total_rows,
        "rejected_rows": total_rejected,
        "kept_rows": total_rows - total_rejected,
        "rejected_share": total_rejected / total_rows if total_rows else 0.0,
        "datasets": serializable_datasets,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    summary = summarize(args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".part")
    temporary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()