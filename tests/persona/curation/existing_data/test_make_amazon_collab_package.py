import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from persona.curation.existing_data.wiki_collab.core import canonical_json, sha256_text


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _review(
    review_id: str,
    timestamp: int,
    category: str,
    rating: int,
    title: str,
    text: str,
    *,
    verified: bool = True,
    helpful_vote: int = 0,
) -> dict:
    return {
        "review_id": review_id,
        "timestamp": timestamp,
        "category": category,
        "rating": rating,
        "title": title,
        "text": text,
        "verified_purchase": verified,
        "helpful_vote": helpful_vote,
    }


def _write_histories(path: Path) -> None:
    _write_jsonl(
        path,
        [
            {
                "user_id": "USER_A",
                "reviews": [
                    _review(
                        "a4",
                        1_704_000_000_000,
                        "Books",
                        4,
                        "Fourth book",
                        "I returned to this series for its careful footnotes.",
                        helpful_vote=4,
                    ),
                    _review(
                        "a1",
                        1_701_000_000_000,
                        "Books",
                        5,
                        "First book",
                        "I compare translations and keep detailed notes.",
                        helpful_vote=1,
                    ),
                    _review(
                        "a3",
                        1_703_000_000_000,
                        "Electronics",
                        3,
                        "Desk lamp",
                        "The dimmer helps with evening reading at my desk.",
                        helpful_vote=0,
                    ),
                    _review(
                        "a2",
                        1_702_000_000_000,
                        "Kitchen",
                        5,
                        "Scale",
                        "Accurate enough for recipe testing every weekend.",
                        verified=False,
                        helpful_vote=2,
                    ),
                ],
            },
            {
                "user_id": "USER_B",
                "reviews": [
                    _review(
                        "b2",
                        1_702_500_000_000,
                        "Video Games",
                        2,
                        "Late game",
                        "The controls felt sluggish after the tutorial.",
                    ),
                    _review(
                        "b1",
                        1_701_500_000_000,
                        "Video Games",
                        4,
                        "Early game",
                        "Great co-op puzzles for short sessions.",
                    ),
                ],
            },
        ],
    )


def _write_dimensions(path: Path) -> None:
    _write_json(
        path,
        {
            "schemaVersion": "2.0",
            "dimensions": [
                {
                    "id": "domain",
                    "label": "Domain",
                    "description": "Primary area of expertise.",
                    "category": "Expertise: Domains",
                    "values": ["Books", "Games"],
                },
                {
                    "id": "core_demo",
                    "label": "Core demographic",
                    "description": "Explicit demographic fact.",
                    "category": "Demographic: Core",
                    "values": ["Stated", "Unstated"],
                },
                {
                    "id": "external_dataset",
                    "label": "External dataset",
                    "description": "External benchmark linkage.",
                    "category": "External: Datasets",
                    "values": ["Known", "Unknown"],
                },
            ],
        },
    )


def _write_mapping(path: Path) -> None:
    _write_json(
        path,
        {
            "evidence_categories": [
                {
                    "id": "expertise",
                    "label": "Expertise",
                    "schema_categories": ["Expertise:*"],
                },
                {
                    "id": "explicit",
                    "label": "Explicit",
                    "schema_categories": ["Demographic:*"],
                },
            ],
            "skip_by_default_schema_categories": ["External:*"],
        },
    )


def _package_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    histories = tmp_path / "user_histories.jsonl"
    dimensions = tmp_path / "dimensions.json"
    mapping = tmp_path / "mapping.json"
    _write_histories(histories)
    _write_dimensions(dimensions)
    _write_mapping(mapping)
    return histories, dimensions, mapping


