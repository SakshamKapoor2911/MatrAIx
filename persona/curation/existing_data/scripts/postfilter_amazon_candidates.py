#!/usr/bin/env python3
"""Post-filter Amazon Reviews 2023 candidate user pools.

Use this after `analyze_amazon_reviews_2023.py` finishes. It avoids rescanning
remote category files when a stricter pool is a subset of an existing candidate
JSONL.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


def parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return int(float(value))


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def passes(row: dict[str, Any], args: argparse.Namespace) -> bool:
    return (
        row.get("review_count", 0) >= args.min_reviews
        and row.get("category_count", 0) >= args.min_categories
        and row.get("history_days", 0) >= args.min_history_days
        and row.get("text_chars", 0) >= args.min_text_chars
        and row.get("verified_share", 0) >= args.min_verified_share
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-reviews", type=parse_int, default=50)
    parser.add_argument("--min-categories", type=parse_int, default=3)
    parser.add_argument("--min-history-days", type=parse_int, default=730)
    parser.add_argument("--min-text-chars", type=parse_int, default=10000)
    parser.add_argument("--min-verified-share", type=float, default=0.8)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    rows = load_rows(args.input)
    filtered = [row for row in rows if passes(row, args)]
    filtered.sort(
        key=lambda row: (
            row.get("review_count", 0),
            row.get("category_count", 0),
            row.get("history_days", 0),
            row.get("text_chars", 0),
        ),
        reverse=True,
    )
    count = write_jsonl(args.output, filtered)
    print(
        json.dumps(
            {
                "input": str(args.input),
                "output": str(args.output),
                "input_count": len(rows),
                "output_count": count,
                "thresholds": {
                    "min_reviews": args.min_reviews,
                    "min_categories": args.min_categories,
                    "min_history_days": args.min_history_days,
                    "min_text_chars": args.min_text_chars,
                    "min_verified_share": args.min_verified_share,
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
