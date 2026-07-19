#!/usr/bin/env python3
"""Create a worker-facing package from Amazon Reviews 2023 user histories.

The package contains rendered review-profile tasks only. Raw user history JSONL
and any owner-side database remain local.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BASE_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from persona.curation.existing_data.scripts.infer_amazon_review_dimensions import (  # noqa: E402
    DEFAULT_EVIDENCE_MAPPING_PATH,
    filter_amazon_supported_dimensions,
    load_evidence_mapping,
    normalize_timestamp,
    timestamp_to_date,
)
from persona.curation.existing_data.scripts.make_collab_package import (  # noqa: E402
    build_archive,
    copy_collab_kit,
    copy_root_launcher,
    load_dimensions,
    prepare_out_dir,
    write_jsonl,
    write_package_manifest,
)
from persona.curation.existing_data.wiki_collab.core import (  # noqa: E402
    canonical_json,
    load_jsonl,
    parse_range,
    sha256_file,
    sha256_text,
    write_json,
)


SOURCE = "amazon_reviews_2023"
FOLD_TEXT_SEPARATOR = "\n\n"
FOLD_TRUNCATION_MARKER = "[fold truncated]"


def _require_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def _compact_text(value: Any, max_chars: int) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    if max_chars <= 16:
        return text[:max_chars]
    return text[: max_chars - 15].rstrip() + " ... [truncated]"


def _review_timestamp(review: dict[str, Any]) -> int | None:
    return normalize_timestamp(review.get("timestamp"))


def _review_date(review: dict[str, Any]) -> str:
    raw_date = review.get("date")
    if raw_date:
        return str(raw_date)
    return timestamp_to_date(review.get("timestamp")) or "unknown"


def _sorted_reviews(reviews: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = [(idx, dict(review)) for idx, review in enumerate(reviews)]
    indexed.sort(
        key=lambda item: (
            _review_timestamp(item[1]) is None,
            _review_timestamp(item[1]) or 0,
            item[0],
        )
    )
    return [review for _idx, review in indexed]


def _spread_across_time(
    reviews: list[dict[str, Any]], max_reviews_per_user: int
) -> list[dict[str, Any]]:
    if len(reviews) <= max_reviews_per_user:
        return reviews
    if max_reviews_per_user == 1:
        return [reviews[len(reviews) // 2]]
    last = len(reviews) - 1
    chosen_indexes = [
        round(pos * last / (max_reviews_per_user - 1))
        for pos in range(max_reviews_per_user)
    ]
    return [reviews[idx] for idx in chosen_indexes]


def _review_category(review: dict[str, Any]) -> str:
    return str(review.get("category") or review.get("source_category") or "Unknown")


def _first_nonblank(review: dict[str, Any], keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = review.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _review_title(review: dict[str, Any]) -> str:
    return _first_nonblank(review, ("title", "product_title"), "(untitled)")


def _review_title_evidence(review: dict[str, Any]) -> str:
    return _first_nonblank(review, ("title", "product_title"))


def _review_text(review: dict[str, Any]) -> str:
    return _first_nonblank(review, ("text", "review_text"))


def _has_review_evidence(review: dict[str, Any]) -> bool:
    return bool(_review_title_evidence(review).strip() or _review_text(review).strip())


def _review_objects(raw_reviews: list[Any], *, user_id: str) -> list[dict[str, Any]]:
    reviews = []
    for idx, review in enumerate(raw_reviews):
        if not isinstance(review, dict):
            raise ValueError(
                f"user {user_id}: bad review row {idx}: expected review object dict, "
                f"got {type(review).__name__}"
            )
        reviews.append(dict(review))
    return reviews


def _review_verified(review: dict[str, Any]) -> Any:
    if "verified_purchase" in review:
        return review.get("verified_purchase")
    if "verified" in review:
        return review.get("verified")
    return "unknown"


def _review_helpful_vote(review: dict[str, Any]) -> Any:
    if "helpful_vote" in review:
        return review.get("helpful_vote")
    if "helpful_votes" in review:
        return review.get("helpful_votes")
    return 0


def _render_review(
    review: dict[str, Any],
    *,
    rendered_review_id: str,
    max_review_text_chars: int,
) -> str:
    lines = [
        f"[{rendered_review_id}]",
        f"date: {_review_date(review)}",
        f"category: {_review_category(review)}",
        f"rating: {review.get('rating', 'unknown')}",
        f"title: {_review_title(review)}",
        f"verified: {_review_verified(review)}",
        f"helpful_vote: {_review_helpful_vote(review)}",
        f"text: {_compact_text(_review_text(review), max_review_text_chars)}",
    ]
    return "\n".join(lines)


def _render_fold(
    fold_id: int,
    effective_cv_folds: int,
    reviews: list[tuple[str, dict[str, Any]]],
    *,
    max_review_text_chars: int,
) -> str:
    lines = [f"=== Fold {fold_id}/{effective_cv_folds} ==="]
    for rendered_review_id, review in reviews:
        lines.append(
            _render_review(
                review,
                rendered_review_id=rendered_review_id,
                max_review_text_chars=max_review_text_chars,
            )
        )
    return "\n\n".join(lines)


def _profile_text(fold_texts: list[dict[str, Any]]) -> str:
    return FOLD_TEXT_SEPARATOR.join(
        str(fold["profile_text"]) for fold in fold_texts if fold["profile_text"]
    )


def _fold_heading(fold: dict[str, Any], effective_cv_folds: int) -> str:
    text = str(fold.get("profile_text") or "")
    if text:
        return text.splitlines()[0]
    return f"=== Fold {fold.get('fold_id', '?')}/{effective_cv_folds} ==="


def _minimum_fold_text(fold: dict[str, Any], effective_cv_folds: int) -> str:
    return f"{_fold_heading(fold, effective_cv_folds)}\n{FOLD_TRUNCATION_MARKER}"


def _minimum_join_chars(
    fold_texts: list[dict[str, Any]],
    *,
    effective_cv_folds: int,
) -> int:
    if not fold_texts:
        return 0
    return sum(
        len(_minimum_fold_text(fold, effective_cv_folds)) for fold in fold_texts
    ) + len(FOLD_TEXT_SEPARATOR) * (len(fold_texts) - 1)


def _truncate_fold_text(
    text: str,
    *,
    minimum_text: str,
    max_chars: int,
) -> str:
    if len(text) <= max_chars:
        return text

    marker = "\n" + FOLD_TRUNCATION_MARKER
    prefix_chars = max_chars - len(marker)
    heading = minimum_text.splitlines()[0]
    if prefix_chars <= len(heading):
        return minimum_text

    prefix = text[:prefix_chars].rstrip()
    if len(prefix) < len(heading) or not prefix.startswith(heading):
        prefix = heading
    return prefix + marker


def _limit_fold_texts_for_profile(
    fold_texts: list[dict[str, Any]],
    max_profile_text_chars: int,
    *,
    effective_min_support: int,
) -> list[dict[str, Any]]:
    if len(_profile_text(fold_texts)) <= max_profile_text_chars:
        return fold_texts

    effective_cv_folds = len(fold_texts)
    min_visible_folds = min(effective_min_support, effective_cv_folds)
    min_required_chars = _minimum_join_chars(
        fold_texts[:min_visible_folds],
        effective_cv_folds=effective_cv_folds,
    )
    if max_profile_text_chars < min_required_chars:
        raise ValueError(
            "max_profile_text_chars is too small to include at least "
            f"{min_visible_folds} fold "
            f"sections: got {max_profile_text_chars}, need at least "
            f"{min_required_chars}"
        )

    limited_folds: list[dict[str, Any]] = []
    used_chars = 0
    visible_folds = 0

    for idx, fold in enumerate(fold_texts):
        limited_fold = dict(fold)
        separator_chars = len(FOLD_TEXT_SEPARATOR) if visible_folds else 0
        remaining_chars = max_profile_text_chars - used_chars - separator_chars
        required_future_folds = max(0, min_visible_folds - (visible_folds + 1))
        future_folds = fold_texts[idx + 1 : idx + 1 + required_future_folds]
        future_reserve_chars = _minimum_join_chars(
            future_folds,
            effective_cv_folds=effective_cv_folds,
        )
        if future_folds:
            future_reserve_chars += len(FOLD_TEXT_SEPARATOR)

        available_chars = remaining_chars - future_reserve_chars
        minimum_text = _minimum_fold_text(fold, effective_cv_folds)
        if available_chars < len(minimum_text):
            limited_fold["profile_text"] = ""
            limited_folds.append(limited_fold)
            continue

        limited_fold["profile_text"] = _truncate_fold_text(
            str(fold["profile_text"]),
            minimum_text=minimum_text,
            max_chars=available_chars,
        )
        used_chars += separator_chars + len(limited_fold["profile_text"])
        visible_folds += 1
        limited_folds.append(limited_fold)

    return limited_folds


def amazon_input_payload(task: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable payload covered by input_sha256."""
    return {key: value for key, value in task.items() if key != "input_sha256"}


