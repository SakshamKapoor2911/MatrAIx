#!/usr/bin/env python3
"""Modal workflow for building a 2018-2023 user-indexed Amazon Reviews artifact.

This uses the Hugging Face dataset configs, e.g. `raw_review_Books`, and writes
Parquet shards partitioned by a stable user_id hash bucket. It avoids a single
shared SQLite writer, which is a poor fit for parallel cloud jobs.

Example:

    modal run personas/existing_data_curation/modal_amazon_user_index.py::build_sample_categories

    modal run personas/existing_data_curation/modal_amazon_user_index.py::build_categories \
      --categories Books,Kindle_Store,Movies_and_TV \
      --start-year 2018 \
      --end-year 2023

Outputs are written to the Modal Volume `amazon-reviews-user-index`.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import modal


APP_NAME = "cs231n-final-project"
VOLUME_NAME = "amazon-reviews-user-index"
VOLUME_MOUNT = Path("/amazon_user_index")
DATASET_NAME = "McAuley-Lab/Amazon-Reviews-2023"

CATEGORIES = [
    "All_Beauty",
    "Amazon_Fashion",
    "Appliances",
    "Arts_Crafts_and_Sewing",
    "Automotive",
    "Baby_Products",
    "Beauty_and_Personal_Care",
    "Books",
    "CDs_and_Vinyl",
    "Cell_Phones_and_Accessories",
    "Clothing_Shoes_and_Jewelry",
    "Digital_Music",
    "Electronics",
    "Gift_Cards",
    "Grocery_and_Gourmet_Food",
    "Handmade_Products",
    "Health_and_Household",
    "Health_and_Personal_Care",
    "Home_and_Kitchen",
    "Industrial_and_Scientific",
    "Kindle_Store",
    "Magazine_Subscriptions",
    "Movies_and_TV",
    "Musical_Instruments",
    "Office_Products",
    "Patio_Lawn_and_Garden",
    "Pet_Supplies",
    "Software",
    "Sports_and_Outdoors",
    "Subscription_Boxes",
    "Tools_and_Home_Improvement",
    "Toys_and_Games",
    "Video_Games",
    "Unknown",
]


image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "datasets==3.6.0",
        "huggingface_hub>=0.23.0,<1.0.0",
        "pyarrow>=15.0.0",
        "tqdm>=4.66.0",
    )
)

app = modal.App(APP_NAME, image=image)
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)


def normalize_timestamp(value: Any) -> int | None:
    if value is None:
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp < 0:
        return None
    if timestamp < 10_000_000_000:
        timestamp *= 1000
    return timestamp


def year_to_timestamp_ms(year: int | None, end: bool = False) -> int | None:
    if year is None:
        return None
    dt = datetime(year + 1 if end else year, 1, 1, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def timestamp_to_date(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date().isoformat()


def user_bucket(user_id: str, bucket_chars: int = 2) -> str:
    return hashlib.sha1(user_id.encode("utf-8")).hexdigest()[:bucket_chars]


def normalize_review(row: dict[str, Any], category: str) -> dict[str, Any] | None:
    user_id = row.get("user_id")
    if not user_id:
        return None
    timestamp = normalize_timestamp(row.get("timestamp"))
    return {
        "source": "amazon_reviews_2023",
        "category": category,
        "user_id": user_id,
        "user_bucket": user_bucket(user_id),
        "parent_asin": row.get("parent_asin"),
        "asin": row.get("asin"),
        "timestamp": timestamp,
        "date": timestamp_to_date(timestamp),
        "rating": row.get("rating"),
        "title": row.get("title") or "",
        "text": row.get("text") or "",
        "verified_purchase": row.get("verified_purchase"),
        "helpful_vote": row.get("helpful_vote"),
    }


def parse_categories(categories: str) -> list[str]:
    if categories == "all":
        return CATEGORIES
    parsed = [part.strip() for part in categories.split(",") if part.strip()]
    unknown = sorted(set(parsed) - set(CATEGORIES))
    if unknown:
        raise ValueError(f"Unknown Amazon Reviews 2023 categories: {', '.join(unknown)}")
    return parsed


def write_parquet(rows: list[dict[str, Any]], output_path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = Path("/tmp") / f"{output_path.name}.{time.time_ns()}.tmp.parquet"
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, tmp_path, compression="zstd", use_dictionary=True)
    shutil.move(str(tmp_path), output_path)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = Path("/tmp") / f"{path.name}.{time.time_ns()}.tmp"
    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    shutil.move(str(tmp_path), path)


@app.function(
    volumes={str(VOLUME_MOUNT): volume},
    timeout=24 * 60 * 60,
    cpu=8,
    memory=65536,
)
def build_category_user_stats(
    category: str,
    start_year: int = 2018,
    end_year: int = 2023,
    output_prefix: str = "amazon_reviews_2018_2023_user_stats",
    progress_every: int = 250_000,
    max_rows: int = 0,
) -> dict[str, Any]:
    """Pass 1: aggregate lightweight 2018-2023 user stats for one category."""
    from datasets import load_dataset

    if category not in CATEGORIES:
        raise ValueError(f"Unknown Amazon Reviews 2023 category: {category}")

    start_ts = year_to_timestamp_ms(start_year)
    end_ts = year_to_timestamp_ms(end_year, end=True)
    config = f"raw_review_{category}"
    output_root = VOLUME_MOUNT / output_prefix

    print(f"[modal_amazon_stats] Loading {DATASET_NAME}/{config}", flush=True)
    dataset = load_dataset(
        DATASET_NAME,
        config,
        split="full",
        streaming=True,
        trust_remote_code=True,
    )

    # user_id -> mutable stats list:
    # [review_count, first_ts, last_ts, text_chars, text_reviews, verified_count, rating_sum, rating_count]
    user_stats: dict[str, list[Any]] = {}
    scanned = 0
    kept = 0
    for row in dataset:
        scanned += 1
        if max_rows and scanned > max_rows:
            break
        if progress_every and scanned % progress_every == 0:
            print(
                f"[modal_amazon_stats] {category}: scanned {scanned:,}; "
                f"kept {kept:,}; users {len(user_stats):,}",
                flush=True,
            )

        row = dict(row)
        user_id = row.get("user_id")
        if not user_id:
            continue
        timestamp = normalize_timestamp(row.get("timestamp"))
        if start_ts is not None and (timestamp is None or timestamp < start_ts):
            continue
        if end_ts is not None and (timestamp is None or timestamp >= end_ts):
            continue

        stats = user_stats.get(user_id)
        if stats is None:
            stats = [0, timestamp, timestamp, 0, 0, 0, 0.0, 0]
            user_stats[user_id] = stats
        stats[0] += 1
        if timestamp is not None:
            stats[1] = timestamp if stats[1] is None else min(stats[1], timestamp)
            stats[2] = timestamp if stats[2] is None else max(stats[2], timestamp)
        text = row.get("text") or ""
        if text:
            stats[3] += len(text)
            stats[4] += 1
        if row.get("verified_purchase") is True:
            stats[5] += 1
        rating = row.get("rating")
        if isinstance(rating, int | float):
            stats[6] += float(rating)
            stats[7] += 1
        kept += 1

    rows_by_bucket: dict[str, list[dict[str, Any]]] = {}
    for user_id, stats in user_stats.items():
        bucket = user_bucket(user_id)
        rows_by_bucket.setdefault(bucket, []).append(
            {
                "user_id": user_id,
                "user_bucket": bucket,
                "category": category,
                "review_count": stats[0],
                "first_timestamp": stats[1],
                "last_timestamp": stats[2],
                "first_date": timestamp_to_date(stats[1]),
                "last_date": timestamp_to_date(stats[2]),
                "text_chars": stats[3],
                "text_reviews": stats[4],
                "verified_count": stats[5],
                "rating_sum": stats[6],
                "rating_count": stats[7],
            }
        )

    shard_count = 0
    for bucket, rows in rows_by_bucket.items():
        out_path = (
            output_root
            / f"bucket={bucket}"
            / f"category={category}"
            / "user_stats.parquet"
        )
        write_parquet(rows, out_path)
        shard_count += 1

    summary = {
        "dataset": DATASET_NAME,
        "config": config,
        "category": category,
        "start_year": start_year,
        "end_year": end_year,
        "scanned_rows": scanned,
        "kept_rows": kept,
        "unique_users": len(user_stats),
        "bucket_count": len(rows_by_bucket),
        "shard_count": shard_count,
        "output_prefix": output_prefix,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_root / "_summaries" / f"{category}.json"
    write_json(summary_path, summary)
    volume.commit()
    print(f"[modal_amazon_stats] {category}: {json.dumps(summary)}", flush=True)
    return summary


@app.function(
    volumes={str(VOLUME_MOUNT): volume},
    timeout=24 * 60 * 60,
    cpu=4,
    memory=16384,
)
def build_category_user_index(
    category: str,
    start_year: int = 2018,
    end_year: int = 2023,
    output_prefix: str = "amazon_reviews_2018_2023_user_buckets",
    bucket_flush_rows: int = 50_000,
    progress_every: int = 250_000,
    max_rows: int = 0,
) -> dict[str, Any]:
    """Build user-bucketed Parquet shards for one Amazon review category."""
    from datasets import load_dataset

    if category not in CATEGORIES:
        raise ValueError(f"Unknown Amazon Reviews 2023 category: {category}")

    start_ts = year_to_timestamp_ms(start_year)
    end_ts = year_to_timestamp_ms(end_year, end=True)
    config = f"raw_review_{category}"
    output_root = VOLUME_MOUNT / output_prefix

    print(f"[modal_amazon_index] Loading {DATASET_NAME}/{config}", flush=True)
    dataset = load_dataset(
        DATASET_NAME,
        config,
        split="full",
        streaming=True,
        trust_remote_code=True,
    )

    buffers: dict[str, list[dict[str, Any]]] = {}
    shard_counts: dict[str, int] = {}
    scanned = 0
    kept = 0
    for row in dataset:
        scanned += 1
        if max_rows and scanned > max_rows:
            break
        if progress_every and scanned % progress_every == 0:
            print(
                f"[modal_amazon_index] {category}: scanned {scanned:,}; kept {kept:,}",
                flush=True,
            )

        normalized = normalize_review(dict(row), category)
        if normalized is None:
            continue
        timestamp = normalized["timestamp"]
        if start_ts is not None and (timestamp is None or timestamp < start_ts):
            continue
        if end_ts is not None and (timestamp is None or timestamp >= end_ts):
            continue

        bucket = normalized["user_bucket"]
        bucket_rows = buffers.setdefault(bucket, [])
        bucket_rows.append(normalized)
        kept += 1
        if len(bucket_rows) >= bucket_flush_rows:
            shard_index = shard_counts.get(bucket, 0)
            out_path = (
                output_root
                / f"bucket={bucket}"
                / f"category={category}"
                / f"part-{shard_index:06d}.parquet"
            )
            write_parquet(bucket_rows, out_path)
            shard_counts[bucket] = shard_index + 1
            buffers[bucket] = []

    for bucket, bucket_rows in list(buffers.items()):
        if not bucket_rows:
            continue
        shard_index = shard_counts.get(bucket, 0)
        out_path = (
            output_root
            / f"bucket={bucket}"
            / f"category={category}"
            / f"part-{shard_index:06d}.parquet"
        )
        write_parquet(bucket_rows, out_path)
        shard_counts[bucket] = shard_index + 1

    summary = {
        "dataset": DATASET_NAME,
        "config": config,
        "category": category,
        "start_year": start_year,
        "end_year": end_year,
        "scanned_rows": scanned,
        "kept_rows": kept,
        "bucket_count": len(shard_counts),
        "shard_count": sum(shard_counts.values()),
        "output_prefix": output_prefix,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_root / "_summaries" / f"{category}.json"
    write_json(summary_path, summary)
    volume.commit()
    print(f"[modal_amazon_index] {category}: {json.dumps(summary)}", flush=True)
    return summary


@app.local_entrypoint()
def build_user_stats(
    categories: str = "all",
    start_year: int = 2018,
    end_year: int = 2023,
    output_prefix: str = "amazon_reviews_2018_2023_user_stats",
    max_rows: int = 0,
    wait: bool = True,
) -> None:
    """Launch Pass 1 lightweight user-stat jobs, one per category."""
    selected = parse_categories(categories)
    print(f"Launching {len(selected)} user-stat category jobs: {', '.join(selected)}")
    calls = [
        build_category_user_stats.spawn(
            category,
            start_year=start_year,
            end_year=end_year,
            output_prefix=output_prefix,
            max_rows=max_rows,
        )
        for category in selected
    ]
    for category, call in zip(selected, calls, strict=True):
        print(f"{category}: {call.object_id}")
    if wait:
        print("Waiting for category jobs to finish...")
        summaries = []
        for category, call in zip(selected, calls, strict=True):
            try:
                summary = call.get()
            except Exception as err:
                print(f"{category}: failed: {err}")
                raise
            summaries.append(summary)
            print(f"{category}: completed {summary}")
        print(f"Completed {len(summaries)} category jobs.")


@app.local_entrypoint()
def build_categories(
    categories: str = "Books,Kindle_Store,Movies_and_TV,Electronics,Office_Products,Home_and_Kitchen,Clothing_Shoes_and_Jewelry",
    start_year: int = 2018,
    end_year: int = 2023,
    output_prefix: str = "amazon_reviews_2018_2023_user_buckets",
    bucket_flush_rows: int = 50_000,
    max_rows: int = 0,
    wait: bool = True,
) -> None:
    """Launch one Modal job per category."""
    selected = parse_categories(categories)
    print(f"Launching {len(selected)} category jobs: {', '.join(selected)}")
    calls = [
        build_category_user_index.spawn(
            category,
            start_year=start_year,
            end_year=end_year,
            output_prefix=output_prefix,
            bucket_flush_rows=bucket_flush_rows,
            max_rows=max_rows,
        )
        for category in selected
    ]
    for category, call in zip(selected, calls, strict=True):
        print(f"{category}: {call.object_id}")
    if wait:
        print("Waiting for category jobs to finish...")
        summaries = []
        for category, call in zip(selected, calls, strict=True):
            try:
                summary = call.get()
            except Exception as err:
                print(f"{category}: failed: {err}")
                raise
            summaries.append(summary)
            print(f"{category}: completed {summary}")
        print(f"Completed {len(summaries)} category jobs.")


@app.local_entrypoint()
def build_sample_categories() -> None:
    """Small smoke test over a bounded number of rows."""
    build_categories(
        categories="All_Beauty,Software",
        start_year=2018,
        end_year=2023,
        output_prefix="amazon_reviews_smoke_test_user_buckets",
        bucket_flush_rows=10_000,
        max_rows=100_000,
    )
