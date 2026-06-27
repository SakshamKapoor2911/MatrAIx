#!/usr/bin/env python3
"""Explore Amazon Reviews 2023 reviewer pools for persona construction.

This script streams category review files and computes reviewer-level signals:

- total reviews
- number of categories reviewed
- history span
- text volume
- verified-purchase share
- rating mean

It writes a summary plus candidate user pool JSONL using thresholds that mirror
the Reddit persona criteria: enough behavior, cross-domain coverage, and enough
time span for stable preference/persona inference.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "raw" / "amazon_reviews_2023" / "exploration"

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


@dataclass
class UserStats:
    user_id: str
    review_count: int = 0
    category_counts: dict[str, int] = field(default_factory=dict)
    first_timestamp: int | None = None
    last_timestamp: int | None = None
    text_chars: int = 0
    text_reviews: int = 0
    verified_count: int = 0
    rating_sum: float = 0.0
    rating_count: int = 0

    def add(self, row: dict[str, Any], category: str) -> None:
        timestamp = normalize_timestamp(row.get("timestamp", row.get("sort_timestamp")))
        self.review_count += 1
        self.category_counts[category] = self.category_counts.get(category, 0) + 1

        if timestamp is not None:
            self.first_timestamp = (
                timestamp
                if self.first_timestamp is None
                else min(self.first_timestamp, timestamp)
            )
            self.last_timestamp = (
                timestamp
                if self.last_timestamp is None
                else max(self.last_timestamp, timestamp)
            )

        text = row.get("text") or ""
        if text:
            self.text_chars += len(text)
            self.text_reviews += 1

        if row.get("verified_purchase") is True:
            self.verified_count += 1

        rating = row.get("rating")
        if isinstance(rating, int | float):
            self.rating_sum += float(rating)
            self.rating_count += 1

    @property
    def category_count(self) -> int:
        return len(self.category_counts)

    @property
    def history_days(self) -> float:
        if self.first_timestamp is None or self.last_timestamp is None:
            return 0.0
        return max(0.0, (self.last_timestamp - self.first_timestamp) / 86_400_000)

    @property
    def verified_share(self) -> float:
        if self.review_count == 0:
            return 0.0
        return self.verified_count / self.review_count

    @property
    def average_rating(self) -> float | None:
        if self.rating_count == 0:
            return None
        return self.rating_sum / self.rating_count

    def to_record(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "review_count": self.review_count,
            "category_count": self.category_count,
            "categories": sorted(self.category_counts),
            "category_counts": dict(sorted(self.category_counts.items())),
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "first_date": timestamp_to_date(self.first_timestamp),
            "last_date": timestamp_to_date(self.last_timestamp),
            "history_days": round(self.history_days, 2),
            "history_years": round(self.history_days / 365.25, 2),
            "text_chars": self.text_chars,
            "text_reviews": self.text_reviews,
            "verified_share": round(self.verified_share, 4),
            "average_rating": (
                None if self.average_rating is None else round(self.average_rating, 3)
            ),
        }

    def to_state_record(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "review_count": self.review_count,
            "category_counts": dict(sorted(self.category_counts.items())),
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "text_chars": self.text_chars,
            "text_reviews": self.text_reviews,
            "verified_count": self.verified_count,
            "rating_sum": self.rating_sum,
            "rating_count": self.rating_count,
        }

    @classmethod
    def from_state_record(cls, row: dict[str, Any]) -> "UserStats":
        return cls(
            user_id=row["user_id"],
            review_count=int(row.get("review_count", 0)),
            category_counts=dict(row.get("category_counts", {})),
            first_timestamp=row.get("first_timestamp"),
            last_timestamp=row.get("last_timestamp"),
            text_chars=int(row.get("text_chars", 0)),
            text_reviews=int(row.get("text_reviews", 0)),
            verified_count=int(row.get("verified_count", 0)),
            rating_sum=float(row.get("rating_sum", 0.0)),
            rating_count=int(row.get("rating_count", 0)),
        )

    def merge(self, other: "UserStats") -> None:
        self.review_count += other.review_count
        for category, count in other.category_counts.items():
            self.category_counts[category] = self.category_counts.get(category, 0) + count

        if other.first_timestamp is not None:
            self.first_timestamp = (
                other.first_timestamp
                if self.first_timestamp is None
                else min(self.first_timestamp, other.first_timestamp)
            )
        if other.last_timestamp is not None:
            self.last_timestamp = (
                other.last_timestamp
                if self.last_timestamp is None
                else max(self.last_timestamp, other.last_timestamp)
            )

        self.text_chars += other.text_chars
        self.text_reviews += other.text_reviews
        self.verified_count += other.verified_count
        self.rating_sum += other.rating_sum
        self.rating_count += other.rating_count


def log(message: str) -> None:
    print(f"[amazon_reviews_2023_analysis] {message}", flush=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return int(float(value))


def parse_categories(value: str) -> list[str]:
    if value == "all":
        return CATEGORIES
    categories = [part.strip() for part in value.split(",") if part.strip()]
    unknown = sorted(set(categories) - set(CATEGORIES))
    if unknown:
        raise ValueError(f"Unknown Amazon Reviews 2023 categories: {', '.join(unknown)}")
    return categories


def normalize_timestamp(value: Any) -> int | None:
    if value is None:
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp < 0:
        return None
    # Amazon Reviews 2023 examples use millisecond timestamps. Convert seconds
    # defensively so all downstream span/date math uses milliseconds.
    if timestamp < 10_000_000_000:
        return timestamp * 1000
    return timestamp


def year_to_timestamp_ms(year: int | None, end: bool = False) -> int | None:
    if year is None:
        return None
    if end:
        dt = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        dt = datetime(year, 1, 1, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def timestamp_to_date(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date().isoformat()


def open_remote_gzip_jsonl(url: str) -> Iterator[dict[str, Any]]:
    try:
        with urllib.request.urlopen(url) as response:
            with gzip.GzipFile(fileobj=response) as gz:
                for raw_line in gz:
                    if raw_line.strip():
                        yield json.loads(raw_line)
    except urllib.error.URLError as err:
        raise RuntimeError(f"Failed to stream {url}: {err}") from err


def review_url(category: str) -> str:
    return REVIEW_URL_TEMPLATE.format(category=category)


def iter_filtered_reviews(
    category: str,
    start_timestamp: int | None,
    end_timestamp: int | None,
    max_reviews: int,
) -> Iterator[dict[str, Any]]:
    seen = 0
    kept = 0
    for row in open_remote_gzip_jsonl(review_url(category)):
        seen += 1
        timestamp = normalize_timestamp(row.get("timestamp", row.get("sort_timestamp")))
        if start_timestamp is not None and (
            timestamp is None or timestamp < start_timestamp
        ):
            continue
        if end_timestamp is not None and (timestamp is None or timestamp >= end_timestamp):
            continue

        yield row
        kept += 1
        if max_reviews and kept >= max_reviews:
            break
        if seen % 1_000_000 == 0:
            log(f"{category}: scanned {seen:,}; kept {kept:,}")


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * pct
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return values[lower]
    weight = pos - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def summarize_users(users: dict[str, UserStats]) -> dict[str, Any]:
    review_counts = [stats.review_count for stats in users.values()]
    category_counts = [stats.category_count for stats in users.values()]
    history_days = [stats.history_days for stats in users.values()]
    return {
        "unique_users": len(users),
        "review_count_percentiles": {
            "p50": percentile(review_counts, 0.50),
            "p75": percentile(review_counts, 0.75),
            "p90": percentile(review_counts, 0.90),
            "p95": percentile(review_counts, 0.95),
            "p99": percentile(review_counts, 0.99),
            "max": max(review_counts, default=0),
        },
        "category_count_percentiles": {
            "p50": percentile(category_counts, 0.50),
            "p75": percentile(category_counts, 0.75),
            "p90": percentile(category_counts, 0.90),
            "p95": percentile(category_counts, 0.95),
            "p99": percentile(category_counts, 0.99),
            "max": max(category_counts, default=0),
        },
        "history_days_percentiles": {
            "p50": percentile(history_days, 0.50),
            "p75": percentile(history_days, 0.75),
            "p90": percentile(history_days, 0.90),
            "p95": percentile(history_days, 0.95),
            "p99": percentile(history_days, 0.99),
            "max": max(history_days, default=0),
        },
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    ensure_dir(path.parent)
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_jsonl_gz(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    ensure_dir(path.parent)
    count = 0
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def iter_jsonl_or_gz(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def load_user_state(path: Path) -> dict[str, UserStats]:
    users: dict[str, UserStats] = {}
    for row in iter_jsonl_or_gz(path):
        stats = UserStats.from_state_record(row)
        existing = users.get(stats.user_id)
        if existing is None:
            users[stats.user_id] = stats
        else:
            existing.merge(stats)
    return users


def write_user_state(path: Path, users: dict[str, UserStats]) -> int:
    return write_jsonl_gz(
        path,
        (stats.to_state_record() for stats in sorted(users.values(), key=lambda item: item.user_id)),
    )


def apply_candidate_filters(users: dict[str, UserStats], args: argparse.Namespace) -> list[UserStats]:
    candidates = [
        stats
        for stats in users.values()
        if stats.review_count >= args.min_reviews
        and stats.category_count >= args.min_categories
        and stats.history_days >= args.min_history_days
        and stats.text_chars >= args.min_text_chars
        and stats.verified_share >= args.min_verified_share
    ]
    candidates.sort(
        key=lambda stats: (
            stats.review_count,
            stats.category_count,
            stats.history_days,
            stats.text_chars,
        ),
        reverse=True,
    )
    if args.top_n:
        candidates = candidates[: args.top_n]
    return candidates


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--categories",
        default="All_Beauty,Software,Office_Products",
        help="Comma-separated categories, or 'all'.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--max-reviews-per-category",
        type=parse_int,
        default=0,
        help="Maximum kept reviews per category after date filtering. Use 0 for all.",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="Only keep reviews from this UTC year onward.",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Only keep reviews through this UTC year, inclusive.",
    )
    parser.add_argument(
        "--min-reviews",
        type=parse_int,
        default=20,
        help="Minimum reviews for candidate user pool.",
    )
    parser.add_argument(
        "--min-categories",
        type=parse_int,
        default=2,
        help="Minimum categories for candidate user pool.",
    )
    parser.add_argument(
        "--min-history-days",
        type=parse_int,
        default=365,
        help="Minimum first-to-last review span for candidate user pool.",
    )
    parser.add_argument(
        "--min-text-chars",
        type=parse_int,
        default=2000,
        help="Minimum review text volume for candidate user pool.",
    )
    parser.add_argument(
        "--min-verified-share",
        type=float,
        default=0.0,
        help="Minimum fraction of reviews with verified_purchase=true.",
    )
    parser.add_argument(
        "--top-n",
        type=parse_int,
        default=1000,
        help="Maximum candidates to write, ranked by review/category/span/text signal.",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="Print supported category names and exit.",
    )
    parser.add_argument(
        "--write-user-state",
        action="store_true",
        help="Write all aggregated user stats to all_user_stats.jsonl.gz.",
    )
    parser.add_argument(
        "--user-state-output",
        type=Path,
        default=None,
        help="Optional path for --write-user-state output.",
    )
    parser.add_argument(
        "--load-user-state",
        type=Path,
        action="append",
        default=[],
        help="Load and merge an existing all_user_stats JSONL or JSONL.GZ file.",
    )
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Do not stream remote categories; only merge --load-user-state files.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)

    if args.list_categories:
        print("\n".join(CATEGORIES))
        return 0

    categories = parse_categories(args.categories)
    ensure_dir(args.output_dir)
    start_timestamp = year_to_timestamp_ms(args.start_year)
    end_timestamp = year_to_timestamp_ms(args.end_year, end=True)

    users: dict[str, UserStats] = {}
    loaded_state_paths = [str(path) for path in args.load_user_state]
    for state_path in args.load_user_state:
        log(f"Loading user state: {state_path}")
        loaded_users = load_user_state(state_path)
        for user_id, stats in loaded_users.items():
            existing = users.get(user_id)
            if existing is None:
                users[user_id] = stats
            else:
                existing.merge(stats)
        log(f"Loaded {len(loaded_users):,} users from {state_path}")

    category_summary: dict[str, dict[str, int]] = {}

    if args.merge_only and not args.load_user_state:
        raise RuntimeError("--merge-only requires at least one --load-user-state file.")

    for category in ([] if args.merge_only else categories):
        log(f"Streaming category: {category}")
        kept = 0
        missing_user_id = 0
        for row in iter_filtered_reviews(
            category=category,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            max_reviews=args.max_reviews_per_category,
        ):
            user_id = row.get("user_id")
            if not user_id:
                missing_user_id += 1
                continue
            users.setdefault(user_id, UserStats(user_id=user_id)).add(row, category)
            kept += 1
            if kept % 1_000_000 == 0:
                log(
                    f"{category}: aggregated {kept:,} kept reviews; "
                    f"{len(users):,} users across selected categories"
                )

        category_summary[category] = {
            "kept_reviews": kept,
            "missing_user_id": missing_user_id,
        }
        log(f"Finished {category}: kept {kept:,} reviews")

    candidates = apply_candidate_filters(users, args)

    summary = {
        "dataset": "amazon_reviews_2023",
        "categories": categories,
        "date_filter": {
            "start_year": args.start_year,
            "end_year": args.end_year,
        },
        "max_reviews_per_category": args.max_reviews_per_category,
        "loaded_user_state_files": loaded_state_paths,
        "merge_only": args.merge_only,
        "thresholds": {
            "min_reviews": args.min_reviews,
            "min_categories": args.min_categories,
            "min_history_days": args.min_history_days,
            "min_text_chars": args.min_text_chars,
            "min_verified_share": args.min_verified_share,
        },
        "category_summary": category_summary,
        "all_users_summary": summarize_users(users),
        "candidate_count": len(candidates),
        "candidate_summary": summarize_users({stats.user_id: stats for stats in candidates}),
    }

    summary_path = args.output_dir / "summary.json"
    candidates_path = args.output_dir / "candidate_users.jsonl"
    write_json(summary_path, summary)
    write_jsonl(candidates_path, (stats.to_record() for stats in candidates))
    if args.write_user_state:
        user_state_path = args.user_state_output or (args.output_dir / "all_user_stats.jsonl.gz")
        user_state_count = write_user_state(user_state_path, users)
        summary["user_state_file"] = str(user_state_path)
        summary["user_state_count"] = user_state_count
        write_json(summary_path, summary)
        log(f"Saved all-user state: {user_state_path}")

    log(f"Saved summary: {summary_path}")
    log(f"Saved candidate users: {candidates_path}")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        log(f"ERROR: {exc}")
        raise
