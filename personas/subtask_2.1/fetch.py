#!/usr/bin/env python3
"""Fetch raw dataset records into each catalog entry's `raw_path` (JSONL).

Best-effort downloader for Hugging Face datasets: the HF dataset id is parsed
from the catalog entry's `link`. Non-HF links (e.g. arXiv) are not fetchable
here — download those manually. Datasets that need a specific config are
reported with a hint rather than guessed.

Requires the `datasets` package:  pip install datasets

Usage:
    python fetch.py                                  # fetch all catalog datasets
    python fetch.py --source nemotron                 # one dataset
    python fetch.py --source nemotron --limit 1000    # cap rows (streamed)
    python fetch.py --source nemotron --force         # redownload if present
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CATALOG = HERE / "catalog.json"

_HF_RE = re.compile(r"huggingface\.co/datasets/([^/?#]+/[^/?#]+)")


def load_catalog(path: Path) -> dict[str, dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {entry["id"]: entry for entry in data["datasets"]}


def hf_id_from_link(link: str) -> str | None:
    """Return 'owner/name' for a Hugging Face dataset link, else None."""
    match = _HF_RE.search(link or "")
    return match.group(1) if match else None


def fetch_dataset(
    entry: dict,
    catalog_dir: Path,
    limit: int | None = None,
    split: str = "train",
    force: bool = False,
) -> int:
    """Download one catalog dataset to its raw_path. Returns rows written."""
    raw_path = entry.get("raw_path")
    if not raw_path:
        print(f"[skip] {entry['id']}: no raw_path", file=sys.stderr)
        return 0
    dst = catalog_dir / raw_path
    if dst.exists() and not force:
        print(f"[skip] {entry['id']}: already present ({dst}); use --force to redownload", file=sys.stderr)
        return 0
    hf_id = hf_id_from_link(entry.get("link", ""))
    if not hf_id:
        print(f"[skip] {entry['id']}: not a Hugging Face dataset link, fetch manually ({entry.get('link')})", file=sys.stderr)
        return 0

    try:
        from datasets import load_dataset
    except ImportError:
        raise SystemExit("the `datasets` package is required for --fetch: pip install datasets")

    print(f"[fetch] {entry['id']}: streaming {hf_id} (split={split})", file=sys.stderr)
    try:
        rows = load_dataset(hf_id, split=split, streaming=True)
    except Exception as exc:  # config missing, wrong split, network, ...
        print(f"[skip] {entry['id']}: could not load {hf_id} ({exc}); may need a config/split — fetch manually", file=sys.stderr)
        return 0

    dst.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with dst.open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
            if limit is not None and n >= limit:
                break
    print(f"[ok] {entry['id']}: {n} records -> {dst}", file=sys.stderr)
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--source", help="fetch only this dataset id (default: all)")
    ap.add_argument("--limit", type=int, default=None, help="cap rows written per dataset")
    ap.add_argument("--split", default="train", help="dataset split to stream (default: train)")
    ap.add_argument("--force", action="store_true", help="redownload even if raw_path exists")
    args = ap.parse_args(argv)

    catalog = load_catalog(args.catalog)
    catalog_dir = args.catalog.resolve().parent

    if args.source:
        if args.source not in catalog:
            raise SystemExit(f"unknown id {args.source!r}; catalog has: {', '.join(catalog)}")
        entries = [catalog[args.source]]
    else:
        entries = list(catalog.values())

    total = sum(
        fetch_dataset(e, catalog_dir, limit=args.limit, split=args.split, force=args.force)
        for e in entries
    )
    print(f"[done] fetched {total} records from {len(entries)} dataset(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
