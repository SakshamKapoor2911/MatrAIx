# Amazon Reviews 2023 CV Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build outbound Amazon Reviews 2023 collaboration packages where each reviewer is one task and the starter solver can validate dimensions across folds of that reviewer’s own reviews.

**Architecture:** Add a focused Amazon package builder beside the existing wiki package builder. Reuse the existing `collab_kit` output shape, but render reviewer histories into fold-labeled `profile_text` and include structured `cv_fold_texts` for robust starter-code cross-validation. Extend `collab_kit/solver.py` with an Amazon-only branch that runs attribution per fold and keeps only values supported by enough folds.

**Tech Stack:** Python stdlib, pytest, existing `personas.existing_data_curation` helpers, existing `wiki_collab/collab_kit`.

---

## File Structure

- Create `personas/existing_data_curation/scripts/make_amazon_collab_package.py`
  - Reads `user_histories.jsonl` or `.jsonl.gz`.
  - Selects requested user range.
  - Selects and folds reviews deterministically.
  - Writes `tasks.jsonl`, filtered `dimensions.json`, `assignment.json`, `README.md`, `collab_kit/`, and optional `.tar.gz`.
  - Reuses safe packaging helpers from `make_collab_package.py`.
- Modify `personas/existing_data_curation/wiki_collab/collab_kit/solver.py`
  - Keeps wiki behavior unchanged.
  - Adds Amazon prompt wording, fold extraction, fold-level attribution, and fold-vote merge.
- Create `tests/personas/existing_data_curation/test_make_amazon_collab_package.py`
  - Tests outbound package shape and archive contents.
  - Tests dimension filtering and `--all-dimensions`.
  - Tests end-to-end mock run on the produced package.
- Modify `tests/personas/existing_data_curation/test_collab_kit.py`
  - Adds unit tests for Amazon fold merging in `solver.py`.

## Task 1: Add Amazon Package Builder Tests

**Files:**
- Create: `tests/personas/existing_data_curation/test_make_amazon_collab_package.py`
- Read: `tests/personas/existing_data_curation/test_make_collab_package.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/personas/existing_data_curation/test_make_amazon_collab_package.py` with these tests:

