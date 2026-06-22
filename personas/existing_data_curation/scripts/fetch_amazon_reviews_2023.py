#!/usr/bin/env python3
"""Retrieve Amazon Reviews 2023 data for behavior-grounded persona work.

The dataset is large, so the default path is sample-first:

1. stream category review JSONL.GZ files from McAuley Lab,
2. save a bounded review sample,
3. build reviewer-level histories suitable for persona construction/evaluation,
4. optionally sample item metadata for reviewed parent ASINs.
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_TARGET_DIR = BASE_DIR / "raw" / "amazon_reviews_2023"

REVIEW_URL_TEMPLATE = (
    "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/"
    "raw/review_categories/{category}.jsonl.gz"
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


def log(message: str) -> None:
    print(f"[amazon_reviews_2023] {message}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return int(float(value))


def open_remote_gzip_jsonl(url: str) -> Iterator[dict[str, Any]]:
    try:
        with urllib.request.urlopen(url) as response:
            with gzip.GzipFile(fileobj=response) as gz:
                for raw_line in gz:
                    if raw_line.strip():
                        yield json.loads(raw_line)
    except urllib.error.URLError as err:
        raise RuntimeError(f"Failed to stream {url}: {err}") from err


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    ensure_dir(path.parent)
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def download_file(url: str, output_path: Path, force: bool = False) -> Path:
    ensure_dir(output_path.parent)
    if output_path.exists() and not force:
        log(f"Skip existing file: {output_path}")
        return output_path

    with tempfile.NamedTemporaryFile(delete=False, dir=output_path.parent) as tmp:
        tmp_path = Path(tmp.name)

    try:
        log(f"Downloading {url}")
        with urllib.request.urlopen(url) as response, open(tmp_path, "wb") as fh:
            shutil.copyfileobj(response, fh)
        tmp_path.replace(output_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    log(f"Saved {output_path}")
    return output_path


def review_url(category: str) -> str:
    return REVIEW_URL_TEMPLATE.format(category=category)


def meta_url(category: str) -> str:
    return META_URL_TEMPLATE.format(category=category)


def normalize_review(row: dict[str, Any], category: str) -> dict[str, Any]:
    timestamp = row.get("timestamp", row.get("sort_timestamp"))
    normalized = {
        "source": "amazon_reviews_2023",
        "category": category,
        "user_id": row.get("user_id"),
        "parent_asin": row.get("parent_asin"),
        "asin": row.get("asin"),
        "timestamp": timestamp,
        "rating": row.get("rating"),
        "title": row.get("title", ""),
        "text": row.get("text", ""),
        "verified_purchase": row.get("verified_purchase"),
        "helpful_vote": row.get("helpful_vote", row.get("helpful_votes")),
    }
    return normalized


def count_users_for_category(category: str, threshold: int) -> dict[str, int]:
    user_counts: dict[str, int] = defaultdict(int)
    total_reviews = 0
    missing_user_id = 0

    for row in open_remote_gzip_jsonl(review_url(category)):
        total_reviews += 1
        user_id = row.get("user_id")
        if not user_id:
            missing_user_id += 1
            continue
        user_counts[user_id] += 1
        if total_reviews % 1_000_000 == 0:
            log(
                f"{category}: processed {total_reviews:,} reviews; "
                f"{len(user_counts):,} unique users"
            )

    users_at_threshold = sum(1 for count in user_counts.values() if count >= threshold)
    max_reviews = max(user_counts.values(), default=0)
    return {
        "total_reviews": total_reviews,
        "unique_users": len(user_counts),
        "missing_user_id": missing_user_id,
        "threshold": threshold,
        "users_at_or_above_threshold": users_at_threshold,
        "max_reviews_per_user": max_reviews,
    }


def sample_reviews_for_category(
    category: str,
    output_dir: Path,
    max_reviews: int,
) -> tuple[Path, int, set[str]]:
    url = review_url(category)
    output_path = output_dir / "reviews" / f"{category}_sample_{max_reviews}.jsonl"
    parent_asins: set[str] = set()

    def rows() -> Iterator[dict[str, Any]]:
        count = 0
        for row in open_remote_gzip_jsonl(url):
            normalized = normalize_review(row, category)
            parent_asin = normalized.get("parent_asin")
            if parent_asin:
                parent_asins.add(parent_asin)
            yield normalized
            count += 1
            if count >= max_reviews:
                break

    count = write_jsonl(output_path, rows())
    log(f"Saved {count} review rows for {category}: {output_path}")
    return output_path, count, parent_asins


def sample_metadata_for_category(
    category: str,
    output_dir: Path,
    parent_asins: set[str],
    max_meta_rows: int,
) -> tuple[Path, int]:
    url = meta_url(category)
    output_path = output_dir / "metadata" / f"meta_{category}_sample.jsonl"

    def rows() -> Iterator[dict[str, Any]]:
        count = 0
        for row in open_remote_gzip_jsonl(url):
            parent_asin = row.get("parent_asin")
            if parent_asins and parent_asin not in parent_asins:
                continue
            yield row
            count += 1
            if count >= max_meta_rows:
                break

    count = write_jsonl(output_path, rows())
    log(f"Saved {count} metadata rows for {category}: {output_path}")
    return output_path, count


def load_reviews(paths: Iterable[Path]) -> Iterator[dict[str, Any]]:
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)


def build_user_histories(
    review_paths: list[Path],
    output_dir: Path,
    min_reviews: int,
    max_users: int,
) -> tuple[Path, int]:
    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for review in load_reviews(review_paths):
        user_id = review.get("user_id")
        if user_id:
            histories[user_id].append(review)

    eligible = [
        (user_id, sorted(reviews, key=lambda row: row.get("timestamp") or 0))
        for user_id, reviews in histories.items()
        if len(reviews) >= min_reviews
    ]
    eligible.sort(key=lambda item: (-len(item[1]), item[0]))
    if max_users:
        eligible = eligible[:max_users]

    output_path = output_dir / "user_histories" / (
        f"user_histories_min{min_reviews}_max{max_users or 'all'}.jsonl"
    )

    def rows() -> Iterator[dict[str, Any]]:
        for user_id, reviews in eligible:
            yield {
                "source": "amazon_reviews_2023",
                "user_id": user_id,
                "review_count": len(reviews),
                "categories": sorted({row["category"] for row in reviews if row.get("category")}),
                "first_timestamp": reviews[0].get("timestamp"),
                "last_timestamp": reviews[-1].get("timestamp"),
                "reviews": reviews,
            }

    count = write_jsonl(output_path, rows())
    log(f"Saved {count} user histories: {output_path}")
    return output_path, count


def write_manifest(
    output_dir: Path,
    categories: list[str],
    review_counts: dict[str, int],
    metadata_counts: dict[str, int],
    user_history_count: int,
) -> Path:
    manifest = {
        "id": "amazon_reviews_2023",
        "dataset_url": "https://amazon-reviews-2023.github.io/",
        "review_url_template": REVIEW_URL_TEMPLATE,
        "meta_url_template": META_URL_TEMPLATE,
        "categories": categories,
        "review_counts": review_counts,
        "metadata_counts": metadata_counts,
        "user_history_count": user_history_count,
    }
    output_path = output_dir / "manifest.json"
    ensure_dir(output_path.parent)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    log(f"Saved manifest: {output_path}")
    return output_path


def parse_categories(value: str) -> list[str]:
    categories = [part.strip() for part in value.split(",") if part.strip()]
    unknown = sorted(set(categories) - set(CATEGORIES))
    if unknown:
        raise ValueError(f"Unknown Amazon Reviews 2023 categories: {', '.join(unknown)}")
    return categories


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--categories",
        default="All_Beauty",
        help="Comma-separated Amazon Reviews 2023 categories, e.g. All_Beauty,Software.",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=DEFAULT_TARGET_DIR,
        help=f"Output directory (default: {DEFAULT_TARGET_DIR}).",
    )
    parser.add_argument(
        "--mode",
        choices=["sample", "full"],
        default="sample",
        help="sample streams bounded JSONL outputs; full downloads raw .jsonl.gz files.",
    )
    parser.add_argument(
        "--max-reviews-per-category",
        type=parse_int,
        default=10000,
        help="Maximum review rows to keep per category in sample mode.",
    )
    parser.add_argument(
        "--include-metadata",
        action="store_true",
        help="Also sample item metadata for parent ASINs seen in sampled reviews.",
    )
    parser.add_argument(
        "--max-meta-rows-per-category",
        type=parse_int,
        default=10000,
        help="Maximum metadata rows to keep per category when --include-metadata is set.",
    )
    parser.add_argument(
        "--min-user-reviews",
        type=parse_int,
        default=3,
        help="Minimum sampled reviews required for a reviewer-level history.",
    )
    parser.add_argument(
        "--max-users",
        type=parse_int,
        default=1000,
        help="Maximum user histories to save. Use 0 for all eligible users.",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="Print supported category names and exit.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing full-download files.",
    )
    parser.add_argument(
        "--count-users",
        action="store_true",
        help="Stream selected categories and count users at or above --user-review-threshold.",
    )
    parser.add_argument(
        "--user-review-threshold",
        type=parse_int,
        default=100,
        help="Threshold used with --count-users.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)

    if args.list_categories:
        print("\n".join(CATEGORIES))
        return 0

    categories = parse_categories(args.categories)
    ensure_dir(args.target_dir)

    if args.count_users:
        for category in categories:
            stats = count_users_for_category(category, args.user_review_threshold)
            print(json.dumps({"category": category, **stats}, indent=2))
        return 0

    review_counts: dict[str, int] = {}
    metadata_counts: dict[str, int] = {}
    review_paths: list[Path] = []

    if args.mode == "full":
        for category in categories:
            review_path = args.target_dir / "raw_gz" / f"{category}.jsonl.gz"
            meta_path = args.target_dir / "raw_gz" / f"meta_{category}.jsonl.gz"
            download_file(review_url(category), review_path, force=args.force)
            if args.include_metadata:
                download_file(meta_url(category), meta_path, force=args.force)
        write_manifest(args.target_dir, categories, review_counts, metadata_counts, 0)
        return 0

    all_parent_asins: dict[str, set[str]] = {}
    for category in categories:
        review_path, review_count, parent_asins = sample_reviews_for_category(
            category=category,
            output_dir=args.target_dir,
            max_reviews=args.max_reviews_per_category,
        )
        review_paths.append(review_path)
        review_counts[category] = review_count
        all_parent_asins[category] = parent_asins

    if args.include_metadata:
        for category in categories:
            _, metadata_count = sample_metadata_for_category(
                category=category,
                output_dir=args.target_dir,
                parent_asins=all_parent_asins[category],
                max_meta_rows=args.max_meta_rows_per_category,
            )
            metadata_counts[category] = metadata_count

    _, user_history_count = build_user_histories(
        review_paths=review_paths,
        output_dir=args.target_dir,
        min_reviews=args.min_user_reviews,
        max_users=args.max_users,
    )
    write_manifest(
        output_dir=args.target_dir,
        categories=categories,
        review_counts=review_counts,
        metadata_counts=metadata_counts,
        user_history_count=user_history_count,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        log(f"ERROR: {exc}")
        raise
