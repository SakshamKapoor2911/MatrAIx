import json
import sys
import types
from pathlib import Path


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_load_user_ids_accepts_markdown_and_preserves_first_seen_order(tmp_path: Path):
    from persona.curation.existing_data.scripts.export_hf_amazon_user_histories import (
        load_user_ids,
    )

    ids_path = tmp_path / "reviewers.md"
    ids_path.write_text(
        "\n".join(
            [
                "1. `AABCDEFGHIJKL`",
                "2. `AZZZZZZZZZZZZ`",
                "3. duplicate `AABCDEFGHIJKL`",
            ]
        ),
        encoding="utf-8",
    )

    assert load_user_ids(ids_path) == ["AABCDEFGHIJKL", "AZZZZZZZZZZZZ"]
    assert load_user_ids(ids_path, limit=1) == ["AABCDEFGHIJKL"]


def test_list_relevant_shards_filters_user_buckets_and_categories(monkeypatch):
    from persona.curation.existing_data.scripts.export_hf_amazon_user_histories import (
        list_relevant_shards,
    )

    fake_hf = types.SimpleNamespace(
        list_repo_files=lambda *_args, **_kwargs: [
            "amazon/modal_artifacts/reviews/bucket=aa/category=Books/part-000.parquet",
            "amazon/modal_artifacts/reviews/bucket=bb/category=Books/part-000.parquet",
            "amazon/modal_artifacts/reviews/bucket=aa/category=Video_Games/part-000.parquet",
            "amazon/modal_artifacts/reviews/bucket=aa/category=Books/not-parquet.jsonl",
            "other/prefix/bucket=aa/category=Books/part-000.parquet",
        ]
    )
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hf)

    assert list_relevant_shards(
        repo_id="example/repo",
        artifact_prefix="amazon/modal_artifacts/reviews",
        buckets={"aa"},
        categories={"Books"},
        token=None,
    ) == ["amazon/modal_artifacts/reviews/bucket=aa/category=Books/part-000.parquet"]


def test_write_histories_sorts_reviews_by_timestamp_and_keeps_requested_order(tmp_path: Path):
    from persona.curation.existing_data.scripts.export_hf_amazon_user_histories import (
        write_histories,
    )

    output = tmp_path / "user_histories.jsonl"
    written = write_histories(
        output,
        {
            "USER_B": [{"timestamp": 20, "review_id": "b2"}],
            "USER_A": [
                {"timestamp": 30, "review_id": "a3"},
                {"timestamp": 10, "review_id": "a1"},
            ],
        },
        ["USER_A", "USER_B", "USER_MISSING"],
    )

    rows = _read_jsonl(output)
    assert written == 2
    assert [row["user_id"] for row in rows] == ["USER_A", "USER_B"]
    assert [review["review_id"] for review in rows[0]["reviews"]] == ["a1", "a3"]
    assert rows[0]["review_count"] == 2
