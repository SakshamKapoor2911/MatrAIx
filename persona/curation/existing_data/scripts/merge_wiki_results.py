#!/usr/bin/env python3
"""Merge accepted offline wiki extraction result archives into one JSONL.GZ."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from persona.curation.existing_data.wiki_collab.results import iter_archive_results


def _existing_indices(out_path: Path) -> set[int]:
    indices: set[int] = set()
    if not out_path.exists():
        return indices
    with gzip.open(out_path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row.get("global_idx"), int):
                indices.add(row["global_idx"])
    return indices


def merge_archives(archives: list[Path], out_path: Path) -> dict[str, int]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen = _existing_indices(out_path)
    written_rows = 0
    duplicate_rows = 0
    input_rows = 0
    with gzip.open(out_path, "at", encoding="utf-8") as out:
        for archive in archives:
            for row in iter_archive_results(archive):
                input_rows += 1
                global_idx = row.get("global_idx")
                if not isinstance(global_idx, int) or global_idx in seen:
                    duplicate_rows += 1
                    continue
                out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                seen.add(global_idx)
                written_rows += 1
    return {
        "input_rows": input_rows,
        "written_rows": written_rows,
        "duplicate_rows": duplicate_rows,
        "total_rows_after_merge": len(seen),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", action="append", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = merge_archives(args.archive, args.out)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