def _build_package(tmp_path: Path, **overrides):
    from persona.curation.existing_data.scripts.make_amazon_collab_package import (
        build_amazon_collab_package,
    )

    histories, dimensions, mapping = _package_inputs(tmp_path)
    kwargs = {
        "user_histories_path": histories,
        "dimensions_path": dimensions,
        "out_dir": tmp_path / "amazon_package",
        "assignment_id": "AMZ-A0001",
        "worker_id": "alice",
        "dataset_id": "amazon-test-v1",
        "dataset_sha256": "d" * 64,
        "range_start": 0,
        "range_end": 2,
        "evidence_mapping_path": mapping,
        "create_archive": True,
    }
    kwargs.update(overrides)
    return build_amazon_collab_package(**kwargs)


def test_build_package_from_synthetic_histories_writes_cv_tasks_and_archive(tmp_path: Path):
    summary = _build_package(tmp_path)
    out_dir = Path(summary["package_dir"])

    assert summary["task_count"] == 2
    assert summary["dimension_count"] == 2
    assert summary["archive_path"].endswith(".tar.gz")
    for rel in (
        "assignment.json",
        "tasks.jsonl",
        "dimensions.json",
        "README.md",
        "run_assignment.sh",
        "package_manifest.json",
        "collab_kit/solver.py",
        "collab_kit/sample/results.jsonl",
    ):
        assert (out_dir / rel).exists()

    assignment = json.loads((out_dir / "assignment.json").read_text(encoding="utf-8"))
    assert assignment["source"] == "amazon_reviews_2023"
    assert assignment["assignment_id"] == "AMZ-A0001"
    assert assignment["worker_id"] == "alice"
    assert assignment["dataset_id"] == "amazon-test-v1"
    assert assignment["dataset_sha256"] == "d" * 64
    assert assignment["range_start"] == 0
    assert assignment["range_end"] == 2
    assert assignment["cv_folds"] == 3
    assert assignment["min_support_folds"] == 2
    assert assignment["max_reviews_per_user"] == 90
    assert assignment["dimensions_scope"] == "amazon_supported"
    assert assignment["task_count"] == 2
    assert assignment["dimension_count"] == 2
    assert len(assignment["tasks_sha256"]) == 64
    assert len(assignment["dimensions_sha256"]) == 64
    assert assignment["return_file"] == "results.jsonl"

    packaged_dimensions = json.loads((out_dir / "dimensions.json").read_text(encoding="utf-8"))
    assert [dimension["id"] for dimension in packaged_dimensions] == ["domain", "core_demo"]

    readme = (out_dir / "README.md").read_text(encoding="utf-8")
    assert "Amazon reviewer profiles" in readme
    assert "Wikipedia person profiles" not in readme
    assert "`cv_fold_texts`" in readme
    assert "./run_assignment.sh --status" in readme
    assert "./run_assignment.sh --validate" in readme

    tasks = _read_jsonl(out_dir / "tasks.jsonl")
    assert [task["global_idx"] for task in tasks] == [0, 1]
    assert [task["task_id"] for task in tasks] == [
        "amazon_reviews_2023:USER_A",
        "amazon_reviews_2023:USER_B",
    ]
    assert [task["qid"] for task in tasks] == ["amazon_user:USER_A", "amazon_user:USER_B"]
    assert [task["title"] for task in tasks] == [
        "Amazon reviewer USER_A",
        "Amazon reviewer USER_B",
    ]

    user_a, user_b = tasks
    assert user_a["source"] == "amazon_reviews_2023"
    assert user_a["user_id"] == "USER_A"
    assert user_a["review_count"] == 4
    assert user_a["selected_review_count"] == 4
    assert user_a["categories"] == ["Books", "Electronics", "Kitchen"]
    assert user_a["cv_folds"] == 3
    assert user_a["effective_cv_folds"] == 3
    assert user_a["min_support_folds"] == 2
    assert len(user_a["input_sha256"]) == 64
    payload = dict(user_a)
    expected_sha = payload.pop("input_sha256")
    assert expected_sha == sha256_text(canonical_json(payload))

    assert "=== Fold 1/3 ===" in user_a["profile_text"]
    assert "=== Fold 2/3 ===" in user_a["profile_text"]
    assert "=== Fold 3/3 ===" in user_a["profile_text"]
    assert "[r0001]" in user_a["profile_text"]
    assert "date: 2023-" in user_a["profile_text"]
    assert "category: Books" in user_a["profile_text"]
    assert "rating: 5" in user_a["profile_text"]
    assert "title: First book" in user_a["profile_text"]
    assert "verified: False" in user_a["profile_text"]
    assert "helpful_vote: 2" in user_a["profile_text"]
    assert "I compare translations" in user_a["profile_text"]

    assert [fold["fold_id"] for fold in user_a["cv_fold_texts"]] == [1, 2, 3]
    assert [fold["review_ids"] for fold in user_a["cv_fold_texts"]] == [
        ["r0001", "r0004"],
        ["r0002"],
        ["r0003"],
    ]
    assert all("profile_text" in fold for fold in user_a["cv_fold_texts"])
    assert "=== Fold 1/3 ===" in user_a["cv_fold_texts"][0]["profile_text"]
    assert "[r0004]" in user_a["cv_fold_texts"][0]["profile_text"]

    assert user_b["user_id"] == "USER_B"
    assert user_b["review_count"] == 2
    assert user_b["selected_review_count"] == 2
    assert user_b["categories"] == ["Video Games"]
    assert user_b["effective_cv_folds"] == 2
    assert [fold["review_ids"] for fold in user_b["cv_fold_texts"]] == [["r0001"], ["r0002"]]
    assert "=== Fold 1/2 ===" in user_b["profile_text"]
    assert "=== Fold 2/2 ===" in user_b["profile_text"]

    with tarfile.open(summary["archive_path"], "r:gz") as tar:
        names = [member.name for member in tar.getmembers()]
    assert len(names) == len(set(names))
    top_levels = {name.split("/", 1)[0] for name in names}
    assert top_levels == {out_dir.name}
    for rel in (
        "assignment.json",
        "tasks.jsonl",
        "dimensions.json",
        "README.md",
        "run_assignment.sh",
        "package_manifest.json",
        "collab_kit/solver.py",
        "collab_kit/sample/results.jsonl",
    ):
        assert f"{out_dir.name}/{rel}" in names


