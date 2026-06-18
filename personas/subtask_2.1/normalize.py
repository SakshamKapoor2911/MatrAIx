#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
DEFAULT_CATALOG = HERE / "catalog.json"
DEFAULT_OUT_DIR = HERE / "normalized"

# Normalizes raw datasets into a common format, and adds a unique persona_id and provenance metadata.
def load_catalog(path: Path) -> dict[str, dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {entry["id"]: entry for entry in data["datasets"]}

# Reads JSONL file, yielding one dict per line. If limit is set, only yields the first N records.
def read_jsonl(path: Path, limit: int | None) -> Iterable[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if limit is not None and i >= limit:
                break
            line = line.strip()
            if line:
                yield json.loads(line)

# Creates a normalized record with a unique persona_id and provenance metadata. The persona_id is derived from the dataset id and a hash of the raw record, ensuring uniqueness across datasets and records. The provenance includes the source dataset id, source URL, and ingestion date.
def envelope(entry: dict, raw: dict) -> dict:
    seed = json.dumps(raw, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha1(f"{entry['id']}:{seed}".encode("utf-8")).hexdigest()[:12]
    return {
        "persona_id": f"mx-{entry['id']}-{digest}",
        "provenance": {
            "source": entry["id"],
            "source_url": entry["link"],
            "ingested_at": date.today().isoformat(),
        },
        "dimensions": {},   # depth TBD — see module docstring
        "narrative": "",     # depth TBD
        "raw": raw,
    }

# Processes a single dataset entry: reads the raw dataset, normalizes each record, and writes the output to a new JSONL file. Returns the number of records processed.
def process(entry: dict, catalog_dir: Path, limit: int | None, out_dir: Path) -> int:
    raw_path = entry.get("raw_path")
    if not raw_path:
        print(f"[skip] {entry['id']}: no raw_path", file=sys.stderr)
        return 0
    
    src = catalog_dir / raw_path
    if not src.exists():
        print(f"[skip] {entry['id']}: raw_path not found ({src})", file=sys.stderr)
        return 0
    
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"{entry['id']}.jsonl"
    n = 0

    with dst.open("w", encoding="utf-8") as out:
        for raw in read_jsonl(src, limit):
            out.write(json.dumps(envelope(entry, raw), ensure_ascii=False) + "\n")
            n += 1
    print(f"[ok] {entry['id']}: {n} records -> {dst}", file=sys.stderr)
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--source", help="process only this dataset id (default: all)")
    ap.add_argument("--limit", type=int, default=None, help="only read first N raw records")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--fetch", action="store_true", help="download missing datasets (via fetch.py) first")
    args = ap.parse_args(argv)

    catalog = load_catalog(args.catalog)
    catalog_dir = args.catalog.resolve().parent

    if args.source:
        if args.source not in catalog:
            raise SystemExit(f"unknown id {args.source!r}; catalog has: {', '.join(catalog)}")
        entries = [catalog[args.source]]
    else:
        entries = list(catalog.values())

    if args.fetch:
        from fetch import fetch_dataset
        for entry in entries:
            fetch_dataset(entry, catalog_dir, limit=args.limit)

    total = sum(process(e, catalog_dir, args.limit, args.out_dir) for e in entries)
    print(f"[done] {total} records from {len(entries)} dataset(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