```python
import json
import subprocess
import sys
import tarfile
from pathlib import Path

from personas.existing_data_curation.scripts.make_amazon_collab_package import (
    build_amazon_collab_package,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_histories(path: Path) -> None:
    rows = [
        {
            "source": "amazon_reviews_2023",
            "user_id": "USER_A",
            "review_count": 4,
            "categories": ["Books", "Electronics"],
            "first_timestamp": 1_577_836_800_000,
            "last_timestamp": 1_672_531_200_000,
            "reviews": [
                {
                    "category": "Books",
                    "timestamp": 1_577_836_800_000,
                    "date": "2020-01-01",
                    "rating": 5,
                    "title": "Great Python reference",
                    "text": "I use this Python book every week for data projects.",
                    "verified_purchase": True,
                    "helpful_vote": 3,
                },
                {
                    "category": "Electronics",
                    "timestamp": 1_609_459_200_000,
                    "date": "2021-01-01",
                    "rating": 4,
                    "title": "Good keyboard",
                    "text": "The keyboard is durable and helps with programming work.",
                    "verified_purchase": True,
                    "helpful_vote": 2,
                },
                {
                    "category": "Books",
                    "timestamp": 1_640_995_200_000,
                    "date": "2022-01-01",
                    "rating": 5,
                    "title": "Machine learning cookbook",
                    "text": "Useful recipes for machine learning experiments.",
                    "verified_purchase": False,
                    "helpful_vote": 1,
                },
                {
                    "category": "Books",
                    "timestamp": 1_672_531_200_000,
                    "date": "2023-01-01",
                    "rating": 3,
                    "title": "Too basic",
                    "text": "I wanted more advanced statistics examples.",
                    "verified_purchase": True,
                    "helpful_vote": 0,
                },
            ],
        },
        {
            "source": "amazon_reviews_2023",
            "user_id": "USER_B",
            "review_count": 2,
            "categories": ["Home_and_Kitchen"],
            "reviews": [
                {
                    "category": "Home_and_Kitchen",
                    "timestamp": 1_577_836_800_000,
                    "date": "2020-01-01",
                    "rating": 5,
                    "title": "Reliable pan",
                    "text": "This pan is practical and easy to clean.",
                    "verified_purchase": True,
                    "helpful_vote": 0,
                },
                {
                    "category": "Home_and_Kitchen",
                    "timestamp": 1_609_459_200_000,
                    "date": "2021-01-01",
                    "rating": 4,
                    "title": "Good organizer",
                    "text": "The organizer keeps small tools tidy.",
                    "verified_purchase": True,
                    "helpful_vote": 0,
                },
            ],
        },
    ]
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_dimensions(path: Path) -> None:
    payload = {
        "schemaVersion": "2.0",
        "dimensions": [
            {
                "id": "domain",
                "label": "Domain",
                "description": "A domain the person appears interested in.",
                "category": "Expertise: Domains",
                "values": ["Programming", "Cooking"],
            },
            {
                "id": "age",
                "label": "Age",
                "description": "Age bracket.",
                "category": "Demographic: Core",
                "values": ["18-24", "25-34"],
            },
            {
                "id": "external_dataset",
                "label": "External",
                "description": "External dataset marker.",
                "category": "External: Datasets",
                "values": ["Amazon"],
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_build_amazon_package_writes_folded_worker_files(tmp_path: Path):
    histories = tmp_path / "user_histories.jsonl"
    dimensions = tmp_path / "dimensions.json"
    out_dir = tmp_path / "package"
    _write_histories(histories)
    _write_dimensions(dimensions)

    summary = build_amazon_collab_package(
        user_histories_path=histories,
        dimensions_path=dimensions,
        out_dir=out_dir,
        assignment_id="AMZ001",
        worker_id="alice",
        dataset_id="amazon-test-v1",
        dataset_sha256="a" * 64,
        range_start=0,
        range_end=2,
        cv_folds=3,
        min_support_folds=2,
        max_reviews_per_user=4,
        max_review_text_chars=200,
        max_profile_text_chars=10_000,
        all_dimensions=False,
        create_archive=True,
        force=False,
    )

    assert summary["task_count"] == 2
    assert summary["dimension_count"] == 2
    assert summary["archive_path"].endswith(".tar.gz")
    assert (out_dir / "assignment.json").exists()
    assert (out_dir / "tasks.jsonl").exists()
    assert (out_dir / "dimensions.json").exists()
    assert (out_dir / "README.md").exists()
    assert (out_dir / "collab_kit" / "solver.py").exists()

    assignment = json.loads((out_dir / "assignment.json").read_text(encoding="utf-8"))
    assert assignment["source"] == "amazon_reviews_2023"
    assert assignment["cv_folds"] == 3
    assert assignment["min_support_folds"] == 2
    assert assignment["range_start"] == 0
    assert assignment["range_end"] == 2
    assert len(assignment["tasks_sha256"]) == 64
    assert len(assignment["dimensions_sha256"]) == 64

    tasks = _jsonl(out_dir / "tasks.jsonl")
    assert [task["global_idx"] for task in tasks] == [0, 1]
    assert tasks[0]["source"] == "amazon_reviews_2023"
    assert tasks[0]["task_id"] == "amazon_reviews_2023:USER_A"
    assert tasks[0]["qid"] == "amazon_user:USER_A"
    assert tasks[0]["title"] == "Amazon reviewer USER_A"
    assert tasks[0]["cv_folds"] == 3
    assert tasks[0]["effective_cv_folds"] == 3
    assert tasks[1]["effective_cv_folds"] == 2
    assert len(tasks[0]["cv_fold_texts"]) == 3
    assert "=== Fold 1/3 ===" in tasks[0]["profile_text"]
    assert "review_id: r0001" in tasks[0]["profile_text"]
    assert "I use this Python book" in tasks[0]["profile_text"]
    assert len(tasks[0]["input_sha256"]) == 64

    packaged_dimensions = json.loads((out_dir / "dimensions.json").read_text(encoding="utf-8"))
    assert [dim["id"] for dim in packaged_dimensions] == ["domain", "age"]

    with tarfile.open(summary["archive_path"], "r:gz") as tar:
        names = [member.name for member in tar.getmembers()]
    assert len(names) == len(set(names))
    assert "assignment.json" in names
    assert "tasks.jsonl" in names
    assert "dimensions.json" in names
    assert "collab_kit/solver.py" in names
    assert "collab_kit/sample/results.jsonl" in names


def test_build_amazon_package_all_dimensions_override(tmp_path: Path):
    histories = tmp_path / "user_histories.jsonl"
    dimensions = tmp_path / "dimensions.json"
    out_dir = tmp_path / "package"
    _write_histories(histories)
    _write_dimensions(dimensions)

    summary = build_amazon_collab_package(
        user_histories_path=histories,
        dimensions_path=dimensions,
        out_dir=out_dir,
        assignment_id="AMZ002",
        worker_id="bob",
        dataset_id="amazon-test-v1",
        dataset_sha256="b" * 64,
        range_start=0,
        range_end=1,
        cv_folds=3,
        min_support_folds=2,
        max_reviews_per_user=4,
        max_review_text_chars=200,
        max_profile_text_chars=10_000,
        all_dimensions=True,
        create_archive=False,
        force=False,
    )

    packaged_dimensions = json.loads((out_dir / "dimensions.json").read_text(encoding="utf-8"))
    assert summary["dimension_count"] == 3
    assert [dim["id"] for dim in packaged_dimensions] == ["domain", "age", "external_dataset"]


def test_packaged_amazon_mock_run_is_conformant(tmp_path: Path):
    histories = tmp_path / "user_histories.jsonl"
    dimensions = tmp_path / "dimensions.json"
    out_dir = tmp_path / "package"
    results = tmp_path / "results.jsonl"
    _write_histories(histories)
    _write_dimensions(dimensions)

    build_amazon_collab_package(
        user_histories_path=histories,
        dimensions_path=dimensions,
        out_dir=out_dir,
        assignment_id="AMZ003",
        worker_id="carol",
        dataset_id="amazon-test-v1",
        dataset_sha256="c" * 64,
        range_start=0,
        range_end=1,
        cv_folds=3,
        min_support_folds=2,
        max_reviews_per_user=4,
        max_review_text_chars=200,
        max_profile_text_chars=10_000,
        all_dimensions=False,
        create_archive=False,
        force=False,
    )

    run = subprocess.run(
        [
            sys.executable,
            str(out_dir / "collab_kit" / "harness.py"),
            "--tasks",
            str(out_dir / "tasks.jsonl"),
            "--dimensions",
            str(out_dir / "dimensions.json"),
            "--out",
            str(results),
            "--backend",
            "mock",
            "--jobs",
            "1",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS conformance" in run.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation/test_make_amazon_collab_package.py -q
```

