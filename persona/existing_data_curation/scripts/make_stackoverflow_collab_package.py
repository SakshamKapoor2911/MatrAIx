#!/usr/bin/env python3
"""Create a worker-facing package from Stack Overflow user posting histories.

The package contains rendered posting-profile tasks only. Raw user history
JSONL and any owner-side database remain local.
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

from persona.existing_data_curation.scripts.history_package_common import (  # noqa: E402
    build_cv_fold_texts,
    compact_text,
    filter_supported_dimensions,
    join_fold_texts,
    limit_fold_texts_for_profile,
    load_evidence_mapping,
    load_history_range,
    normalize_timestamp,
    require_positive,
    sorted_by_time,
    spread_across_time,
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
from persona.existing_data_curation.wiki_collab.core import (  # noqa: E402
    canonical_json,
    parse_range,
    sha256_file,
    sha256_text,
    write_json,
)


SOURCE = "stackoverflow_persona"
DEFAULT_EVIDENCE_MAPPING_PATH = (
    Path(__file__).resolve().parent.parent
    / "configs"
    / "stackoverflow_evidence_mapping.json"
)


def _post_timestamp(post: dict[str, Any]) -> int | None:
    return normalize_timestamp(post.get("timestamp"))


def _post_date(post: dict[str, Any]) -> str:
    raw_date = post.get("date")
    if raw_date:
        return str(raw_date)
    return timestamp_to_date(post.get("timestamp")) or "unknown"


def _first_nonblank(post: dict[str, Any], keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = post.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _post_title(post: dict[str, Any]) -> str:
    return _first_nonblank(post, ("title",), "(untitled)")


def _post_title_evidence(post: dict[str, Any]) -> str:
    return _first_nonblank(post, ("title",))


def _post_text(post: dict[str, Any]) -> str:
    return _first_nonblank(post, ("text", "body"))


def _post_type(post: dict[str, Any]) -> str:
    value = str(post.get("post_type") or "").strip().lower()
    return value or "post"


def _post_tags(post: dict[str, Any]) -> list[str]:
    tags = post.get("tags")
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()]
    if isinstance(tags, str) and tags.strip():
        return [part for part in (piece.strip() for piece in tags.split(",")) if part]
    return []


def _post_accepted(post: dict[str, Any]) -> str:
    accepted = post.get("accepted")
    if _post_type(post) == "answer" and isinstance(accepted, bool):
        return "true" if accepted else "false"
    return "n/a"


def _has_post_evidence(post: dict[str, Any]) -> bool:
    return bool(_post_title_evidence(post).strip() or _post_text(post).strip())


def _post_objects(raw_posts: list[Any], *, user_id: str) -> list[dict[str, Any]]:
    posts = []
    for idx, post in enumerate(raw_posts):
        if not isinstance(post, dict):
            raise ValueError(
                f"user {user_id}: bad post row {idx}: expected post object dict, "
                f"got {type(post).__name__}"
            )
        posts.append(dict(post))
    return posts


def _render_post(
    post: dict[str, Any],
    *,
    rendered_post_id: str,
    max_post_text_chars: int,
) -> str:
    tags = _post_tags(post)
    lines = [
        f"[{rendered_post_id}]",
        f"date: {_post_date(post)}",
        f"type: {_post_type(post)}",
        f"tags: {', '.join(tags) if tags else '(none)'}",
        f"title: {_post_title(post)}",
        f"score: {post['score'] if post.get('score') is not None else 'unknown'}",
        f"accepted: {_post_accepted(post)}",
        f"text: {compact_text(_post_text(post), max_post_text_chars)}",
    ]
    return "\n".join(lines)


def stackoverflow_input_payload(task: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable payload covered by input_sha256."""
    return {key: value for key, value in task.items() if key != "input_sha256"}


