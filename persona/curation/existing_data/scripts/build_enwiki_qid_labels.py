#!/usr/bin/env python3
"""Build an English display-label sidecar for QIDs used by person filters.

This does not attempt to mirror Wikidata's multilingual labels. It creates a
small pragmatic label index from enwiki page titles, enough for demos and
filter UIs that need to render QIDs like Q30 as readable text.
"""

from __future__ import annotations

import argparse
import bz2
import gzip
import json
from pathlib import Path
import sys
import time
from urllib.parse import quote


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create QID labels from enwiki page titles."
    )
    parser.add_argument("--attributes", type=Path, required=True)
    parser.add_argument("--page-qids", type=Path, required=True)
    parser.add_argument("--enwiki-index", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def qid_sort_key(qid: str) -> int:
    return int(qid[1:])


def source_url(title: str) -> str:
    return "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_"), safe="/:_()")


def collect_needed_qids(attributes_path: Path) -> set[str]:
    needed: set[str] = set()
    with gzip.open(attributes_path, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            needed.add(row["qid"])
            for key, value in row.items():
                if key.endswith("_qids") and isinstance(value, list):
                    needed.update(item for item in value if isinstance(item, str) and item.startswith("Q"))
    return needed


def load_needed_page_qids(page_qids_path: Path, needed_qids: set[str]) -> dict[int, str]:
    page_to_qid: dict[int, str] = {}
    with gzip.open(page_qids_path, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            qid = row["qid"]
            if qid in needed_qids:
                page_to_qid[int(row["page_id"])] = qid
    return page_to_qid


def build_labels_from_index(index_path: Path, page_to_qid: dict[int, str]) -> dict[str, dict]:
    labels: dict[str, dict] = {}
    with bz2.open(index_path, "rt", encoding="utf-8", errors="replace") as source:
        for line in source:
            parts = line.rstrip("\n").split(":", 2)
            if len(parts) != 3:
                continue
            try:
                page_id = int(parts[1])
            except ValueError:
                continue
            qid = page_to_qid.get(page_id)
            if qid is None:
                continue
            title = parts[2]
            existing = labels.get(qid)
            # Prefer shorter namespace-0 looking titles if duplicate page IDs/QIDs appear.
            if existing is None or (":" in existing["enwiki_title"] and ":" not in title):
                labels[qid] = {
                    "qid": qid,
                    "label": title,
                    "label_language": "en",
                    "label_source": "enwiki_title",
                    "enwiki_page_id": page_id,
                    "enwiki_title": title,
                    "enwiki_url": source_url(title),
                }
    return labels


def write_labels(out_path: Path, labels: dict[str, dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    with gzip.open(tmp_path, "wt", encoding="utf-8", compresslevel=3) as out:
        for qid in sorted(labels, key=qid_sort_key):
            out.write(json.dumps(labels[qid], ensure_ascii=False, separators=(",", ":")))
            out.write("\n")
    tmp_path.replace(out_path)


def main() -> int:
    args = parse_args()
    start = time.time()
    needed_qids = collect_needed_qids(args.attributes)
    print(f"needed_qids={len(needed_qids)}", file=sys.stderr)
    page_to_qid = load_needed_page_qids(args.page_qids, needed_qids)
    print(f"matching_enwiki_page_ids={len(page_to_qid)}", file=sys.stderr)
    labels = build_labels_from_index(args.enwiki_index, page_to_qid)
    write_labels(args.out, labels)
    summary = {
        "needed_qids": len(needed_qids),
        "label_rows": len(labels),
        "missing_qids": len(needed_qids) - len(labels),
        "elapsed_seconds": round(time.time() - start, 3),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
