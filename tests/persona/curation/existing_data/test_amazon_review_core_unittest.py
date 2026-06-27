import importlib
import sys
import types
from argparse import Namespace

import pytest


class _ModalImage:
    @classmethod
    def debian_slim(cls, **_kwargs):
        return cls()

    def pip_install(self, *_args, **_kwargs):
        return self


class _ModalApp:
    def __init__(self, *_args, **_kwargs):
        pass

    def function(self, *_args, **_kwargs):
        def decorator(func):
            return func

        return decorator

    def local_entrypoint(self, *_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


class _ModalVolume:
    @classmethod
    def from_name(cls, *_args, **_kwargs):
        return cls()


class _ModalSecret:
    @classmethod
    def from_name(cls, *_args, **_kwargs):
        return cls()


@pytest.fixture(scope="module", autouse=True)
def modal_stub():
    sys.modules.setdefault(
        "modal",
        types.SimpleNamespace(
            Image=_ModalImage,
            App=_ModalApp,
            Volume=_ModalVolume,
            Secret=_ModalSecret,
        ),
    )


@pytest.fixture(scope="module")
def amazon_index_module(modal_stub):
    return importlib.import_module("persona.curation.existing_data.modal_amazon_user_index")


@pytest.fixture(scope="module")
def inference_module():
    return importlib.import_module(
        "persona.curation.existing_data.scripts.infer_amazon_review_dimensions"
    )


@pytest.fixture(scope="module")
def holdout_eval_module():
    return importlib.import_module(
        "persona.curation.existing_data.scripts.evaluate_amazon_persona_rating_holdout"
    )


def test_temporal_train_validation_split_keeps_earliest_construction_rows(
    amazon_index_module,
):
    reviews = [
        {"review_id": "late-2", "timestamp": 9000, "rating": 2},
        {"review_id": "early-1", "timestamp": 1000, "rating": 5},
        {"review_id": "late-1", "timestamp": 8000, "rating": 4},
        {"review_id": "early-2", "timestamp": 2000, "rating": 4},
        {"review_id": "mid-3", "timestamp": 7000, "rating": 5},
        {"review_id": "mid-1", "timestamp": 3000, "rating": 3},
        {"review_id": "mid-2", "timestamp": 4000, "rating": 2},
        {"review_id": "mid-4", "timestamp": 5000, "rating": 1},
        {"review_id": "mid-5", "timestamp": 6000, "rating": 5},
        {"review_id": "latest", "timestamp": 10000, "rating": 5},
    ]

    construction, validation, summary = amazon_index_module.temporal_train_validation_split(
        reviews,
        train_fraction=0.8,
    )

    assert [row["timestamp"] for row in construction] == [
        1000,
        2000,
        3000,
        4000,
        5000,
        6000,
        7000,
        8000,
    ]
    assert [row["timestamp"] for row in validation] == [9000, 10000]
    assert summary["method"] == "per_user_temporal"
    assert summary["construction_row_count"] == 8
    assert summary["validation_row_count"] == 2
    assert summary["construction_last_timestamp"] == 8000
    assert summary["validation_first_timestamp"] == 9000


def test_normalized_reviews_get_stable_ids_and_context_preserves_them(
    amazon_index_module,
    inference_module,
):
    raw_review = {
        "user_id": "user-123",
        "parent_asin": "PARENT1",
        "asin": "ASIN1",
        "timestamp": 1_700_000_000_000,
        "rating": 4,
        "title": "Useful little cable",
        "text": "Works well on my desk.",
        "verified_purchase": True,
        "helpful_vote": 2,
    }

    first = amazon_index_module.normalize_review(raw_review, "Electronics")
    second = amazon_index_module.normalize_review(dict(raw_review), "Electronics")

    assert first["review_id"] == second["review_id"]
    assert first["review_id"].isascii()
    assert first["review_id"].startswith("amzrev_")

    preserved = amazon_index_module.normalize_review(
        {**raw_review, "review_id": "existing-review-42"},
        "Electronics",
    )
    assert preserved["review_id"] == "existing-review-42"

    context = inference_module.context_rows_for_reviews([first], max_review_text_chars=200)
    assert context[0]["review_id"] == first["review_id"]


def test_hf_export_requests_and_backfills_stable_review_ids(
    amazon_index_module,
    monkeypatch,
):
    captured_column_sets = []
    hf_row = {
        "source": "amazon_reviews_2023",
        "category": "Books",
        "user_id": "u-hf",
        "user_bucket": "aa",
        "parent_asin": "P-HF",
        "asin": "A-HF",
        "timestamp": 1_700_000_000_000,
        "date": "2023-11-14",
        "rating": 5,
        "title": "Helpful reference",
        "text": "Kept this on my desk.",
        "verified_purchase": True,
        "helpful_vote": 0,
    }

    def fake_read_hf_parquet_rows(_repo_id, _path, revision, columns):
        captured_column_sets.append(list(columns))
        if "review_id" in columns:
            raise ValueError("No match for FieldRef.Name(review_id) in schema")
        yield dict(hf_row)

    monkeypatch.setattr(
        amazon_index_module,
        "read_hf_parquet_rows",
        fake_read_hf_parquet_rows,
    )

    result = amazon_index_module.export_user_histories_for_bucket_from_hf(
        bucket="aa",
        user_ids=["u-hf"],
        repo_files=["amazon/modal_artifacts/reviews/bucket=aa/category=Books/part-0.parquet"],
        path_prefix="amazon/modal_artifacts",
        review_prefix="reviews",
        filter_fulfillment_reviews=False,
    )

    assert len(captured_column_sets) == 2
    assert "review_id" in captured_column_sets[0]
    assert "review_id" not in captured_column_sets[1]
    review = result["histories"]["u-hf"][0]
    assert review["review_id"] == amazon_index_module.stable_review_id(
        hf_row,
        "Books",
        amazon_index_module.normalize_timestamp(hf_row["timestamp"]),
    )


def test_attach_product_metadata_sidecar_attaches_to_train_and_validation(
    inference_module,
):
    user_row = {
        "user_id": "u1",
        "reviews": [{"parent_asin": "P1", "category": "Books"}],
        "validation_reviews": [{"parent_asin": "P2", "category": "Video_Games"}],
    }
    metadata = {
        ("P1", "Books"): {
            "parent_asin": "P1",
            "source_category": "Books",
            "title": "Book One",
        },
        ("P2", ""): {
            "parent_asin": "P2",
            "source_category": "Video_Games",
            "title": "Game Two",
        },
    }

    result = inference_module.attach_product_metadata_sidecar(user_row, metadata)

    assert result["reviews"][0]["product_metadata"]["title"] == "Book One"
    assert result["validation_reviews"][0]["product_metadata"]["title"] == "Game Two"


def test_modal_inline_metadata_attachment_prefers_matching_category(
    amazon_index_module,
):
    metadata = {
        ("SHARED", "Books"): {
            "parent_asin": "SHARED",
            "source_category": "Books",
            "title": "Book Metadata",
        },
        ("SHARED", "Video_Games"): {
            "parent_asin": "SHARED",
            "source_category": "Video_Games",
            "title": "Game Metadata",
        },
    }
    reviews = [
        {"parent_asin": "SHARED", "category": "Books"},
        {"parent_asin": "SHARED", "category": "Video_Games"},
    ]

    amazon_index_module.attach_inline_product_metadata(reviews, metadata)

    assert reviews[0]["product_metadata"]["title"] == "Book Metadata"
    assert reviews[1]["product_metadata"]["title"] == "Game Metadata"


def test_review_corpus_stats_summarizes_rating_only_product_metadata(
    inference_module,
):
    reviews = [
        {
            "timestamp": 1000,
            "category": "Books",
            "rating": 5,
            "text": "",
            "product_metadata": {
                "title": "Python Patterns",
                "main_category": "Books",
                "categories_json": '["Books", "Programming"]',
            },
        },
        {
            "timestamp": 2000,
            "category": "Books",
            "rating": 2,
            "text": "Thin examples.",
            "product_metadata": {
                "title": "Sparse Guide",
                "main_category": "Books",
                "categories_json": '["Books", "Programming"]',
            },
        },
        {
            "timestamp": 3000,
            "category": "Electronics",
            "rating": 1,
            "text": "",
            "product_metadata": {
                "title": "USB Hub",
                "main_category": "Electronics",
                "categories_json": '[["Electronics", "Computer Accessories"]]',
            },
        },
        {
            "timestamp": 4000,
            "category": "Books",
            "rating": 5,
            "text": "",
            "product_metadata": {
                "title": "Python Patterns",
                "main_category": "Books",
                "categories_json": '["Books", "Programming"]',
            },
        },
    ]

    stats = inference_module.review_corpus_stats(reviews)

    assert stats["row_count"] == 4
    assert stats["text_review_count"] == 1
    assert stats["rating_count"] == 4
    assert stats["rating_only_count"] == 3
    assert stats["category_counts"] == {"Books": 3, "Electronics": 1}
    rating_only = stats["rating_only_summary"]
    assert rating_only["row_count"] == 3
    assert rating_only["rating_counts"] == {"1": 1, "5": 2}
    assert rating_only["top_product_names"]["Python Patterns"] == 2
    assert rating_only["top_main_categories"] == {"Books": 2, "Electronics": 1}
    assert rating_only["top_product_categories"]["Programming"] == 2
    assert rating_only["top_product_categories"]["Computer Accessories"] == 1


def test_validate_temporal_split_rejects_unsplit_histories_unless_allowed(
    inference_module,
):
    unsplit = {"user_id": "u1", "reviews": [{"rating": 5}]}

    with pytest.raises(ValueError, match="missing temporal_split"):
        inference_module.validate_temporal_split_user_row(
            unsplit,
            Namespace(allow_unsplit_histories=False),
        )

    inference_module.validate_temporal_split_user_row(
        unsplit,
        Namespace(allow_unsplit_histories=True),
    )

    inference_module.validate_temporal_split_user_row(
        {
            "user_id": "u1",
            "reviews": [{"rating": 5}],
            "validation_reviews": [{"rating": 4}],
            "temporal_split": {"method": "per_user_temporal", "train_fraction": 0.8},
        },
        Namespace(allow_unsplit_histories=False),
    )


def test_blind_rating_holdout_targets_remove_rating_and_cohort(holdout_eval_module):
    target = {
        "target_id": "u1::v000001",
        "user_id": "u1",
        "cohort": "harsh_low",
        "true_rating": 1.0,
        "product_context": {"source_category": "Books"},
    }

    blind = holdout_eval_module.blind_target(target)

    assert blind == {
        "target_id": "u1::v000001",
        "user_id": "u1",
        "product_context": {"source_category": "Books"},
    }