Expected: FAIL during import with `ModuleNotFoundError` or `ImportError` for `make_amazon_collab_package`.

## Task 2: Implement Amazon Package Builder

**Files:**
- Create: `personas/existing_data_curation/scripts/make_amazon_collab_package.py`
- Reuse: `personas/existing_data_curation/scripts/make_collab_package.py`
- Reuse: `personas/existing_data_curation/scripts/infer_amazon_review_dimensions.py`

- [ ] **Step 1: Create the builder module**

Create `personas/existing_data_curation/scripts/make_amazon_collab_package.py` with these public functions and CLI:

```python
#!/usr/bin/env python3
"""Create a worker-facing Amazon Reviews 2023 attribution package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from personas.existing_data_curation.scripts.infer_amazon_review_dimensions import (  # noqa: E402
    DEFAULT_EVIDENCE_MAPPING_PATH,
    compact_text,
    filter_amazon_supported_dimensions,
    load_evidence_mapping,
    normalize_timestamp,
    timestamp_to_date,
)
from personas.existing_data_curation.scripts.make_collab_package import (  # noqa: E402
    DEFAULT_DIMENSIONS,
    build_archive,
    copy_collab_kit,
    load_dimensions,
    prepare_out_dir,
    write_jsonl,
    write_worker_readme,
)
from personas.existing_data_curation.wiki_collab.core import (  # noqa: E402
    canonical_json,
    load_jsonl,
    sha256_file,
    sha256_text,
    write_json,
)


def select_reviews(reviews: list[dict[str, Any]], max_reviews: int) -> list[dict[str, Any]]:
    sorted_reviews = sorted(reviews, key=lambda row: normalize_timestamp(row.get("timestamp")) or 0)
    usable = [row for row in sorted_reviews if str(row.get("text") or row.get("title") or "").strip()]
    if max_reviews <= 0 or len(usable) <= max_reviews:
        return usable
    if max_reviews == 1:
        return [usable[-1]]
    last = len(usable) - 1
    indices = sorted({round(i * last / (max_reviews - 1)) for i in range(max_reviews)})
    return [usable[idx] for idx in indices]


def assign_review_folds(
    reviews: list[dict[str, Any]],
    requested_folds: int,
) -> tuple[list[list[dict[str, Any]]], int]:
    if requested_folds < 2:
        raise ValueError("--cv-folds must be at least 2")
    effective_folds = min(requested_folds, len(reviews))
    if effective_folds < 2:
        raise ValueError("Amazon CV packaging requires at least two usable reviews per user")
    folds: list[list[dict[str, Any]]] = [[] for _ in range(effective_folds)]
    for idx, review in enumerate(reviews):
        folds[idx % effective_folds].append(review)
    return folds, effective_folds


def review_to_text(review: dict[str, Any], review_id: str, fold_idx: int, max_review_text_chars: int) -> str:
    date = review.get("date") or timestamp_to_date(review.get("timestamp")) or ""
    text = compact_text(review.get("text"), max_review_text_chars)
    title = compact_text(review.get("title"), 180)
    return "\n".join(
        [
            f"review_id: {review_id}",
            f"fold: {fold_idx}",
            f"date: {date}",
            f"category: {review.get('category') or ''}",
            f"rating: {review.get('rating') if review.get('rating') is not None else ''}",
            f"verified_purchase: {review.get('verified_purchase')}",
            f"helpful_vote: {review.get('helpful_vote', review.get('helpful_votes', ''))}",
            f"title: {title}",
            f"text: {text}",
        ]
    )


def render_fold_texts(
    folds: list[list[dict[str, Any]]],
    *,
    max_review_text_chars: int,
    max_profile_text_chars: int,
) -> tuple[list[dict[str, Any]], str]:
    fold_texts: list[dict[str, Any]] = []
    review_counter = 1
    for fold_index, fold_reviews in enumerate(folds, start=1):
        review_blocks = []
        review_ids = []
        for review in fold_reviews:
            review_id = f"r{review_counter:04d}"
            review_counter += 1
            review_ids.append(review_id)
            review_blocks.append(review_to_text(review, review_id, fold_index, max_review_text_chars))
        text = "\n\n".join([f"=== Fold {fold_index}/{len(folds)} ===", *review_blocks])
        fold_texts.append({"fold_id": fold_index, "review_ids": review_ids, "profile_text": text})
    profile_text = "\n\n".join(fold["profile_text"] for fold in fold_texts)
    if len(profile_text) > max_profile_text_chars:
        profile_text = profile_text[: max_profile_text_chars - 1].rstrip() + "…"
    return fold_texts, profile_text


def amazon_input_payload(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "global_idx": int(task["global_idx"]),
        "task_id": task["task_id"],
        "qid": task["qid"],
        "title": task["title"],
        "source_url": task["source_url"],
        "source": task["source"],
        "user_id": task["user_id"],
        "review_count": task["review_count"],
        "categories": task["categories"],
        "cv_folds": task["cv_folds"],
        "effective_cv_folds": task["effective_cv_folds"],
        "min_support_folds": task["min_support_folds"],
        "profile_text": task["profile_text"],
        "cv_fold_texts": task["cv_fold_texts"],
    }


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
    user_id = str(row.get("user_id") or "")
    if not user_id:
        raise ValueError(f"history row {global_idx} missing user_id")
    selected_reviews = select_reviews(list(row.get("reviews") or []), max_reviews_per_user)
    folds, effective_folds = assign_review_folds(selected_reviews, cv_folds)
    effective_min_support = min(min_support_folds, effective_folds)
    if effective_min_support < 2:
        raise ValueError(f"user {user_id}: min_support_folds must be at least 2 after fold reduction")
    fold_texts, profile_text = render_fold_texts(
        folds,
        max_review_text_chars=max_review_text_chars,
        max_profile_text_chars=max_profile_text_chars,
    )
    task = {
        "global_idx": global_idx,
        "task_id": f"amazon_reviews_2023:{user_id}",
        "qid": f"amazon_user:{user_id}",
        "title": f"Amazon reviewer {user_id}",
        "source_url": "",
        "source": "amazon_reviews_2023",
        "user_id": user_id,
        "review_count": int(row.get("review_count") or len(row.get("reviews") or [])),
        "selected_review_count": len(selected_reviews),
        "categories": row.get("categories") or [],
        "cv_folds": cv_folds,
        "effective_cv_folds": effective_folds,
        "min_support_folds": effective_min_support,
        "profile_text": profile_text,
        "cv_fold_texts": fold_texts,
    }
    task["input_sha256"] = sha256_text(canonical_json(amazon_input_payload(task)))
    return task


def load_history_range(path: Path, range_start: int, range_end: int) -> list[tuple[int, dict[str, Any]]]:
    rows = list(load_jsonl(path))
    expected = range_end - range_start
    selected = rows[range_start:range_end]
    if len(selected) != expected:
        raise ValueError(f"range [{range_start}, {range_end}) expected {expected} rows, got {len(selected)}")
    return [(range_start + offset, row) for offset, row in enumerate(selected)]


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
    max_profile_text_chars: int = 70_000,
    all_dimensions: bool = False,
    evidence_mapping_path: Path = DEFAULT_EVIDENCE_MAPPING_PATH,
    create_archive: bool = True,
    force: bool = False,
) -> dict[str, Any]:
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
    dimensions_out_path.write_text(json.dumps(dimensions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    copy_collab_kit(out_dir)
    write_worker_readme(out_dir)
    assignment = {
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "source": "amazon_reviews_2023",
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_sha256,
        "range_start": range_start,
        "range_end": range_end,
        "task_count": len(tasks),
        "dimension_count": len(dimensions),
        "cv_folds": cv_folds,
        "min_support_folds": min_support_folds,
        "max_reviews_per_user": max_reviews_per_user,
        "dimensions_scope": "all" if all_dimensions else "amazon_supported",
        "tasks_file": "tasks.jsonl",
        "tasks_sha256": sha256_file(tasks_path),
        "dimensions_file": "dimensions.json",
        "dimensions_sha256": sha256_file(dimensions_out_path),
        "kit": "collab_kit",
        "return_file": "results.jsonl",
    }
    write_json(out_dir / "assignment.json", assignment)
    archive_path = build_archive(out_dir) if create_archive else None
    return {
        "package_dir": str(out_dir),
        "archive_path": str(archive_path) if archive_path else None,
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "task_count": len(tasks),
        "dimension_count": len(dimensions),
    }


def parse_range(raw: str) -> tuple[int, int]:
    start_s, end_s = raw.split(":", 1)
    start = int(start_s)
    end = int(end_s)
    if start < 0 or end <= start:
        raise ValueError(f"range must satisfy 0 <= start < end, got {raw!r}")
    return start, end


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-histories", type=Path, required=True)
    parser.add_argument("--dimensions", type=Path, default=DEFAULT_DIMENSIONS)
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
    parser.add_argument("--max-profile-text-chars", type=int, default=70_000)
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
```

