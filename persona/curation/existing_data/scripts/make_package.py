#!/usr/bin/env python3
"""Create a worker-facing package from a supported persona data source.

This is the owner-side unified entrypoint for collaborator packages. It keeps
the source-specific builders separate and only dispatches to the requested
package type.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BASE_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from persona.curation.existing_data.scripts.make_amazon_collab_package import (  # noqa: E402
    DEFAULT_EVIDENCE_MAPPING_PATH,
    build_amazon_collab_package,
)
from persona.curation.existing_data.scripts.make_collab_package import (  # noqa: E402
    DEFAULT_DIMENSIONS,
    build_collab_package,
    parse_categories,
    parse_range,
)


SOURCE_WIKI = "wiki"
SOURCE_AMAZON = "amazon"
SOURCE_AMAZON_REVIEWS_2023 = "amazon_reviews_2023"
SOURCE_CHOICES = (SOURCE_WIKI, SOURCE_AMAZON, SOURCE_AMAZON_REVIEWS_2023)


def normalize_source(source: str) -> str:
    if source == SOURCE_AMAZON_REVIEWS_2023:
        return SOURCE_AMAZON
    if source in {SOURCE_WIKI, SOURCE_AMAZON}:
        return source
    raise ValueError(f"unsupported package source: {source}")


def build_package(
    *,
    source: str,
    dimensions_path: Path,
    out_dir: Path,
    assignment_id: str,
    worker_id: str,
    dataset_id: str,
    dataset_sha256: str,
    range_start: int,
    range_end: int,
    db_path: Path | None = None,
    user_histories_path: Path | None = None,
    categories: list[str] | None = None,
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
    normalized_source = normalize_source(source)
    if normalized_source == SOURCE_WIKI:
        if db_path is None:
            raise ValueError("db_path is required for wiki packages")
        return build_collab_package(
            db_path=db_path,
            dimensions_path=dimensions_path,
            out_dir=out_dir,
            assignment_id=assignment_id,
            worker_id=worker_id,
            dataset_id=dataset_id,
            dataset_sha256=dataset_sha256,
            range_start=range_start,
            range_end=range_end,
            categories=categories,
            create_archive=create_archive,
            force=force,
        )

    if user_histories_path is None:
        raise ValueError("user_histories_path is required for Amazon packages")
    return build_amazon_collab_package(
        user_histories_path=user_histories_path,
        dimensions_path=dimensions_path,
        out_dir=out_dir,
        assignment_id=assignment_id,
        worker_id=worker_id,
        dataset_id=dataset_id,
        dataset_sha256=dataset_sha256,
        range_start=range_start,
        range_end=range_end,
        cv_folds=cv_folds,
        min_support_folds=min_support_folds,
        max_reviews_per_user=max_reviews_per_user,
        max_review_text_chars=max_review_text_chars,
        max_profile_text_chars=max_profile_text_chars,
        all_dimensions=all_dimensions,
        evidence_mapping_path=evidence_mapping_path,
        create_archive=create_archive,
        force=force,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=SOURCE_CHOICES, required=True)

    parser.add_argument("--dimensions", type=Path, default=DEFAULT_DIMENSIONS)
    parser.add_argument("--range", required=True, dest="range_spec")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--assignment-id", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--no-archive", action="store_true")
    parser.add_argument("--force", action="store_true")

    parser.add_argument("--db", type=Path, help="Wiki profile SQLite database.")
    parser.add_argument(
        "--categories",
        help="Wiki-only comma-separated category names or slugs. Omit for all dimensions.",
    )

    parser.add_argument("--user-histories", type=Path, help="Amazon user histories JSONL.")
    parser.add_argument("--cv-folds", type=int, default=3)
    parser.add_argument("--min-support-folds", type=int, default=2)
    parser.add_argument("--max-reviews-per-user", type=int, default=90)
    parser.add_argument("--max-review-text-chars", type=int, default=900)
    parser.add_argument("--max-profile-text-chars", type=int, default=70000)
    parser.add_argument("--all-dimensions", action="store_true")
    parser.add_argument("--evidence-mapping", type=Path, default=DEFAULT_EVIDENCE_MAPPING_PATH)

    args = parser.parse_args(argv)
    normalized_source = normalize_source(args.source)
    if normalized_source == SOURCE_WIKI and args.db is None:
        parser.error("--db is required when --source wiki")
    if normalized_source == SOURCE_AMAZON and args.user_histories is None:
        parser.error("--user-histories is required when --source amazon")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    range_start, range_end = parse_range(args.range_spec)
    summary = build_package(
        source=args.source,
        db_path=args.db,
        user_histories_path=args.user_histories,
        dimensions_path=args.dimensions,
        out_dir=args.out_dir,
        assignment_id=args.assignment_id,
        worker_id=args.worker_id,
        dataset_id=args.dataset_id,
        dataset_sha256=args.dataset_sha256,
        range_start=range_start,
        range_end=range_end,
        categories=parse_categories(args.categories),
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
