#!/usr/bin/env python3
"""Retrieve full Amazon Reviews 2023 histories for selected candidate users.

This bridges the exploration outputs and persona inference:

1. read candidate_users.jsonl from the reviewer-pool analysis,
2. stream the relevant Amazon review category files,
3. keep reviews for selected user_ids,
4. write user_histories.jsonl for downstream schema inference.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import json
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_dimension_inference"
    / "user_histories.jsonl"
)

REVIEW_URL_TEMPLATE = (
    "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/"
    "raw/review_categories/{category}.jsonl.gz"
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
    print(f"[amazon_history_retrieval] {message}", flush=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def iter_jsonl_or_gz(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


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


def review_url(category: str) -> str:
    return REVIEW_URL_TEMPLATE.format(category=category)


def open_remote_gzip_jsonl(url: str) -> Iterator[dict[str, Any]]:
    try:
        with urllib.request.urlopen(url) as response:
            with gzip.GzipFile(fileobj=response) as gz:
                for raw_line in gz:
                    if raw_line.strip():
                        yield json.loads(raw_line)
    except urllib.error.URLError as err:
        raise RuntimeError(f"Failed to stream {url}: {err}") from err


def parse_categories(value: str, candidate_rows: list[dict[str, Any]]) -> list[str]:
    if value == "candidate_categories":
        categories = sorted(
            {
                category
                for row in candidate_rows
                for category in row.get("categories", [])
                if category
            }
        )
    elif value == "all":
        categories = CATEGORIES
    else:
        categories = [part.strip() for part in value.split(",") if part.strip()]
    unknown = sorted(set(categories) - set(CATEGORIES))
    if unknown:
        raise ValueError(f"Unknown Amazon Reviews 2023 categories: {', '.join(unknown)}")
    return categories


def normalize_review(row: dict[str, Any], category: str) -> dict[str, Any]:
    timestamp = normalize_timestamp(row.get("timestamp", row.get("sort_timestamp")))
    return {
        "source": "amazon_reviews_2023",
        "category": category,
        "user_id": row.get("user_id"),
        "parent_asin": row.get("parent_asin"),
        "asin": row.get("asin"),
        "timestamp": timestamp,
        "date": timestamp_to_date(timestamp),
        "rating": row.get("rating"),
        "title": row.get("title", ""),
        "text": row.get("text", ""),
        "verified_purchase": row.get("verified_purchase"),
        "helpful_vote": row.get("helpful_vote", row.get("helpful_votes")),
    }


def load_candidate_users(path: Path, top_n: int) -> list[dict[str, Any]]:
    rows = list(iter_jsonl_or_gz(path))
    if top_n:
        rows = rows[:top_n]
    return rows


def retrieve_histories(
    candidate_rows: list[dict[str, Any]],
    categories: list[str],
    start_timestamp: int | None,
    end_timestamp: int | None,
    max_reviews_per_category: int,
    early_stop_from_candidate_counts: bool,
    workers: int,
    progress_every: int,
) -> dict[str, list[dict[str, Any]]]:
    selected_user_ids = {row["user_id"] for row in candidate_rows if row.get("user_id")}
    expected_counts_by_category = {}
    if early_stop_from_candidate_counts:
        for category in categories:
            expected_counts_by_category[category] = sum(
                int(row.get("category_counts", {}).get(category, 0) or 0)
                for row in candidate_rows
            )

    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def retrieve_category(category: str) -> list[dict[str, Any]]:
        category_reviews = []
        scanned = 0
        kept = 0
        expected_count = expected_counts_by_category.get(category, 0)
        if expected_count:
            log(f"{category}: expecting {expected_count:,} selected-user reviews")
        for row in open_remote_gzip_jsonl(review_url(category)):
            scanned += 1
            if progress_every and scanned % progress_every == 0:
                log(f"{category}: scanned {scanned:,}; kept {kept:,}")
            user_id = row.get("user_id")
            if user_id not in selected_user_ids:
                continue
            timestamp = normalize_timestamp(row.get("timestamp", row.get("sort_timestamp")))
            if start_timestamp is not None and (timestamp is None or timestamp < start_timestamp):
                continue
            if end_timestamp is not None and (timestamp is None or timestamp >= end_timestamp):
                continue
            category_reviews.append(normalize_review(row, category))
            kept += 1
            if expected_count and kept >= expected_count:
                log(
                    f"{category}: found all {kept:,} expected selected-user reviews; "
                    f"stopping after {scanned:,} scanned"
                )
                break
            if max_reviews_per_category and kept >= max_reviews_per_category:
                break
        log(f"{category}: scanned {scanned:,}; kept {kept:,}")
        return category_reviews

    if workers <= 1 or len(categories) <= 1:
        for category in categories:
            for review in retrieve_category(category):
                histories[review["user_id"]].append(review)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_category = {
                executor.submit(retrieve_category, category): category
                for category in categories
            }
            for future in concurrent.futures.as_completed(future_to_category):
                category = future_to_category[future]
                try:
                    reviews = future.result()
                except Exception as err:
                    raise RuntimeError(f"Failed retrieving category {category}: {err}") from err
                for review in reviews:
                    histories[review["user_id"]].append(review)
    return histories


def write_histories(
    path: Path,
    candidate_rows: list[dict[str, Any]],
    histories: dict[str, list[dict[str, Any]]],
) -> int:
    ensure_dir(path.parent)
    candidate_by_user = {row.get("user_id"): row for row in candidate_rows}
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for user_id, reviews in sorted(
            histories.items(),
            key=lambda item: (-len(item[1]), str(item[0])),
        ):
            reviews = sorted(reviews, key=lambda row: row.get("timestamp") or 0)
            row = {
                "source": "amazon_reviews_2023",
                "user_id": user_id,
                "review_count": len(reviews),
                "categories": sorted({review["category"] for review in reviews}),
                "first_timestamp": reviews[0].get("timestamp") if reviews else None,
                "last_timestamp": reviews[-1].get("timestamp") if reviews else None,
                "candidate_user_stats": candidate_by_user.get(user_id, {}),
                "reviews": reviews,
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-users", type=Path, required=True)
    parser.add_argument(
        "--categories",
        default="candidate_categories",
        help="Comma-separated categories, 'all', or 'candidate_categories'.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2023)
    parser.add_argument(
        "--max-reviews-per-category",
        type=int,
        default=0,
        help="Stop after this many kept selected-user reviews per category. 0 means all.",
    )
    parser.add_argument(
        "--disable-early-stop",
        action="store_true",
        help=(
            "Do not stop early using category_counts from candidate users. "
            "By default, category_counts lets the retriever stop once all expected "
            "selected-user reviews are found for a category."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of categories to stream in parallel. Use 1 for sequential scans.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=250_000,
        help="Log progress every N scanned review rows per category. Use 0 to disable.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    candidate_rows = load_candidate_users(args.candidate_users, args.top_n)
    categories = parse_categories(args.categories, candidate_rows)
    log(f"Selected {len(candidate_rows):,} candidate users")
    log(f"Streaming {len(categories):,} categories: {', '.join(categories)}")
    histories = retrieve_histories(
        candidate_rows,
        categories,
        start_timestamp=year_to_timestamp_ms(args.start_year),
        end_timestamp=year_to_timestamp_ms(args.end_year, end=True),
        max_reviews_per_category=args.max_reviews_per_category,
        early_stop_from_candidate_counts=not args.disable_early_stop,
        workers=args.workers,
        progress_every=args.progress_every,
    )
    count = write_histories(args.output, candidate_rows, histories)
    log(f"Wrote {count:,} user histories: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(130)