def test_truncated_profile_text_limits_fold_texts_to_visible_evidence(tmp_path: Path):
    summary = _build_package(
        tmp_path,
        range_start=0,
        range_end=1,
        max_profile_text_chars=320,
        create_archive=False,
    )
    out_dir = Path(summary["package_dir"])
    task = _read_jsonl(out_dir / "tasks.jsonl")[0]

    stored_fold_texts = [
        fold["profile_text"] for fold in task["cv_fold_texts"] if fold["profile_text"]
    ]
    assert len(task["profile_text"]) <= 320
    assert task["profile_text"] == "\n\n".join(stored_fold_texts)
    assert len(stored_fold_texts) >= 2
    assert all(text in task["profile_text"] for text in stored_fold_texts)
    assert all(text.startswith("=== Fold ") for text in stored_fold_texts)

    hidden_tail_quote = "careful footnotes"
    assert hidden_tail_quote not in task["profile_text"]
    assert all(
        hidden_tail_quote not in fold["profile_text"] for fold in task["cv_fold_texts"]
    )


def test_truncated_profile_text_preserves_min_support_fold_texts(tmp_path: Path):
    summary = _build_package(
        tmp_path,
        range_start=0,
        range_end=1,
        cv_folds=3,
        min_support_folds=3,
        max_profile_text_chars=103,
        create_archive=False,
    )
    out_dir = Path(summary["package_dir"])
    task = _read_jsonl(out_dir / "tasks.jsonl")[0]

    stored_fold_texts = [
        fold["profile_text"] for fold in task["cv_fold_texts"] if fold["profile_text"]
    ]
    assert len(task["profile_text"]) <= 103
    assert len(stored_fold_texts) >= 3
    assert task["min_support_folds"] == 3


