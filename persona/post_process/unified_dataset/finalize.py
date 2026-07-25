#!/usr/bin/env python3
"""Validate and finalize a physically materialized Persona8B dataset."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

import pyarrow.parquet as pq

from persona.post_process.unified_dataset.schema import UNIFIED_SCHEMA


EXPECTED_COUNTS = {
    "synthetic": 8_397_777_004,
    "wiki": 1_946_442,
    "amazon": 97_915,
    "stackoverflow": 113_120,
    "prism": 1_487,
    "gss": 63_532,
    "real_human_survey": 508,
}
EXPECTED_TOTAL = 8_400_000_008

DATASET_CARD = """---
pretty_name: MatrAIx Persona8B Unified
task_categories:
- text-generation
tags:
- persona
- synthetic
- survey
- parquet
size_categories:
- n>1T
---

# MatrAIx Persona8B Unified

This revision contains a physical, sharded copy of **8,400,000,008 personas**
after quality filtering and deduplication. It does not require the original 10B
synthetic source or rejection bitmaps.

## Sources

| Source | Rows |
|---|---:|
| synthetic | 8,397,777,004 |
| wiki | 1,946,442 |
| amazon | 97,915 |
| stackoverflow | 113,120 |
| prism | 1,487 |
| gss | 63,532 |
| real_human_survey | 508 |

## Columns

- `source`: source product identifier.
- `source_row_index`: stable row index in the source product.
- `source_record_id`: source-specific public identifier when available.
- `attributes`: 645-byte packed categorical vector for 1,290 ordered fields;
    each byte contains two 4-bit codes.
- `null_bitmap`: optional 162-byte little-endian bitmap; set bits mark null
    fields. A null bitmap value means no fields are null.
- `attribute_overrides`: sparse lossless values not represented by the current
    categorical codebook; these take precedence over `attributes`.
- `has_description`: whether field-level natural-language descriptions exist.
- `descriptions`: sparse `(field_index, text)` natural-language descriptions.
- `grounding`: sparse evidence, confidence, and assignment-type records.
- `metadata_json`: source-specific metadata serialized as JSON.

`persona_codes.schema.json` defines field order and code-to-value mappings.
For field index `i`, the code is the low nibble when `i` is even and the high
nibble when `i` is odd. Apply `null_bitmap` and then `attribute_overrides` when
decoding.

Descriptions and evidence in LLM-extracted sources are model-generated and may
contain errors. Survey mappings depend on their source crosswalks. Source terms
and licenses continue to apply.
"""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def finalize(root: Path, reports_dir: Path, schema_source: Path, verify_hashes: bool) -> dict[str, Any]:
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(reports_dir.glob("*.json"))]
    if not reports:
        raise ValueError(f"No task reports found in {reports_dir}")
    by_source: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    parquet_paths = []
    for report in reports:
        source = report["source"]
        for key in ("rows", "bytes", "files", "description_rows", "grounding_rows", "override_rows"):
            by_source[source][key] += int(report.get(key, 0))
        parquet_paths.extend(Path(path) for path in report["paths"])
    counts = {source: stats["rows"] for source, stats in by_source.items()}
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"Retained counts do not match production accounting: {counts}")
    if sum(counts.values()) != EXPECTED_TOTAL:
        raise ValueError("Unified row total does not match the expected total")
    files = []
    for path in parquet_paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        metadata = pq.read_metadata(path)
        if metadata.schema.to_arrow_schema() != UNIFIED_SCHEMA:
            raise ValueError(f"Schema mismatch: {path}")
        item = {"path": str(path.relative_to(root)), "rows": metadata.num_rows, "bytes": path.stat().st_size}
        if verify_hashes:
            item["sha256"] = _sha256(path)
        files.append(item)
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(schema_source, root / "persona_codes.schema.json")
    (root / "README.md").write_text(DATASET_CARD, encoding="utf-8")
    manifest = {
        "format": "matraix_unified_persona_dataset",
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rows": EXPECTED_TOTAL,
        "bytes": sum(item["bytes"] for item in files),
        "files": len(files),
        "sources": {source: dict(stats) for source, stats in sorted(by_source.items())},
        "parquet_files": files,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--schema-source", type=Path, required=True)
    parser.add_argument("--verify-hashes", action="store_true")
    args = parser.parse_args()
    print(json.dumps(finalize(args.root, args.reports_dir, args.schema_source, args.verify_hashes), indent=2))


if __name__ == "__main__":
    main()