- [ ] **Step 2: Run package tests**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation/test_make_amazon_collab_package.py -q
```

Expected: PASS.

- [ ] **Step 3: Run existing wiki package tests**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation/test_make_collab_package.py -q
```

Expected: PASS, proving wiki packaging still works.

## Task 3: Add Solver CV Merge Tests

**Files:**
- Modify: `tests/personas/existing_data_curation/test_collab_kit.py`
- Modify later: `personas/existing_data_curation/wiki_collab/collab_kit/solver.py`

- [ ] **Step 1: Add focused tests for fold merging**

Append these tests to `tests/personas/existing_data_curation/test_collab_kit.py`:

```python
import solver  # already imported near the top of this file


def test_solver_merges_amazon_fold_fields_by_min_support():
    dimensions = [
        {
            "id": "domain",
            "label": "Domain",
            "description": "Interest domain.",
            "category": "Expertise: Domains",
            "values": ["Programming", "Cooking"],
        },
        {
            "id": "decision_style",
            "label": "Decision style",
            "description": "How the reviewer evaluates products.",
            "category": "Risk & Decision",
            "values": ["Careful", "Impulsive"],
        },
    ]
    fold_outputs = [
        [
            {
                "field_id": "domain",
                "value": "Programming",
                "confidence": 0.8,
                "evidence": "r0001: Python book",
                "assignment_type": "summary_inference",
            },
            {
                "field_id": "decision_style",
                "value": "Careful",
                "confidence": 0.7,
                "evidence": "r0001: compared options",
                "assignment_type": "summary_inference",
            },
        ],
        [
            {
                "field_id": "domain",
                "value": "Programming",
                "confidence": 0.6,
                "evidence": "r0002: programming work",
                "assignment_type": "summary_inference",
            },
            {
                "field_id": "decision_style",
                "value": None,
                "confidence": 0.0,
                "evidence": "",
                "assignment_type": "unsupported",
            },
        ],
        [
            {
                "field_id": "domain",
                "value": "Cooking",
                "confidence": 0.9,
                "evidence": "r0003: recipe book",
                "assignment_type": "summary_inference",
            }
        ],
    ]

    merged = solver.merge_amazon_fold_fields(
        fold_outputs,
        dimensions,
        min_support_folds=2,
        fold_count=3,
    )

    by_id = {field["field_id"]: field for field in merged}
    assert by_id["domain"]["value"] == "Programming"
    assert by_id["domain"]["confidence"] == 0.467
    assert "r0001: Python book" in by_id["domain"]["evidence"]
    assert "r0002: programming work" in by_id["domain"]["evidence"]
    assert by_id["domain"]["assignment_type"] == "summary_inference"
    assert by_id["decision_style"]["value"] is None
    assert by_id["decision_style"]["assignment_type"] == "unsupported"


def test_solver_runs_amazon_attribute_once_per_fold(monkeypatch):
    dimensions = [
        {
            "id": "domain",
            "label": "Domain",
            "description": "Interest domain.",
            "category": "Expertise: Domains",
            "values": ["Programming", "Cooking"],
        }
    ]
    profile = {
        "source": "amazon_reviews_2023",
        "user_id": "USER_A",
        "min_support_folds": 2,
        "cv_fold_texts": [
            {"fold_id": 1, "profile_text": "=== Fold 1/3 ===\nreview_id: r0001\ntext: Python book"},
            {"fold_id": 2, "profile_text": "=== Fold 2/3 ===\nreview_id: r0002\ntext: programming keyboard"},
            {"fold_id": 3, "profile_text": "=== Fold 3/3 ===\nreview_id: r0003\ntext: recipe book"},
        ],
        "profile_text": "full text",
    }
    calls = []

    def fake_single_pass(profile_arg, dimensions_arg, *, backend, model, effort):
        calls.append(profile_arg["profile_text"])
        if "recipe" in profile_arg["profile_text"]:
            value = "Cooking"
        else:
            value = "Programming"
        return [
            {
                "field_id": "domain",
                "value": value,
                "confidence": 0.75,
                "evidence": profile_arg["profile_text"].splitlines()[-1],
                "assignment_type": "summary_inference",
            }
        ]

    monkeypatch.setattr(solver, "_attribute_single_pass", fake_single_pass)

    fields = solver.attribute(
        profile,
        dimensions,
        backend="external-command",
        model="fake-model",
        effort="high",
    )

    assert len(calls) == 3
    assert fields[0]["field_id"] == "domain"
    assert fields[0]["value"] == "Programming"
    assert fields[0]["confidence"] == 0.5
```

