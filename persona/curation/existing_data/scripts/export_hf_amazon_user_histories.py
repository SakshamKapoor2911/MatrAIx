#!/usr/bin/env python3
"""Export Amazon user histories from user-bucketed Hugging Face artifacts.

This owner-side helper reads Parquet shards that were already bucketed by
`sha1(user_id)[:2]` and writes the JSONL shape consumed by the Amazon persona
inference and packaging scripts:

    {"user_id": "...", "review_count": 12, "reviews": [...]}

The script only downloads buckets needed for the requested reviewer IDs.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_REPO_ID = "MatrAIx/MatrAIx"
DEFAULT_ARTIFACT_PREFIX = (
    "amazon/modal_artifacts/"
    "amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000"
)
DEFAULT_OUTPUT_PATH = BASE_DIR / "raw" / "amazon_reviews_2023" / "user_histories.jsonl"

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

USER_ID_RE = re.compile(r"\bA[A-Z0-9]{10,}\b")


def log(message: str) -> None:
    print(f"[hf_amazon_histories] {message}", flush=True)


def user_bucket(user_id: str) -> str:
    return hashlib.sha1(user_id.encode("utf-8")).hexdigest()[:2]


def iter_jsonl_or_gz(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def load_user_ids(path: Path, limit: int = 0) -> list[str]:
    if path.suffix in {".jsonl", ".gz"}:
        ids = [
            str(row["user_id"])
            for row in iter_jsonl_or_gz(path)
            if row.get("user_id")
        ]
    else:
        ids = USER_ID_RE.findall(path.read_text(encoding="utf-8"))

    deduped = list(dict.fromkeys(ids))
    if limit:
        deduped = deduped[:limit]
    if not deduped:
        raise ValueError(f"No user IDs found in {path}")
    return deduped


def parse_categories(value: str) -> list[str]:
    if value == "all":
        return CATEGORIES
    parsed = [part.strip() for part in value.split(",") if part.strip()]
    unknown = sorted(set(parsed) - set(CATEGORIES))
    if unknown:
        raise ValueError(f"Unknown Amazon Reviews 2023 categories: {', '.join(unknown)}")
    return parsed


def list_relevant_shards(
    repo_id: str,
    artifact_prefix: str,
    buckets: set[str],
    categories: set[str],
    token: str | bool | None,
) -> list[str]:
    from huggingface_hub import list_repo_files

    files = list_repo_files(repo_id, repo_type="dataset", token=token)
    prefix = artifact_prefix.rstrip("/") + "/"
    wanted = []
    for filename in files:
        if not filename.startswith(prefix) or not filename.endswith(".parquet"):
            continue
        parts = filename[len(prefix) :].split("/")
        if len(parts) != 3:
            continue
        bucket_part, category_part, _name = parts
        if not bucket_part.startswith("bucket=") or not category_part.startswith(
            "category="
        ):
            continue
        bucket = bucket_part.split("=", 1)[1]
        category = category_part.split("=", 1)[1]
        if bucket in buckets and category in categories:
            wanted.append(filename)
    return sorted(wanted)


def read_shard_rows(
    repo_id: str,
    filename: str,
    token: str | bool | None,
) -> list[dict[str, Any]]:
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq

    local_path = hf_hub_download(
        repo_id=repo_id,
        repo_type="dataset",
        filename=filename,
        token=token,
    )
    return pq.read_table(local_path).to_pylist()


def normalize_review(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": row.get("source", "amazon_reviews_2023"),
        "category": row.get("category"),
        "user_id": row.get("user_id"),
        "parent_asin": row.get("parent_asin"),
        "asin": row.get("asin"),
        "timestamp": row.get("timestamp"),
        "date": row.get("date"),
        "rating": row.get("rating"),
        "title": row.get("title") or "",
        "text": row.get("text") or "",
        "verified_purchase": row.get("verified_purchase"),
        "helpful_vote": row.get("helpful_vote"),
    }


def write_histories(
    path: Path,
    histories: dict[str, list[dict[str, Any]]],
    user_ids: list[str],
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for user_id in user_ids:
            reviews = sorted(
                histories.get(user_id, []),
                key=lambda row: row.get("timestamp") or 0,
            )
            if not reviews:
                continue
            fh.write(
                json.dumps(
                    {
                        "user_id": user_id,
                        "review_count": len(reviews),
                        "reviews": reviews,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            count += 1
    return count


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-ids",
        type=Path,
        required=True,
        help="JSONL, Markdown, or text file containing Amazon reviewer IDs.",
    )
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--artifact-prefix", default=DEFAULT_ARTIFACT_PREFIX)
    parser.add_argument("--categories", default="all")
    parser.add_argument("--max-users", type=int, default=0, help="0 means all user IDs.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--token",
        default=None,
        help="Optional HF token. If omitted, huggingface_hub uses local auth.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    token: str | bool | None = args.token or None
    user_ids = load_user_ids(args.user_ids, limit=args.max_users)
    selected_user_ids = set(user_ids)
    buckets = {user_bucket(user_id) for user_id in user_ids}
    categories = set(parse_categories(args.categories))

    log(
        f"Loading {len(user_ids):,} users from {args.repo_id}/"
        f"{args.artifact_prefix} across {len(buckets)} buckets"
    )
    shards = list_relevant_shards(
        repo_id=args.repo_id,
        artifact_prefix=args.artifact_prefix,
        buckets=buckets,
        categories=categories,
        token=token,
    )
    if not shards:
        raise RuntimeError("No matching HF Parquet shards found for requested buckets/categories.")
    log(f"Found {len(shards):,} matching Parquet shards")

    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, filename in enumerate(shards, start=1):
        log(f"[{index:,}/{len(shards):,}] {filename}")
        for row in read_shard_rows(args.repo_id, filename, token=token):
            user_id = row.get("user_id")
            if user_id in selected_user_ids:
                histories[user_id].append(normalize_review(row))

    written = write_histories(args.output, histories, user_ids)
    missing = len(user_ids) - written
    log(f"Wrote {written:,} user histories to {args.output}")
    if missing:
        log(f"{missing:,} requested users had no matched reviews in selected categories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
