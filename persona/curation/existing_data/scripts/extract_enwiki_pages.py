#!/usr/bin/env python3
"""Extract article pages from enwiki XML dump shards.

The extractor is intentionally conservative: it streams compressed XML shards,
keeps raw wikitext unchanged, and writes one JSONL shard per input dump part.
Downstream jobs can parse wikitext into sections/chunks without re-reading the
original dump.
"""

from __future__ import annotations

import argparse
import bz2
import concurrent.futures
import csv
import gzip
import json
import os
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET


MEDIAWIKI_NS = "{http://www.mediawiki.org/xml/export-0.11/}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract enwiki article pages from pages-articles XML shards."
    )
    parser.add_argument(
        "--dump-parts",
        required=True,
        type=Path,
        help="Directory containing enwiki pages-articles *.bz2 shard files.",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        type=Path,
        help="Output directory for JSONL shards and manifest.json.",
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        help=(
            "Optional JSONL/CSV/TSV with title or enwiki_title. If omitted, all "
            "matching namespace pages are extracted."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=min(8, os.cpu_count() or 1),
        help="Parallel dump shard workers.",
    )
    parser.add_argument(
        "--namespace",
        type=int,
        default=0,
        help="MediaWiki namespace to extract; namespace 0 is articles.",
    )
    parser.add_argument(
        "--include-redirects",
        action="store_true",
        help="Keep redirect pages. By default redirects are skipped.",
    )
    parser.add_argument(
        "--compression",
        choices=("gzip", "none"),
        default="gzip",
        help="Output compression for JSONL shards.",
    )
    parser.add_argument(
        "--gzip-level",
        type=int,
        default=3,
        help="gzip compression level when --compression=gzip.",
    )
    parser.add_argument(
        "--dump-date",
        default="20260601",
        help="Dump date to record in output rows.",
    )
    parser.add_argument(
        "--source-project",
        default="enwiki",
        help="Wiki project identifier to record in output rows.",
    )
    parser.add_argument(
        "--max-parts",
        type=int,
        help="For smoke tests, process only the first N sorted dump shards.",
    )
    parser.add_argument(
        "--limit-pages-per-part",
        type=int,
        help="For smoke tests, stop each shard after N extracted pages.",
    )
    return parser.parse_args()


def normalize_title(title: str) -> str:
    return title.replace("_", " ").strip()


def load_candidates(path: Path | None) -> dict[str, dict] | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(path)

    candidates: dict[str, dict] = {}
    suffixes = path.suffixes

    if path.suffix == ".jsonl" or suffixes[-2:] == [".jsonl", ".gz"]:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                title = (
                    row.get("enwiki_title")
                    or row.get("wiki_title")
                    or row.get("title")
                    or row.get("page_title")
                )
                if not title:
                    raise ValueError(f"{path}:{line_no} missing title/enwiki_title")
                candidates[normalize_title(title)] = row
        return candidates

    delimiter = "\t" if path.suffix == ".tsv" else ","
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        for line_no, row in enumerate(reader, 2):
            title = (
                row.get("enwiki_title")
                or row.get("wiki_title")
                or row.get("title")
                or row.get("page_title")
            )
            if not title:
                raise ValueError(f"{path}:{line_no} missing title/enwiki_title")
            candidates[normalize_title(title)] = row
    return candidates


def text_of(parent: ET.Element, path: str) -> str | None:
    node = parent.find(path)
    return node.text if node is not None else None


def int_or_none(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def output_path(out_dir: Path, part_index: int, compression: str) -> Path:
    suffix = ".jsonl.gz" if compression == "gzip" else ".jsonl"
    return out_dir / f"part-{part_index:05d}{suffix}"


def open_output(path: Path, compression: str, gzip_level: int):
    if compression == "gzip":
        return gzip.open(path, "wt", encoding="utf-8", compresslevel=gzip_level)
    return open(path, "w", encoding="utf-8")


def candidate_metadata(candidate: dict | None) -> dict:
    if not candidate:
        return {}
    out = {}
    for key in (
        "qid",
        "entity_type",
        "tags",
        "description",
        "label",
        "language_sitelinks",
        "available_languages",
    ):
        if key in candidate:
            out[key] = candidate[key]
    return out


def extract_part(
    part_index: int,
    dump_file: Path,
    out_dir: Path,
    candidates: dict[str, dict] | None,
    namespace: int,
    include_redirects: bool,
    compression: str,
    gzip_level: int,
    dump_date: str,
    source_project: str,
    limit_pages_per_part: int | None,
) -> dict:
    start = time.time()
    out_path = output_path(out_dir, part_index, compression)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

    scanned_pages = 0
    extracted_pages = 0
    skipped_redirects = 0
    skipped_namespace = 0

    ns_title = f"{MEDIAWIKI_NS}title"
    ns_ns = f"{MEDIAWIKI_NS}ns"
    ns_id = f"{MEDIAWIKI_NS}id"
    ns_redirect = f"{MEDIAWIKI_NS}redirect"
    ns_revision = f"{MEDIAWIKI_NS}revision"
    ns_rev_id = f"{MEDIAWIKI_NS}id"
    ns_rev_ts = f"{MEDIAWIKI_NS}timestamp"
    ns_rev_text = f"{MEDIAWIKI_NS}text"

    with bz2.open(dump_file, "rb") as source, open_output(
        tmp_path, compression, gzip_level
    ) as out:
        context = ET.iterparse(source, events=("end",))
        for _, elem in context:
            if elem.tag != f"{MEDIAWIKI_NS}page":
                continue

            scanned_pages += 1
            page_ns = int_or_none(text_of(elem, ns_ns))
            if page_ns != namespace:
                skipped_namespace += 1
                elem.clear()
                continue

            is_redirect = elem.find(ns_redirect) is not None
            if is_redirect and not include_redirects:
                skipped_redirects += 1
                elem.clear()
                continue

            title = normalize_title(text_of(elem, ns_title) or "")
            candidate = candidates.get(title) if candidates is not None else None
            if candidates is not None and candidate is None:
                elem.clear()
                continue

            revision = elem.find(ns_revision)
            revision_id = None
            revision_timestamp = None
            wikitext = ""
            if revision is not None:
                revision_id = int_or_none(text_of(revision, ns_rev_id))
                revision_timestamp = text_of(revision, ns_rev_ts)
                wikitext = text_of(revision, ns_rev_text) or ""

            row = {
                "source_project": source_project,
                "source_dump": f"{source_project}-{dump_date}",
                "source_dump_file": dump_file.name,
                "page_id": int_or_none(text_of(elem, ns_id)),
                "title": title,
                "namespace": page_ns,
                "is_redirect": is_redirect,
                "revision_id": revision_id,
                "revision_timestamp": revision_timestamp,
                "wikitext": wikitext,
            }
            row.update(candidate_metadata(candidate))
            out.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            out.write("\n")
            extracted_pages += 1

            elem.clear()
            if limit_pages_per_part and extracted_pages >= limit_pages_per_part:
                break

    tmp_path.replace(out_path)
    return {
        "part_index": part_index,
        "dump_file": dump_file.name,
        "output_file": out_path.name,
        "scanned_pages": scanned_pages,
        "extracted_pages": extracted_pages,
        "skipped_namespace": skipped_namespace,
        "skipped_redirects": skipped_redirects,
        "elapsed_seconds": round(time.time() - start, 3),
    }


def list_dump_parts(path: Path) -> list[Path]:
    files = sorted(path.glob("*.bz2"))
    if not files:
        raise FileNotFoundError(f"No .bz2 dump parts found under {path}")
    return files


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    candidates = load_candidates(args.candidates)
    dump_parts = list_dump_parts(args.dump_parts)
    if args.max_parts:
        dump_parts = dump_parts[: args.max_parts]

    manifest = {
        "source_project": args.source_project,
        "dump_date": args.dump_date,
        "dump_parts_dir": str(args.dump_parts),
        "candidate_file": str(args.candidates) if args.candidates else None,
        "candidate_count": len(candidates) if candidates is not None else None,
        "namespace": args.namespace,
        "include_redirects": args.include_redirects,
        "compression": args.compression,
        "workers": args.workers,
        "parts": [],
    }

    print(
        f"extracting {len(dump_parts)} parts with {args.workers} workers "
        f"to {args.out_dir}",
        file=sys.stderr,
    )
    if candidates is not None:
        print(f"loaded {len(candidates)} candidate titles", file=sys.stderr)

    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                extract_part,
                idx,
                dump_file,
                args.out_dir,
                candidates,
                args.namespace,
                args.include_redirects,
                args.compression,
                args.gzip_level,
                args.dump_date,
                args.source_project,
                args.limit_pages_per_part,
            ): dump_file
            for idx, dump_file in enumerate(dump_parts)
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            manifest["parts"].append(result)
            print(
                f"[part {result['part_index']:05d}] extracted "
                f"{result['extracted_pages']} pages from {result['dump_file']} "
                f"in {result['elapsed_seconds']}s",
                file=sys.stderr,
            )

    manifest["parts"].sort(key=lambda item: item["part_index"])
    manifest["total_scanned_pages"] = sum(p["scanned_pages"] for p in manifest["parts"])
    manifest["total_extracted_pages"] = sum(
        p["extracted_pages"] for p in manifest["parts"]
    )
    manifest["total_skipped_redirects"] = sum(
        p["skipped_redirects"] for p in manifest["parts"]
    )
    manifest_path = args.out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote manifest to {manifest_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
