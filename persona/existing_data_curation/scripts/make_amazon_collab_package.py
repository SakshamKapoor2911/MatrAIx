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
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from persona.existing_data_curation.scripts.infer_amazon_review_dimensions import (  # noqa: E402
    DEFAULT_EVIDENCE_MAPPING_PATH,
    filter_amazon_supported_dimensions,
    load_evidence_mapping,
    normalize_timestamp,
    timestamp_to_date,
)
from persona.existing_data_curation.scripts.make_collab_package import (  # noqa: E402
    build_archive,
    copy_collab_kit,
    copy_root_launcher,
    load_dimensions,
    prepare_out_dir,
    write_jsonl,
    write_package_manifest,
)
from persona.existing_data_curation.scripts.history_package_common import (  # noqa: E402
    build_cv_fold_texts,
    compact_text,
    join_fold_texts,
    limit_fold_texts_for_profile,
    load_history_range,
    require_positive,
    sorted_by_time,
    spread_across_time,
)
from persona.existing_data_curation.wiki_collab.core import (  # noqa: E402
    canonical_json,
    parse_range,
    sha256_file,
    sha256_text,
    write_json,
)


SOURCE = "amazon_reviews_2023"


def _review_timestamp(review: dict[str, Any]) -> int | None:
    return normalize_timestamp(review.get("timestamp"))


def _review_date(review: dict[str, Any]) -> str:
    raw_date = review.get("date")
    if raw_date:
        return str(raw_date)
    return timestamp_to_date(review.get("timestamp")) or "unknown"


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
        f"text: {compact_text(_review_text(review), max_review_text_chars)}",
    ]
    return "\n".join(lines)


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

    sorted_reviews = sorted_by_time(usable_reviews, _review_timestamp)
    selected_reviews = spread_across_time(sorted_reviews, max_reviews_per_user)
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
        (
            f"r{idx:04d}",
            _render_review(
                review,
                rendered_review_id=f"r{idx:04d}",
                max_review_text_chars=max_review_text_chars,
            ),
        )
        for idx, review in enumerate(selected_reviews, start=1)
    ]
    cv_fold_texts = build_cv_fold_texts(
        rendered_reviews, effective_cv_folds, id_field="review_ids"
    )
    cv_fold_texts = limit_fold_texts_for_profile(
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
        "profile_text": join_fold_texts(cv_fold_texts),
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
    readme = """# MatrAIx Amazon Reviewer Attribution Assignment

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
    require_positive("cv_folds", cv_folds)
    require_positive("min_support_folds", min_support_folds)
    if min_support_folds > cv_folds:
        raise ValueError(
            "min_support_folds must be <= cv_folds, got "
            f"min_support_folds={min_support_folds}, cv_folds={cv_folds}"
        )
    require_positive("max_reviews_per_user", max_reviews_per_user)
    require_positive("max_review_text_chars", max_review_text_chars)
    require_positive("max_profile_text_chars", max_profile_text_chars)

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