- [ ] **Step 2: Run solver tests to verify they fail**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation/test_collab_kit.py::test_solver_merges_amazon_fold_fields_by_min_support tests/personas/existing_data_curation/test_collab_kit.py::test_solver_runs_amazon_attribute_once_per_fold -q
```

Expected: FAIL because `merge_amazon_fold_fields` and `_attribute_single_pass` do not exist yet.

## Task 4: Implement Amazon CV Solver Path

**Files:**
- Modify: `personas/existing_data_curation/wiki_collab/collab_kit/solver.py`

- [ ] **Step 1: Refactor single-pass attribution and add helpers**

Modify `solver.py` so the existing non-mock real backend path moves into `_attribute_single_pass`, and add these helpers:

```python
def _is_amazon_profile(profile: Profile) -> bool:
    return profile.get("source") == "amazon_reviews_2023"


def _fold_profiles(profile: Profile) -> list[Profile]:
    fold_texts = profile.get("cv_fold_texts")
    if isinstance(fold_texts, list) and fold_texts:
        folds = []
        for item in fold_texts:
            if not isinstance(item, dict):
                continue
            text = str(item.get("profile_text") or "").strip()
            if not text:
                continue
            fold_profile = dict(profile)
            fold_profile["profile_text"] = text
            fold_profile["cv_fold_id"] = item.get("fold_id")
            folds.append(fold_profile)
        if folds:
            return folds
    return [profile]


