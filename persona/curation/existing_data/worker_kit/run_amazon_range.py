#!/usr/bin/env python3
"""Run an assigned Amazon-review persona inference range."""

from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
import tarfile
import time
from typing import Any, Iterable

from persona.curation.existing_data.scripts.infer_amazon_review_dimensions import (
    DEFAULT_EVIDENCE_MAPPING_PATH,
    DEFAULT_MODEL,
    DEFAULT_SCHEMA_PATH,
    filter_amazon_supported_dimensions,
    filter_dimensions,
    infer_user_from_evidence_profile,
    load_evidence_mapping,
    load_schema,
    parse_csv_filter,
)
from persona.curation.existing_data.wiki_collab.amazon_collab import (
    AMAZON_PROTOCOL_ID,
    AMAZON_SOURCE_TYPE,
    AmazonProfileRow,
    load_amazon_profiles,
)
from persona.curation.existing_data.wiki_collab.core import (
    build_result_archive_name,
    load_protocol_manifest,
    parse_range,
)
from persona.curation.existing_data.worker_kit.backends import (
    DEFAULT_EFFORT,
    RUNNER_VERSION,
)


def write_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_archive(work_dir: Path, archive_path: Path) -> None:
    if archive_path.exists():
        archive_path.unlink()
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(work_dir / "results.jsonl.gz", arcname="results.jsonl.gz")
        tar.add(work_dir / "failures.jsonl.gz", arcname="failures.jsonl.gz")
        tar.add(work_dir / "run_manifest.json", arcname="run_manifest.json")