def test_too_tiny_profile_text_budget_fails_with_clear_value_error(tmp_path: Path):
    with pytest.raises(ValueError, match="at least 2 fold sections"):
        _build_package(
            tmp_path,
            range_start=0,
            range_end=1,
            max_profile_text_chars=10,
            create_archive=False,
        )


def test_profile_text_budget_below_min_support_folds_fails_clearly(tmp_path: Path):
    with pytest.raises(ValueError, match="at least 3 fold sections"):
        _build_package(
            tmp_path,
            range_start=0,
            range_end=1,
            cv_folds=3,
            min_support_folds=3,
            max_profile_text_chars=102,
            create_archive=False,
        )


def test_all_dimensions_includes_dimensions_skipped_by_default(tmp_path: Path):
    summary = _build_package(tmp_path, all_dimensions=True, create_archive=False)
    out_dir = Path(summary["package_dir"])

    packaged_dimensions = json.loads((out_dir / "dimensions.json").read_text(encoding="utf-8"))
    assert summary["dimension_count"] == 3
    assert [dimension["id"] for dimension in packaged_dimensions] == [
        "domain",
        "core_demo",
        "external_dataset",
    ]

    assignment = json.loads((out_dir / "assignment.json").read_text(encoding="utf-8"))
    assert assignment["dimensions_scope"] == "all"


def test_build_rejects_empty_range_before_creating_output_dir(tmp_path: Path):
    out_dir = tmp_path / "amazon_package"

    with pytest.raises(ValueError, match=r"range_start .* range_end"):
        _build_package(
            tmp_path,
            out_dir=out_dir,
            range_start=1,
            range_end=1,
            create_archive=False,
        )

    assert not out_dir.exists()


def test_build_rejects_min_support_folds_above_cv_folds_before_creating_output_dir(
    tmp_path: Path,
):
    out_dir = tmp_path / "amazon_package"

    with pytest.raises(ValueError, match="min_support_folds .* cv_folds"):
        _build_package(
            tmp_path,
            out_dir=out_dir,
            cv_folds=3,
            min_support_folds=4,
            create_archive=False,
        )

    assert not out_dir.exists()


def test_histories_with_fewer_than_two_usable_reviews_fail(tmp_path: Path):
    from persona.curation.existing_data.scripts.make_amazon_collab_package import (
        build_amazon_collab_package,
    )

    histories = tmp_path / "user_histories.jsonl"
    dimensions = tmp_path / "dimensions.json"
    mapping = tmp_path / "mapping.json"
    _write_jsonl(
        histories,
        [
            {
                "user_id": "USER_EMPTY",
                "reviews": [
                    {
                        "review_id": "empty-1",
                        "timestamp": 1_701_000_000_000,
                        "category": "Books",
                        "rating": 5,
                        "title": "   ",
                        "text": "",
                    },
                    {
                        "review_id": "empty-2",
                        "timestamp": 1_702_000_000_000,
                        "category": "Books",
                        "rating": 4,
                        "product_title": "",
                        "review_text": "   ",
                    },
                    {
                        "review_id": "usable-1",
                        "timestamp": 1_703_000_000_000,
                        "category": "Books",
                        "rating": 3,
                        "title": "",
                        "text": "One useful review is not enough for CV folds.",
                    },
                ],
            }
        ],
    )
    _write_dimensions(dimensions)
    _write_mapping(mapping)

    with pytest.raises(ValueError, match="fewer than 2 usable reviews"):
        build_amazon_collab_package(
            user_histories_path=histories,
            dimensions_path=dimensions,
            out_dir=tmp_path / "amazon_package",
            assignment_id="AMZ-A0002",
            worker_id="alice",
            dataset_id="amazon-test-v1",
            dataset_sha256="d" * 64,
            range_start=0,
            range_end=1,
            evidence_mapping_path=mapping,
            create_archive=False,
        )


