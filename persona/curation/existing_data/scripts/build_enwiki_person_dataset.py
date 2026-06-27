#!/usr/bin/env python3
"""Build person-only enwiki raw wikitext shards.

Inputs:
  * enwiki page_props.sql.gz: maps enwiki page_id to Wikidata QID
  * Wikidata truthy NT dump: classifies QIDs as humans or fictional characters
  * enwiki article JSONL shards: raw full-page wikitext extracted from XML dump

Outputs:
  * enwiki_page_qids.jsonl.gz
  * person_candidates.jsonl.gz
  * person_pages_raw/part-*.jsonl.gz
"""

from __future__ import annotations

import argparse
import bz2
import concurrent.futures
import contextlib
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


WIKIBASE_ITEM_RE = re.compile(
    rb"\((\d+),'wikibase_item','(Q\d+)',(?:NULL|\d+)\)"
)
TRIPLE_RE = re.compile(
    rb"^<http://www\.wikidata\.org/entity/(Q\d+)>\s+"
    rb"<http://www\.wikidata\.org/prop/direct/(P31|P279)>\s+"
    rb"<http://www\.wikidata\.org/entity/(Q\d+)>\s+\.\s*$"
)

Q_HUMAN = "Q5"
Q_CHARACTER = "Q95074"
_FILTER_CANDIDATES: dict[int, dict] = {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter enwiki article shards to real and fictional people."
    )
    parser.add_argument("--page-props", type=Path, required=True)
    parser.add_argument("--wikidata-truthy", type=Path, required=True)
    parser.add_argument("--raw-articles", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--dump-date", default="20260601")
    parser.add_argument("--source-project", default="enwiki")
    parser.add_argument(
        "--skip-page-qids",
        action="store_true",
        help="Reuse an existing enwiki_page_qids.jsonl.gz in --out-dir.",
    )
    parser.add_argument(
        "--skip-candidates",
        action="store_true",
        help="Reuse an existing person_candidates.jsonl.gz in --out-dir.",
    )
    parser.add_argument(
        "--max-raw-shards",
        type=int,
        help="Smoke test: filter only the first N sorted raw article shards.",
    )
    return parser.parse_args()


def build_page_qids(page_props: Path, out_path: Path) -> dict[int, str]:
    start = time.time()
    mapping: dict[int, str] = {}
    line_count = 0
    with gzip.open(page_props, "rb") as source, gzip.open(out_path, "wt", encoding="utf-8") as out:
        for line in source:
            line_count += 1
            if b"wikibase_item" not in line:
                continue
            for match in WIKIBASE_ITEM_RE.finditer(line):
                page_id = int(match.group(1))
                qid = match.group(2).decode("ascii")
                mapping[page_id] = qid
                out.write(json.dumps({"page_id": page_id, "qid": qid}, separators=(",", ":")))
                out.write("\n")
    print(
        f"page_qids: {len(mapping)} rows from {line_count} SQL lines in "
        f"{time.time() - start:.1f}s",
        file=sys.stderr,
    )
    return mapping


def load_page_qids(path: Path) -> dict[int, str]:
    mapping = {}
    with gzip.open(path, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            mapping[int(row["page_id"])] = row["qid"]
    return mapping


@contextlib.contextmanager
def open_truthy_statement_lines(wikidata_truthy: Path):
    """Yield only Wikidata P31/P279 truthy lines.

    The full truthy dump is huge. When available, let bzip2 and ripgrep do the
    broad streaming filter so Python only parses candidate statement lines.
    """

    decompressor_path = (
        shutil.which("lbzip2")
        or shutil.which("pbzip2")
        or shutil.which("bzip2")
    )
    rg_path = shutil.which("rg")
    if decompressor_path and rg_path:
        decompress = subprocess.Popen(
            [decompressor_path, "-dc", str(wikidata_truthy)],
            stdout=subprocess.PIPE,
        )
        assert decompress.stdout is not None
        grep = subprocess.Popen(
            [rg_path, "--text", "--no-line-number", r"/prop/direct/P(31|279)>"],
            stdin=decompress.stdout,
            stdout=subprocess.PIPE,
        )
        decompress.stdout.close()
        assert grep.stdout is not None
        try:
            yield grep.stdout
        finally:
            grep.stdout.close()
            grep_return = grep.wait()
            decompress_return = decompress.wait()
            if grep_return not in (0, 1):
                raise RuntimeError(f"ripgrep failed with exit code {grep_return}")
            if decompress_return != 0:
                raise RuntimeError(
                    f"{Path(decompressor_path).name} failed with exit code {decompress_return}"
                )
        return

    with bz2.open(wikidata_truthy, "rb") as source:
        yield source


def classify_candidates(
    wikidata_truthy: Path,
    page_qids: dict[int, str],
    out_path: Path,
) -> dict[int, dict]:
    start = time.time()
    qids_with_pages = set(page_qids.values())
    qid_to_page_ids: dict[str, list[int]] = {}
    for page_id, qid in page_qids.items():
        qid_to_page_ids.setdefault(qid, []).append(page_id)

    subclass_children: dict[str, set[str]] = {}
    page_qid_instances: list[tuple[str, str]] = []
    p31_count = 0
    p279_count = 0

    with open_truthy_statement_lines(wikidata_truthy) as source:
        for line_no, line in enumerate(source, 1):
            if b"/prop/direct/P31>" not in line and b"/prop/direct/P279>" not in line:
                continue
            match = TRIPLE_RE.match(line)
            if not match:
                continue
            subject = match.group(1).decode("ascii")
            predicate = match.group(2).decode("ascii")
            obj = match.group(3).decode("ascii")
            if predicate == "P279":
                subclass_children.setdefault(obj, set()).add(subject)
                p279_count += 1
            elif predicate == "P31":
                p31_count += 1
                if subject in qids_with_pages:
                    page_qid_instances.append((subject, obj))
            if line_no % 500_000 == 0:
                print(
                    f"truthy statement_scan line={line_no} p31={p31_count} p279={p279_count} "
                    f"page_qid_instances={len(page_qid_instances)}",
                    file=sys.stderr,
                )

    fictional_classes = {Q_CHARACTER}
    frontier = [Q_CHARACTER]
    while frontier:
        parent = frontier.pop()
        for child in subclass_children.get(parent, ()):
            if child not in fictional_classes:
                fictional_classes.add(child)
                frontier.append(child)

    qid_types: dict[str, set[str]] = {}
    for qid, instance_qid in page_qid_instances:
        if instance_qid == Q_HUMAN:
            qid_types.setdefault(qid, set()).add("real_person")
        if instance_qid in fictional_classes:
            qid_types.setdefault(qid, set()).add("fictional_character")

    candidate_by_page_id: dict[int, dict] = {}
    counts = {"real_person": 0, "fictional_character": 0, "both": 0}
    with gzip.open(out_path, "wt", encoding="utf-8") as out:
        for qid, entity_types in sorted(qid_types.items(), key=lambda item: int(item[0][1:])):
            if not entity_types:
                continue
            if len(entity_types) > 1:
                entity_type = "real_person;fictional_character"
                counts["both"] += 1
            else:
                entity_type = next(iter(entity_types))
                counts[entity_type] += 1
            tags = sorted(entity_types)
            for page_id in qid_to_page_ids.get(qid, []):
                row = {
                    "page_id": page_id,
                    "qid": qid,
                    "entity_type": entity_type,
                    "tags": tags,
                }
                candidate_by_page_id[page_id] = row
                out.write(json.dumps(row, separators=(",", ":")))
                out.write("\n")

    print(
        f"candidates: pages={len(candidate_by_page_id)} qids={len(qid_types)} "
        f"fictional_classes={len(fictional_classes)} counts={counts} "
        f"in {time.time() - start:.1f}s",
        file=sys.stderr,
    )
    return candidate_by_page_id


def load_candidates(path: Path) -> dict[int, dict]:
    candidates = {}
    with gzip.open(path, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            candidates[int(row["page_id"])] = row
    return candidates


def candidate_counts(candidates: dict[int, dict]) -> dict[str, int]:
    counts = {
        "candidate_pages": len(candidates),
        "real_person_pages": 0,
        "fictional_character_pages": 0,
        "both_pages": 0,
    }
    for row in candidates.values():
        tags = set(row.get("tags") or [])
        if "real_person" in tags:
            counts["real_person_pages"] += 1
        if "fictional_character" in tags:
            counts["fictional_character_pages"] += 1
        if {"real_person", "fictional_character"}.issubset(tags):
            counts["both_pages"] += 1
    return counts


def init_filter_worker(candidates: dict[int, dict]) -> None:
    global _FILTER_CANDIDATES
    _FILTER_CANDIDATES = candidates


def filter_shard(shard_index: int, shard_path: Path, out_dir: Path) -> dict:
    start = time.time()
    out_path = out_dir / f"part-{shard_index:05d}.jsonl.gz"
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    scanned = 0
    kept = 0
    tag_counts = {
        "real_person_pages": 0,
        "fictional_character_pages": 0,
        "both_pages": 0,
    }
    with gzip.open(shard_path, "rt", encoding="utf-8") as source, gzip.open(
        tmp_path, "wt", encoding="utf-8", compresslevel=3
    ) as out:
        for line in source:
            scanned += 1
            row = json.loads(line)
            candidate = _FILTER_CANDIDATES.get(int(row["page_id"]))
            if candidate is None:
                continue
            row.update(candidate)
            row["source_url"] = "https://en.wikipedia.org/wiki/" + row["title"].replace(" ", "_")
            tags = set(row.get("tags") or [])
            if "real_person" in tags:
                tag_counts["real_person_pages"] += 1
            if "fictional_character" in tags:
                tag_counts["fictional_character_pages"] += 1
            if {"real_person", "fictional_character"}.issubset(tags):
                tag_counts["both_pages"] += 1
            out.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            out.write("\n")
            kept += 1
    tmp_path.replace(out_path)
    return {
        "shard_index": shard_index,
        "input_file": shard_path.name,
        "output_file": out_path.name,
        "scanned_pages": scanned,
        "kept_pages": kept,
        **tag_counts,
        "elapsed_seconds": round(time.time() - start, 3),
    }


def filter_raw_articles(
    raw_dir: Path,
    out_dir: Path,
    candidates: dict[int, dict],
    workers: int,
    max_raw_shards: int | None,
) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    shards = sorted(raw_dir.glob("part-*.jsonl.gz"))
    if max_raw_shards:
        shards = shards[:max_raw_shards]
    results = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers,
        initializer=init_filter_worker,
        initargs=(candidates,),
    ) as executor:
        futures = {
            executor.submit(filter_shard, idx, shard, out_dir): shard
            for idx, shard in enumerate(shards)
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"[filter {result['shard_index']:05d}] kept {result['kept_pages']} "
                f"of {result['scanned_pages']} from {result['input_file']} "
                f"in {result['elapsed_seconds']}s",
                file=sys.stderr,
            )
    results.sort(key=lambda item: item["shard_index"])
    return results


def write_dataset_card(out_dir: Path, manifest: dict) -> None:
    attributes_section = ""
    if "attribute_rows" in manifest:
        coverage_lines = "\n".join(
            f"- {key}: `{value}`"
            for key, value in sorted(manifest["attribute_coverage"].items())
        )
        attributes_section = f"""
## Filter Attributes

- Attribute rows: `{manifest["attribute_rows"]}`
{coverage_lines}

`person_attributes.jsonl.gz` contains Wikidata-derived filter fields:
item-valued fields as Wikidata QIDs plus raw date fields and derived
`birth_years` / `death_years`.
"""
    labels_section = ""
    if "label_rows" in manifest:
        labels_section = f"""
## QID Labels

- Needed QIDs: `{manifest["label_needed_qids"]}`
- Label rows: `{manifest["label_rows"]}`
- Missing QIDs: `{manifest["label_missing_qids"]}`

`wikidata_labels.jsonl.gz` maps QIDs used by the person and filter sidecars to
English display labels derived from enwiki page titles. It is intended for UI
display and filtering previews; it is not a full Wikidata multilingual label
dump.
"""
    card = f"""---
license: cc-by-sa-4.0
language:
- en
task_categories:
- text-generation
- information-extraction
pretty_name: Enwiki Person-Only Raw Wikitext
---

# Enwiki Person-Only Raw Wikitext

This dataset contains raw English Wikipedia namespace-0 pages for entities tagged
as real people or fictional characters through Wikidata.

It is intended as an intermediate corpus for persona dimension extraction and
persona field assignment. The broader all-article extraction is not included.

## Scope

- Source project: `{manifest["source_project"]}`
- Dump date: `{manifest["dump_date"]}`
- Candidate pages: `{manifest["candidate_pages"]}`
- Candidate real-person pages: `{manifest["real_person_pages"]}`
- Candidate fictional-character pages: `{manifest["fictional_character_pages"]}`
- Candidate pages tagged as both: `{manifest["both_pages"]}`
- Kept raw pages: `{manifest["total_kept_pages"]}`
- Kept raw real-person pages: `{manifest["kept_real_person_pages"]}`
- Kept raw fictional-character pages: `{manifest["kept_fictional_character_pages"]}`
- Kept raw pages tagged as both: `{manifest["kept_both_pages"]}`

## Files

- `person_candidates.jsonl.gz`: page-to-Wikidata candidate labels.
- `person_attributes.jsonl.gz`: Wikidata-derived filter attributes.
- `wikidata_labels.jsonl.gz`: English display labels for QIDs used in filters.
- `person_pages_raw/part-*.jsonl.gz`: raw page records with full wikitext.
- `manifest.json`: build inputs, counts, and per-shard extraction statistics.

{attributes_section}
{labels_section}

## Row Format

Rows in `person_pages_raw/part-*.jsonl.gz` are JSON objects with fields such as:

- `page_id`
- `title`
- `revision_id`
- `revision_timestamp`
- `wikitext`
- `qid`
- `entity_type`
- `tags`
- `source_url`

`wikitext` is kept raw so downstream jobs can choose their own parser for plain
text, sections, chunks, or media references.

## Attribution and License

Content is derived from English Wikipedia and Wikidata dumps. Wikipedia text is
available under Creative Commons Attribution-ShareAlike terms; downstream users
must preserve attribution and license requirements when redistributing derived
text.
"""
    (out_dir / "README.md").write_text(card, encoding="utf-8")


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    page_qids_path = args.out_dir / "enwiki_page_qids.jsonl.gz"
    candidates_path = args.out_dir / "person_candidates.jsonl.gz"
    person_pages_dir = args.out_dir / "person_pages_raw"

    if args.skip_page_qids:
        page_qids = load_page_qids(page_qids_path)
    else:
        page_qids = build_page_qids(args.page_props, page_qids_path)

    if args.skip_candidates:
        candidates = load_candidates(candidates_path)
    else:
        candidates = classify_candidates(args.wikidata_truthy, page_qids, candidates_path)

    counts = candidate_counts(candidates)
    shard_results = filter_raw_articles(
        args.raw_articles,
        person_pages_dir,
        candidates,
        args.workers,
        args.max_raw_shards,
    )
    manifest = {
        "page_props": str(args.page_props),
        "wikidata_truthy": str(args.wikidata_truthy),
        "raw_articles": str(args.raw_articles),
        "source_project": args.source_project,
        "dump_date": args.dump_date,
        "page_qids_file": page_qids_path.name,
        "candidates_file": candidates_path.name,
        "person_pages_dir": person_pages_dir.name,
        "workers": args.workers,
        "dataset_scope": "enwiki namespace-0 raw wikitext for real people and fictional characters only",
        **counts,
        "total_scanned_pages": sum(row["scanned_pages"] for row in shard_results),
        "total_kept_pages": sum(row["kept_pages"] for row in shard_results),
        "kept_real_person_pages": sum(row["real_person_pages"] for row in shard_results),
        "kept_fictional_character_pages": sum(
            row["fictional_character_pages"] for row in shard_results
        ),
        "kept_both_pages": sum(row["both_pages"] for row in shard_results),
        "shards": shard_results,
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_dataset_card(args.out_dir, manifest)
    print(f"wrote manifest to {args.out_dir / 'manifest.json'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
