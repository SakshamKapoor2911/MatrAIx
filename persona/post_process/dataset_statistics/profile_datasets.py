#!/usr/bin/env python3
"""Stream persona products once and cache paper-oriented aggregate statistics."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import random
from typing import Any, Iterable, Iterator, NamedTuple, TextIO


REPO_ROOT = Path("/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx")
PERSONA_ROOT = REPO_ROOT / "persona"
DATA_ROOT = PERSONA_ROOT / "human_extraction/data"
RESULTS_DIR = PERSONA_ROOT / "post_process/dataset_statistics/results"
SCHEMA_PATH = PERSONA_ROOT / "schema/dimensions.json"
CONFIDENCE_RESERVOIR_SIZE = 50_000
RANDOM_SEED = 20260719


class ProductSpec(NamedTuple):
    product_id: str
    display_name: str
    source_type: str
    method: str
    target_rows: int
    expected_rows: int
    scan_mode: str
    notes: str


PRODUCTS = [
    ProductSpec(
        "synthetic",
        "Full-DAG synthetic",
        "probabilistic graph",
        "Graph sampling; all dimensions assigned by construction",
        10_000_000_000,
        10_000_000_000,
        "declared",
        "No payload scan; completed production manifests are the source of scale.",
    ),
    ProductSpec(
        "wiki",
        "Wiki-grounded",
        "Wikipedia-derived profiles",
        "Qwen3.6 extraction with 1,200 subscription/API upgrades",
        2_125_897,
        1_997_743,
        "sample",
        "5,000-row deterministic stratified shard-head sample; rates are estimates.",
    ),
    ProductSpec(
        "amazon",
        "Amazon Review",
        "chronological review histories",
        "Qwen3.6 medium_b extraction with schema sanitizer",
        100_000,
        100_000,
        "full",
        "Final 256-bucket assembly: 167 continuation plus 89 source buckets.",
    ),
    ProductSpec(
        "stackoverflow",
        "Stack Overflow survey",
        "2023-2025 developer surveys",
        "Qwen3.6 extraction translated to the 1,290-field contract",
        113_335,
        113_335,
        "full",
        "Translated files only; raw extraction files are not double counted.",
    ),
    ProductSpec(
        "prism",
        "PRISM Alignment",
        "PRISM participant survey",
        "Exact demographic overlay plus Qwen3-235B-A22B extraction",
        1_500,
        1_500,
        "full",
        "Full validated v1.1 gzip shard.",
    ),
    ProductSpec(
        "gss",
        "General Social Survey",
        "NORC GSS 1972-2024",
        "Rule-based observed crosswalk; no LLM",
        75_699,
        75_699,
        "full",
        "Full scan of five validated gzip shards.",
    ),
]


def open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def iter_jsonl(paths: Iterable[Path]) -> Iterator[dict[str, Any]]:
    for path in paths:
        with open_text(path) as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"invalid JSON: {path}:{line_number}") from error
                if not isinstance(row, dict):
                    raise ValueError(f"non-object row: {path}:{line_number}")
                yield row


def iter_wiki_sample() -> Iterator[dict[str, Any]]:
    strata = [(0, 3), *((shard_id, 263) for shard_id in range(10, 200, 10))]
    for shard_id, rows_per_shard in strata:
        path = DATA_ROOT / f"wiki/extraction_v1/shard_{shard_id:04d}.jsonl"
        with path.open(encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if index >= rows_per_shard:
                    break
                yield json.loads(line)


def iter_amazon() -> Iterator[dict[str, Any]]:
    amazon = DATA_ROOT / "amazon"
    completion = json.loads(
        (amazon / "extraction_resume_20260717/EXTRACTION_COMPLETE.json").read_text()
    )
    continuation_buckets = set(completion["buckets"])
    for value in range(256):
        bucket = f"{value:02x}"
        if bucket in continuation_buckets:
            path = amazon / f"extraction_resume_20260717/shard_{bucket}.jsonl"
        else:
            path = amazon / f"hf_snapshot_20260719/data/shard_{bucket}.jsonl.gz"
        yield from iter_jsonl([path])


def iter_stackoverflow() -> Iterator[dict[str, Any]]:
    base = (
        DATA_ROOT
        / "stackoverflow/hf_pr55/StackExchange_Persona/extraction_v1/qwen36"
        / "stackoverflow_vllm_v2_pr53_compatible"
    )
    paths = [base / str(year) / f"merged_{year}_hf_pr53.jsonl" for year in range(2023, 2026)]
    yield from iter_jsonl(paths)


def iter_product(product_id: str) -> Iterator[dict[str, Any]]:
    if product_id == "wiki":
        yield from iter_wiki_sample()
    elif product_id == "amazon":
        yield from iter_amazon()
    elif product_id == "stackoverflow":
        yield from iter_stackoverflow()
    elif product_id == "prism":
        yield from iter_jsonl(
            [DATA_ROOT / "prism/hf_main/extraction_v1/shard_00.jsonl.gz"]
        )
    elif product_id == "gss":
        base = DATA_ROOT / "gss/hf_main/extraction_v1"
        yield from iter_jsonl(sorted(base.glob("shard_*.jsonl.gz")))
    else:
        raise ValueError(f"no row iterator for {product_id}")


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {key: None for key in ("min", "p05", "p25", "median", "p75", "p95", "max", "mean")}
    ordered = sorted(values)

    def percentile(fraction: float) -> float:
        position = fraction * (len(ordered) - 1)
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        weight = position - lower
        return ordered[lower] * (1 - weight) + ordered[upper] * weight

    return {
        "min": ordered[0],
        "p05": percentile(0.05),
        "p25": percentile(0.25),
        "median": percentile(0.50),
        "p75": percentile(0.75),
        "p95": percentile(0.95),
        "max": ordered[-1],
        "mean": sum(ordered) / len(ordered),
    }


class Reservoir:
    def __init__(self, limit: int, seed: int) -> None:
        self.limit = limit
        self.random = random.Random(seed)
        self.values: list[float] = []
        self.seen = 0

    def add(self, value: float) -> None:
        self.seen += 1
        if len(self.values) < self.limit:
            self.values.append(value)
            return
        index = self.random.randrange(self.seen)
        if index < self.limit:
            self.values[index] = value


class Profiler:
    def __init__(self, spec: ProductSpec, dimensions: list[dict[str, Any]]) -> None:
        self.spec = spec
        self.dimensions = dimensions
        self.dimension_ids = [str(item["id"]) for item in dimensions]
        self.dimension_set = set(self.dimension_ids)
        self.category_by_id = {
            str(item["id"]): str(item.get("category") or "Uncategorized")
            for item in dimensions
        }
        self.allowed = {
            str(item["id"]): {str(value) for value in item.get("values", [])}
            for item in dimensions
        }
        self.rows = 0
        self.populated_per_row: list[int] = []
        self.emitted_per_row: list[int] = []
        self.observed_per_row: list[int] = []
        self.assignment_types: Counter[str] = Counter()
        self.dimension_emitted: Counter[str] = Counter()
        self.dimension_populated: Counter[str] = Counter()
        self.dimension_evidence: Counter[str] = Counter()
        self.dimension_description: Counter[str] = Counter()
        self.category_populated: Counter[str] = Counter()
        self.category_emitted: Counter[str] = Counter()
        self.unknown_field_ids: Counter[str] = Counter()
        self.duplicate_field_ids = 0
        self.malformed_fields = 0
        self.off_schema_values = 0
        self.populated_fields = 0
        self.populated_with_evidence = 0
        self.populated_with_description = 0
        self.confidence = Reservoir(CONFIDENCE_RESERVOIR_SIZE, RANDOM_SEED)

    def ingest(self, row: dict[str, Any]) -> None:
        fields = row.get("fields")
        if not isinstance(fields, list):
            raise ValueError(f"{self.spec.product_id} row lacks fields list")
        self.rows += 1
        emitted = populated = 0
        seen: set[str] = set()
        for field in fields:
            if not isinstance(field, dict):
                self.malformed_fields += 1
                continue
            field_id = str(field.get("field_id") or "")
            if not field_id:
                self.malformed_fields += 1
                continue
            if field_id in seen:
                self.duplicate_field_ids += 1
            seen.add(field_id)
            if field_id not in self.dimension_set:
                self.unknown_field_ids[field_id] += 1
                continue
            emitted += 1
            category = self.category_by_id[field_id]
            self.dimension_emitted[field_id] += 1
            self.category_emitted[category] += 1
            assignment_type = str(field.get("assignment_type") or "missing")
            self.assignment_types[assignment_type] += 1
            value = field.get("value")
            if value is None or value == "":
                continue
            populated += 1
            self.populated_fields += 1
            self.dimension_populated[field_id] += 1
            self.category_populated[category] += 1
            allowed = self.allowed[field_id]
            if allowed and str(value) not in allowed:
                self.off_schema_values += 1
            evidence = str(field.get("evidence") or "").strip()
            description = str(field.get("description") or "").strip()
            if evidence:
                self.populated_with_evidence += 1
                self.dimension_evidence[field_id] += 1
            if description:
                self.populated_with_description += 1
                self.dimension_description[field_id] += 1
            confidence = field.get("confidence")
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                confidence_value = None
            if confidence_value is not None and 0.0 <= confidence_value <= 1.0:
                self.confidence.add(confidence_value)
        self.emitted_per_row.append(emitted)
        self.populated_per_row.append(populated)
        observed = row.get("observed")
        self.observed_per_row.append(len(observed) if isinstance(observed, dict) else 0)

    def finish(self) -> dict[str, Any]:
        rows = self.rows
        categories = sorted(set(self.category_by_id.values()))
        category_dimensions = Counter(self.category_by_id.values())
        category_summary = []
        for category in categories:
            denominator = rows * category_dimensions[category]
            category_summary.append(
                {
                    "category": category,
                    "dimensions": category_dimensions[category],
                    "populated_fields": self.category_populated[category],
                    "emitted_fields": self.category_emitted[category],
                    "populated_rate": self.category_populated[category] / denominator if denominator else 0.0,
                    "mean_populated_per_persona": self.category_populated[category] / rows if rows else 0.0,
                }
            )
        dimension_summary = []
        for dimension in self.dimensions:
            field_id = str(dimension["id"])
            populated = self.dimension_populated[field_id]
            dimension_summary.append(
                {
                    "field_id": field_id,
                    "category": self.category_by_id[field_id],
                    "populated": populated,
                    "emitted": self.dimension_emitted[field_id],
                    "prevalence": populated / rows if rows else 0.0,
                    "evidence_rate": self.dimension_evidence[field_id] / populated if populated else None,
                    "description_rate": self.dimension_description[field_id] / populated if populated else None,
                }
            )
        return {
            "product_id": self.spec.product_id,
            "display_name": self.spec.display_name,
            "source_type": self.spec.source_type,
            "method": self.spec.method,
            "target_rows": self.spec.target_rows,
            "available_rows": self.spec.expected_rows,
            "rows_scanned": rows,
            "scan_mode": self.spec.scan_mode,
            "statistics_exact": self.spec.scan_mode in {"full", "declared"},
            "notes": self.spec.notes,
            "schema_dimensions": len(self.dimensions),
            "emitted_attributes": quantiles([float(value) for value in self.emitted_per_row]),
            "populated_attributes": quantiles([float(value) for value in self.populated_per_row]),
            "observed_attributes": quantiles([float(value) for value in self.observed_per_row]),
            "populated_attribute_distribution": self.populated_per_row,
            "assignment_types": dict(self.assignment_types),
            "populated_fields": self.populated_fields,
            "evidence_coverage": self.populated_with_evidence / self.populated_fields if self.populated_fields else None,
            "description_coverage": self.populated_with_description / self.populated_fields if self.populated_fields else None,
            "confidence": quantiles(self.confidence.values),
            "confidence_sample_size": len(self.confidence.values),
            "contract": {
                "unknown_field_occurrences": sum(self.unknown_field_ids.values()),
                "unknown_field_ids": dict(self.unknown_field_ids.most_common()),
                "duplicate_field_ids": self.duplicate_field_ids,
                "malformed_fields": self.malformed_fields,
                "off_schema_values": self.off_schema_values,
            },
            "categories": category_summary,
            "dimensions": dimension_summary,
        }


def synthetic_result(spec: ProductSpec, dimensions: list[dict[str, Any]]) -> dict[str, Any]:
    category_dimensions = Counter(str(item.get("category") or "Uncategorized") for item in dimensions)
    fixed = {
        "min": 1290.0,
        "p05": 1290.0,
        "p25": 1290.0,
        "median": 1290.0,
        "p75": 1290.0,
        "p95": 1290.0,
        "max": 1290.0,
        "mean": 1290.0,
    }
    return {
        "product_id": spec.product_id,
        "display_name": spec.display_name,
        "source_type": spec.source_type,
        "method": spec.method,
        "target_rows": spec.target_rows,
        "available_rows": spec.expected_rows,
        "rows_scanned": 0,
        "scan_mode": spec.scan_mode,
        "statistics_exact": True,
        "notes": spec.notes,
        "schema_dimensions": len(dimensions),
        "emitted_attributes": fixed,
        "populated_attributes": fixed,
        "observed_attributes": {key: None for key in fixed},
        "populated_attribute_distribution": [1290],
        "assignment_types": {"graph_assigned": spec.expected_rows * len(dimensions)},
        "populated_fields": spec.expected_rows * len(dimensions),
        "evidence_coverage": None,
        "description_coverage": None,
        "confidence": {key: None for key in fixed},
        "confidence_sample_size": 0,
        "contract": {
            "unknown_field_occurrences": 0,
            "unknown_field_ids": {},
            "duplicate_field_ids": 0,
            "malformed_fields": 0,
            "off_schema_values": 0,
        },
        "categories": [
            {
                "category": category,
                "dimensions": count,
                "populated_fields": spec.expected_rows * count,
                "emitted_fields": spec.expected_rows * count,
                "populated_rate": 1.0,
                "mean_populated_per_persona": float(count),
            }
            for category, count in sorted(category_dimensions.items())
        ],
        "dimensions": [
            {
                "field_id": str(item["id"]),
                "category": str(item.get("category") or "Uncategorized"),
                "populated": spec.expected_rows,
                "emitted": spec.expected_rows,
                "prevalence": 1.0,
                "evidence_rate": None,
                "description_rate": None,
            }
            for item in dimensions
        ],
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--products", default=",".join(spec.product_id for spec in PRODUCTS))
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="retain unselected products from an existing dataset_statistics.json",
    )
    args = parser.parse_args()
    selected = {item.strip() for item in args.products.split(",") if item.strip()}
    dimensions = json.loads(SCHEMA_PATH.read_text())["dimensions"]
    existing_by_id: dict[str, dict[str, Any]] = {}
    existing_path = args.results_dir / "dataset_statistics.json"
    if args.merge_existing:
        if not existing_path.exists():
            raise FileNotFoundError(f"cannot merge missing cache: {existing_path}")
        existing = json.loads(existing_path.read_text())
        existing_by_id = {item["product_id"]: item for item in existing["products"]}
    computed: dict[str, dict[str, Any]] = {}
    for spec in PRODUCTS:
        if spec.product_id not in selected:
            continue
        print(f"profiling {spec.product_id} ({spec.scan_mode})", flush=True)
        if spec.product_id == "synthetic":
            result = synthetic_result(spec, dimensions)
        else:
            profiler = Profiler(spec, dimensions)
            for row_number, row in enumerate(iter_product(spec.product_id), start=1):
                profiler.ingest(row)
                if row_number % 10_000 == 0:
                    print(f"  {row_number:,} rows", flush=True)
            result = profiler.finish()
            if spec.scan_mode == "full" and result["rows_scanned"] != spec.expected_rows:
                raise ValueError(
                    f"{spec.product_id}: scanned {result['rows_scanned']} rows, "
                    f"expected {spec.expected_rows}"
                )
        computed[spec.product_id] = result

    results = []
    for spec in PRODUCTS:
        result = computed.get(spec.product_id) or existing_by_id.get(spec.product_id)
        if result is not None:
            results.append(result)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_path": str(SCHEMA_PATH),
        "schema_sha256": hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest(),
        "schema_dimensions": len(dimensions),
        "random_seed": RANDOM_SEED,
        "products": results,
    }
    args.results_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.results_dir / "dataset_statistics.json"
    json_path.write_text(json.dumps(output, indent=2) + "\n")

    summary_rows = []
    category_rows = []
    dimension_rows = []
    for result in results:
        summary_rows.append(
            {
                "product_id": result["product_id"],
                "display_name": result["display_name"],
                "available_rows": result["available_rows"],
                "target_rows": result["target_rows"],
                "coverage_pct": 100 * result["available_rows"] / result["target_rows"],
                "rows_scanned": result["rows_scanned"],
                "scan_mode": result["scan_mode"],
                "statistics_exact": result["statistics_exact"],
                "schema_dimensions": result["schema_dimensions"],
                "mean_populated": result["populated_attributes"]["mean"],
                "median_populated": result["populated_attributes"]["median"],
                "p05_populated": result["populated_attributes"]["p05"],
                "p95_populated": result["populated_attributes"]["p95"],
                "mean_emitted": result["emitted_attributes"]["mean"],
                "evidence_coverage": result["evidence_coverage"],
                "description_coverage": result["description_coverage"],
                "unknown_field_occurrences": result["contract"]["unknown_field_occurrences"],
                "duplicate_field_ids": result["contract"]["duplicate_field_ids"],
                "off_schema_values": result["contract"]["off_schema_values"],
            }
        )
        for category in result["categories"]:
            category_rows.append({"product_id": result["product_id"], **category})
        for dimension in result["dimensions"]:
            dimension_rows.append({"product_id": result["product_id"], **dimension})

    write_csv(args.results_dir / "dataset_summary.csv", summary_rows, list(summary_rows[0]))
    write_csv(args.results_dir / "category_summary.csv", category_rows, list(category_rows[0]))
    write_csv(args.results_dir / "dimension_summary.csv", dimension_rows, list(dimension_rows[0]))
    print(f"wrote {json_path}")


if __name__ == "__main__":
    main()