def _unsupported(dim: Dimension) -> Field:
    return {
        "field_id": str(dim["id"]),
        "value": None,
        "confidence": 0.0,
        "evidence": "",
        "assignment_type": "unsupported",
    }


def _attribute_single_pass(
    profile: Profile,
    dimensions: list[Dimension],
    *,
    backend: str,
    model: str | None,
    effort: str,
) -> list[Field]:
    _ensure_default_command(backend)
    from backends import create_backend

    prompt = build_prompt(profile, dimensions)
    out = create_backend(backend, model, effort).run(prompt, profile)
    return list(out.fields)
```

Update `build_prompt` to choose source-aware opening text:

```python
source_line = (
    "You are extracting persona-attribution fields from Amazon review evidence for one reviewer."
    if profile.get("source") == "amazon_reviews_2023"
    else "You are extracting persona-attribution fields from a Wikipedia-derived profile."
)
lines = [
    source_line,
    "",
    "Return ONLY JSON with this shape (no markdown, no commentary):",
]
```

Also add one Amazon-specific rule inside `build_prompt`:

```python
if profile.get("source") == "amazon_reviews_2023":
    lines.extend(
        [
            "- For Amazon reviews, evidence must be copied from review title/text in the supplied fold.",
            "- Do not infer demographics, health, identity, family status, politics, religion, or occupation unless directly stated in the review text.",
        ]
    )