def build_task(
    row: dict[str, Any],
    *,
    global_idx: int,
    cv_folds: int,
    min_support_folds: int,
    max_posts_per_user: int,
    max_post_text_chars: int,
    max_profile_text_chars: int,
) -> dict[str, Any]:
    user_id = str(row.get("user_id") or "").strip()
    if not user_id:
        raise ValueError(f"global_idx {global_idx}: missing user_id")

    raw_posts = row.get("posts")
    if not isinstance(raw_posts, list):
        raise ValueError(f"user {user_id}: expected posts list")

    post_objects = _post_objects(raw_posts, user_id=user_id)
    usable_posts = [post for post in post_objects if _has_post_evidence(post)]
    if len(usable_posts) < 2:
        raise ValueError(
            f"user {user_id}: fewer than 2 usable posts with non-empty title or text "
            f"({len(usable_posts)} usable of {len(raw_posts)} raw posts)"
        )

    sorted_posts = sorted_by_time(usable_posts, _post_timestamp)
    selected_posts = spread_across_time(sorted_posts, max_posts_per_user)
    usable_post_count = len(selected_posts)
    effective_cv_folds = min(cv_folds, usable_post_count)
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

    rendered_posts = [
        (
            f"p{idx:04d}",
            _render_post(
                post,
                rendered_post_id=f"p{idx:04d}",
                max_post_text_chars=max_post_text_chars,
            ),
        )
        for idx, post in enumerate(selected_posts, start=1)
    ]
    cv_fold_texts = build_cv_fold_texts(
        rendered_posts, effective_cv_folds, id_field="post_ids"
    )
    cv_fold_texts = limit_fold_texts_for_profile(
        cv_fold_texts,
        max_profile_text_chars,
        effective_min_support=effective_min_support,
    )

    tags = sorted({tag for post in selected_posts for tag in _post_tags(post)})
    task = {
        "global_idx": global_idx,
        "task_id": f"{SOURCE}:{user_id}",
        "qid": f"so_user:{user_id}",
        "title": f"Stack Overflow user {user_id}",
        "source_url": f"stackexchange://stackoverflow/user/{user_id}",
        "profile_text": join_fold_texts(cv_fold_texts),
        "source": SOURCE,
        "user_id": user_id,
        "post_count": len(raw_posts),
        "selected_post_count": usable_post_count,
        "tags": tags,
        "cv_folds": cv_folds,
        "effective_cv_folds": effective_cv_folds,
        "min_support_folds": effective_min_support,
        "cv_fold_texts": cv_fold_texts,
    }
    task["input_sha256"] = sha256_text(canonical_json(stackoverflow_input_payload(task)))
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
    filtered = filter_supported_dimensions(dimensions, mapping)
    if not filtered:
        raise ValueError(
            "Stack Overflow-supported dimension filtering returned no dimensions"
        )
    return filtered


def write_stackoverflow_worker_readme(out_dir: Path) -> None:
    readme = """# MatrAIx Stack Overflow Attribution Assignment

You received a self-contained assignment package. Work inside this directory.
Requires Python 3.10+; no Python packages need to be installed.

Files:

- `assignment.json`: assignment metadata for this user range.
- `tasks.jsonl`: Stack Overflow user posting profiles to process.
- `dimensions.json`: persona dimensions and allowed values to fill.
- `package_manifest.json`: checksums for files that should not change.
- `run_assignment.sh`: the main entrypoint.
- `collab_kit/solver.py`: the starter code you may edit.
- `results.jsonl`: the file you send back after a passing run.

Each task represents one Stack Overflow user. The task `profile_text` is
rendered from the user's public posts: dates, types (question/answer), tags,
titles, scores, accepted status, and body text. Posts are split into CV
folds. The `cv_fold_texts` field lists each fold with its `fold_id`,
`post_ids`, and rendered `profile_text`; support evidence should come from
enough distinct folds for the task's `min_support_folds` setting.

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


def build_stackoverflow_collab_package(
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
    max_posts_per_user: int = 90,
    max_post_text_chars: int = 900,
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
    require_positive("max_posts_per_user", max_posts_per_user)
    require_positive("max_post_text_chars", max_post_text_chars)
    require_positive("max_profile_text_chars", max_profile_text_chars)

    prepare_out_dir(out_dir, force=force)
    histories = load_history_range(user_histories_path, range_start, range_end)
    tasks = [
        build_task(
            row,
            global_idx=global_idx,
            cv_folds=cv_folds,
            min_support_folds=min_support_folds,
            max_posts_per_user=max_posts_per_user,
            max_post_text_chars=max_post_text_chars,
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
    write_stackoverflow_worker_readme(out_dir)

    dimensions_scope = "all" if all_dimensions else "stackoverflow_supported"
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
        "max_posts_per_user": max_posts_per_user,
        "max_post_text_chars": max_post_text_chars,
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
    parser.add_argument("--max-posts-per-user", type=int, default=90)
    parser.add_argument("--max-post-text-chars", type=int, default=900)
    parser.add_argument("--max-profile-text-chars", type=int, default=70000)
    parser.add_argument("--all-dimensions", action="store_true")
    parser.add_argument("--evidence-mapping", type=Path, default=DEFAULT_EVIDENCE_MAPPING_PATH)
    parser.add_argument("--no-archive", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    range_start, range_end = parse_range(args.range_spec)
    summary = build_stackoverflow_collab_package(
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
        max_posts_per_user=args.max_posts_per_user,
        max_post_text_chars=args.max_post_text_chars,
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
