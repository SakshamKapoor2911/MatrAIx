#!/usr/bin/env python3
"""Targeted product-info enrichment for prepared Amazon histories.

This runs after temporal splitting. It only joins compact product metadata for
construction rows that will affect the worker package: selected high-signal text
reviews and non-text construction rows used in summary stats.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any, Iterable

from huggingface_hub import list_repo_files

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from persona.curation.existing_data.scripts.export_hf_amazon_user_histories import (  # noqa: E402
    compact_product_info,
    list_relevant_metadata_shards,
    read_shard_rows,
)
from persona.curation.existing_data.scripts.make_amazon_collab_package import (  # noqa: E402
    _select_high_signal_text_reviews,
)
from persona.curation.existing_data.scripts.prepare_hf_amazon_user_histories import (  # noqa: E402
    category_review_stats,
    review_text,
)


DEFAULT_REPO_ID = "MatrAIx/MatrAIx"
DEFAULT_METADATA_PREFIX = (
    "amazon/modal_artifacts/amazon_reviews_2023_metadata_by_parent_asin_bucket_v2"
)


def log(message: str) -> None:
    print(f"[amazon_product_enrich] {message}", flush=True)


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def metadata_cache_key(parent_asin: str, category: str) -> str:
    return json.dumps([parent_asin, category], separators=(",", ":"))


def parse_metadata_cache_key(value: str) -> tuple[str, str]:
    parent_asin, category = json.loads(value)
    return str(parent_asin), str(category)


def load_cache(path: Path | None) -> tuple[dict[tuple[str, str], dict[str, Any]], set[str]]:
    if path is None or not path.exists():
        return {}, set()
    data = json.loads(path.read_text(encoding="utf-8"))
    metadata = {
        parse_metadata_cache_key(key): value
        for key, value in (data.get("metadata") or {}).items()
        if isinstance(value, dict)
    }
    processed_files = {str(item) for item in data.get("processed_files") or []}
    log(
        f"loaded cache: {len(metadata):,} matched pairs, "
        f"{len(processed_files):,} processed metadata files"
    )
    return metadata, processed_files


def write_cache(
    path: Path | None,
    *,
    metadata: dict[tuple[str, str], dict[str, Any]],
    processed_files: set[str],
) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(
            {
                "metadata": {
                    metadata_cache_key(parent_asin, category): info
                    for (parent_asin, category), info in sorted(metadata.items())
                },
                "processed_files": sorted(processed_files),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def review_key(review: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(review.get("category") or ""),
        str(review.get("parent_asin") or ""),
        str(review.get("asin") or ""),
        str(review.get("timestamp") or ""),
        str(review.get("text") or ""),
    )


def collect_requested(
    rows: list[dict[str, Any]],
    *,
    max_text_reviews_per_user: int,
) -> dict[str, set[str]]:
    requested: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        reviews = row.get("reviews")
        if not isinstance(reviews, list):
            continue
        selected_text_keys = {
            review_key(review)
            for review in _select_high_signal_text_reviews(
                [review for review in reviews if isinstance(review, dict)],
                max_text_reviews_per_user,
            )
        }
        for review in reviews:
            if not isinstance(review, dict):
                continue
            parent_asin = str(review.get("parent_asin") or "")
            category = str(review.get("category") or "")
            if not parent_asin or not category:
                continue
            is_selected_text = review_key(review) in selected_text_keys
            is_non_text = not review_text(review)
            if is_selected_text or is_non_text:
                requested[category].add(parent_asin)
    return requested


def load_product_metadata(
    *,
    repo_id: str,
    metadata_prefix: str,
    repo_files: list[str],
    requested: dict[str, set[str]],
    token: str | bool | None,
    download_delay_seconds: float,
    cache_path: Path | None,
) -> dict[tuple[str, str], dict[str, Any]]:
    metadata_shards = list_relevant_metadata_shards(repo_files, metadata_prefix, requested)
    shard_count = sum(len(value) for value in metadata_shards.values())
    pair_count = sum(len(value) for value in requested.values())
    log(f"requested category-parent_asin pairs: {pair_count:,}")
    log(f"targeted metadata shards: {shard_count:,}")

    metadata, processed_files = load_cache(cache_path)
    columns = ["parent_asin", "source_category", "main_category", "title", "categories_json"]
    for index, ((bucket, category), filenames) in enumerate(
        sorted(metadata_shards.items()), start=1
    ):
        log(
            f"[{index:,}/{len(metadata_shards):,}] "
            f"bucket={bucket} source_category={category} ({len(filenames)} shards)"
        )
        wanted_parent_asins = requested.get(category, set())
        for filename in filenames:
            if filename in processed_files:
                continue
            for row in read_shard_rows(
                repo_id,
                filename,
                token=token,
                columns=columns,
                download_delay_seconds=download_delay_seconds,
            ):
                parent_asin = str(row.get("parent_asin") or "")
                if parent_asin in wanted_parent_asins:
                    metadata[(parent_asin, category)] = compact_product_info(row)
            processed_files.add(filename)
            write_cache(cache_path, metadata=metadata, processed_files=processed_files)
    log(f"matched category-parent_asin pairs: {len(metadata):,}")
    return metadata


def apply_metadata(
    rows: list[dict[str, Any]],
    metadata: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, int]:
    updated_reviews = 0
    updated_validation_reviews = 0
    for row in rows:
        for review in row.get("reviews") or []:
            if not isinstance(review, dict):
                continue
            parent_asin = str(review.get("parent_asin") or "")
            category = str(review.get("category") or "")
            info = metadata.get((parent_asin, category))
            if info:
                review.update(info)
                updated_reviews += 1
        row["category_review_stats"] = category_review_stats(row.get("reviews") or [])

        for review in row.get("validation_reviews") or []:
            if not isinstance(review, dict):
                continue
            parent_asin = str(review.get("parent_asin") or "")
            category = str(review.get("category") or "")
            info = metadata.get((parent_asin, category))
            if info:
                review.update(info)
                updated_validation_reviews += 1
        row["validation_category_review_stats"] = category_review_stats(
            row.get("validation_reviews") or []
        )
    return {
        "updated_construction_reviews": updated_reviews,
        "updated_validation_reviews": updated_validation_reviews,
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, default=None)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--metadata-artifact-prefix", default=DEFAULT_METADATA_PREFIX)
    parser.add_argument("--max-text-reviews-per-user", type=int, default=200)
    parser.add_argument("--download-delay-seconds", type=float, default=0.05)
    parser.add_argument("--cache", type=Path, default=None)
    parser.add_argument("--token", default=None)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    token: str | bool | None = args.token or None
    started_at = time.time()
    rows = list(iter_jsonl(args.input))
    requested = collect_requested(
        rows,
        max_text_reviews_per_user=args.max_text_reviews_per_user,
    )
    repo_files = list_repo_files(args.repo_id, repo_type="dataset", token=token)
    metadata = load_product_metadata(
        repo_id=args.repo_id,
        metadata_prefix=args.metadata_artifact_prefix,
        repo_files=repo_files,
        requested=requested,
        token=token,
        download_delay_seconds=args.download_delay_seconds,
        cache_path=args.cache,
    )
    update_summary = apply_metadata(rows, metadata)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "input": str(args.input),
        "output": str(args.output),
        "rows": len(rows),
        "requested_category_parent_asin_pairs": sum(len(v) for v in requested.values()),
        "requested_categories": len(requested),
        "matched_category_parent_asin_pairs": len(metadata),
        **update_summary,
        "elapsed_seconds": round(time.time() - started_at, 3),
        "policy": "selected_text_reviews_and_non_text_construction_rows_only",
    }
    summary_path = args.summary_output or args.output.with_suffix(
        args.output.suffix + ".product_enrich_summary.json"
    )
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log(f"wrote enriched histories: {args.output}")
    log(f"summary: {json.dumps(summary, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