```

- [ ] **Step 2: Add fold merge implementation**

Add `merge_amazon_fold_fields`:

```python
def merge_amazon_fold_fields(
    fold_outputs: list[list[Field]],
    dimensions: list[Dimension],
    *,
    min_support_folds: int,
    fold_count: int,
) -> list[Field]:
    by_dim = {str(dim["id"]): dim for dim in dimensions}
    votes: dict[tuple[str, str], list[Field]] = {}
    for fields in fold_outputs:
        seen_in_fold: set[tuple[str, str]] = set()
        for field in fields:
            field_id = str(field.get("field_id") or "")
            value = field.get("value")
            if field_id not in by_dim or not isinstance(value, str):
                continue
            key = (field_id, value)
            if key in seen_in_fold:
                continue
            seen_in_fold.add(key)
            votes.setdefault(key, []).append(field)

    merged: list[Field] = []
    for dim in dimensions:
        field_id = str(dim["id"])
        candidates = [
            (value, supporting)
            for (candidate_id, value), supporting in votes.items()
            if candidate_id == field_id and len(supporting) >= min_support_folds
        ]
        if not candidates:
            merged.append(_unsupported(dim))
            continue
        value, supporting = max(
            candidates,
            key=lambda item: (
                len(item[1]),
                sum(float(field.get("confidence") or 0.0) for field in item[1]) / len(item[1]),
            ),
        )
        avg_confidence = sum(float(field.get("confidence") or 0.0) for field in supporting) / len(supporting)
        fold_support = len(supporting) / max(1, fold_count)
        evidence = " | ".join(
            str(field.get("evidence") or "").strip()
            for field in supporting
            if str(field.get("evidence") or "").strip()
        )
        assignment_types = [
            str(field.get("assignment_type"))
            for field in supporting
            if field.get("assignment_type") != "unsupported"
        ]
        merged.append(
            {
                "field_id": field_id,
                "value": value,
                "confidence": round(avg_confidence * fold_support, 3),
                "evidence": evidence[:1200],
                "assignment_type": assignment_types[0] if assignment_types else "summary_inference",
            }
        )
    return merged