def build_task(
    row: dict[str, Any],
    *,
    global_idx: int,
    cv_folds: int,
    min_support_folds: int,
    max_reviews_per_user: int,
    max_review_text_chars: int,
    max_profile_text_chars: int,
) -> dict[str, Any]:
    user_id = str(row.get("user_id") or row.get("reviewer_id") or "").strip()
    if not user_id:
        raise ValueError(f"global_idx {global_idx}: missing user_id")

    raw_reviews = row.get("reviews")
    if not isinstance(raw_reviews, list):
        raise ValueError(f"user {user_id}: expected reviews list")

    review_objects = _review_objects(raw_reviews, user_id=user_id)
    usable_reviews = [review for review in review_objects if _has_review_evidence(review)]
    if len(usable_reviews) < 2:
        raise ValueError(
            f"user {user_id}: fewer than 2 usable reviews with non-empty title or text "
            f"({len(usable_reviews)} usable of {len(raw_reviews)} raw reviews)"
        )

    sorted_reviews = _sorted_reviews(usable_reviews)
    selected_reviews = _spread_across_time(sorted_reviews, max_reviews_per_user)
    usable_review_count = len(selected_reviews)
    effective_cv_folds = min(cv_folds, usable_review_count)
    if effective_cv_folds < 2:
        raise ValueError(
            f"user {user_id}: effective_cv_folds must be at least 2, got {effective_cv_folds}"
        )
    effective_min_support = min(min_support_folds, effective_cv_folds)
    if effective_min_support < 2:
        raise ValueError(
            f"user {user_id}: effective min_support_folds must be at least 2, got "
            f"{effective_min_support}"
        )

    rendered_reviews = [
        (f"r{idx:04d}", review) for idx, review in enumerate(selected_reviews, start=1)
    ]
    reviews_by_fold: list[list[tuple[str, dict[str, Any]]]] = [
        [] for _ in range(effective_cv_folds)
    ]
    for idx, rendered_review in enumerate(rendered_reviews):
        reviews_by_fold[idx % effective_cv_folds].append(rendered_review)

    cv_fold_texts = []
    for fold_idx, fold_reviews in enumerate(reviews_by_fold, start=1):
        cv_fold_texts.append(
            {
                "fold_id": fold_idx,
                "review_ids": [rendered_review_id for rendered_review_id, _ in fold_reviews],
                "profile_text": _render_fold(
                    fold_idx,
                    effective_cv_folds,
                    fold_reviews,
                    max_review_text_chars=max_review_text_chars,
                ),
            }
        )
    cv_fold_texts = _limit_fold_texts_for_profile(
        cv_fold_texts,
        max_profile_text_chars,
        effective_min_support=effective_min_support,
    )

    categories = sorted({_review_category(review) for review in selected_reviews})
    task = {
        "global_idx": global_idx,
        "task_id": f"{SOURCE}:{user_id}",
        "qid": f"amazon_user:{user_id}",
        "title": f"Amazon reviewer {user_id}",
        "source_url": f"amazon-reviews-2023://user/{user_id}",
        "profile_text": _profile_text(cv_fold_texts),
        "source": SOURCE,
        "user_id": user_id,
        "review_count": len(raw_reviews),
        "selected_review_count": usable_review_count,
        "categories": categories,
        "cv_folds": cv_folds,
        "effective_cv_folds": effective_cv_folds,
        "min_support_folds": effective_min_support,
        "cv_fold_texts": cv_fold_texts,
    }
    task["input_sha256"] = sha256_text(canonical_json(amazon_input_payload(task)))
    return task


