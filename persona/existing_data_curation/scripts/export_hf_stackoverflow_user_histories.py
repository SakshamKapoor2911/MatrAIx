#!/usr/bin/env python3
"""Export Stack Overflow user posting histories from reindexed HF artifacts.

This is the package-owner retrieval path for Stack Overflow persona curation.
It reads year-partitioned Parquet batches from a Hugging Face dataset artifact
and writes the normalized JSONL format consumed by
``make_stackoverflow_package.sh``:

    {"user_id": "...", "post_count": 42, "posts": [...]}

The artifact layout is ``StackExchange_Persona/<year>/*.parquet``. The dataset
is gated; request access on Hugging Face and ``huggingface-cli login`` first.

The parquet column names are an assumption pending verification against the
gated artifact (see the design doc). The alias tables below accept both a
per-post row shape (one post per row, grouped by owner id) and a per-user row
shape (a user id plus a nested posts list). If neither shape matches, the
exporter fails with the columns it actually saw so the fix is a one-line
alias addition.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import gzip
from html import unescape
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Iterator


DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "configs" / "stackexchange_persona.json"
)
DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "outputs"
    / "stackexchange_persona"
    / "user_histories.jsonl"
)


def load_default_source_config(config_path: Path = DEFAULT_CONFIG_PATH) -> tuple[str, str]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    source = payload.get("source") or {}
    repo_id = source.get("repo_id")
    artifact_prefix = source.get("artifact_prefix")
    if not repo_id or not artifact_prefix:
        raise ValueError(
            f"{config_path}: expected source.repo_id and source.artifact_prefix"
        )
    return str(repo_id), str(artifact_prefix)


DEFAULT_REPO_ID, DEFAULT_ARTIFACT_PREFIX = load_default_source_config()

USER_ID_ALIASES = ("user_id", "owner_user_id", "OwnerUserId", "account_id")
POST_LIST_ALIASES = ("posts", "history", "records")
POST_ID_ALIASES = ("post_id", "Id", "id")
POST_TYPE_ALIASES = ("post_type", "PostTypeId", "post_type_id")
TIMESTAMP_ALIASES = ("timestamp", "creation_date", "CreationDate")
TAGS_ALIASES = ("tags", "Tags")
TITLE_ALIASES = ("title", "Title")
TEXT_ALIASES = ("text", "body", "Body")
SCORE_ALIASES = ("score", "Score")
ACCEPTED_ALIASES = ("accepted", "is_accepted", "accepted_answer")

POST_TYPE_ID_MAP = {"1": "question", "2": "answer"}
TAG_STRING_RE = re.compile(r"<([^<>]+)>")
HTML_TAG_RE = re.compile(r"<[^>]+>")
NUMERIC_USER_ID_RE = re.compile(r"\b\d{1,12}\b")


def log(message: str) -> None:
    print(f"[hf_stackoverflow_histories] {message}", flush=True)


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
        ids = NUMERIC_USER_ID_RE.findall(path.read_text(encoding="utf-8"))

    deduped = list(dict.fromkeys(ids))
    if limit:
        deduped = deduped[:limit]
    if not deduped:
        raise ValueError(f"No user IDs found in {path}")
    return deduped


def _first_present(row: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for key in aliases:
        if key in row and row[key] is not None:
            return row[key]
    return None


def _parse_timestamp(value: Any) -> tuple[int | None, str | None]:
    """Return (epoch_seconds, iso_date) from epoch numbers or ISO strings."""
    if value is None:
        return None, None
    if isinstance(value, (int, float)):
        timestamp = int(value)
        if timestamp <= 0:
            return None, None
        if timestamp > 10_000_000_000:
            timestamp //= 1000
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
        return timestamp, date
    text = str(value).strip()
    if not text:
        return None, None
    if text.isdigit():
        return _parse_timestamp(int(text))
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None, None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp()), parsed.date().isoformat()


def _parse_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(tag).strip() for tag in value if str(tag).strip()]
    text = str(value).strip()
    if not text:
        return []
    if "<" in text:
        return [tag for tag in TAG_STRING_RE.findall(text) if tag.strip()]
    return [part for part in (piece.strip() for piece in text.split(",")) if part]


def _strip_html(value: str) -> str:
    if "<" not in value:
        return value
    return " ".join(unescape(HTML_TAG_RE.sub(" ", value)).split())


def _post_type_of(row: dict[str, Any]) -> str:
    raw = _first_present(row, POST_TYPE_ALIASES)
    if raw is None:
        return "post"
    text = str(raw).strip().lower()
    if text in POST_TYPE_ID_MAP:
        return POST_TYPE_ID_MAP[text]
    if text.isdigit():
        return "post"
    return text or "post"


def normalize_post(row: dict[str, Any]) -> dict[str, Any]:
    timestamp, date = _parse_timestamp(_first_present(row, TIMESTAMP_ALIASES))
    accepted = _first_present(row, ACCEPTED_ALIASES)
    return {
        "post_id": str(_first_present(row, POST_ID_ALIASES) or ""),
        "post_type": _post_type_of(row),
        "timestamp": timestamp,
        "date": date,
        "tags": _parse_tags(_first_present(row, TAGS_ALIASES)),
        "title": str(_first_present(row, TITLE_ALIASES) or ""),
        "text": _strip_html(str(_first_present(row, TEXT_ALIASES) or "")),
        "score": _first_present(row, SCORE_ALIASES),
        "accepted": accepted if isinstance(accepted, bool) else None,
        "site": "stackoverflow",
    }


def extract_user_rows(
    rows: list[dict[str, Any]], *, source_name: str
) -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """Yield (user_id, [normalized posts]) from either supported parquet shape."""
    if not rows:
        return
    sample = rows[0]
    user_key = next((key for key in USER_ID_ALIASES if key in sample), None)
    if user_key is None:
        raise ValueError(
            f"{source_name}: no user id column; saw columns {sorted(sample)}, "
            f"expected one of {list(USER_ID_ALIASES)}"
        )

    posts_key = next(
        (key for key in POST_LIST_ALIASES if isinstance(sample.get(key), list)), None
    )
    if posts_key is not None:
        for row in rows:
            user_id = str(row.get(user_key) or "").strip()
            if not user_id:
                continue
            posts = [
                normalize_post(post)
                for post in (row.get(posts_key) or [])
                if isinstance(post, dict)
            ]
            yield user_id, posts
        return

    if not any(key in sample for key in TEXT_ALIASES + TITLE_ALIASES):
        raise ValueError(
            f"{source_name}: rows are neither user-grouped (no list column among "
            f"{list(POST_LIST_ALIASES)}) nor post-shaped (no column among "
            f"{list(TEXT_ALIASES + TITLE_ALIASES)}); saw columns {sorted(sample)}"
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        user_id = str(row.get(user_key) or "").strip()
        if not user_id:
            continue
        grouped[user_id].append(normalize_post(row))
    yield from grouped.items()


def list_relevant_shards(
    *,
    repo_id: str,
    artifact_prefix: str,
    years: set[str] | None,
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
        if len(parts) != 2:
            continue
        year_part, _batch_name = parts
        if years and year_part not in years:
            continue
        wanted.append(filename)
    return sorted(wanted)


def read_shard_rows(
    repo_id: str, filename: str, token: str | bool | None
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


def _ordered_all_users(histories: dict[str, list[dict[str, Any]]]) -> list[str]:
    return sorted(
        histories,
        key=lambda user_id: (0, int(user_id)) if user_id.isdigit() else (1, user_id),
    )


def write_histories(
    path: Path,
    histories: dict[str, list[dict[str, Any]]],
    ordered_user_ids: list[str],
    *,
    min_posts: int,
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    required = max(1, min_posts)
    count = 0
    with opener(path, "wt", encoding="utf-8") as fh:
        for user_id in ordered_user_ids:
            posts = sorted(
                histories.get(user_id, []),
                key=lambda post: (post.get("timestamp") is None, post.get("timestamp") or 0),
            )
            if len(posts) < required:
                continue
            fh.write(
                json.dumps(
                    {
                        "user_id": user_id,
                        "post_count": len(posts),
                        "posts": posts,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            count += 1
    return count


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--user-ids",
        type=Path,
        help="JSONL, Markdown, or text file containing Stack Overflow user IDs.",
    )
    selection.add_argument(
        "--all-users",
        action="store_true",
        help="Export every user found in the selected shards.",
    )
    parser.add_argument(
        "--years",
        default="",
        help="Comma-separated year folders to read (default: all available).",
    )
    parser.add_argument(
        "--min-posts",
        type=int,
        default=0,
        help="Skip users with fewer posts than this (0 means any non-empty history).",
    )
    parser.add_argument(
        "--repo-id",
        default=os.environ.get("STACKEXCHANGE_PERSONA_REPO_ID", DEFAULT_REPO_ID),
    )
    parser.add_argument(
        "--artifact-prefix",
        default=os.environ.get(
            "STACKEXCHANGE_PERSONA_ARTIFACT_PREFIX", DEFAULT_ARTIFACT_PREFIX
        ),
    )
    parser.add_argument("--max-users", type=int, default=0, help="0 means all user IDs.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--token",
        default=None,
        help="Optional HF token. If omitted, huggingface_hub uses local login state.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    token: str | bool | None = args.token or None
    years = {part.strip() for part in args.years.split(",") if part.strip()} or None

    requested_user_ids: list[str] | None = None
    selected_user_ids: set[str] | None = None
    if args.user_ids:
        requested_user_ids = load_user_ids(args.user_ids, limit=args.max_users)
        selected_user_ids = set(requested_user_ids)
        log(f"Loading {len(requested_user_ids):,} users from {args.repo_id}/{args.artifact_prefix}")
    else:
        log(f"Loading all users from {args.repo_id}/{args.artifact_prefix}")

    shards = list_relevant_shards(
        repo_id=args.repo_id,
        artifact_prefix=args.artifact_prefix,
        years=years,
        token=token,
    )
    if not shards:
        raise RuntimeError("No matching HF Parquet shards found for requested years.")
    log(f"Found {len(shards):,} matching Parquet shards")

    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, filename in enumerate(shards, start=1):
        log(f"[{index:,}/{len(shards):,}] {filename}")
        rows = read_shard_rows(args.repo_id, filename, token)
        for user_id, posts in extract_user_rows(rows, source_name=filename):
            if selected_user_ids is not None and user_id not in selected_user_ids:
                continue
            histories[user_id].extend(posts)

    if requested_user_ids is None:
        min_posts_floor = max(1, args.min_posts)
        filtered_histories = {
            uid: posts
            for uid, posts in histories.items()
            if len(posts) >= min_posts_floor
        }
        ordered_user_ids = _ordered_all_users(filtered_histories)
        if args.max_users:
            ordered_user_ids = ordered_user_ids[: args.max_users]
        below_min = len(histories) - len(filtered_histories)
        written = write_histories(
            args.output, filtered_histories, ordered_user_ids, min_posts=args.min_posts
        )
        missing = len(ordered_user_ids) - written
        log(f"Wrote {written:,} user histories to {args.output}")
        if below_min:
            log(f"{below_min:,} users skipped: fewer than --min-posts ({min_posts_floor}) posts")
        if missing:
            log(f"{missing:,} users had no matching posts in selected shards")
    else:
        ordered_user_ids = requested_user_ids
        written = write_histories(
            args.output, histories, ordered_user_ids, min_posts=args.min_posts
        )
        missing = len(ordered_user_ids) - written
        no_posts = sum(1 for uid in ordered_user_ids if not histories.get(uid))
        below_min = missing - no_posts
        log(f"Wrote {written:,} user histories to {args.output}")
        if no_posts:
            log(f"{no_posts:,} requested users had no matching posts in selected shards")
        if below_min:
            log(f"{below_min:,} requested users filtered by --min-posts ({max(1, args.min_posts)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
