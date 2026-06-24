#!/usr/bin/env python3
"""QA checks for derived Wikipedia person clean text, sections, and chunks."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re
import sys
import time


SUSPICIOUS_PATTERNS = {
    "template_open": re.compile(r"\{\{"),
    "template_close": re.compile(r"\}\}"),
    "wikilink_open": re.compile(r"\[\["),
    "wikilink_close": re.compile(r"\]\]"),
    "ref_tag": re.compile(r"<\s*/?\s*ref\b", re.IGNORECASE),
    "html_comment": re.compile(r"<!--"),
    "table_start": re.compile(r"\{\|"),
    "category_link": re.compile(r"\[\[Category:", re.IGNORECASE),
    "file_link": re.compile(r"\[\[(?:File|Image):", re.IGNORECASE),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QA derived person text JSONL shards.")
    parser.add_argument("--derivatives-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sample-limit", type=int, default=25)
    parser.add_argument("--short-page-chars", type=int, default=200)
    parser.add_argument("--short-section-chars", type=int, default=80)
    parser.add_argument("--short-chunk-chars", type=int, default=120)
    parser.add_argument("--long-chunk-chars", type=int, default=2600)
    return parser.parse_args()


def empty_counter() -> dict[str, int]:
    return {name: 0 for name in SUSPICIOUS_PATTERNS}


def pattern_hits(text: str) -> list[str]:
    return [name for name, pattern in SUSPICIOUS_PATTERNS.items() if pattern.search(text)]


def append_sample(samples: list[dict], row: dict, reason: str, text: str, limit: int) -> None:
    if len(samples) >= limit:
        return
    samples.append(
        {
            "reason": reason,
            "page_id": row.get("page_id"),
            "qid": row.get("qid"),
            "title": row.get("title"),
            "section_heading": row.get("section_heading") or row.get("heading"),
            "chunk_id": row.get("chunk_id"),
            "char_count": len(text),
            "text_preview": text[:500],
        }
    )


def scan_clean_pages(clean_dir: Path, args: argparse.Namespace) -> tuple[dict, list[dict]]:
    stats = {
        "rows": 0,
        "short_pages": 0,
        "zero_sections": 0,
        "zero_chunks": 0,
        "plain_text_chars": 0,
        "section_count_sum": 0,
        "chunk_count_sum": 0,
        "pattern_rows": empty_counter(),
    }
    samples: list[dict] = []
    for path in sorted(clean_dir.glob("part-*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as source:
            for line in source:
                row = json.loads(line)
                text = row.get("plain_text") or ""
                stats["rows"] += 1
                stats["plain_text_chars"] += len(text)
                stats["section_count_sum"] += int(row.get("section_count") or 0)
                stats["chunk_count_sum"] += int(row.get("chunk_count") or 0)
                if len(text) < args.short_page_chars:
                    stats["short_pages"] += 1
                    append_sample(samples, row, "short_page", text, args.sample_limit)
                if int(row.get("section_count") or 0) == 0:
                    stats["zero_sections"] += 1
                    append_sample(samples, row, "zero_sections", text, args.sample_limit)
                if int(row.get("chunk_count") or 0) == 0:
                    stats["zero_chunks"] += 1
                    append_sample(samples, row, "zero_chunks", text, args.sample_limit)
                for hit in pattern_hits(text):
                    stats["pattern_rows"][hit] += 1
                    append_sample(samples, row, f"page_{hit}", text, args.sample_limit)
    return stats, samples


def scan_text_rows(
    directory: Path,
    text_key: str,
    short_threshold: int,
    long_threshold: int | None,
    args: argparse.Namespace,
) -> tuple[dict, list[dict]]:
    stats = {
        "rows": 0,
        "short_rows": 0,
        "long_rows": 0,
        "text_chars": 0,
        "pattern_rows": empty_counter(),
    }
    samples: list[dict] = []
    for path in sorted(directory.glob("part-*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as source:
            for line in source:
                row = json.loads(line)
                text = row.get(text_key) or ""
                stats["rows"] += 1
                stats["text_chars"] += len(text)
                if len(text) < short_threshold:
                    stats["short_rows"] += 1
                    append_sample(samples, row, "short_row", text, args.sample_limit)
                if long_threshold is not None and len(text) > long_threshold:
                    stats["long_rows"] += 1
                    append_sample(samples, row, "long_row", text, args.sample_limit)
                for hit in pattern_hits(text):
                    stats["pattern_rows"][hit] += 1
                    append_sample(samples, row, hit, text, args.sample_limit)
    return stats, samples


def add_rates(stats: dict) -> dict:
    rows = stats.get("rows") or 0
    out = dict(stats)
    if rows:
        for key, value in list(stats.items()):
            if key.endswith("_rows") or key in {
                "short_pages",
                "zero_sections",
                "zero_chunks",
                "short_rows",
                "long_rows",
            }:
                if isinstance(value, int):
                    out[f"{key}_rate"] = value / rows
        if "pattern_rows" in stats:
            out["pattern_row_rates"] = {
                key: value / rows for key, value in stats["pattern_rows"].items()
            }
    return out


def main() -> int:
    args = parse_args()
    start = time.time()
    clean_stats, clean_samples = scan_clean_pages(
        args.derivatives_dir / "person_pages_clean", args
    )
    section_stats, section_samples = scan_text_rows(
        args.derivatives_dir / "person_page_sections",
        "text",
        args.short_section_chars,
        None,
        args,
    )
    chunk_stats, chunk_samples = scan_text_rows(
        args.derivatives_dir / "person_page_chunks",
        "text",
        args.short_chunk_chars,
        args.long_chunk_chars,
        args,
    )

    report = {
        "derivatives_dir": str(args.derivatives_dir),
        "thresholds": {
            "short_page_chars": args.short_page_chars,
            "short_section_chars": args.short_section_chars,
            "short_chunk_chars": args.short_chunk_chars,
            "long_chunk_chars": args.long_chunk_chars,
        },
        "clean_pages": add_rates(clean_stats),
        "sections": add_rates(section_stats),
        "chunks": add_rates(chunk_stats),
        "samples": {
            "clean_pages": clean_samples,
            "sections": section_samples,
            "chunks": chunk_samples,
        },
        "elapsed_seconds": round(time.time() - start, 3),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote QA report to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
