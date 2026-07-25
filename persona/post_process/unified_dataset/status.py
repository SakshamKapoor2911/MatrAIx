#!/usr/bin/env python3
"""Summarize unified Persona8B materialization progress from atomic reports."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess


JOB_IDS = ("33386504", "33386505", "33386507", "33386509", "33386510")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).parent / "results/persona8b_8_4b_20260720",
    )
    args = parser.parse_args()
    reports = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((args.root / "reports").glob("*.json"))
    ]
    rows = Counter()
    bytes_by_source = Counter()
    descriptions = Counter()
    for report in reports:
        source = report["source"]
        rows[source] += int(report["rows"])
        bytes_by_source[source] += int(report["bytes"])
        descriptions[source] += int(report.get("description_rows", 0))
    result = subprocess.run(
        ["sacct", "-n", "-X", "-j", ",".join(JOB_IDS), "--format=JobName,State"],
        check=False,
        capture_output=True,
        text=True,
    )
    states = Counter(line.strip() for line in result.stdout.splitlines() if line.strip())
    print(
        json.dumps(
            {
                "completed_reports": len(reports),
                "rows": dict(sorted(rows.items())),
                "bytes": dict(sorted(bytes_by_source.items())),
                "description_rows": dict(sorted(descriptions.items())),
                "slurm": dict(sorted(states.items())),
                "manifest_ready": (args.root / "manifest.json").is_file(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()