```

- [ ] **Step 3: Route Amazon profiles through CV**

Update `attribute`:

```python
def attribute(
    profile: Profile,
    dimensions: list[Dimension],
    *,
    backend: str = "mock",
    model: str | None = None,
    effort: str = "high",
) -> list[Field]:
    if backend == "mock":
        return [_unsupported(d) for d in dimensions]

    if _is_amazon_profile(profile):
        fold_profiles = _fold_profiles(profile)
        min_support_folds = int(profile.get("min_support_folds") or min(2, len(fold_profiles)))
        min_support_folds = max(1, min(min_support_folds, len(fold_profiles)))
        fold_outputs = [
            _attribute_single_pass(
                fold_profile,
                dimensions,
                backend=backend,
                model=model,
                effort=effort,
            )
            for fold_profile in fold_profiles
        ]
        return merge_amazon_fold_fields(
            fold_outputs,
            dimensions,
            min_support_folds=min_support_folds,
            fold_count=len(fold_profiles),
        )

    return _attribute_single_pass(
        profile,
        dimensions,
        backend=backend,
        model=model,
        effort=effort,
    )
```

- [ ] **Step 4: Run solver tests**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation/test_collab_kit.py::test_solver_merges_amazon_fold_fields_by_min_support tests/personas/existing_data_curation/test_collab_kit.py::test_solver_runs_amazon_attribute_once_per_fold -q
```

Expected: PASS.

- [ ] **Step 5: Run the full collab kit test file**

Run:

```bash
python3 -m pytest tests/personas/existing_data_curation/test_collab_kit.py -q
```

Expected: PASS.

## Task 5: Full Verification

**Files:**
- No new implementation files.
- Verify: Amazon package tests, wiki package tests, collab kit tests, existing category protocol tests.

- [ ] **Step 1: Run targeted suite**

Run:

```bash
python3 -m pytest \
  tests/personas/existing_data_curation/test_make_amazon_collab_package.py \
  tests/personas/existing_data_curation/test_make_collab_package.py \
  tests/personas/existing_data_curation/test_collab_kit.py \
  tests/personas/existing_data_curation/test_run_and_merge_categories.py \
  tests/personas/existing_data_curation/test_generate_category_protocols.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Smoke the new CLI**

Create a tiny `/tmp` fixture:

```bash
python3 - <<'PY'
import json
from pathlib import Path

histories = [
    {
        "source": "amazon_reviews_2023",
        "user_id": "SMOKE_USER",
        "review_count": 2,
        "categories": ["Books"],
        "reviews": [
            {
                "category": "Books",
                "timestamp": 1577836800000,
                "date": "2020-01-01",
                "rating": 5,
                "title": "Useful Python book",
                "text": "I use this Python book for data projects.",
                "verified_purchase": True,
                "helpful_vote": 1,
            },
            {
                "category": "Books",
                "timestamp": 1609459200000,
                "date": "2021-01-01",
                "rating": 4,
                "title": "Good programming reference",
                "text": "Helpful programming examples and clear explanations.",
                "verified_purchase": True,
                "helpful_vote": 0,
            },
        ],
    }
]
dimensions = {
    "dimensions": [
        {
            "id": "domain",
            "label": "Domain",
            "description": "A domain the person appears interested in.",
            "category": "Expertise: Domains",
            "values": ["Programming", "Cooking"],
        }
    ]
}
with Path("/tmp/amazon_user_histories.jsonl").open("w", encoding="utf-8") as fh:
    for row in histories:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
Path("/tmp/amazon_dimensions.json").write_text(json.dumps(dimensions), encoding="utf-8")
PY
```

Then run:

```bash
python3 personas/existing_data_curation/scripts/make_amazon_collab_package.py \
  --user-histories /tmp/amazon_user_histories.jsonl \
  --dimensions /tmp/amazon_dimensions.json \
  --range 0:1 \
  --out-dir /tmp/amazon_cv_package \
  --assignment-id amazon-smoke-001 \
  --worker-id smoke \
  --dataset-id amazon_reviews_2023_smoke \
  --dataset-sha256 dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd \
  --force \
  --no-archive
```

Expected: JSON summary printed with `"task_count": 1` and package files written under `/tmp/amazon_cv_package`.

- [ ] **Step 3: Inspect git status**

Run:

```bash
git status --short
```

Expected: only intended implementation and test files are modified or created, plus pre-existing unrelated dirty files remain untouched.