def select_dimensions(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    dimensions = load_schema(args.schema_path)
    mapping = load_evidence_mapping(args.evidence_mapping_path)
    explicit_filter = bool(args.dimension_categories or args.dimension_ids)
    dimensions = filter_dimensions(
        dimensions,
        category_filter=parse_csv_filter(args.dimension_categories),
        id_filter=parse_csv_filter(args.dimension_ids),
    )
    if (
        not args.no_amazon_default_schema_filter
        and not explicit_filter
    ):
        dimensions = filter_amazon_supported_dimensions(dimensions, mapping)
    if not dimensions:
        raise ValueError("No dimensions selected after filtering.")
    return dimensions, mapping


def mock_inference(row: AmazonProfileRow, dimensions: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    reviews = row.payload.get("reviews") or []
    first_review = next((review for review in reviews if isinstance(review, dict)), {})
    review_id = str(first_review.get("review_id") or "review-0")
    first_dimension = dimensions[0] if dimensions else {}
    values = first_dimension.get("values") if isinstance(first_dimension, dict) else []
    value = values[0] if isinstance(values, list) and values else "mock"
    quote = str(
        first_review.get("text")
        or first_review.get("title")
        or "Mock construction-review evidence."
    )
    evidence_item = {
        "id": "mock-evidence-1",
        "category": "mock",
        "summary": quote[:240],
        "supporting_reviews": [
            {
                "review_id": review_id,
                "quote": quote[:240],
            }
        ],
    }
    inferred_attributes = []
    if first_dimension:
        inferred_attributes.append(
            {
                "dimension_id": str(first_dimension["id"]),
                "value": value,
                "confidence": 0.5,
                "evidence_item_ids": [evidence_item["id"]],
                "evidence_review_ids": [review_id],
                "evidence_quotes": [quote[:240]],
                "reasoning": "Mock backend cites the first construction review for smoke validation.",
            }
        )
    return {
        "source": AMAZON_SOURCE_TYPE,
        "inference_mode": "evidence_profile",
        "schema_routing_mode": args.schema_routing_mode,
        "schema_path": str(args.schema_path),
        "schema_dimension_count": len(dimensions),
        "schema_mapped_dimension_count": len(dimensions),
        "schema_routed_category_count": 0,
        "schema_routed_categories": [],
        "schema_category_routes": [],
        "rejected_schema_category_routes": [],
        "recall_pass_dimension_count": 0,
        "recall_pass_valid_count": 0,
        "recall_pass_rejected_count": 0,
        "evidence_mapping_path": str(args.evidence_mapping_path),
        "user_id": row.user_id,
        "review_count": len(reviews),
        "review_context_count": len(reviews),
        "evidence_item_count": 1,
        "model": args.model,
        "request_count": 0,
        "status": "ok",
        "evidence_profile": {
            "user_id": row.user_id,
            "overview": "Mock Amazon collaboration run.",
            "evidence_items": [evidence_item],
        },
        "rejected_evidence_items": [],
        "inferred_attributes": inferred_attributes,
        "rejected_attributes": [],
    }


def run_one(
    *,
    row: AmazonProfileRow,
    args: argparse.Namespace,
    dimensions: list[dict[str, Any]],
    mapping: dict[str, Any] | None,
    api_key: str,
    existing_profiles: dict[str, dict[str, Any]],
    prompt_sha256: str,
    protocol_sha256: str,
    worker_id: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    started = time.time()
    try:
        if args.backend == "mock":
            inference_result = mock_inference(row, dimensions, args)
        elif args.inference_mode == "evidence_profile":
            if mapping is None:
                raise ValueError("Evidence mapping is required for evidence_profile mode.")
            inference_result = infer_user_from_evidence_profile(
                row.payload,
                dimensions,
                mapping,
                args,
                api_key,
                existing_profiles,
            )
        result = {
            "global_idx": row.global_idx,
            "task_id": row.task_id,
            "qid": row.qid,
            "source_type": AMAZON_SOURCE_TYPE,
            "user_id": row.user_id,
            "status": inference_result.get("status", "ok"),
            "input_sha256": row.input_sha256,
            "provenance": {
                "worker_id": worker_id,
                "backend": args.backend,
                "provider": "mock" if args.backend == "mock" else "openai",
                "requested_model": args.model,
                "reported_model": inference_result.get("model") or args.model,
                "model_source": "runner",
                "model_confidence": "exact" if args.backend != "mock" else "mock",
                "prompt_sha256": prompt_sha256,
                "protocol_sha256": protocol_sha256,
                "runner_version": RUNNER_VERSION,
                "effort": args.effort,
                "elapsed_seconds": round(time.time() - started, 3),
                "inference_mode": "evidence_profile",
            },
            "inference_result": inference_result,
            "inferred_attributes": inference_result.get("inferred_attributes") or [],
            "rejected_attributes": inference_result.get("rejected_attributes") or [],
            "evidence_profile": inference_result.get("evidence_profile"),
        }
        return result, None
    except Exception as exc:
        return None, {
            "global_idx": row.global_idx,
            "task_id": row.task_id,
            "qid": row.qid,
            "source_type": AMAZON_SOURCE_TYPE,
            "user_id": row.user_id,
            "status": "failed",
            "input_sha256": row.input_sha256,
            "worker_id": worker_id,
            "backend": args.backend,
            "requested_model": args.model,
            "effort": args.effort,
            "error": str(exc),
        }


def run_amazon_range(
    *,
    db_path: Path,
    protocol_dir: Path,
    range_start: int,
    range_end: int,
    worker_id: str,
    out_dir: Path,
    dataset_id: str,
    dataset_sha256: str,
    args: argparse.Namespace,
) -> Path:
    manifest = load_protocol_manifest(protocol_dir)
    if manifest.protocol_id != AMAZON_PROTOCOL_ID:
        raise ValueError(f"expected protocol_id {AMAZON_PROTOCOL_ID}, got {manifest.protocol_id}")
    rows = load_amazon_profiles(db_path, range_start, range_end)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_name = build_result_archive_name(worker_id, manifest.protocol_id, range_start, range_end)
    work_dir = out_dir / archive_name.removesuffix(".tar.gz")
    work_dir.mkdir(parents=True, exist_ok=True)
    if args.evidence_profiles_output is None:
        args.evidence_profiles_output = work_dir / "review_memory.jsonl"
    dimensions, mapping = select_dimensions(args)
    api_key = "" if args.backend == "mock" else os.environ.get("OPENAI_API_KEY", "")
    if args.backend != "mock" and not api_key:
        raise RuntimeError("OPENAI_API_KEY is required unless --backend mock is used.")
    existing_profiles: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in rows:
        result, failure = run_one(
            row=row,
            args=args,
            dimensions=dimensions,
            mapping=mapping,
            api_key=api_key,
            existing_profiles=existing_profiles,
            prompt_sha256=manifest.prompt_sha256,
            protocol_sha256=manifest.protocol_sha256,
            worker_id=worker_id,
        )
        if result is not None:
            results.append(result)
        if failure is not None:
            failures.append(failure)
    results.sort(key=lambda item: item["global_idx"])
    failures.sort(key=lambda item: item["global_idx"])
    write_jsonl_gz(work_dir / "results.jsonl.gz", results)
    write_jsonl_gz(work_dir / "failures.jsonl.gz", failures)
    run_manifest = {
        "worker_id": worker_id,
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_sha256,
        "protocol_id": manifest.protocol_id,
        "protocol_sha256": manifest.protocol_sha256,
        "range_start": range_start,
        "range_end": range_end,
        "backend": args.backend,
        "provider": "mock" if args.backend == "mock" else "openai",
        "requested_model": args.model,
        "reported_models": _reported_models(results),
        "auth_mode": "none" if args.backend == "mock" else "api_key",
        "concurrency": 1,
        "effort": args.effort,
        "runner_version": RUNNER_VERSION,
        "source_type": AMAZON_SOURCE_TYPE,
        "inference_mode": "evidence_profile",
        "schema_path": str(args.schema_path),
        "evidence_mapping_path": str(args.evidence_mapping_path),
        "succeeded": len(results),
        "failed": len(failures),
    }
    (work_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    archive_path = out_dir / archive_name
    build_archive(work_dir, archive_path)
    return archive_path


def _reported_models(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in results:
        model = str(row.get("provenance", {}).get("reported_model") or "unknown")
        counts[model] = counts.get(model, 0) + 1
    return counts


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--range", required=True, dest="range_spec")
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("amazon_collab_runs"))
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--backend", choices=("openai-api", "mock"), default="openai-api")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--effort", default=DEFAULT_EFFORT)
    parser.add_argument("--schema-path", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument(
        "--inference-mode",
        choices=("evidence_profile",),
        default="evidence_profile",
        help="Compatibility flag; Amazon collaboration always uses evidence_profile mode.",
    )
    parser.add_argument("--evidence-mapping-path", type=Path, default=DEFAULT_EVIDENCE_MAPPING_PATH)
    parser.add_argument("--evidence-profiles-output", type=Path)
    parser.add_argument("--review-memory-output", dest="evidence_profiles_output", type=Path)
    parser.add_argument("--overwrite-profiles", action="store_true")
    parser.add_argument("--no-amazon-default-schema-filter", action="store_true")
    parser.add_argument("--max-reviews-per-user", type=int, default=80)
    parser.add_argument("--power-user-min-reviews", type=int, default=1000)
    parser.add_argument("--power-user-min-text-chars", type=int, default=250_000)
    parser.add_argument("--power-user-max-reviews", type=int, default=200)
    parser.add_argument("--no-adaptive-power-review-cap", action="store_true")
    parser.add_argument(
        "--context-selection-strategy",
        choices=("temporal", "category_temporal", "informative_category_temporal"),
        default="category_temporal",
    )
    parser.add_argument("--max-review-text-chars", type=int, default=500)
    parser.add_argument("--max-review-context-chars", type=int, default=100_000)
    parser.add_argument("--window-summary-threshold-chars", type=int, default=40_000)
    parser.add_argument("--window-summary-max-chars", type=int, default=40_000)
    parser.add_argument("--window-summary-max-rows", type=int, default=80)
    parser.add_argument("--max-evidence-items", type=int, default=120)
    parser.add_argument("--max-window-evidence-items", type=int, default=100)
    parser.add_argument(
        "--schema-routing-mode",
        choices=("none", "category", "recall"),
        default="recall",
        help="Default is recall for better assignment recall in collaboration runs.",
    )
    parser.add_argument("--schema-router-min-confidence", type=float, default=0.25)
    parser.add_argument(
        "--schema-router-always-include",
        default=(
            "Interests:*,Behavior:*,Values & Motivation,Risk & Decision,"
            "Linguistic:*,Expertise:*,Personality:*,Health:*,"
            "Worldview: Beliefs,Demographic: Family,Demographic: Life Events,"
            "Social Identity, Relationships & Community"
        ),
    )
    parser.add_argument(
        "--recall-pass-categories",
        default=(
            "Personality:*,Values & Motivation,Risk & Decision,Behavior:*,"
            "Expertise:*,Health:*,Worldview: Beliefs,Demographic: Family,"
            "Demographic: Life Events,Social Identity, Relationships & Community"
        ),
    )
    parser.add_argument("--recall-dimensions-per-call", type=int, default=120)
    parser.add_argument("--dimensions-per-call", type=int, default=200)
    parser.add_argument("--dimension-categories", default="")
    parser.add_argument("--dimension-ids", default="")
    parser.add_argument("--allow-unsplit-histories", action="store_true")
    return parser.parse_args(list(argv) if argv is not None else None)


def main() -> int:
    args = parse_args()
    range_start, range_end = parse_range(args.range_spec)
    archive = run_amazon_range(
        db_path=args.db,
        protocol_dir=args.protocol,
        range_start=range_start,
        range_end=range_end,
        worker_id=args.worker_id,
        out_dir=args.out_dir,
        dataset_id=args.dataset_id,
        dataset_sha256=args.dataset_sha256,
        args=args,
    )
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
