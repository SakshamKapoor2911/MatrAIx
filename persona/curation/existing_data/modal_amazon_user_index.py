#!/usr/bin/env python3
"""Modal workflow for Amazon Reviews 2023 persona-construction artifacts.

The main path is:

1. build 2018-2023 per-user summary stats,
2. reduce those stats into an eligible user pool,
3. build review-level user-bucketed Parquet for eligible users,
4. build parent-ASIN-bucketed product metadata,
5. export selected candidate users to local JSONL histories for inference.

Outputs are written to the Modal Volume `amazon-reviews-user-index`.
"""

from __future__ import annotations

import hashlib
import gzip
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import modal


APP_NAME = "personabench-amazon-reviews"
VOLUME_NAME = "amazon-reviews-user-index"
VOLUME_MOUNT = Path("/amazon_user_index")
DATASET_NAME = "McAuley-Lab/Amazon-Reviews-2023"
DEFAULT_STATS_PREFIX = "amazon_reviews_2018_2023_user_stats"
DEFAULT_ELIGIBLE_USERS_PREFIX = "amazon_reviews_2018_2023_eligible_users_min30_verified70_text2000"
DEFAULT_ELIGIBLE_REVIEW_PREFIX = "amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000"
DEFAULT_DERIVED_ELIGIBLE_USERS_PREFIX = "amazon_reviews_2018_2023_eligible_users_min30_verified70_text3000"
DEFAULT_DERIVED_REVIEW_PREFIX = "amazon_reviews_2018_2023_user_buckets_min30_verified70_text3000"
DEFAULT_METADATA_PREFIX = "amazon_reviews_2023_metadata_by_parent_asin_bucket_v2"
DEFAULT_HF_REPO_ID = "ElegantLin/PersonaBench"
DEFAULT_HF_AMAZON_PREFIX = "amazon/modal_artifacts"
CURRENT_MODAL_ARTIFACT_PREFIXES = [
    DEFAULT_STATS_PREFIX,
    DEFAULT_ELIGIBLE_USERS_PREFIX,
    DEFAULT_ELIGIBLE_REVIEW_PREFIX,
    DEFAULT_METADATA_PREFIX,
]
DEFAULT_LOCAL_HISTORY_OUTPUT = (
    Path("raw")
    / "amazon_reviews_2023"
    / "persona_dimension_inference"
    / "user_histories.jsonl"
)
META_URL_TEMPLATE = (
    "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/"
    "raw/meta_categories/meta_{category}.jsonl.gz"
)

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

