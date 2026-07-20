#!/usr/bin/env python3
"""Finalize documentation and validate a built Persona 1M release."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

from persona.post_process.coreset_1m.build_coreset import CORESET_SCHEMA, SOURCE_COUNTS


def finalize(root: Path, method_source: Path) -> dict:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["rows"] != 1_000_000 or manifest["sources"] != SOURCE_COUNTS:
        raise ValueError("Manifest does not contain the required 1M and 60/40 source accounting")
    counts: Counter[str] = Counter()
    description_rows = populated_sum = rows = 0
    for item in manifest["files"]:
        path = root / item["path"]
        parquet = pq.ParquetFile(path)
        if parquet.schema_arrow != CORESET_SCHEMA or parquet.metadata.num_rows != item["rows"]:
            raise ValueError(f"Parquet validation failed: {path}")
        for batch in parquet.iter_batches(columns=["source", "has_description", "populated_attribute_count"]):
            table = batch.to_pydict()
            counts.update(table["source"])
            description_rows += sum(table["has_description"])
            populated_sum += sum(table["populated_attribute_count"])
            rows += len(table["source"])
    if rows != 1_000_000 or dict(counts) != SOURCE_COUNTS:
        raise ValueError(f"Physical row accounting failed: rows={rows}, sources={dict(counts)}")
    results = {
        "rows": rows,
        "sources": dict(counts),
        "description_rows": description_rows,
        "description_coverage": description_rows / rows,
        "mean_populated_attributes": populated_sum / rows,
    }
    audit = json.loads((root / "audit.json").read_text(encoding="utf-8"))
    calibration_sections = []
    for dimension, dimension_audit in audit["calibration"].items():
        category_rows = "".join(
            f"| {value} | {stats['target']:.4%} | {stats['achieved']:.4%} | {stats['absolute_error']:.4%} |\n"
            for value, stats in dimension_audit["categories"].items()
        )
        calibration_sections.append(
            f"### `{dimension}`\n\n"
            f"Known: {dimension_audit['known_rows']:,}; missing: {dimension_audit['missing_rows']:,}; "
            f"maximum absolute error: {dimension_audit['max_absolute_error']:.4%}.\n\n"
            "| Value | Target | Achieved | Absolute error |\n|---|---:|---:|---:|\n"
            + category_rows
        )
    (root / "RESULTS.md").write_text(
        "# Persona 1M Build Results\n\n"
        f"Validated rows: **{rows:,}**. Human-grounded: **600,000 (60%)**; synthetic: **400,000 (40%)**.\n\n"
        "| Source | Rows |\n|---|---:|\n"
        + "".join(f"| {source} | {count:,} |\n" for source, count in counts.items())
        + f"\nRows with field-level natural-language descriptions: **{description_rows:,} ({description_rows / rows:.2%})**.\n\n"
        + f"Mean populated attributes per persona: **{populated_sum / rows:.2f} / 1,290**.\n\n"
        "## Calibration results\n\n"
        + "\n".join(calibration_sections)
        + "\nDetailed residual feasibility diagnostics and source statistics are in `audit.json`.\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(method_source.read_text(encoding="utf-8"), encoding="utf-8")
    manifest["validation"] = results
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--method-source", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.root, args.method_source), indent=2))


if __name__ == "__main__":
    main()