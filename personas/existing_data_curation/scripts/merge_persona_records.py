#!/usr/bin/env python3
"""Union per-category result archives into one persona record per profile.

The standard merge (merge_wiki_results.py) DEDUPS by global_idx — correct when
each profile is attributed exactly once (one protocol, disjoint ranges). For the
1339-dim flow each profile is attributed up to 39 times (once per category), so
we must UNION the fields across archives keyed by global_idx instead of skipping
duplicates. Each dimension belongs to exactly one category, so the union is
conflict-free; field_ids are joined against the catalog for coverage and to flag
any id not in the 1339-dim taxonomy (drift).

Output: one JSON record per profile (gzipped JSONL):
  {global_idx, qid, task_id, title, input_sha256,
   dimensions: {dim_id: {value, confidence, evidence, assignment_type,
                         category, protocol_id, in_catalog}},
   coverage: {total_dimensions, attributed, in_catalog_fields, unmapped_fields,
              by_category: {category: {attributed, total}}}}

Run from the repo root with the repo on PYTHONPATH:
  PYTHONPATH=. python personas/existing_data_curation/scripts/merge_persona_records.py \
    --archive runs/results_alice_persona_attribution_demographic_core_*.tar.gz \
    --archive runs/results_alice_persona_attribution_expertise_domains_*.tar.gz \
    --dimensions personas/dimensions+new.json \
    --out persona_records.jsonl.gz
"""

from __future__ import annotations

import argparse
import gzip
import json
import tarfile
from pathlib import Path
from typing import Any


def _read_member_jsonl(archive_path: Path, member: str) -> list[dict[str, Any]]:
    with tarfile.open(archive_path, "r:gz") as tar:
        try:
            handle = tar.extractfile(member)
        except KeyError:
            return []
        if handle is None:
            return []
        with gzip.open(handle, "rt", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]


def _read_member_json(archive_path: Path, member: str) -> dict[str, Any]:
    with tarfile.open(archive_path, "r:gz") as tar:
        try:
            handle = tar.extractfile(member)
        except KeyError:
            return {}
        if handle is None:
            return {}
        return json.loads(handle.read().decode("utf-8"))


def load_catalog(dimensions_path: Path) -> tuple[dict[str, str], int]:
    """Return (dim_id -> category, total_dimension_count)."""
    data = json.loads(dimensions_path.read_text(encoding="utf-8"))
    dims = data.get("dimensions", [])
    id_to_category = {str(d["id"]): str(d.get("category", "Uncategorized")) for d in dims}
    return id_to_category, len(dims)


def _is_attributed(field: dict[str, Any]) -> bool:
    return field.get("value") is not None and field.get("assignment_type") != "unsupported"


def merge_persona_records(
    archives: list[Path], dimensions_path: Path
) -> list[dict[str, Any]]:
    id_to_category, total_dims = load_catalog(dimensions_path)
    category_totals: dict[str, int] = {}
    for category in id_to_category.values():
        category_totals[category] = category_totals.get(category, 0) + 1

    records: dict[int, dict[str, Any]] = {}
    for archive in archives:
        manifest = _read_member_json(archive, "run_manifest.json")
        protocol_id = manifest.get("protocol_id")
        for row in _read_member_jsonl(archive, "results.jsonl.gz"):
            gi = row.get("global_idx")
            if not isinstance(gi, int):
                continue
            rec = records.setdefault(
                gi,
                {
                    "global_idx": gi,
                    "qid": row.get("qid"),
                    "task_id": row.get("task_id"),
                    "title": row.get("title"),
                    "input_sha256": row.get("input_sha256"),
                    "dimensions": {},
                },
            )
            for field in row.get("fields", []):
                if not isinstance(field, dict):
                    continue
                fid = field.get("field_id")
                if not fid:
                    continue
                rec["dimensions"][str(fid)] = {
                    "value": field.get("value"),
                    "confidence": field.get("confidence"),
                    "evidence": field.get("evidence"),
                    "assignment_type": field.get("assignment_type"),
                    "category": id_to_category.get(str(fid)),
                    "protocol_id": protocol_id,
                    "in_catalog": str(fid) in id_to_category,
                }

    out: list[dict[str, Any]] = []
    for gi in sorted(records):
        rec = records[gi]
        dims = rec["dimensions"]
        by_category: dict[str, dict[str, int]] = {}
        attributed = 0
        in_catalog_fields = 0
        unmapped_fields = 0
        for fid, cell in dims.items():
            if cell["in_catalog"]:
                in_catalog_fields += 1
                category = cell["category"] or "Uncategorized"
                bucket = by_category.setdefault(
                    category, {"attributed": 0, "total": category_totals.get(category, 0)}
                )
                if _is_attributed(cell):
                    attributed += 1
                    bucket["attributed"] += 1
            else:
                unmapped_fields += 1
        rec["coverage"] = {
            "total_dimensions": total_dims,
            "attributed": attributed,
            "in_catalog_fields": in_catalog_fields,
            "unmapped_fields": unmapped_fields,
            "by_category": by_category,
        }
        out.append(rec)
    return out


def write_records(records: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if out_path.suffix == ".gz" else open
    with opener(out_path, "wt", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False))
            fh.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", action="append", type=Path, required=True, dest="archives")
    ap.add_argument(
        "--dimensions",
        type=Path,
        default=Path("personas/dimensions+new.json"),
    )
    ap.add_argument("--out", type=Path, required=True)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    records = merge_persona_records(args.archives, args.dimensions)
    write_records(records, args.out)
    total_attr = sum(r["coverage"]["attributed"] for r in records)
    total_dims = records[0]["coverage"]["total_dimensions"] if records else 0
    print(f"Merged {len(args.archives)} archives -> {len(records)} persona records -> {args.out}")
    if records:
        avg = total_attr / len(records)
        print(f"Avg attributed dims/person: {avg:.1f} / {total_dims}")
        unmapped = sum(r["coverage"]["unmapped_fields"] for r in records)
        if unmapped:
            print(f"Warning: {unmapped} field rows had ids not in the catalog (drift).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