def test_malformed_review_row_fails_with_clear_value_error(tmp_path: Path):
    from persona.curation.existing_data.scripts.make_amazon_collab_package import (
        build_amazon_collab_package,
    )

    histories = tmp_path / "user_histories.jsonl"
    dimensions = tmp_path / "dimensions.json"
    mapping = tmp_path / "mapping.json"
    _write_jsonl(
        histories,
        [
            {
                "user_id": "USER_BAD_REVIEW",
                "reviews": [
                    _review(
                        "good-1",
                        1_701_000_000_000,
                        "Books",
                        5,
                        "Useful first review",
                        "This row is a valid review object.",
                    ),
                    "not a review object",
                    _review(
                        "good-2",
                        1_702_000_000_000,
                        "Books",
                        4,
                        "Useful second review",
                        "This row is also a valid review object.",
                    ),
                ],
            }
        ],
    )
    _write_dimensions(dimensions)
    _write_mapping(mapping)

    with pytest.raises(ValueError, match="expected review object"):
        build_amazon_collab_package(
            user_histories_path=histories,
            dimensions_path=dimensions,
            out_dir=tmp_path / "amazon_package",
            assignment_id="AMZ-A0004",
            worker_id="alice",
            dataset_id="amazon-test-v1",
            dataset_sha256="d" * 64,
            range_start=0,
            range_end=1,
            evidence_mapping_path=mapping,
            create_archive=False,
        )


def test_alias_title_and_review_text_are_usable_when_primary_fields_are_whitespace(
    tmp_path: Path,
):
    from persona.curation.existing_data.scripts.make_amazon_collab_package import (
        build_amazon_collab_package,
    )

    histories = tmp_path / "user_histories.jsonl"
    dimensions = tmp_path / "dimensions.json"
    mapping = tmp_path / "mapping.json"
    _write_jsonl(
        histories,
        [
            {
                "user_id": "USER_ALIAS",
                "reviews": [
                    {
                        "review_id": "alias-1",
                        "timestamp": 1_701_000_000_000,
                        "category": "Books",
                        "rating": 5,
                        "title": "   ",
                        "product_title": "Alias product title one",
                        "text": "   ",
                        "review_text": "Alias review text one.",
                    },
                    {
                        "review_id": "alias-2",
                        "timestamp": 1_702_000_000_000,
                        "category": "Books",
                        "rating": 4,
                        "title": "\t",
                        "product_title": "Alias product title two",
                        "text": "\n",
                        "review_text": "Alias review text two.",
                    },
                ],
            }
        ],
    )
    _write_dimensions(dimensions)
    _write_mapping(mapping)

    summary = build_amazon_collab_package(
        user_histories_path=histories,
        dimensions_path=dimensions,
        out_dir=tmp_path / "amazon_package",
        assignment_id="AMZ-A0003",
        worker_id="alice",
        dataset_id="amazon-test-v1",
        dataset_sha256="d" * 64,
        range_start=0,
        range_end=1,
        evidence_mapping_path=mapping,
        create_archive=False,
    )

    tasks = _read_jsonl(Path(summary["package_dir"]) / "tasks.jsonl")
    assert len(tasks) == 1
    task = tasks[0]
    assert task["review_count"] == 2
    assert task["selected_review_count"] == 2
    assert task["effective_cv_folds"] == 2
    assert "title: Alias product title one" in task["profile_text"]
    assert "text: Alias review text one." in task["profile_text"]
    assert "title: Alias product title two" in task["profile_text"]
    assert "text: Alias review text two." in task["profile_text"]
    assert "title: (untitled)" not in task["profile_text"]


def test_packaged_mock_harness_run_is_conformant(tmp_path: Path):
    summary = _build_package(tmp_path, create_archive=False)
    out_dir = Path(summary["package_dir"])
    results = out_dir / "results.jsonl"

    proc = subprocess.run(
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
            "--model",
            "mock-model",
            "--jobs",
            "1",
        ],
        cwd=out_dir / "collab_kit",
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS conformance" in proc.stdout
    output_rows = _read_jsonl(results)
    assert [row["global_idx"] for row in output_rows] == [0, 1]
    assert all(len(row["fields"]) == 2 for row in output_rows)