FULFILLMENT_OR_TEMPLATE_REVIEW_PATTERNS = [
    "never arrived",
    "did not arrive",
    "didn't arrive",
    "never received",
    "never received it",
    "never received item",
    "never received product",
    "item never arrived",
    "package never arrived",
    "product never arrived",
    "order never arrived",
    "did not receive",
    "didn't receive",
    "not received",
    "lost package",
    "lost in shipping",
    "tracking says delivered",
    "tracking showed delivered",
    "delivered to wrong address",
    "delivered to the wrong address",
    "sent to wrong address",
    "wrong item",
    "wrong product",
    "wrong product sent",
    "sent wrong item",
    "sent the wrong item",
    "received wrong item",
    "received the wrong item",
    "missing item",
    "missing items",
    "missing parts",
    "missing pieces",
    "incomplete order",
    "arrived damaged",
    "came damaged",
    "delivered damaged",
    "damaged in shipping",
    "damaged during shipping",
    "damaged during delivery",
    "box was damaged",
    "box arrived damaged",
    "damaged box",
    "crushed box",
    "dented box",
    "torn box",
    "package was open",
    "package arrived open",
    "box was open",
    "opened box",
    "resealed box",
    "returning unopened",
    "returned unopened",
    "had to return it",
    "had to send it back",
    "could not use because it arrived damaged",
    "can't review the product",
    "cannot review the product",
    "unable to review the product",
    "not the product's fault",
    "not the products fault",
    "only giving one star because delivery",
    "one star because delivery",
    "one star for delivery",
    "one star due to delivery",
    "review is for delivery",
    "reviewing the delivery",
    "in exchange for my honest review",
    "in exchange for an honest review",
    "in exchange for this review",
    "in exchange for a review",
    "received this product for free",
    "received the product for free",
    "received this item for free",
    "received the item for free",
    "received a free product",
    "received the product for free",
    "received a free sample",
    "received free product",
    "received free sample",
    "received a discount in exchange for",
    "received a discounted product in exchange for",
    "received this product at a discount",
    "received this item at a discount",
    "provided for my honest review",
    "provided in exchange for my honest review",
    "provided for an honest review",
    "provided in exchange for an honest review",
    "sent to me for my honest review",
    "sent to me in exchange for my honest review",
    "sample provided for review",
    "free sample provided for review",
    "complimentary product provided for review",
    "complimentary sample provided for review",
    "sponsored review",
    "this is a sponsored review",
    "paid review",
    "this is a paid review",
    "promotional review",
    "amazon vine",
    "vine customer review",
    "vine voice",
    "amazon vine voice",
    "vine program",
    "early reviewer program",
    "i am writing this review in exchange for",
    "i'm writing this review in exchange for",
    "i was given this product in exchange for",
    "i was given this item in exchange for",
    "i was provided this product in exchange for",
    "i was provided this item in exchange for",
    "i was sent this product in exchange for",
    "i was sent this item in exchange for",
    "i received compensation for this review",
    "compensated for this review",
    "discounted for my honest review",
    "free for my honest review",
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


def stable_review_id(row: dict[str, Any], category: str, timestamp: int | None) -> str:
    existing = row.get("review_id")
    if existing is not None:
        existing_id = str(existing)
        if existing_id and existing_id.isascii():
            return existing_id

    text_hash = hashlib.sha1(
        (
            str(row.get("title") or "")
            + "\0"
            + str(row.get("text") or "")
        ).encode("utf-8", errors="replace")
    ).hexdigest()
    payload = {
        "category": category,
        "user_id": row.get("user_id"),
        "parent_asin": row.get("parent_asin"),
        "asin": row.get("asin"),
        "timestamp": timestamp,
        "rating": row.get("rating"),
        "title_text_hash": text_hash,
    }
    digest = hashlib.sha1(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode(
            "ascii"
        )
    ).hexdigest()
    return f"amzrev_{digest[:24]}"


def user_bucket(user_id: str, bucket_chars: int = 2) -> str:
    return hashlib.sha1(user_id.encode("utf-8")).hexdigest()[:bucket_chars]


def parent_asin_bucket(parent_asin: str, bucket_chars: int = 2) -> str:
    return hashlib.sha1(parent_asin.encode("utf-8")).hexdigest()[:bucket_chars]


def metadata_url(category: str) -> str:
    return META_URL_TEMPLATE.format(category=category)


def open_remote_gzip_jsonl(url: str) -> Iterator[dict[str, Any]]:
    try:
        with urllib.request.urlopen(url) as response:
            with gzip.GzipFile(fileobj=response) as gz:
                for raw_line in gz:
                    if raw_line.strip():
                        yield json.loads(raw_line)
    except urllib.error.URLError as err:
        raise RuntimeError(f"Failed to stream {url}: {err}") from err


def json_dumps_or_empty(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def string_or_empty(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_review_match_text(value: str) -> str:
    value = value.lower()
    value = value.replace("’", "'").replace("`", "'").replace("´", "'")
    value = re.sub(r"[^a-z0-9']+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


FULFILLMENT_OR_TEMPLATE_REVIEW_MATCH_PATTERNS = [
    normalize_review_match_text(pattern)
    for pattern in FULFILLMENT_OR_TEMPLATE_REVIEW_PATTERNS
]


def fulfillment_or_template_review_match(review: dict[str, Any]) -> str | None:
    match_text = normalize_review_match_text(
        f"{review.get('title') or ''} {review.get('text') or ''}"
    )
    if not match_text:
        return None
    padded = f" {match_text} "
    for pattern in FULFILLMENT_OR_TEMPLATE_REVIEW_MATCH_PATTERNS:
        if pattern and f" {pattern} " in padded:
            return pattern
    return None


def category_review_stats(reviews: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    stats_by_category: dict[str, dict[str, Any]] = {}
    for review in reviews:
        category = str(review.get("category") or "Unknown")
        stats = stats_by_category.setdefault(
            category,
            {
                "review_count": 0,
                "rating_count": 0,
                "rating_sum": 0.0,
                "average_rating": None,
                "rating_counts": {},
            },
        )
        stats["review_count"] += 1
        rating = float_or_none(review.get("rating"))
        if rating is None:
            continue
        rating_key = str(int(rating)) if rating.is_integer() else str(rating)
        stats["rating_count"] += 1
        stats["rating_sum"] += rating
        stats["rating_counts"][rating_key] = stats["rating_counts"].get(rating_key, 0) + 1

    for stats in stats_by_category.values():
        rating_count = stats["rating_count"]
        if rating_count:
            stats["average_rating"] = round(stats["rating_sum"] / rating_count, 4)
        stats["rating_sum"] = round(stats["rating_sum"], 4)
        stats["rating_counts"] = dict(sorted(stats["rating_counts"].items()))
    return dict(sorted(stats_by_category.items()))


def merge_category_review_stats(
    target: dict[str, dict[str, Any]],
    source: dict[str, dict[str, Any]],
) -> None:
    for category, source_stats in source.items():
        target_stats = target.setdefault(
            category,
            {
                "review_count": 0,
                "rating_count": 0,
                "rating_sum": 0.0,
                "average_rating": None,
                "rating_counts": {},
            },
        )
        target_stats["review_count"] += int(source_stats.get("review_count") or 0)
        target_stats["rating_count"] += int(source_stats.get("rating_count") or 0)
        target_stats["rating_sum"] += float(source_stats.get("rating_sum") or 0.0)
        for rating, count in source_stats.get("rating_counts", {}).items():
            rating_counts = target_stats["rating_counts"]
            rating_counts[str(rating)] = rating_counts.get(str(rating), 0) + int(count or 0)


def finalize_category_review_stats(
    stats_by_category: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    finalized = {}
    for category, stats in sorted(stats_by_category.items()):
        rating_count = int(stats.get("rating_count") or 0)
        rating_sum = round(float(stats.get("rating_sum") or 0.0), 4)
        finalized[category] = {
            "review_count": int(stats.get("review_count") or 0),
            "rating_count": rating_count,
            "rating_sum": rating_sum,
            "average_rating": round(rating_sum / rating_count, 4) if rating_count else None,
            "rating_counts": dict(sorted(stats.get("rating_counts", {}).items())),
        }
    return finalized


def temporal_train_validation_split(
    reviews: list[dict[str, Any]],
    train_fraction: float = 0.8,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not 0 < train_fraction <= 1:
        raise ValueError("train_fraction must be in (0, 1]")
    sorted_reviews = sorted(
        reviews,
        key=lambda row: (
            row.get("timestamp") or 0,
            str(row.get("category") or ""),
            str(row.get("parent_asin") or ""),
            str(row.get("asin") or ""),
        ),
    )
    if train_fraction == 1 or len(sorted_reviews) <= 1:
        split_index = len(sorted_reviews)
    else:
        split_index = int(len(sorted_reviews) * train_fraction)
        split_index = max(1, min(split_index, len(sorted_reviews) - 1))
    train_reviews = sorted_reviews[:split_index]
    validation_reviews = sorted_reviews[split_index:]
    train_text_reviews = sum(1 for review in train_reviews if review.get("text"))
    validation_text_reviews = sum(1 for review in validation_reviews if review.get("text"))
    train_rating_count = sum(1 for review in train_reviews if float_or_none(review.get("rating")) is not None)
    validation_rating_count = sum(
        1 for review in validation_reviews if float_or_none(review.get("rating")) is not None
    )
    train_rating_only_count = sum(
        1
        for review in train_reviews
        if float_or_none(review.get("rating")) is not None and not review.get("text")
    )
    validation_rating_only_count = sum(
        1
        for review in validation_reviews
        if float_or_none(review.get("rating")) is not None and not review.get("text")
    )
    split_summary = {
        "method": "per_user_temporal",
        "unit": "review_or_rating_row",
        "train_fraction": train_fraction,
        "construction_row_count": len(train_reviews),
        "validation_row_count": len(validation_reviews),
        "full_row_count": len(sorted_reviews),
        "construction_review_count": len(train_reviews),
        "validation_review_count": len(validation_reviews),
        "full_review_count": len(sorted_reviews),
        "construction_text_review_count": train_text_reviews,
        "validation_text_review_count": validation_text_reviews,
        "construction_rating_count": train_rating_count,
        "validation_rating_count": validation_rating_count,
        "construction_rating_only_count": train_rating_only_count,
        "validation_rating_only_count": validation_rating_only_count,
        "construction_first_timestamp": train_reviews[0].get("timestamp") if train_reviews else None,
        "construction_last_timestamp": train_reviews[-1].get("timestamp") if train_reviews else None,
        "validation_first_timestamp": validation_reviews[0].get("timestamp") if validation_reviews else None,
        "validation_last_timestamp": validation_reviews[-1].get("timestamp") if validation_reviews else None,
    }
    return train_reviews, validation_reviews, split_summary


def normalize_review(row: dict[str, Any], category: str) -> dict[str, Any] | None:
    user_id = row.get("user_id")
    if not user_id:
        return None
    timestamp = normalize_timestamp(row.get("timestamp"))
    return {
        "source": "amazon_reviews_2023",
        "category": category,
        "user_id": user_id,
        "review_id": stable_review_id(row, category, timestamp),
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


def normalize_metadata(row: dict[str, Any], category: str) -> dict[str, Any] | None:
    parent_asin = row.get("parent_asin")
    if not parent_asin:
        return None
    bucket = parent_asin_bucket(parent_asin)
    return {
        "source": "amazon_reviews_2023",
        "source_category": category,
        "parent_asin": parent_asin,
        "metadata_bucket": bucket,
        "main_category": string_or_empty(row.get("main_category")),
        "title": string_or_empty(row.get("title")),
        "average_rating": float_or_none(row.get("average_rating")),
        "rating_number": int_or_none(row.get("rating_number")),
        "features_json": json_dumps_or_empty(row.get("features")),
        "description_json": json_dumps_or_empty(row.get("description")),
        "price_text": string_or_empty(row.get("price")),
        "store": string_or_empty(row.get("store")),
        "categories_json": json_dumps_or_empty(row.get("categories")),
        "details_json": json_dumps_or_empty(row.get("details")),
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


def bucket_values(bucket_chars: int = 2) -> list[str]:
    return [f"{idx:0{bucket_chars}x}" for idx in range(16**bucket_chars)]


def parse_buckets(value: str, bucket_chars: int = 2) -> list[str]:
    if value == "all":
        return bucket_values(bucket_chars)
    parsed = [part.strip().lower() for part in value.split(",") if part.strip()]
    valid = set(bucket_values(bucket_chars))
    unknown = sorted(set(parsed) - valid)
    if unknown:
        raise ValueError(f"Unknown user buckets: {', '.join(unknown)}")
    return parsed


def read_parquet_rows(path: Path) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    # Read the file directly. pq.read_table(path) can infer Hive partitions
    # from parent dirs like category=Books, which conflicts with the explicit
    # category column written in the file.
    table = pq.ParquetFile(path).read()
    return table.to_pylist()


def read_parquet_rows_with_columns(path: Path, columns: list[str]) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    table = pq.ParquetFile(path).read(columns=columns)
    return table.to_pylist()


def hf_path(path_prefix: str, *parts: str) -> str:
    path_parts = [path_prefix.strip("/")]
    path_parts.extend(str(part).strip("/") for part in parts if str(part).strip("/"))
    return "/".join(path_parts)


def hf_api():
    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN") or None
    return HfApi(token=token)


def hf_repo_files(repo_id: str, revision: str = "main") -> list[str]:
    return hf_api().list_repo_files(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
    )


def hf_files_under(repo_files: list[str], prefix: str) -> list[str]:
    normalized_prefix = prefix.strip("/") + "/"
    return sorted(path for path in repo_files if path.startswith(normalized_prefix))


def read_hf_parquet_rows(
    repo_id: str,
    path_in_repo: str,
    revision: str = "main",
    columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq

    local_path = hf_hub_download(
        repo_id=repo_id,
        repo_type="dataset",
        filename=path_in_repo,
        revision=revision,
    )
    table = pq.ParquetFile(local_path).read(columns=columns)
    return table.to_pylist()


def iter_local_jsonl_or_gz(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def write_local_jsonl(path: Path, rows: Iterator[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_eligible_user_ids(eligible_prefix: str) -> set[str]:
    root = VOLUME_MOUNT / eligible_prefix
    user_ids: set[str] = set()
    for bucket_dir in sorted(root.glob("bucket=*")):
        parquet_path = bucket_dir / "eligible_users.parquet"
        if not parquet_path.exists():
            continue
        for row in read_parquet_rows(parquet_path):
            user_id = row.get("user_id")
            if user_id:
                user_ids.add(str(user_id))
    return user_ids


def metadata_for_parent_asins(
    parent_asins_by_category: dict[str, set[str]],
    metadata_prefix: str,
) -> dict[tuple[str, str], dict[str, Any]]:
    metadata: dict[tuple[str, str], dict[str, Any]] = {}
    columns = [
        "parent_asin",
        "source_category",
        "main_category",
        "title",
        "average_rating",
        "rating_number",
        "features_json",
        "description_json",
        "price_text",
        "store",
        "categories_json",
        "details_json",
    ]
    for category, parent_asins in parent_asins_by_category.items():
        parent_asins_by_bucket: dict[str, set[str]] = {}
        for parent_asin in parent_asins:
            parent_asins_by_bucket.setdefault(parent_asin_bucket(parent_asin), set()).add(parent_asin)
        for bucket, bucket_parent_asins in parent_asins_by_bucket.items():
            metadata_dir = (
                VOLUME_MOUNT
                / metadata_prefix
                / f"bucket={bucket}"
                / f"source_category={category}"
            )
            if not metadata_dir.exists():
                continue
            for parquet_path in sorted(metadata_dir.glob("part-*.parquet")):
                for row in read_parquet_rows_with_columns(parquet_path, columns):
                    parent_asin = row.get("parent_asin")
                    if parent_asin in bucket_parent_asins:
                        source_category = str(row.get("source_category") or category)
                        metadata[(str(parent_asin), source_category)] = row
    return metadata


def attach_inline_product_metadata(
    reviews: list[dict[str, Any]],
    metadata: dict[tuple[str, str], dict[str, Any]],
) -> None:
    for review in reviews:
        parent_asin = review.get("parent_asin")
        if not parent_asin:
            continue
        category = str(review.get("category") or "")
        row = metadata.get((str(parent_asin), category)) or metadata.get((str(parent_asin), ""))
        if row:
            review["product_metadata"] = row


def compact_metadata_sidecar_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "amazon_reviews_2023",
        "parent_asin": row.get("parent_asin"),
        "source_category": row.get("source_category"),
        "main_category": row.get("main_category"),
        "title": row.get("title"),
        "categories_json": row.get("categories_json"),
    }


def parent_asins_by_category_from_histories(path: Path) -> dict[str, set[str]]:
    parent_asins_by_category: dict[str, set[str]] = {}
    for user_row in iter_local_jsonl_or_gz(path):
        for field in ("reviews", "validation_reviews"):
            reviews = user_row.get(field) or []
            if not isinstance(reviews, list):
                continue
            for review in reviews:
                if not isinstance(review, dict):
                    continue
                parent_asin = review.get("parent_asin")
                category = review.get("category")
                if parent_asin and category:
                    parent_asins_by_category.setdefault(str(category), set()).add(str(parent_asin))
    return parent_asins_by_category


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
    timeout=12 * 60 * 60,
    cpu=4,
    memory=32768,
)
def reduce_eligible_users_for_bucket(
    bucket: str,
    stats_prefix: str = DEFAULT_STATS_PREFIX,
    output_prefix: str = DEFAULT_ELIGIBLE_USERS_PREFIX,
    min_reviews: int = 30,
    min_text_chars: int = 2000,
    min_verified_share: float = 0.7,
) -> dict[str, Any]:
    """Pass 2a: merge Phase 1 stats for one user bucket and write eligible users."""
    stats_root = VOLUME_MOUNT / stats_prefix / f"bucket={bucket}"
    output_root = VOLUME_MOUNT / output_prefix / f"bucket={bucket}"

    # user_id -> [review_count, first_ts, last_ts, text_chars, text_reviews,
    #             verified_count, rating_sum, rating_count, categories_set]
    merged: dict[str, list[Any]] = {}
    category_files = sorted(stats_root.glob("category=*/user_stats.parquet"))
    for parquet_path in category_files:
        for row in read_parquet_rows(parquet_path):
            user_id = row.get("user_id")
            if not user_id:
                continue
            category = row.get("category")
            stats = merged.get(user_id)
            if stats is None:
                stats = [0, None, None, 0, 0, 0, 0.0, 0, set()]
                merged[user_id] = stats
            review_count = int(row.get("review_count") or 0)
            first_ts = row.get("first_timestamp")
            last_ts = row.get("last_timestamp")
            stats[0] += review_count
            if first_ts is not None:
                stats[1] = first_ts if stats[1] is None else min(stats[1], first_ts)
            if last_ts is not None:
                stats[2] = last_ts if stats[2] is None else max(stats[2], last_ts)
            stats[3] += int(row.get("text_chars") or 0)
            stats[4] += int(row.get("text_reviews") or 0)
            stats[5] += int(row.get("verified_count") or 0)
            stats[6] += float(row.get("rating_sum") or 0.0)
            stats[7] += int(row.get("rating_count") or 0)
            if category:
                stats[8].add(category)

    eligible_rows = []
    for user_id, stats in merged.items():
        review_count = stats[0]
        if review_count < min_reviews:
            continue
        verified_share = stats[5] / review_count if review_count else 0.0
        if verified_share < min_verified_share:
            continue
        if stats[3] < min_text_chars:
            continue
        rating_count = stats[7]
        eligible_rows.append(
            {
                "user_id": user_id,
                "user_bucket": bucket,
                "review_count": review_count,
                "category_count": len(stats[8]),
                "categories": sorted(stats[8]),
                "first_timestamp": stats[1],
                "last_timestamp": stats[2],
                "first_date": timestamp_to_date(stats[1]),
                "last_date": timestamp_to_date(stats[2]),
                "text_chars": stats[3],
                "text_reviews": stats[4],
                "verified_count": stats[5],
                "verified_share": verified_share,
                "rating_sum": stats[6],
                "rating_count": rating_count,
                "average_rating": stats[6] / rating_count if rating_count else None,
            }
        )

    output_root.mkdir(parents=True, exist_ok=True)
    parquet_path = output_root / "eligible_users.parquet"
    if eligible_rows:
        write_parquet(eligible_rows, parquet_path)
    elif parquet_path.exists():
        parquet_path.unlink()

    summary = {
        "bucket": bucket,
        "stats_prefix": stats_prefix,
        "output_prefix": output_prefix,
        "category_files": len(category_files),
        "users_seen": len(merged),
        "eligible_users": len(eligible_rows),
        "min_reviews": min_reviews,
        "min_text_chars": min_text_chars,
        "min_verified_share": min_verified_share,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = VOLUME_MOUNT / output_prefix / "_summaries" / f"bucket={bucket}.json"
    write_json(summary_path, summary)
    volume.commit()
    print(f"[modal_amazon_eligible] {bucket}: {json.dumps(summary)}", flush=True)
    return summary


@app.function(
    volumes={str(VOLUME_MOUNT): volume},
    timeout=60 * 60,
    cpu=2,
    memory=8192,
)
def filter_eligible_users_for_bucket(
    bucket: str,
    source_prefix: str = DEFAULT_ELIGIBLE_USERS_PREFIX,
    output_prefix: str = DEFAULT_DERIVED_ELIGIBLE_USERS_PREFIX,
    min_reviews: int = 30,
    min_text_chars: int = 3000,
    min_verified_share: float = 0.7,
) -> dict[str, Any]:
    """Filter an existing eligible-user bucket into a stricter derived pool."""
    if output_prefix == source_prefix:
        raise ValueError("output_prefix must differ from source_prefix for derived filtering")
    source_path = VOLUME_MOUNT / source_prefix / f"bucket={bucket}" / "eligible_users.parquet"
    output_root = VOLUME_MOUNT / output_prefix / f"bucket={bucket}"
    output_path = output_root / "eligible_users.parquet"

    rows_seen = 0
    rows_kept = 0
    eligible_rows = []
    if source_path.exists():
        for row in read_parquet_rows(source_path):
            rows_seen += 1
            if int(row.get("review_count") or 0) < min_reviews:
                continue
            if float(row.get("verified_share") or 0.0) < min_verified_share:
                continue
            if int(row.get("text_chars") or 0) < min_text_chars:
                continue
            eligible_rows.append(row)
            rows_kept += 1

    output_root.mkdir(parents=True, exist_ok=True)
    if eligible_rows:
        write_parquet(eligible_rows, output_path)
    elif output_path.exists():
        output_path.unlink()

    summary = {
        "bucket": bucket,
        "source_prefix": source_prefix,
        "output_prefix": output_prefix,
        "source_exists": source_path.exists(),
        "rows_seen": rows_seen,
        "eligible_users": rows_kept,
        "min_reviews": min_reviews,
        "min_text_chars": min_text_chars,
        "min_verified_share": min_verified_share,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = VOLUME_MOUNT / output_prefix / "_summaries" / f"bucket={bucket}.json"
    write_json(summary_path, summary)
    volume.commit()
    print(f"[modal_amazon_filter_eligible] {bucket}: {json.dumps(summary)}", flush=True)
    return summary


@app.function(
    volumes={str(VOLUME_MOUNT): volume},
    timeout=12 * 60 * 60,
    cpu=4,
    memory=16384,
)
def filter_user_index_bucket_by_eligible(
    bucket: str,
    source_review_prefix: str = DEFAULT_ELIGIBLE_REVIEW_PREFIX,
    eligible_prefix: str = DEFAULT_DERIVED_ELIGIBLE_USERS_PREFIX,
    output_prefix: str = DEFAULT_DERIVED_REVIEW_PREFIX,
    bucket_flush_rows: int = 50_000,
) -> dict[str, Any]:
    """Filter an existing user-bucketed review index to a derived eligible-user pool."""
    if output_prefix == source_review_prefix:
        raise ValueError("output_prefix must differ from source_review_prefix for derived filtering")
    eligible_path = VOLUME_MOUNT / eligible_prefix / f"bucket={bucket}" / "eligible_users.parquet"
    source_root = VOLUME_MOUNT / source_review_prefix / f"bucket={bucket}"
    output_root = VOLUME_MOUNT / output_prefix / f"bucket={bucket}"
    if output_root.exists():
        shutil.rmtree(output_root)

    eligible_user_ids: set[str] = set()
    if eligible_path.exists():
        for row in read_parquet_rows(eligible_path):
            user_id = row.get("user_id")
            if user_id:
                eligible_user_ids.add(str(user_id))

    scanned_rows = 0
    kept_rows = 0
    source_files = sorted(source_root.glob("category=*/part-*.parquet"))
    shard_counts: dict[str, int] = {}
    buffers: dict[str, list[dict[str, Any]]] = {}

    for parquet_path in source_files:
        category = parquet_path.parent.name.removeprefix("category=")
        category_buffer = buffers.setdefault(category, [])
        for row in read_parquet_rows(parquet_path):
            scanned_rows += 1
            user_id = row.get("user_id")
            if not user_id or str(user_id) not in eligible_user_ids:
                continue
            category_buffer.append(row)
            kept_rows += 1
            if len(category_buffer) >= bucket_flush_rows:
                shard_index = shard_counts.get(category, 0)
                out_path = output_root / f"category={category}" / f"part-{shard_index:06d}.parquet"
                write_parquet(category_buffer, out_path)
                shard_counts[category] = shard_index + 1
                buffers[category] = []
                category_buffer = buffers[category]

    for category, category_buffer in list(buffers.items()):
        if not category_buffer:
            continue
        shard_index = shard_counts.get(category, 0)
        out_path = output_root / f"category={category}" / f"part-{shard_index:06d}.parquet"
        write_parquet(category_buffer, out_path)
        shard_counts[category] = shard_index + 1

    summary = {
        "bucket": bucket,
        "source_review_prefix": source_review_prefix,
        "eligible_prefix": eligible_prefix,
        "output_prefix": output_prefix,
        "eligible_users": len(eligible_user_ids),
        "source_files": len(source_files),
        "scanned_rows": scanned_rows,
        "kept_rows": kept_rows,
        "category_count": len(shard_counts),
        "shard_count": sum(shard_counts.values()),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = VOLUME_MOUNT / output_prefix / "_summaries" / f"bucket={bucket}.json"
    write_json(summary_path, summary)
    volume.commit()
    print(f"[modal_amazon_filter_index] {bucket}: {json.dumps(summary)}", flush=True)
    return summary


@app.function(
    volumes={str(VOLUME_MOUNT): volume},
    timeout=6 * 60 * 60,
    cpu=4,
    memory=32768,
)
def export_user_histories_for_bucket(
    bucket: str,
    user_ids: list[str],
    review_prefix: str = DEFAULT_ELIGIBLE_REVIEW_PREFIX,
    metadata_prefix: str = DEFAULT_METADATA_PREFIX,
    include_metadata: bool = False,
    filter_fulfillment_reviews: bool = True,
) -> dict[str, Any]:
    """Read one user bucket from the Modal review index and return selected histories."""
    selected_user_ids = set(user_ids)
    review_root = VOLUME_MOUNT / review_prefix / f"bucket={bucket}"
    histories: dict[str, list[dict[str, Any]]] = {user_id: [] for user_id in selected_user_ids}
    scanned_rows = 0
    kept_rows = 0
    selected_rows = 0
    removed_rows = 0
    removed_by_category: dict[str, int] = {}
    removed_by_user: dict[str, int] = {}
    removed_by_user_category: dict[str, dict[str, int]] = {}
    removed_by_pattern: dict[str, int] = {}
    parquet_files = sorted(review_root.glob("category=*/part-*.parquet"))
    for parquet_path in parquet_files:
        for row in read_parquet_rows(parquet_path):
            scanned_rows += 1
            user_id = row.get("user_id")
            if user_id not in selected_user_ids:
                continue
            selected_rows += 1
            if filter_fulfillment_reviews:
                pattern = fulfillment_or_template_review_match(row)
                if pattern:
                    category = str(row.get("category") or "Unknown")
                    user_id = str(user_id)
                    removed_rows += 1
                    removed_by_category[category] = removed_by_category.get(category, 0) + 1
                    removed_by_user[user_id] = removed_by_user.get(user_id, 0) + 1
                    user_categories = removed_by_user_category.setdefault(user_id, {})
                    user_categories[category] = user_categories.get(category, 0) + 1
                    removed_by_pattern[pattern] = removed_by_pattern.get(pattern, 0) + 1
                    continue
            histories.setdefault(str(user_id), []).append(row)
            kept_rows += 1

    if include_metadata:
        parent_asins_by_category: dict[str, set[str]] = {}
        for reviews in histories.values():
            for review in reviews:
                parent_asin = review.get("parent_asin")
                category = review.get("category")
                if parent_asin and category:
                    parent_asins_by_category.setdefault(str(category), set()).add(str(parent_asin))
        metadata = metadata_for_parent_asins(parent_asins_by_category, metadata_prefix)
        for reviews in histories.values():
            attach_inline_product_metadata(reviews, metadata)

    histories = {
        user_id: sorted(reviews, key=lambda row: row.get("timestamp") or 0)
        for user_id, reviews in histories.items()
        if reviews
    }
    summary = {
        "bucket": bucket,
        "review_prefix": review_prefix,
        "metadata_prefix": metadata_prefix if include_metadata else "",
        "include_metadata": include_metadata,
        "filter_fulfillment_reviews": filter_fulfillment_reviews,
        "requested_users": len(selected_user_ids),
        "users_found": len(histories),
        "parquet_files": len(parquet_files),
        "scanned_rows": scanned_rows,
        "selected_rows": selected_rows,
        "kept_rows": kept_rows,
        "removed_rows": removed_rows,
        "removed_by_category": dict(sorted(removed_by_category.items())),
        "removed_by_user": dict(sorted(removed_by_user.items())),
        "removed_by_user_category": {
            user_id: dict(sorted(category_counts.items()))
            for user_id, category_counts in sorted(removed_by_user_category.items())
        },
        "removed_by_pattern": dict(sorted(removed_by_pattern.items())),
    }
    print(f"[modal_amazon_export] {bucket}: {json.dumps(summary)}", flush=True)
    return {"summary": summary, "histories": histories}


@app.function(
    volumes={str(VOLUME_MOUNT): volume},
    timeout=60 * 60,
    cpu=2,
    memory=8192,
)
def load_candidate_users_for_bucket(
    bucket: str,
    eligible_prefix: str = DEFAULT_ELIGIBLE_USERS_PREFIX,
    top_n_per_bucket: int = 100,
    min_category_count: int = 1,
    min_history_days: int = 0,
) -> dict[str, Any]:
    """Read one eligible-user bucket and return its strongest candidate rows."""
    parquet_path = VOLUME_MOUNT / eligible_prefix / f"bucket={bucket}" / "eligible_users.parquet"
    if not parquet_path.exists():
        return {
            "summary": {
                "bucket": bucket,
                "eligible_prefix": eligible_prefix,
                "rows_seen": 0,
                "rows_kept": 0,
                "returned": 0,
            },
            "candidates": [],
        }

    candidates = []
    rows_seen = 0
    for row in read_parquet_rows(parquet_path):
        rows_seen += 1
        if int(row.get("category_count") or 0) < min_category_count:
            continue
        first_ts = row.get("first_timestamp")
        last_ts = row.get("last_timestamp")
        history_days = 0.0
        if first_ts is not None and last_ts is not None:
            history_days = max(0.0, (int(last_ts) - int(first_ts)) / 86_400_000)
        if history_days < min_history_days:
            continue
        row["history_days"] = round(history_days, 2)
        row["history_years"] = round(history_days / 365.25, 2)
        candidates.append(row)

    candidates.sort(
        key=lambda row: (
            -int(row.get("review_count") or 0),
            -int(row.get("text_chars") or 0),
            -int(row.get("category_count") or 0),
            str(row.get("user_id") or ""),
        )
    )
    if top_n_per_bucket:
        candidates = candidates[:top_n_per_bucket]
    summary = {
        "bucket": bucket,
        "eligible_prefix": eligible_prefix,
        "rows_seen": rows_seen,
        "rows_kept": len(candidates),
        "returned": len(candidates),
        "min_category_count": min_category_count,
        "min_history_days": min_history_days,
    }
    print(f"[modal_amazon_candidates] {bucket}: {json.dumps(summary)}", flush=True)
    return {"summary": summary, "candidates": candidates}


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
    eligible_prefix: str = "",
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
    eligible_user_ids: set[str] | None = None
    if eligible_prefix:
        print(f"[modal_amazon_index] Loading eligible users from {eligible_prefix}", flush=True)
        eligible_user_ids = read_eligible_user_ids(eligible_prefix)
        print(
            f"[modal_amazon_index] Loaded {len(eligible_user_ids):,} eligible users",
            flush=True,
        )

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
        if eligible_user_ids is not None and normalized["user_id"] not in eligible_user_ids:
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
        "eligible_prefix": eligible_prefix,
        "eligible_filter_users": len(eligible_user_ids) if eligible_user_ids is not None else None,
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


@app.function(
    volumes={str(VOLUME_MOUNT): volume},
    timeout=24 * 60 * 60,
    cpu=4,
    memory=32768,
)
def build_category_metadata_index(
    category: str,
    output_prefix: str = "amazon_reviews_2023_metadata_by_parent_asin_bucket_v2",
    bucket_flush_rows: int = 50_000,
    progress_every: int = 250_000,
    max_rows: int = 0,
) -> dict[str, Any]:
    """Build parent_asin-bucketed item metadata Parquet shards for one category."""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown Amazon Reviews 2023 category: {category}")

    url = metadata_url(category)
    output_root = VOLUME_MOUNT / output_prefix

    print(f"[modal_amazon_meta] Streaming {url}", flush=True)

    buffers: dict[str, list[dict[str, Any]]] = {}
    shard_counts: dict[str, int] = {}
    seen_parent_asins: set[str] = set()
    scanned = 0
    kept = 0
    for row in open_remote_gzip_jsonl(url):
        scanned += 1
        if max_rows and scanned > max_rows:
            break
        if progress_every and scanned % progress_every == 0:
            print(
                f"[modal_amazon_meta] {category}: scanned {scanned:,}; kept {kept:,}",
                flush=True,
            )

        normalized = normalize_metadata(dict(row), category)
        if normalized is None:
            continue
        parent_asin = normalized["parent_asin"]
        if parent_asin in seen_parent_asins:
            continue
        seen_parent_asins.add(parent_asin)

        bucket = normalized["metadata_bucket"]
        bucket_rows = buffers.setdefault(bucket, [])
        bucket_rows.append(normalized)
        kept += 1
        if len(bucket_rows) >= bucket_flush_rows:
            shard_index = shard_counts.get(bucket, 0)
            out_path = (
                output_root
                / f"bucket={bucket}"
                / f"source_category={category}"
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
            / f"source_category={category}"
            / f"part-{shard_index:06d}.parquet"
        )
        write_parquet(bucket_rows, out_path)
        shard_counts[bucket] = shard_index + 1

    summary = {
        "dataset": DATASET_NAME,
        "source_url": url,
        "category": category,
        "scanned_rows": scanned,
        "kept_rows": kept,
        "unique_parent_asins": len(seen_parent_asins),
        "bucket_count": len(shard_counts),
        "shard_count": sum(shard_counts.values()),
        "output_prefix": output_prefix,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_root / "_summaries" / f"{category}.json"
    write_json(summary_path, summary)
    volume.commit()
    print(f"[modal_amazon_meta] {category}: {json.dumps(summary)}", flush=True)
    return summary


@app.local_entrypoint()
def build_user_stats(
    categories: str = "all",
    start_year: int = 2018,
    end_year: int = 2023,
    output_prefix: str = DEFAULT_STATS_PREFIX,
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
def build_eligible_users(
    stats_prefix: str = DEFAULT_STATS_PREFIX,
    output_prefix: str = DEFAULT_ELIGIBLE_USERS_PREFIX,
    min_reviews: int = 30,
    min_text_chars: int = 2000,
    min_verified_share: float = 0.7,
    wait: bool = True,
) -> None:
    """Reduce Pass 1 category stats into globally eligible user buckets."""
    buckets = bucket_values()
    print(
        f"Launching {len(buckets)} eligible-user reducer jobs from {stats_prefix} "
        f"to {output_prefix}"
    )
    calls = [
        reduce_eligible_users_for_bucket.spawn(
            bucket,
            stats_prefix=stats_prefix,
            output_prefix=output_prefix,
            min_reviews=min_reviews,
            min_text_chars=min_text_chars,
            min_verified_share=min_verified_share,
        )
        for bucket in buckets
    ]
    for bucket, call in zip(buckets, calls, strict=True):
        print(f"bucket={bucket}: {call.object_id}")
    if wait:
        print("Waiting for eligible-user reducer jobs to finish...")
        total_seen = 0
        total_eligible = 0
        for bucket, call in zip(buckets, calls, strict=True):
            try:
                summary = call.get()
            except Exception as err:
                print(f"bucket={bucket}: failed: {err}")
                raise
            total_seen += int(summary.get("users_seen") or 0)
            total_eligible += int(summary.get("eligible_users") or 0)
            print(f"bucket={bucket}: completed {summary}")
        print(
            f"Completed {len(buckets)} reducer jobs. "
            f"Users seen: {total_seen:,}; eligible users: {total_eligible:,}"
        )


@app.local_entrypoint()
def derive_eligible_users(
    source_prefix: str = DEFAULT_ELIGIBLE_USERS_PREFIX,
    output_prefix: str = DEFAULT_DERIVED_ELIGIBLE_USERS_PREFIX,
    min_reviews: int = 30,
    min_text_chars: int = 3000,
    min_verified_share: float = 0.7,
    wait: bool = True,
) -> None:
    """Filter an existing eligible-user pool into a stricter derived pool."""
    buckets = bucket_values()
    print(
        f"Filtering {len(buckets)} eligible-user buckets from {source_prefix} "
        f"to {output_prefix}: min_reviews={min_reviews}, "
        f"min_verified_share={min_verified_share}, min_text_chars={min_text_chars}"
    )
    calls = [
        filter_eligible_users_for_bucket.spawn(
            bucket,
            source_prefix=source_prefix,
            output_prefix=output_prefix,
            min_reviews=min_reviews,
            min_text_chars=min_text_chars,
            min_verified_share=min_verified_share,
        )
        for bucket in buckets
    ]
    for bucket, call in zip(buckets, calls, strict=True):
        print(f"bucket={bucket}: {call.object_id}")
    if not wait:
        return

    total_seen = 0
    total_eligible = 0
    for bucket, call in zip(buckets, calls, strict=True):
        try:
            summary = call.get()
        except Exception as err:
            print(f"bucket={bucket}: failed: {err}")
            raise
        total_seen += int(summary.get("rows_seen") or 0)
        total_eligible += int(summary.get("eligible_users") or 0)
        print(f"bucket={bucket}: completed {summary}")
    print(
        f"Completed {len(buckets)} derived eligible-user jobs. "
        f"Rows seen: {total_seen:,}; eligible users: {total_eligible:,}"
    )


@app.local_entrypoint()
def derive_user_buckets(
    source_review_prefix: str = DEFAULT_ELIGIBLE_REVIEW_PREFIX,
    eligible_prefix: str = DEFAULT_DERIVED_ELIGIBLE_USERS_PREFIX,
    output_prefix: str = DEFAULT_DERIVED_REVIEW_PREFIX,
    bucket_flush_rows: int = 50_000,
    wait: bool = True,
) -> None:
    """Filter an existing user-bucketed review index to a derived eligible-user pool."""
    buckets = bucket_values()
    print(
        f"Filtering {len(buckets)} review-index buckets from {source_review_prefix} "
        f"to {output_prefix} using eligible users from {eligible_prefix}"
    )
    calls = [
        filter_user_index_bucket_by_eligible.spawn(
            bucket,
            source_review_prefix=source_review_prefix,
            eligible_prefix=eligible_prefix,
            output_prefix=output_prefix,
            bucket_flush_rows=bucket_flush_rows,
        )
        for bucket in buckets
    ]
    for bucket, call in zip(buckets, calls, strict=True):
        print(f"bucket={bucket}: {call.object_id}")
    if not wait:
        return

    total_scanned = 0
    total_kept = 0
    total_eligible = 0
    for bucket, call in zip(buckets, calls, strict=True):
        try:
            summary = call.get()
        except Exception as err:
            print(f"bucket={bucket}: failed: {err}")
            raise
        total_scanned += int(summary.get("scanned_rows") or 0)
        total_kept += int(summary.get("kept_rows") or 0)
        total_eligible += int(summary.get("eligible_users") or 0)
        print(f"bucket={bucket}: completed {summary}")
    print(
        f"Completed {len(buckets)} derived review-index jobs. "
        f"Eligible users: {total_eligible:,}; scanned rows: {total_scanned:,}; "
        f"kept rows: {total_kept:,}"
    )


@app.local_entrypoint()
def build_categories(
    categories: str = "Books,Kindle_Store,Movies_and_TV,Electronics,Office_Products,Home_and_Kitchen,Clothing_Shoes_and_Jewelry",
    start_year: int = 2018,
    end_year: int = 2023,
    output_prefix: str = DEFAULT_ELIGIBLE_REVIEW_PREFIX,
    eligible_prefix: str = "",
    bucket_flush_rows: int = 50_000,
    max_rows: int = 0,
    wait: bool = True,
) -> None:
    """Launch one Modal review-index job per category."""
    selected = parse_categories(categories)
    print(f"Launching {len(selected)} category jobs: {', '.join(selected)}")
    if eligible_prefix:
        print(f"Filtering to eligible users from {eligible_prefix}")
    calls = [
        build_category_user_index.spawn(
            category,
            start_year=start_year,
            end_year=end_year,
            output_prefix=output_prefix,
            eligible_prefix=eligible_prefix,
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
def build_metadata(
    categories: str = "all",
    output_prefix: str = DEFAULT_METADATA_PREFIX,
    bucket_flush_rows: int = 50_000,
    max_rows: int = 0,
    wait: bool = True,
) -> None:
    """Launch one Modal metadata-index job per category."""
    selected = parse_categories(categories)
    print(f"Launching {len(selected)} metadata jobs: {', '.join(selected)}")
    calls = [
        build_category_metadata_index.spawn(
            category,
            output_prefix=output_prefix,
            bucket_flush_rows=bucket_flush_rows,
            max_rows=max_rows,
        )
        for category in selected
    ]
    for category, call in zip(selected, calls, strict=True):
        print(f"{category}: {call.object_id}")
    if wait:
        print("Waiting for metadata jobs to finish...")
        summaries = []
        total_rows = 0
        for category, call in zip(selected, calls, strict=True):
            try:
                summary = call.get()
            except Exception as err:
                print(f"{category}: failed: {err}")
                raise
            summaries.append(summary)
            total_rows += int(summary.get("kept_rows") or 0)
            print(f"{category}: completed {summary}")
        print(
            f"Completed {len(summaries)} metadata jobs. "
            f"Metadata rows written: {total_rows:,}"
        )


@app.local_entrypoint()
def export_candidate_users(
    output: str = "raw/amazon_reviews_2023/candidates/eligible_candidates_top100.jsonl",
    eligible_prefix: str = DEFAULT_ELIGIBLE_USERS_PREFIX,
    top_n: int = 100,
    top_n_per_bucket: int = 100,
    min_category_count: int = 1,
    min_history_days: int = 0,
    wait: bool = True,
) -> None:
    """Export ranked candidate users from the Modal eligible-user pool."""
    buckets = bucket_values()
    print(
        f"Exporting candidate users from {eligible_prefix}: "
        f"{len(buckets)} buckets, top {top_n_per_bucket} per bucket"
    )
    calls = [
        load_candidate_users_for_bucket.spawn(
            bucket,
            eligible_prefix=eligible_prefix,
            top_n_per_bucket=top_n_per_bucket,
            min_category_count=min_category_count,
            min_history_days=min_history_days,
        )
        for bucket in buckets
    ]
    for bucket, call in zip(buckets, calls, strict=True):
        print(f"bucket={bucket}: {call.object_id}")
    if not wait:
        return

    candidates = []
    rows_seen = 0
    for bucket, call in zip(buckets, calls, strict=True):
        try:
            result = call.get()
        except Exception as err:
            print(f"bucket={bucket}: failed: {err}")
            raise
        summary = result["summary"]
        rows_seen += int(summary.get("rows_seen") or 0)
        candidates.extend(result["candidates"])
        print(f"bucket={bucket}: completed {summary}")

    candidates.sort(
        key=lambda row: (
            -int(row.get("review_count") or 0),
            -int(row.get("text_chars") or 0),
            -int(row.get("category_count") or 0),
            str(row.get("user_id") or ""),
        )
    )
    if top_n:
        candidates = candidates[:top_n]

    output_path = Path(output)
    written = write_local_jsonl(output_path, iter(candidates))
    print(
        f"Wrote {written:,} candidates to {output_path}. "
        f"Eligible rows scanned: {rows_seen:,}."
    )


def load_candidate_users_for_bucket_from_hf(
    bucket: str,
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    eligible_prefix: str = DEFAULT_ELIGIBLE_USERS_PREFIX,
    revision: str = "main",
    top_n_per_bucket: int = 100,
    min_category_count: int = 1,
    min_history_days: int = 0,
) -> dict[str, Any]:
    """Read one eligible-user bucket from Hugging Face and return candidate rows."""
    path_in_repo = hf_path(
        path_prefix,
        eligible_prefix,
        f"bucket={bucket}",
        "eligible_users.parquet",
    )
    candidates = []
    rows_seen = 0
    try:
        rows = read_hf_parquet_rows(repo_id, path_in_repo, revision=revision)
    except Exception as err:
        return {
            "summary": {
                "bucket": bucket,
                "repo_id": repo_id,
                "path_in_repo": path_in_repo,
                "eligible_prefix": eligible_prefix,
                "rows_seen": 0,
                "rows_kept": 0,
                "returned": 0,
                "error": str(err),
            },
            "candidates": [],
        }
    for row in rows:
        rows_seen += 1
        if int(row.get("category_count") or 0) < min_category_count:
            continue
        first_ts = row.get("first_timestamp")
        last_ts = row.get("last_timestamp")
        history_days = 0.0
        if first_ts is not None and last_ts is not None:
            history_days = max(0.0, (int(last_ts) - int(first_ts)) / 86_400_000)
        if history_days < min_history_days:
            continue
        row["history_days"] = round(history_days, 2)
        row["history_years"] = round(history_days / 365.25, 2)
        candidates.append(row)

    candidates.sort(
        key=lambda row: (
            -int(row.get("review_count") or 0),
            -int(row.get("text_chars") or 0),
            -int(row.get("category_count") or 0),
            str(row.get("user_id") or ""),
        )
    )
    if top_n_per_bucket:
        candidates = candidates[:top_n_per_bucket]
    return {
        "summary": {
            "bucket": bucket,
            "repo_id": repo_id,
            "path_in_repo": path_in_repo,
            "eligible_prefix": eligible_prefix,
            "rows_seen": rows_seen,
            "rows_kept": len(candidates),
            "returned": len(candidates),
            "min_category_count": min_category_count,
            "min_history_days": min_history_days,
        },
        "candidates": candidates,
    }


@app.function(
    timeout=60 * 60,
    cpu=2,
    memory=8192,
)
def load_candidate_users_for_bucket_from_hf_remote(
    bucket: str,
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    eligible_prefix: str = DEFAULT_ELIGIBLE_USERS_PREFIX,
    revision: str = "main",
    top_n_per_bucket: int = 100,
    min_category_count: int = 1,
    min_history_days: int = 0,
) -> dict[str, Any]:
    """Modal worker: read one HF eligible-user bucket and return candidate rows."""
    return load_candidate_users_for_bucket_from_hf(
        bucket=bucket,
        repo_id=repo_id,
        path_prefix=path_prefix,
        eligible_prefix=eligible_prefix,
        revision=revision,
        top_n_per_bucket=top_n_per_bucket,
        min_category_count=min_category_count,
        min_history_days=min_history_days,
    )


@app.local_entrypoint()
def export_candidate_users_from_hf(
    output: str = "raw/amazon_reviews_2023/candidates/eligible_candidates_top100.jsonl",
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    eligible_prefix: str = DEFAULT_ELIGIBLE_USERS_PREFIX,
    revision: str = "main",
    buckets: str = "all",
    top_n: int = 100,
    top_n_per_bucket: int = 100,
    min_category_count: int = 1,
    min_history_days: int = 0,
) -> None:
    """Export ranked candidate users from Hugging Face artifact parquet files."""
    selected_buckets = parse_buckets(buckets)
    print(
        f"Exporting candidate users from hf://datasets/{repo_id}/"
        f"{hf_path(path_prefix, eligible_prefix)}: "
        f"{len(selected_buckets)} buckets, top {top_n_per_bucket} per bucket"
    )
    candidates = []
    rows_seen = 0
    calls = [
        load_candidate_users_for_bucket_from_hf_remote.spawn(
            bucket,
            repo_id=repo_id,
            path_prefix=path_prefix,
            eligible_prefix=eligible_prefix,
            revision=revision,
            top_n_per_bucket=top_n_per_bucket,
            min_category_count=min_category_count,
            min_history_days=min_history_days,
        )
        for bucket in selected_buckets
    ]
    for bucket, call in zip(selected_buckets, calls, strict=True):
        print(f"bucket={bucket}: {call.object_id}")
    for bucket, call in zip(selected_buckets, calls, strict=True):
        try:
            result = call.get()
        except Exception as err:
            print(f"bucket={bucket}: failed: {err}")
            raise
        summary = result["summary"]
        rows_seen += int(summary.get("rows_seen") or 0)
        candidates.extend(result["candidates"])
        print(f"bucket={bucket}: completed {summary}")

    candidates.sort(
        key=lambda row: (
            -int(row.get("review_count") or 0),
            -int(row.get("text_chars") or 0),
            -int(row.get("category_count") or 0),
            str(row.get("user_id") or ""),
        )
    )
    if top_n:
        candidates = candidates[:top_n]

    output_path = Path(output)
    written = write_local_jsonl(output_path, iter(candidates))
    print(
        f"Wrote {written:,} candidates to {output_path}. "
        f"Eligible rows scanned: {rows_seen:,}."
    )


@app.local_entrypoint()
def export_user_histories(
    candidate_users: str = "samples/amazon_reviews_2023/candidate_users_top100.jsonl",
    output: str = str(DEFAULT_LOCAL_HISTORY_OUTPUT),
    top_n: int = 100,
    review_prefix: str = DEFAULT_ELIGIBLE_REVIEW_PREFIX,
    metadata_prefix: str = DEFAULT_METADATA_PREFIX,
    include_metadata: bool = False,
    filter_fulfillment_reviews: bool = True,
    temporal_train_fraction: float = 0.8,
    filter_summary_output: str = "",
    wait: bool = True,
) -> None:
    """Export selected users from the Modal user-index into local inference JSONL."""
    candidate_path = Path(candidate_users)
    output_path = Path(output)
    candidate_rows = list(iter_local_jsonl_or_gz(candidate_path))
    if top_n:
        candidate_rows = candidate_rows[:top_n]
    candidate_by_user = {
        str(row["user_id"]): row
        for row in candidate_rows
        if row.get("user_id")
    }
    users_by_bucket: dict[str, list[str]] = {}
    for user_id in candidate_by_user:
        users_by_bucket.setdefault(user_bucket(user_id), []).append(user_id)

    print(
        f"Exporting {len(candidate_by_user):,} users from {len(users_by_bucket):,} "
        f"user buckets in {review_prefix}"
    )
    if include_metadata:
        print(f"Joining product metadata from {metadata_prefix}")

    calls = [
        export_user_histories_for_bucket.spawn(
            bucket,
            user_ids,
            review_prefix=review_prefix,
            metadata_prefix=metadata_prefix,
            include_metadata=include_metadata,
            filter_fulfillment_reviews=filter_fulfillment_reviews,
        )
        for bucket, user_ids in sorted(users_by_bucket.items())
    ]
    for bucket, call in zip(sorted(users_by_bucket), calls, strict=True):
        print(f"bucket={bucket}: {call.object_id}")
    if not wait:
        return

    histories_by_user: dict[str, list[dict[str, Any]]] = {}
    total_scanned = 0
    total_selected = 0
    total_kept = 0
    total_removed = 0
    removed_by_category: dict[str, int] = {}
    removed_by_user: dict[str, int] = {}
    removed_by_user_category: dict[str, dict[str, int]] = {}
    removed_by_pattern: dict[str, int] = {}
    category_stats_all_users: dict[str, dict[str, Any]] = {}
    category_stats_by_user: dict[str, dict[str, dict[str, Any]]] = {}
    validation_category_stats_all_users: dict[str, dict[str, Any]] = {}
    validation_category_stats_by_user: dict[str, dict[str, dict[str, Any]]] = {}
    total_construction_reviews = 0
    total_validation_reviews = 0
    total_construction_text_reviews = 0
    total_validation_text_reviews = 0
    total_construction_ratings = 0
    total_validation_ratings = 0
    total_construction_rating_only = 0
    total_validation_rating_only = 0

    def add_counts(target: dict[str, int], source: dict[str, Any]) -> None:
        for key, value in source.items():
            target[str(key)] = target.get(str(key), 0) + int(value or 0)

    for bucket, call in zip(sorted(users_by_bucket), calls, strict=True):
        try:
            result = call.get()
        except Exception as err:
            print(f"bucket={bucket}: failed: {err}")
            raise
        summary = result["summary"]
        total_scanned += int(summary.get("scanned_rows") or 0)
        total_selected += int(summary.get("selected_rows") or 0)
        total_kept += int(summary.get("kept_rows") or 0)
        total_removed += int(summary.get("removed_rows") or 0)
        add_counts(removed_by_category, summary.get("removed_by_category", {}))
        add_counts(removed_by_user, summary.get("removed_by_user", {}))
        add_counts(removed_by_pattern, summary.get("removed_by_pattern", {}))
        for user_id, category_counts in summary.get("removed_by_user_category", {}).items():
            user_target = removed_by_user_category.setdefault(str(user_id), {})
            add_counts(user_target, category_counts)
        histories_by_user.update(result["histories"])
        print(f"bucket={bucket}: completed {summary}")

    def rows() -> Iterator[dict[str, Any]]:
        nonlocal total_construction_reviews, total_validation_reviews
        nonlocal total_construction_text_reviews, total_validation_text_reviews
        nonlocal total_construction_ratings, total_validation_ratings
        nonlocal total_construction_rating_only, total_validation_rating_only
        for user_id, reviews in sorted(
            histories_by_user.items(),
            key=lambda item: (-len(item[1]), str(item[0])),
        ):
            construction_reviews, validation_reviews, split_summary = temporal_train_validation_split(
                reviews,
                temporal_train_fraction,
            )
            total_construction_reviews += len(construction_reviews)
            total_validation_reviews += len(validation_reviews)
            total_construction_text_reviews += int(split_summary["construction_text_review_count"])
            total_validation_text_reviews += int(split_summary["validation_text_review_count"])
            total_construction_ratings += int(split_summary["construction_rating_count"])
            total_validation_ratings += int(split_summary["validation_rating_count"])
            total_construction_rating_only += int(split_summary["construction_rating_only_count"])
            total_validation_rating_only += int(split_summary["validation_rating_only_count"])
            categories = sorted(
                {
                    str(review.get("category"))
                    for review in construction_reviews
                    if review.get("category")
                }
            )
            validation_categories = sorted(
                {
                    str(review.get("category"))
                    for review in validation_reviews
                    if review.get("category")
                }
            )
            user_category_stats = category_review_stats(construction_reviews)
            user_validation_category_stats = category_review_stats(validation_reviews)
            category_stats_by_user[user_id] = user_category_stats
            validation_category_stats_by_user[user_id] = user_validation_category_stats
            merge_category_review_stats(category_stats_all_users, user_category_stats)
            merge_category_review_stats(validation_category_stats_all_users, user_validation_category_stats)
            yield {
                "source": "amazon_reviews_2023",
                "user_id": user_id,
                "review_count": len(construction_reviews),
                "retrieved_review_count": len(reviews),
                "validation_review_count": len(validation_reviews),
                "categories": categories,
                "validation_categories": validation_categories,
                "temporal_split": split_summary,
                "category_review_stats": user_category_stats,
                "validation_category_review_stats": user_validation_category_stats,
                "first_timestamp": construction_reviews[0].get("timestamp") if construction_reviews else None,
                "last_timestamp": construction_reviews[-1].get("timestamp") if construction_reviews else None,
                "validation_first_timestamp": validation_reviews[0].get("timestamp") if validation_reviews else None,
                "validation_last_timestamp": validation_reviews[-1].get("timestamp") if validation_reviews else None,
                "candidate_user_stats": candidate_by_user.get(user_id, {}),
                "review_filter_summary": {
                    "filter_fulfillment_reviews": filter_fulfillment_reviews,
                    "removed_reviews": removed_by_user.get(user_id, 0),
                    "removed_by_category": removed_by_user_category.get(user_id, {}),
                },
                "reviews": construction_reviews,
                "validation_reviews": validation_reviews,
            }

    written = write_local_jsonl(output_path, rows())
    missing = len(candidate_by_user) - written
    aggregate_category_stats = finalize_category_review_stats(category_stats_all_users)
    aggregate_validation_category_stats = finalize_category_review_stats(validation_category_stats_all_users)
    filter_summary = {
        "candidate_users": str(candidate_path),
        "output": str(output_path),
        "review_prefix": review_prefix,
        "metadata_prefix": metadata_prefix if include_metadata else "",
        "include_metadata": include_metadata,
        "filter_fulfillment_reviews": filter_fulfillment_reviews,
        "temporal_split": {
            "method": "per_user_temporal",
            "unit": "review_or_rating_row",
            "train_fraction": temporal_train_fraction,
            "construction_reviews": total_construction_reviews,
            "validation_reviews": total_validation_reviews,
            "construction_text_reviews": total_construction_text_reviews,
            "validation_text_reviews": total_validation_text_reviews,
            "construction_ratings": total_construction_ratings,
            "validation_ratings": total_validation_ratings,
            "construction_rating_only_rows": total_construction_rating_only,
            "validation_rating_only_rows": total_validation_rating_only,
        },
        "requested_users": len(candidate_by_user),
        "written_users": written,
        "missing_users": missing,
        "scanned_indexed_rows": total_scanned,
        "selected_reviews_before_filter": total_selected,
        "kept_reviews": total_kept,
        "removed_reviews": total_removed,
        "category_review_stats": aggregate_category_stats,
        "validation_category_review_stats": aggregate_validation_category_stats,
        "user_category_review_stats": {
            user_id: category_stats
            for user_id, category_stats in sorted(category_stats_by_user.items())
        },
        "user_validation_category_review_stats": {
            user_id: category_stats
            for user_id, category_stats in sorted(validation_category_stats_by_user.items())
        },
        "removed_by_category": dict(sorted(removed_by_category.items())),
        "removed_by_user": dict(sorted(removed_by_user.items())),
        "removed_by_user_category": {
            user_id: dict(sorted(category_counts.items()))
            for user_id, category_counts in sorted(removed_by_user_category.items())
        },
        "removed_by_pattern": dict(sorted(removed_by_pattern.items())),
    }
    summary_path = (
        Path(filter_summary_output)
        if filter_summary_output
        else output_path.with_suffix(output_path.suffix + ".filter_summary.json")
    )
    write_json(summary_path, filter_summary)
    print(
        f"Wrote {written:,} user histories to {output_path}. "
        f"Missing users: {missing:,}. Scanned indexed rows: {total_scanned:,}; "
        f"selected reviews: {total_selected:,}; removed reviews: {total_removed:,}; "
        f"kept reviews: {total_kept:,}; construction reviews: {total_construction_reviews:,}; "
        f"validation reviews: {total_validation_reviews:,}. Filter summary: {summary_path}"
    )


def export_user_histories_for_bucket_from_hf(
    bucket: str,
    user_ids: list[str],
    repo_files: list[str],
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    review_prefix: str = DEFAULT_ELIGIBLE_REVIEW_PREFIX,
    revision: str = "main",
    filter_fulfillment_reviews: bool = True,
) -> dict[str, Any]:
    """Read one user bucket from Hugging Face artifacts and return selected histories."""
    selected_user_ids = set(user_ids)
    review_root = hf_path(path_prefix, review_prefix, f"bucket={bucket}")
    parquet_files = [
        path
        for path in hf_files_under(repo_files, review_root)
        if path.endswith(".parquet") and "/category=" in path
    ]
    histories: dict[str, list[dict[str, Any]]] = {user_id: [] for user_id in selected_user_ids}
    scanned_rows = 0
    kept_rows = 0
    selected_rows = 0
    removed_rows = 0
    removed_by_category: dict[str, int] = {}
    removed_by_user: dict[str, int] = {}
    removed_by_user_category: dict[str, dict[str, int]] = {}
    removed_by_pattern: dict[str, int] = {}
    columns = [
        "source",
        "category",
        "user_id",
        "review_id",
        "user_bucket",
        "parent_asin",
        "asin",
        "timestamp",
        "date",
        "rating",
        "title",
        "text",
        "verified_purchase",
        "helpful_vote",
    ]
    columns_without_review_id = [column for column in columns if column != "review_id"]

    def iter_rows_for_path(parquet_path: str) -> Iterator[dict[str, Any]]:
        try:
            yield from read_hf_parquet_rows(
                repo_id,
                parquet_path,
                revision=revision,
                columns=columns,
            )
        except Exception as err:
            if not missing_optional_review_id_projection_error(err):
                raise
            yield from read_hf_parquet_rows(
                repo_id,
                parquet_path,
                revision=revision,
                columns=columns_without_review_id,
            )

    for parquet_path in parquet_files:
        for row in iter_rows_for_path(parquet_path):
            scanned_rows += 1
            user_id = row.get("user_id")
            if user_id not in selected_user_ids:
                continue
            selected_rows += 1
            if filter_fulfillment_reviews:
                pattern = fulfillment_or_template_review_match(row)
                if pattern:
                    category = str(row.get("category") or "Unknown")
                    user_id = str(user_id)
                    removed_rows += 1
                    removed_by_category[category] = removed_by_category.get(category, 0) + 1
                    removed_by_user[user_id] = removed_by_user.get(user_id, 0) + 1
                    user_categories = removed_by_user_category.setdefault(user_id, {})
                    user_categories[category] = user_categories.get(category, 0) + 1
                    removed_by_pattern[pattern] = removed_by_pattern.get(pattern, 0) + 1
                    continue
            if not row.get("review_id"):
                category = str(row.get("category") or "Unknown")
                row["review_id"] = stable_review_id(
                    row,
                    category,
                    normalize_timestamp(row.get("timestamp")),
                )
            histories.setdefault(str(user_id), []).append(row)
            kept_rows += 1

    histories = {
        user_id: sorted(reviews, key=lambda row: row.get("timestamp") or 0)
        for user_id, reviews in histories.items()
        if reviews
    }
    summary = {
        "bucket": bucket,
        "source": "huggingface",
        "repo_id": repo_id,
        "review_prefix": review_prefix,
        "filter_fulfillment_reviews": filter_fulfillment_reviews,
        "requested_users": len(selected_user_ids),
        "users_found": len(histories),
        "parquet_files": len(parquet_files),
        "scanned_rows": scanned_rows,
        "selected_rows": selected_rows,
        "kept_rows": kept_rows,
        "removed_rows": removed_rows,
        "removed_by_category": dict(sorted(removed_by_category.items())),
        "removed_by_user": dict(sorted(removed_by_user.items())),
        "removed_by_user_category": {
            user_id: dict(sorted(category_counts.items()))
            for user_id, category_counts in sorted(removed_by_user_category.items())
        },
        "removed_by_pattern": dict(sorted(removed_by_pattern.items())),
    }
    print(f"[hf_amazon_export] {bucket}: {json.dumps(summary)}", flush=True)
    return {"summary": summary, "histories": histories}


@app.function(
    timeout=6 * 60 * 60,
    cpu=4,
    memory=32768,
)
def export_user_histories_for_bucket_from_hf_remote(
    bucket: str,
    user_ids: list[str],
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    review_prefix: str = DEFAULT_ELIGIBLE_REVIEW_PREFIX,
    revision: str = "main",
    filter_fulfillment_reviews: bool = True,
) -> dict[str, Any]:
    """Modal worker: read selected histories from Hugging Face user-index artifacts."""
    repo_files = hf_repo_files(repo_id, revision=revision)
    return export_user_histories_for_bucket_from_hf(
        bucket=bucket,
        user_ids=user_ids,
        repo_files=repo_files,
        repo_id=repo_id,
        path_prefix=path_prefix,
        review_prefix=review_prefix,
        revision=revision,
        filter_fulfillment_reviews=filter_fulfillment_reviews,
    )


def write_temporal_user_histories(
    histories_by_user: dict[str, list[dict[str, Any]]],
    candidate_by_user: dict[str, dict[str, Any]],
    candidate_path: Path,
    output_path: Path,
    review_prefix: str,
    metadata_prefix: str,
    include_metadata: bool,
    filter_fulfillment_reviews: bool,
    temporal_train_fraction: float,
    filter_summary_output: str,
    total_scanned: int,
    total_selected: int,
    total_kept: int,
    total_removed: int,
    removed_by_category: dict[str, int],
    removed_by_user: dict[str, int],
    removed_by_user_category: dict[str, dict[str, int]],
    removed_by_pattern: dict[str, int],
    artifact_source: str,
) -> None:
    category_stats_all_users: dict[str, dict[str, Any]] = {}
    category_stats_by_user: dict[str, dict[str, dict[str, Any]]] = {}
    validation_category_stats_all_users: dict[str, dict[str, Any]] = {}
    validation_category_stats_by_user: dict[str, dict[str, dict[str, Any]]] = {}
    total_construction_reviews = 0
    total_validation_reviews = 0
    total_construction_text_reviews = 0
    total_validation_text_reviews = 0
    total_construction_ratings = 0
    total_validation_ratings = 0
    total_construction_rating_only = 0
    total_validation_rating_only = 0

    def rows() -> Iterator[dict[str, Any]]:
        nonlocal total_construction_reviews, total_validation_reviews
        nonlocal total_construction_text_reviews, total_validation_text_reviews
        nonlocal total_construction_ratings, total_validation_ratings
        nonlocal total_construction_rating_only, total_validation_rating_only
        for user_id, reviews in sorted(
            histories_by_user.items(),
            key=lambda item: (-len(item[1]), str(item[0])),
        ):
            construction_reviews, validation_reviews, split_summary = temporal_train_validation_split(
                reviews,
                temporal_train_fraction,
            )
            total_construction_reviews += len(construction_reviews)
            total_validation_reviews += len(validation_reviews)
            total_construction_text_reviews += int(split_summary["construction_text_review_count"])
            total_validation_text_reviews += int(split_summary["validation_text_review_count"])
            total_construction_ratings += int(split_summary["construction_rating_count"])
            total_validation_ratings += int(split_summary["validation_rating_count"])
            total_construction_rating_only += int(split_summary["construction_rating_only_count"])
            total_validation_rating_only += int(split_summary["validation_rating_only_count"])
            categories = sorted(
                {
                    str(review.get("category"))
                    for review in construction_reviews
                    if review.get("category")
                }
            )
            validation_categories = sorted(
                {
                    str(review.get("category"))
                    for review in validation_reviews
                    if review.get("category")
                }
            )
            user_category_stats = category_review_stats(construction_reviews)
            user_validation_category_stats = category_review_stats(validation_reviews)
            category_stats_by_user[user_id] = user_category_stats
            validation_category_stats_by_user[user_id] = user_validation_category_stats
            merge_category_review_stats(category_stats_all_users, user_category_stats)
            merge_category_review_stats(validation_category_stats_all_users, user_validation_category_stats)
            yield {
                "source": "amazon_reviews_2023",
                "artifact_source": artifact_source,
                "user_id": user_id,
                "review_count": len(construction_reviews),
                "retrieved_review_count": len(reviews),
                "validation_review_count": len(validation_reviews),
                "categories": categories,
                "validation_categories": validation_categories,
                "temporal_split": split_summary,
                "category_review_stats": user_category_stats,
                "validation_category_review_stats": user_validation_category_stats,
                "first_timestamp": construction_reviews[0].get("timestamp") if construction_reviews else None,
                "last_timestamp": construction_reviews[-1].get("timestamp") if construction_reviews else None,
                "validation_first_timestamp": validation_reviews[0].get("timestamp") if validation_reviews else None,
                "validation_last_timestamp": validation_reviews[-1].get("timestamp") if validation_reviews else None,
                "candidate_user_stats": candidate_by_user.get(user_id, {}),
                "review_filter_summary": {
                    "filter_fulfillment_reviews": filter_fulfillment_reviews,
                    "removed_reviews": removed_by_user.get(user_id, 0),
                    "removed_by_category": removed_by_user_category.get(user_id, {}),
                },
                "reviews": construction_reviews,
                "validation_reviews": validation_reviews,
            }

    written = write_local_jsonl(output_path, rows())
    missing = len(candidate_by_user) - written
    filter_summary = {
        "artifact_source": artifact_source,
        "candidate_users": str(candidate_path),
        "output": str(output_path),
        "review_prefix": review_prefix,
        "metadata_prefix": metadata_prefix if include_metadata else "",
        "include_metadata": include_metadata,
        "filter_fulfillment_reviews": filter_fulfillment_reviews,
        "temporal_split": {
            "method": "per_user_temporal",
            "unit": "review_or_rating_row",
            "train_fraction": temporal_train_fraction,
            "construction_reviews": total_construction_reviews,
            "validation_reviews": total_validation_reviews,
            "construction_text_reviews": total_construction_text_reviews,
            "validation_text_reviews": total_validation_text_reviews,
            "construction_ratings": total_construction_ratings,
            "validation_ratings": total_validation_ratings,
            "construction_rating_only_rows": total_construction_rating_only,
            "validation_rating_only_rows": total_validation_rating_only,
        },
        "requested_users": len(candidate_by_user),
        "written_users": written,
        "missing_users": missing,
        "scanned_indexed_rows": total_scanned,
        "selected_reviews_before_filter": total_selected,
        "kept_reviews": total_kept,
        "removed_reviews": total_removed,
        "category_review_stats": finalize_category_review_stats(category_stats_all_users),
        "validation_category_review_stats": finalize_category_review_stats(
            validation_category_stats_all_users
        ),
        "user_category_review_stats": {
            user_id: category_stats
            for user_id, category_stats in sorted(category_stats_by_user.items())
        },
        "user_validation_category_review_stats": {
            user_id: category_stats
            for user_id, category_stats in sorted(validation_category_stats_by_user.items())
        },
        "removed_by_category": dict(sorted(removed_by_category.items())),
        "removed_by_user": dict(sorted(removed_by_user.items())),
        "removed_by_user_category": {
            user_id: dict(sorted(category_counts.items()))
            for user_id, category_counts in sorted(removed_by_user_category.items())
        },
        "removed_by_pattern": dict(sorted(removed_by_pattern.items())),
    }
    summary_path = (
        Path(filter_summary_output)
        if filter_summary_output
        else output_path.with_suffix(output_path.suffix + ".filter_summary.json")
    )
    write_json(summary_path, filter_summary)
    print(
        f"Wrote {written:,} user histories to {output_path}. "
        f"Missing users: {missing:,}. Scanned indexed rows: {total_scanned:,}; "
        f"selected reviews: {total_selected:,}; removed reviews: {total_removed:,}; "
        f"kept reviews: {total_kept:,}; construction reviews: {total_construction_reviews:,}; "
        f"validation reviews: {total_validation_reviews:,}. Filter summary: {summary_path}"
    )


@app.local_entrypoint()
def export_user_histories_from_hf(
    candidate_users: str = "raw/amazon_reviews_2023/candidates/eligible_candidates_top100.jsonl",
    output: str = str(DEFAULT_LOCAL_HISTORY_OUTPUT),
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    review_prefix: str = DEFAULT_ELIGIBLE_REVIEW_PREFIX,
    revision: str = "main",
    top_n: int = 100,
    filter_fulfillment_reviews: bool = True,
    temporal_train_fraction: float = 0.8,
    filter_summary_output: str = "",
) -> None:
    """Export selected user histories from Hugging Face user-index artifacts."""
    candidate_path = Path(candidate_users)
    output_path = Path(output)
    candidate_rows = list(iter_local_jsonl_or_gz(candidate_path))
    if top_n:
        candidate_rows = candidate_rows[:top_n]
    candidate_by_user = {
        str(row["user_id"]): row
        for row in candidate_rows
        if row.get("user_id")
    }
    users_by_bucket: dict[str, list[str]] = {}
    for user_id in candidate_by_user:
        users_by_bucket.setdefault(user_bucket(user_id), []).append(user_id)

    print(
        f"Exporting {len(candidate_by_user):,} users from {len(users_by_bucket):,} "
        f"Hugging Face user buckets in {hf_path(path_prefix, review_prefix)}"
    )
    histories_by_user: dict[str, list[dict[str, Any]]] = {}
    total_scanned = 0
    total_selected = 0
    total_kept = 0
    total_removed = 0
    removed_by_category: dict[str, int] = {}
    removed_by_user: dict[str, int] = {}
    removed_by_user_category: dict[str, dict[str, int]] = {}
    removed_by_pattern: dict[str, int] = {}

    def add_counts(target: dict[str, int], source: dict[str, Any]) -> None:
        for key, value in source.items():
            target[str(key)] = target.get(str(key), 0) + int(value or 0)

    calls = [
        export_user_histories_for_bucket_from_hf_remote.spawn(
            bucket,
            user_ids,
            repo_id=repo_id,
            path_prefix=path_prefix,
            review_prefix=review_prefix,
            revision=revision,
            filter_fulfillment_reviews=filter_fulfillment_reviews,
        )
        for bucket, user_ids in sorted(users_by_bucket.items())
    ]
    for bucket, call in zip(sorted(users_by_bucket), calls, strict=True):
        print(f"bucket={bucket}: {call.object_id}")
    for bucket, call in zip(sorted(users_by_bucket), calls, strict=True):
        try:
            result = call.get()
        except Exception as err:
            print(f"bucket={bucket}: failed: {err}")
            raise
        summary = result["summary"]
        total_scanned += int(summary.get("scanned_rows") or 0)
        total_selected += int(summary.get("selected_rows") or 0)
        total_kept += int(summary.get("kept_rows") or 0)
        total_removed += int(summary.get("removed_rows") or 0)
        add_counts(removed_by_category, summary.get("removed_by_category", {}))
        add_counts(removed_by_user, summary.get("removed_by_user", {}))
        add_counts(removed_by_pattern, summary.get("removed_by_pattern", {}))
        for user_id, category_counts in summary.get("removed_by_user_category", {}).items():
            user_target = removed_by_user_category.setdefault(str(user_id), {})
            add_counts(user_target, category_counts)
        histories_by_user.update(result["histories"])
        print(f"bucket={bucket}: completed {summary}")

    write_temporal_user_histories(
        histories_by_user=histories_by_user,
        candidate_by_user=candidate_by_user,
        candidate_path=candidate_path,
        output_path=output_path,
        review_prefix=review_prefix,
        metadata_prefix="",
        include_metadata=False,
        filter_fulfillment_reviews=filter_fulfillment_reviews,
        temporal_train_fraction=temporal_train_fraction,
        filter_summary_output=filter_summary_output,
        total_scanned=total_scanned,
        total_selected=total_selected,
        total_kept=total_kept,
        total_removed=total_removed,
        removed_by_category=removed_by_category,
        removed_by_user=removed_by_user,
        removed_by_user_category=removed_by_user_category,
        removed_by_pattern=removed_by_pattern,
        artifact_source=f"huggingface:{repo_id}/{path_prefix}@{revision}",
    )


@app.function(
    volumes={str(VOLUME_MOUNT): volume},
    timeout=2 * 60 * 60,
    cpu=2,
    memory=8192,
)
def export_metadata_sidecar_for_category(
    category: str,
    parent_asins: list[str],
    metadata_prefix: str = DEFAULT_METADATA_PREFIX,
) -> dict[str, Any]:
    """Fetch compact product metadata for selected parent_asins in one category."""
    requested = set(parent_asins)
    metadata = metadata_for_parent_asins({category: requested}, metadata_prefix)
    rows_by_parent_asin = {
        parent_asin: compact_metadata_sidecar_row(row)
        for (parent_asin, _source_category), row in metadata.items()
    }
    summary = {
        "category": category,
        "metadata_prefix": metadata_prefix,
        "requested_parent_asins": len(requested),
        "matched_parent_asins": len(rows_by_parent_asin),
        "missing_parent_asins": len(requested) - len(rows_by_parent_asin),
    }
    print(f"[modal_amazon_metadata_sidecar] {category}: {json.dumps(summary)}", flush=True)
    return {"summary": summary, "metadata_rows": list(rows_by_parent_asin.values())}


@app.local_entrypoint()
def export_history_metadata(
    user_histories: str,
    output: str = "",
    metadata_prefix: str = DEFAULT_METADATA_PREFIX,
    wait: bool = True,
) -> None:
    """Export compact product metadata sidecar for an existing user-history JSONL."""
    history_path = Path(user_histories)
    output_path = (
        Path(output)
        if output
        else history_path.with_suffix(history_path.suffix + ".product_metadata.jsonl")
    )
    parent_asins_by_category = parent_asins_by_category_from_histories(history_path)
    total_parent_asins = sum(len(parent_asins) for parent_asins in parent_asins_by_category.values())
    print(
        f"Exporting compact metadata for {total_parent_asins:,} category-parent_asin "
        f"pairs across {len(parent_asins_by_category):,} categories from {history_path}"
    )
    calls = [
        export_metadata_sidecar_for_category.spawn(
            category,
            sorted(parent_asins),
            metadata_prefix=metadata_prefix,
        )
        for category, parent_asins in sorted(parent_asins_by_category.items())
    ]
    for category, call in zip(sorted(parent_asins_by_category), calls, strict=True):
        print(f"{category}: {call.object_id}")
    if not wait:
        return

    rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    summaries = []
    requested = 0
    matched = 0
    for category, call in zip(sorted(parent_asins_by_category), calls, strict=True):
        try:
            result = call.get()
        except Exception as err:
            print(f"{category}: failed: {err}")
            raise
        summary = result["summary"]
        summaries.append(summary)
        requested += int(summary.get("requested_parent_asins") or 0)
        matched += int(summary.get("matched_parent_asins") or 0)
        for row in result["metadata_rows"]:
            parent_asin = row.get("parent_asin")
            source_category = row.get("source_category") or category
            if parent_asin:
                rows_by_key[(str(parent_asin), str(source_category))] = row
        print(f"{category}: completed {summary}")

    rows = [
        row
        for _, row in sorted(
            rows_by_key.items(),
            key=lambda item: (item[0][1], item[0][0]),
        )
    ]
    written = write_local_jsonl(output_path, iter(rows))
    summary_path = output_path.with_suffix(output_path.suffix + ".summary.json")
    write_json(
        summary_path,
        {
            "user_histories": str(history_path),
            "output": str(output_path),
            "metadata_prefix": metadata_prefix,
            "requested_category_parent_asin_pairs": requested,
            "matched_category_parent_asin_pairs": matched,
            "written_rows": written,
            "categories": summaries,
        },
    )
    print(
        f"Wrote {written:,} compact metadata rows to {output_path}. "
        f"Requested pairs: {requested:,}; matched pairs: {matched:,}. "
        f"Summary: {summary_path}"
    )


def metadata_for_parent_asins_from_hf(
    parent_asins_by_category: dict[str, set[str]],
    repo_files: list[str],
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    metadata_prefix: str = DEFAULT_METADATA_PREFIX,
    revision: str = "main",
) -> dict[tuple[str, str], dict[str, Any]]:
    metadata: dict[tuple[str, str], dict[str, Any]] = {}
    columns = [
        "parent_asin",
        "source_category",
        "main_category",
        "title",
        "average_rating",
        "rating_number",
        "categories_json",
    ]
    for category, parent_asins in parent_asins_by_category.items():
        parent_asins_by_bucket: dict[str, set[str]] = {}
        for parent_asin in parent_asins:
            parent_asins_by_bucket.setdefault(parent_asin_bucket(parent_asin), set()).add(parent_asin)
        for bucket, bucket_parent_asins in parent_asins_by_bucket.items():
            metadata_root = hf_path(
                path_prefix,
                metadata_prefix,
                f"bucket={bucket}",
                f"source_category={category}",
            )
            parquet_files = [
                path
                for path in hf_files_under(repo_files, metadata_root)
                if path.endswith(".parquet")
            ]
            for parquet_path in parquet_files:
                for row in read_hf_parquet_rows(
                    repo_id,
                    parquet_path,
                    revision=revision,
                    columns=columns,
                ):
                    parent_asin = row.get("parent_asin")
                    if parent_asin in bucket_parent_asins:
                        source_category = str(row.get("source_category") or category)
                        metadata[(str(parent_asin), source_category)] = row
    return metadata


def missing_optional_review_id_projection_error(err: Exception) -> bool:
    message = str(err).lower()
    if "review_id" not in message:
        return False
    return any(
        marker in message
        for marker in (
            "fieldref",
            "field",
            "column",
            "schema",
            "not found",
            "no match",
            "missing",
        )
    )


@app.function(
    timeout=2 * 60 * 60,
    cpu=2,
    memory=8192,
)
def export_metadata_sidecar_for_category_from_hf_remote(
    category: str,
    parent_asins: list[str],
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    metadata_prefix: str = DEFAULT_METADATA_PREFIX,
    revision: str = "main",
) -> dict[str, Any]:
    """Modal worker: fetch compact product metadata from Hugging Face artifacts."""
    requested = set(parent_asins)
    repo_files = hf_repo_files(repo_id, revision=revision)
    metadata = metadata_for_parent_asins_from_hf(
        {category: requested},
        repo_files=repo_files,
        repo_id=repo_id,
        path_prefix=path_prefix,
        metadata_prefix=metadata_prefix,
        revision=revision,
    )
    rows_by_parent_asin = {
        parent_asin: compact_metadata_sidecar_row(row)
        for (parent_asin, _source_category), row in metadata.items()
    }
    summary = {
        "category": category,
        "source": "huggingface",
        "repo_id": repo_id,
        "metadata_prefix": metadata_prefix,
        "requested_parent_asins": len(requested),
        "matched_parent_asins": len(rows_by_parent_asin),
        "missing_parent_asins": len(requested) - len(rows_by_parent_asin),
    }
    print(f"[hf_amazon_metadata_sidecar] {category}: {json.dumps(summary)}", flush=True)
    return {"summary": summary, "metadata_rows": list(rows_by_parent_asin.values())}


@app.local_entrypoint()
def export_history_metadata_from_hf(
    user_histories: str,
    output: str = "",
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    metadata_prefix: str = DEFAULT_METADATA_PREFIX,
    revision: str = "main",
) -> None:
    """Export compact product metadata sidecar from Hugging Face artifacts."""
    history_path = Path(user_histories)
    output_path = (
        Path(output)
        if output
        else history_path.with_suffix(history_path.suffix + ".product_metadata.jsonl")
    )
    parent_asins_by_category = parent_asins_by_category_from_histories(history_path)
    total_parent_asins = sum(len(parent_asins) for parent_asins in parent_asins_by_category.values())
    print(
        f"Exporting compact metadata for {total_parent_asins:,} category-parent_asin "
        f"pairs across {len(parent_asins_by_category):,} categories from "
        f"hf://datasets/{repo_id}/{hf_path(path_prefix, metadata_prefix)}"
    )
    calls = [
        export_metadata_sidecar_for_category_from_hf_remote.spawn(
            category,
            sorted(parent_asins),
            repo_id=repo_id,
            path_prefix=path_prefix,
            metadata_prefix=metadata_prefix,
            revision=revision,
        )
        for category, parent_asins in sorted(parent_asins_by_category.items())
    ]
    for category, call in zip(sorted(parent_asins_by_category), calls, strict=True):
        print(f"{category}: {call.object_id}")

    rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    summaries = []
    requested = 0
    matched = 0
    for category, call in zip(sorted(parent_asins_by_category), calls, strict=True):
        try:
            result = call.get()
        except Exception as err:
            print(f"{category}: failed: {err}")
            raise
        summary = result["summary"]
        summaries.append(summary)
        requested += int(summary.get("requested_parent_asins") or 0)
        matched += int(summary.get("matched_parent_asins") or 0)
        for row in result["metadata_rows"]:
            parent_asin = row.get("parent_asin")
            source_category = row.get("source_category") or category
            if parent_asin:
                rows_by_key[(str(parent_asin), str(source_category))] = row
        print(f"{category}: completed {summary}")

    rows = [
        row
        for _, row in sorted(
            rows_by_key.items(),
            key=lambda item: (item[0][1], item[0][0]),
        )
    ]
    written = write_local_jsonl(output_path, iter(rows))
    summary_path = output_path.with_suffix(output_path.suffix + ".summary.json")
    write_json(
        summary_path,
        {
            "artifact_source": f"huggingface:{repo_id}/{path_prefix}@{revision}",
            "user_histories": str(history_path),
            "output": str(output_path),
            "metadata_prefix": metadata_prefix,
            "requested_category_parent_asin_pairs": requested,
            "matched_category_parent_asin_pairs": matched,
            "written_rows": written,
            "categories": summaries,
        },
    )
    print(
        f"Wrote {written:,} compact metadata rows to {output_path}. "
        f"Requested pairs: {requested:,}; matched pairs: {matched:,}. "
        f"Summary: {summary_path}"
    )


@app.function(
    volumes={str(VOLUME_MOUNT): volume},
    secrets=[modal.Secret.from_name("huggingface-secret")],
    timeout=24 * 60 * 60,
    cpu=4,
    memory=16384,
)
def upload_modal_artifacts_to_huggingface(
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    artifact_prefixes: list[str] | None = None,
    max_files_per_artifact: int = 0,
    create_pr: bool = False,
) -> dict[str, Any]:
    """Upload selected Modal Volume artifact folders directly to Hugging Face."""
    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is required. Add it to Modal secret huggingface-secret.")

    artifact_prefixes = artifact_prefixes or CURRENT_MODAL_ARTIFACT_PREFIXES
    api = HfApi(token=token)
    uploaded = []
    missing = []
    root_readme_path = Path("/tmp") / "amazon_modal_artifacts_README.md"
    root_readme_path.write_text(
        "\n".join(
            [
                "# Amazon Reviews 2023 Modal Artifacts",
                "",
                "This folder mirrors selected artifacts from the Modal Volume "
                f"`{VOLUME_NAME}` for the Amazon Reviews 2023 persona workflow.",
                "",
                "Artifacts are uploaded file-by-file from Modal to Hugging Face "
                "so migration progress is observable and does not require local "
                "laptop staging.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    api.upload_file(
        repo_id=repo_id,
        repo_type="dataset",
        path_or_fileobj=str(root_readme_path),
        path_in_repo=f"{path_prefix.rstrip('/')}/README.md",
        commit_message="Create Amazon Modal artifact folder",
        create_pr=create_pr,
    )
    print(
        f"[modal_hf_upload] initialized {repo_id}/{path_prefix.rstrip('/')}/",
        flush=True,
    )

    for artifact_prefix in artifact_prefixes:
        local_path = VOLUME_MOUNT / artifact_prefix
        if not local_path.exists():
            missing.append(artifact_prefix)
            print(f"[modal_hf_upload] missing: {artifact_prefix}", flush=True)
            continue
        artifact_path_in_repo = f"{path_prefix.rstrip('/')}/{artifact_prefix}"
        artifact_files = sorted(path for path in local_path.rglob("*") if path.is_file())
        if max_files_per_artifact > 0:
            artifact_files = artifact_files[:max_files_per_artifact]
        print(
            f"[modal_hf_upload] uploading {len(artifact_files):,} files from "
            f"{local_path} -> {repo_id}/{artifact_path_in_repo}",
            flush=True,
        )
        uploaded_files = 0
        uploaded_bytes = 0
        for file_index, file_path in enumerate(artifact_files, start=1):
            relative_path = file_path.relative_to(local_path)
            repo_file_path = f"{artifact_path_in_repo}/{relative_path.as_posix()}"
            file_size = file_path.stat().st_size
            print(
                f"[modal_hf_upload] {artifact_prefix} "
                f"{file_index:,}/{len(artifact_files):,}: "
                f"{relative_path.as_posix()} ({file_size:,} bytes)",
                flush=True,
            )
            api.upload_file(
                repo_id=repo_id,
                repo_type="dataset",
                path_or_fileobj=str(file_path),
                path_in_repo=repo_file_path,
                commit_message=f"Upload Amazon artifact file: {artifact_prefix}",
                create_pr=create_pr,
            )
            uploaded_files += 1
            uploaded_bytes += file_size
        uploaded.append(
            {
                "artifact_prefix": artifact_prefix,
                "path_in_repo": artifact_path_in_repo,
                "files": uploaded_files,
                "bytes": uploaded_bytes,
            }
        )
        print(
            f"[modal_hf_upload] completed: {artifact_prefix}; "
            f"files={uploaded_files:,}; bytes={uploaded_bytes:,}",
            flush=True,
        )

    manifest = {
        "source": f"Modal volume {VOLUME_NAME}",
        "repo_id": repo_id,
        "path_prefix": path_prefix,
        "dataset": DATASET_NAME,
        "time_window": "2018-2023 for review/user artifacts; 2023 metadata index",
        "uploaded": uploaded,
        "missing": missing,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_definitions": {
            DEFAULT_STATS_PREFIX: "Per-category per-user summary stats.",
            DEFAULT_ELIGIBLE_USERS_PREFIX: (
                "Eligible users with review_count >= 30, verified_share >= 0.70, "
                "and text_chars >= 2000."
            ),
            DEFAULT_ELIGIBLE_REVIEW_PREFIX: (
                "User-indexed review/rating rows for eligible users, bucketed by "
                "sha1(user_id)[:2]."
            ),
            DEFAULT_METADATA_PREFIX: (
                "Product metadata indexed by sha1(parent_asin)[:2], with source "
                "category partitions."
            ),
        },
    }
    manifest_path = Path("/tmp") / "amazon_modal_artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    api.upload_file(
        repo_id=repo_id,
        repo_type="dataset",
        path_or_fileobj=str(manifest_path),
        path_in_repo=f"{path_prefix.rstrip('/')}/manifest.json",
        commit_message="Upload Amazon artifact manifest",
        create_pr=create_pr,
    )
    print(
        f"[modal_hf_upload] uploaded manifest to "
        f"{repo_id}/{path_prefix.rstrip('/')}/manifest.json",
        flush=True,
    )
    return manifest


@app.local_entrypoint()
def upload_current_artifacts_to_hf(
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    artifact_prefixes: str = ",".join(CURRENT_MODAL_ARTIFACT_PREFIXES),
    max_files_per_artifact: int = 0,
    create_pr: bool = False,
    wait: bool = False,
) -> None:
    """Start direct Modal Volume -> Hugging Face upload for current artifacts."""
    prefixes = [part.strip() for part in artifact_prefixes.split(",") if part.strip()]
    call = upload_modal_artifacts_to_huggingface.spawn(
        repo_id=repo_id,
        path_prefix=path_prefix,
        artifact_prefixes=prefixes,
        max_files_per_artifact=max_files_per_artifact,
        create_pr=create_pr,
    )
    print(f"Started Hugging Face upload: {call.object_id}")
    print(f"Repo: https://huggingface.co/datasets/{repo_id}/tree/main/{path_prefix}")
    if not wait:
        return
    result = call.get()
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.function(
    volumes={str(VOLUME_MOUNT): volume},
    secrets=[modal.Secret.from_name("huggingface-secret")],
    timeout=24 * 60 * 60,
    cpu=4,
    memory=16384,
)
def upload_single_artifact_folder_to_hf_pr(
    artifact_prefix: str,
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
) -> dict[str, Any]:
    """Upload one Modal artifact folder as one Hugging Face dataset PR."""
    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is required. Add it to Modal secret huggingface-secret.")

    local_path = VOLUME_MOUNT / artifact_prefix
    if not local_path.exists():
        raise FileNotFoundError(f"Modal artifact does not exist: {local_path}")

    files = sorted(path for path in local_path.rglob("*") if path.is_file())
    total_bytes = sum(path.stat().st_size for path in files)
    path_in_repo = f"{path_prefix.rstrip('/')}/{artifact_prefix}"
    print(
        f"[modal_hf_artifact_pr] uploading {artifact_prefix}: "
        f"{len(files):,} files, {total_bytes:,} bytes -> {repo_id}/{path_in_repo}",
        flush=True,
    )

    api = HfApi(token=token)
    commit_info = api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=str(local_path),
        path_in_repo=path_in_repo,
        commit_message=f"Upload Amazon artifact folder: {artifact_prefix}",
        create_pr=True,
    )
    result = {
        "repo_id": repo_id,
        "artifact_prefix": artifact_prefix,
        "path_in_repo": path_in_repo,
        "files": len(files),
        "bytes": total_bytes,
        "commit_info": {
            "commit_url": getattr(commit_info, "commit_url", None),
            "commit_message": getattr(commit_info, "commit_message", None),
            "pr_url": getattr(commit_info, "pr_url", None),
        },
    }
    print(f"[modal_hf_artifact_pr] completed: {json.dumps(result)}", flush=True)
    return result


def hf_pr_revision_from_commit_info(commit_info: Any) -> str | None:
    pr_revision = getattr(commit_info, "pr_revision", None)
    if pr_revision:
        return str(pr_revision)
    pr_url = getattr(commit_info, "pr_url", None)
    if not pr_url:
        return None
    match = re.search(r"/discussions/(\d+)", str(pr_url))
    if not match:
        return None
    return f"refs/pr/{match.group(1)}"


@app.function(
    volumes={str(VOLUME_MOUNT): volume},
    secrets=[modal.Secret.from_name("huggingface-secret")],
    timeout=24 * 60 * 60,
    cpu=4,
    memory=16384,
)
def upload_single_artifact_folder_to_hf_pr_chunked(
    artifact_prefix: str,
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    batch_size: int = 200,
    max_files: int = 0,
) -> dict[str, Any]:
    """Upload one artifact folder as one HF PR, committing files in batches."""
    from huggingface_hub import CommitOperationAdd, HfApi

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is required. Add it to Modal secret huggingface-secret.")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    local_path = VOLUME_MOUNT / artifact_prefix
    if not local_path.exists():
        raise FileNotFoundError(f"Modal artifact does not exist: {local_path}")

    files = sorted(path for path in local_path.rglob("*") if path.is_file())
    if max_files > 0:
        files = files[:max_files]
    total_bytes = sum(path.stat().st_size for path in files)
    path_in_repo = f"{path_prefix.rstrip('/')}/{artifact_prefix}"
    api = HfApi(token=token)

    print(
        f"[modal_hf_artifact_pr_chunked] uploading {artifact_prefix}: "
        f"{len(files):,} files, {total_bytes:,} bytes, batch_size={batch_size:,} "
        f"-> {repo_id}/{path_in_repo}",
        flush=True,
    )

    pr_url = None
    pr_revision = None
    uploaded_files = 0
    uploaded_bytes = 0
    batches = 0
    total_batches = (len(files) + batch_size - 1) // batch_size if files else 0

    for batch_start in range(0, len(files), batch_size):
        batch = files[batch_start : batch_start + batch_size]
        batches += 1
        batch_bytes = sum(path.stat().st_size for path in batch)
        operations = [
            CommitOperationAdd(
                path_in_repo=(
                    f"{path_in_repo}/{file_path.relative_to(local_path).as_posix()}"
                ),
                path_or_fileobj=str(file_path),
            )
            for file_path in batch
        ]
        commit_message = (
            f"Upload Amazon artifact {artifact_prefix} "
            f"batch {batches}/{total_batches}"
        )
        print(
            f"[modal_hf_artifact_pr_chunked] {artifact_prefix} "
            f"batch {batches:,}/{total_batches:,}: "
            f"files={len(batch):,}; bytes={batch_bytes:,}; "
            f"first={batch[0].relative_to(local_path).as_posix()}",
            flush=True,
        )
        kwargs = {
            "repo_id": repo_id,
            "repo_type": "dataset",
            "operations": operations,
            "commit_message": commit_message,
        }
        if pr_revision:
            kwargs["revision"] = pr_revision
        else:
            kwargs["create_pr"] = True
        commit_info = api.create_commit(**kwargs)
        if not pr_url:
            pr_url = getattr(commit_info, "pr_url", None)
        if not pr_revision:
            pr_revision = hf_pr_revision_from_commit_info(commit_info)
        uploaded_files += len(batch)
        uploaded_bytes += batch_bytes
        print(
            f"[modal_hf_artifact_pr_chunked] completed batch {batches:,}; "
            f"uploaded_files={uploaded_files:,}/{len(files):,}; "
            f"pr_url={pr_url}; pr_revision={pr_revision}",
            flush=True,
        )

    result = {
        "repo_id": repo_id,
        "artifact_prefix": artifact_prefix,
        "path_in_repo": path_in_repo,
        "files": uploaded_files,
        "bytes": uploaded_bytes,
        "batches": batches,
        "pr_url": pr_url,
        "pr_revision": pr_revision,
    }
    print(f"[modal_hf_artifact_pr_chunked] completed: {json.dumps(result)}", flush=True)
    return result


@app.local_entrypoint()
def upload_artifact_folder_to_hf_pr(
    artifact_prefix: str,
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    wait: bool = True,
) -> None:
    """Start one Hugging Face PR for one Modal artifact folder."""
    call = upload_single_artifact_folder_to_hf_pr.spawn(
        artifact_prefix=artifact_prefix,
        repo_id=repo_id,
        path_prefix=path_prefix,
    )
    print(f"Started Hugging Face artifact PR upload: {call.object_id}")
    print(f"Artifact: {artifact_prefix}")
    print(f"Target: https://huggingface.co/datasets/{repo_id}/tree/main/{path_prefix}")
    if not wait:
        return
    result = call.get()
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.local_entrypoint()
def upload_artifact_folder_to_hf_pr_chunked(
    artifact_prefix: str,
    repo_id: str = DEFAULT_HF_REPO_ID,
    path_prefix: str = DEFAULT_HF_AMAZON_PREFIX,
    batch_size: int = 200,
    max_files: int = 0,
    wait: bool = True,
) -> None:
    """Start one chunked Hugging Face PR for one Modal artifact folder."""
    call = upload_single_artifact_folder_to_hf_pr_chunked.spawn(
        artifact_prefix=artifact_prefix,
        repo_id=repo_id,
        path_prefix=path_prefix,
        batch_size=batch_size,
        max_files=max_files,
    )
    print(f"Started chunked Hugging Face artifact PR upload: {call.object_id}")
    print(f"Artifact: {artifact_prefix}")
    print(f"Target: https://huggingface.co/datasets/{repo_id}/tree/main/{path_prefix}")
    if not wait:
        return
    result = call.get()
    print(json.dumps(result, indent=2, ensure_ascii=False))


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