def load_history_range(
    path: Path, range_start: int, range_end: int
) -> list[tuple[int, dict[str, Any]]]:
    expected_count = range_end - range_start
    rows: list[tuple[int, dict[str, Any]]] = []
    for offset, row in enumerate(load_jsonl(path)):
        if offset < range_start:
            continue
        if offset >= range_end:
            break
        rows.append((offset, row))
    if len(rows) != expected_count:
        raise ValueError(
            f"range [{range_start}, {range_end}) expected {expected_count} rows, got "
            f"{len(rows)}"
        )
    return rows


def package_dimensions(
    dimensions_path: Path,
    *,
    all_dimensions: bool,
    evidence_mapping_path: Path,
) -> list[dict[str, Any]]:
    dimensions = load_dimensions(dimensions_path)
    if all_dimensions:
        return dimensions
    mapping = load_evidence_mapping(evidence_mapping_path)
    filtered = filter_amazon_supported_dimensions(dimensions, mapping)
    if not filtered:
        raise ValueError("Amazon-supported dimension filtering returned no dimensions")
    return filtered


def write_amazon_worker_readme(out_dir: Path) -> None:
    readme = """# PersonaBench Amazon Reviewer Attribution Assignment

You received a self-contained assignment package. Work inside this directory.
Requires Python 3.10+; no Python packages need to be installed.

Files:

- `assignment.json`: assignment metadata for this reviewer range.
- `tasks.jsonl`: Amazon reviewer profiles to process.
- `dimensions.json`: persona dimensions and allowed values to fill.
- `package_manifest.json`: checksums for files that should not change.
- `run_assignment.sh`: the main entrypoint.
- `collab_kit/solver.py`: the starter code you may edit.
- `results.jsonl`: the file you send back after a passing run.

Each task represents one Amazon reviewer. The task `profile_text` is rendered
from the reviewer's review titles, text, ratings, categories, dates, verified
status, and helpful votes. Reviews are split into CV folds. The `cv_fold_texts`
field lists each fold with its `fold_id`, `review_ids`, and rendered
`profile_text`; support evidence should come from enough distinct folds for the
task's `min_support_folds` setting.

Quickstart:

```bash
./run_assignment.sh
./run_assignment.sh --status
./run_assignment.sh --validate
```

Use the menu to choose Codex or Claude Code, effort, parallelism, smoke test,
environment/CLI health check, real run, and validation. The runner verifies
checksums before every action, saves settings in `.wiki_collab_settings.yaml`,
and resumes from `results.jsonl.progress.jsonl` if quota runs out. You may
improve `solver.py` to get better results; keep the output contract unchanged
and return only `results.jsonl` unless the owner asks for logs.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")


def build_amazon_collab_package(
    *,
    user_histories_path: Path,
    dimensions_path: Path,
    out_dir: Path,
    assignment_id: str,
    worker_id: str,
    dataset_id: str,
    dataset_sha256: str,
    range_start: int,
    range_end: int,
    cv_folds: int = 3,
    min_support_folds: int = 2,
    max_reviews_per_user: int = 90,
    max_review_text_chars: int = 900,
    max_profile_text_chars: int = 70000,
    all_dimensions: bool = False,
    evidence_mapping_path: Path = DEFAULT_EVIDENCE_MAPPING_PATH,
    create_archive: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    if not 0 <= range_start < range_end:
        raise ValueError(
            "range_start must be >= 0 and less than range_end, got "
            f"range_start={range_start}, range_end={range_end}"
        )
    _require_positive("cv_folds", cv_folds)
    _require_positive("min_support_folds", min_support_folds)
    if min_support_folds > cv_folds:
        raise ValueError(
            "min_support_folds must be <= cv_folds, got "
            f"min_support_folds={min_support_folds}, cv_folds={cv_folds}"
        )
    _require_positive("max_reviews_per_user", max_reviews_per_user)
    _require_positive("max_review_text_chars", max_review_text_chars)
    _require_positive("max_profile_text_chars", max_profile_text_chars)

    prepare_out_dir(out_dir, force=force)
    histories = load_history_range(user_histories_path, range_start, range_end)
    tasks = [
        build_task(
            row,
            global_idx=global_idx,
            cv_folds=cv_folds,
            min_support_folds=min_support_folds,
            max_reviews_per_user=max_reviews_per_user,
            max_review_text_chars=max_review_text_chars,
            max_profile_text_chars=max_profile_text_chars,
        )
        for global_idx, row in histories
    ]
    dimensions = package_dimensions(
        dimensions_path,
        all_dimensions=all_dimensions,
        evidence_mapping_path=evidence_mapping_path,
    )

    tasks_path = out_dir / "tasks.jsonl"
    dimensions_out_path = out_dir / "dimensions.json"
    write_jsonl(tasks_path, tasks)
    dimensions_out_path.write_text(
        json.dumps(dimensions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    copy_collab_kit(out_dir)
    copy_root_launcher(out_dir)
    write_amazon_worker_readme(out_dir)

    dimensions_scope = "all" if all_dimensions else "amazon_supported"
    assignment = {
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "source": SOURCE,
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_sha256,
        "range_start": range_start,
        "range_end": range_end,
        "task_count": len(tasks),
        "dimension_count": len(dimensions),
        "cv_folds": cv_folds,
        "min_support_folds": min_support_folds,
        "min_support_folds_requested": min_support_folds,
        "effective_min_support_policy": "cap_each_task_to_effective_cv_folds",
        "max_reviews_per_user": max_reviews_per_user,
        "max_review_text_chars": max_review_text_chars,
        "max_profile_text_chars": max_profile_text_chars,
        "dimensions_scope": dimensions_scope,
        "categories": dimensions_scope,
        "tasks_file": "tasks.jsonl",
        "tasks_sha256": sha256_file(tasks_path),
        "dimensions_file": "dimensions.json",
        "dimensions_sha256": sha256_file(dimensions_out_path),
        "kit": "collab_kit",
        "return_file": "results.jsonl",
    }
    write_json(out_dir / "assignment.json", assignment)
    write_package_manifest(out_dir, assignment)

    archive_path = build_archive(out_dir) if create_archive else None
    return {
        "package_dir": str(out_dir),
        "archive_path": str(archive_path) if archive_path else None,
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "task_count": len(tasks),
        "dimension_count": len(dimensions),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-histories", type=Path, required=True)
    parser.add_argument("--dimensions", type=Path, required=True)
    parser.add_argument("--range", required=True, dest="range_spec")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--assignment-id", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--cv-folds", type=int, default=3)
    parser.add_argument("--min-support-folds", type=int, default=2)
    parser.add_argument("--max-reviews-per-user", type=int, default=90)
    parser.add_argument("--max-review-text-chars", type=int, default=900)
    parser.add_argument("--max-profile-text-chars", type=int, default=70000)
    parser.add_argument("--all-dimensions", action="store_true")
    parser.add_argument("--evidence-mapping", type=Path, default=DEFAULT_EVIDENCE_MAPPING_PATH)
    parser.add_argument("--no-archive", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    range_start, range_end = parse_range(args.range_spec)
    summary = build_amazon_collab_package(
        user_histories_path=args.user_histories,
        dimensions_path=args.dimensions,
        out_dir=args.out_dir,
        assignment_id=args.assignment_id,
        worker_id=args.worker_id,
        dataset_id=args.dataset_id,
        dataset_sha256=args.dataset_sha256,
        range_start=range_start,
        range_end=range_end,
        cv_folds=args.cv_folds,
        min_support_folds=args.min_support_folds,
        max_reviews_per_user=args.max_reviews_per_user,
        max_review_text_chars=args.max_review_text_chars,
        max_profile_text_chars=args.max_profile_text_chars,
        all_dimensions=args.all_dimensions,
        evidence_mapping_path=args.evidence_mapping,
        create_archive=not args.no_archive,
        force=args.force,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
