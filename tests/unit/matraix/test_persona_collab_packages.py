import json
import tarfile
from pathlib import Path


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _dimensions_file(tmp_path: Path) -> Path:
    path = tmp_path / "dimensions.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "att_online_reviews",
                    "label": "Attitude: Online reviews",
                    "category": "Behavior: Preferences",
                    "description": "Stance toward online reviews.",
                    "values": ["trusts reviews", "skeptical of reviews"],
                }
            ],
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_wiki_collab_package_builds_extractable_archive(tmp_path: Path) -> None:
    from persona.existing_data_curation.scripts.build_wiki_profile_db import (
        build_profile_database,
    )
    from persona.existing_data_curation.scripts.make_collab_package import (
        build_collab_package,
    )

    clean_dir = tmp_path / "clean"
    _write_jsonl(
        clean_dir / "part-00000.jsonl",
        [
            {
                "page_id": 20,
                "qid": "Q20",
                "title": "Ada Example",
                "source_url": "https://en.wikipedia.org/wiki/Ada_Example",
                "plain_text": "Ada writes detailed reviews and values reliable tools.",
            },
            {
                "page_id": 10,
                "qid": "Q10",
                "title": "Grace Example",
                "source_url": "https://en.wikipedia.org/wiki/Grace_Example",
                "plain_text": "Grace compares books carefully before recommending them.",
            },
        ],
    )

    db_path = tmp_path / "profiles.sqlite"
    manifest_path = tmp_path / "manifest.json"
    manifest = build_profile_database(
        clean_dir=clean_dir,
        out_db=db_path,
        manifest_path=manifest_path,
        dataset_id="wiki_test",
    )
    assert manifest["row_count"] == 2

    out_dir = tmp_path / "A_0_2_alice"
    summary = build_collab_package(
        db_path=db_path,
        dimensions_path=_dimensions_file(tmp_path),
        out_dir=out_dir,
        assignment_id="A_0_2",
        worker_id="alice",
        dataset_id="wiki_test",
        dataset_sha256=manifest["db_sha256"],
        range_start=0,
        range_end=2,
        categories=None,
        force=True,
    )

    assert Path(summary["archive_path"]).is_file()
    assert (out_dir / "run_assignment.sh").stat().st_mode & 0o111
    assert _read_jsonl(out_dir / "tasks.jsonl")[0]["title"] == "Grace Example"
    assert json.loads((out_dir / "assignment.json").read_text())["task_count"] == 2

    with tarfile.open(summary["archive_path"], "r:gz") as archive:
        names = set(archive.getnames())

    assert "A_0_2_alice/tasks.jsonl" in names
    assert "A_0_2_alice/dimensions.json" in names
    assert "A_0_2_alice/package_manifest.json" in names
    assert "A_0_2_alice/collab_kit/conformance.py" in names


def test_amazon_collab_package_builds_extractable_archive(tmp_path: Path) -> None:
    from persona.existing_data_curation.scripts.make_amazon_collab_package import (
        build_amazon_collab_package,
    )
    from persona.existing_data_curation.wiki_collab.core import sha256_file

    histories = tmp_path / "amazon_histories.jsonl"
    _write_jsonl(
        histories,
        [
            {
                "user_id": "user-1",
                "reviews": [
                    {
                        "timestamp": 1_704_067_200_000,
                        "category": "Books",
                        "rating": 5,
                        "title": "Careful reading guide",
                        "text": "I liked the detailed comparisons and practical examples.",
                        "verified_purchase": True,
                    },
                    {
                        "timestamp": 1_707_004_800_000,
                        "category": "Tools",
                        "rating": 4,
                        "title": "Reliable home tool",
                        "text": "Durable, useful, and worth the price for repeated use.",
                        "verified_purchase": True,
                    },
                ],
            }
        ],
    )

    out_dir = tmp_path / "A_0_1_bob"
    summary = build_amazon_collab_package(
        user_histories_path=histories,
        dimensions_path=_dimensions_file(tmp_path),
        out_dir=out_dir,
        assignment_id="A_0_1",
        worker_id="bob",
        dataset_id="amazon_test",
        dataset_sha256=sha256_file(histories),
        range_start=0,
        range_end=1,
        cv_folds=2,
        min_support_folds=2,
        all_dimensions=True,
        force=True,
    )

    tasks = _read_jsonl(out_dir / "tasks.jsonl")
    assignment = json.loads((out_dir / "assignment.json").read_text())

    assert Path(summary["archive_path"]).is_file()
    assert tasks[0]["source"] == "amazon_reviews_2023"
    assert tasks[0]["effective_cv_folds"] == 2
    assert len(tasks[0]["cv_fold_texts"]) == 2
    assert assignment["dimensions_scope"] == "all"

    with tarfile.open(summary["archive_path"], "r:gz") as archive:
        names = set(archive.getnames())

    assert "A_0_1_bob/tasks.jsonl" in names
    assert "A_0_1_bob/README.md" in names
    assert "A_0_1_bob/collab_kit/conformance.py" in names


def test_hf_amazon_exporter_writes_normalized_user_histories(
    tmp_path: Path, monkeypatch
) -> None:
    from persona.existing_data_curation.scripts import export_hf_amazon_user_histories

    requested_user = "A1B2C3D4E5F6"
    skipped_user = "A9B8C7D6E5F4"
    user_ids = tmp_path / "reviewer_ids.md"
    user_ids.write_text(
        f"# Reviewers\n\n- {requested_user}\n- {skipped_user}\n",
        encoding="utf-8",
    )

    def fake_list_relevant_shards(*, buckets, categories, **_kwargs):
        assert buckets == {export_hf_amazon_user_histories.user_bucket(requested_user)}
        assert categories == {"Books"}
        return ["amazon/reviews/bucket=xx/category=Books/part-000.parquet"]

    def fake_read_shard_rows(_repo_id, _filename, _token):
        return [
            {
                "source": "amazon_reviews_2023",
                "category": "Books",
                "user_id": requested_user,
                "parent_asin": "P2",
                "asin": "B2",
                "timestamp": 20,
                "date": "2023-01-02",
                "rating": 4,
                "title": "Second review",
                "text": "Useful and durable.",
                "verified_purchase": True,
                "helpful_vote": 2,
            },
            {
                "source": "amazon_reviews_2023",
                "category": "Books",
                "user_id": requested_user,
                "parent_asin": "P1",
                "asin": "B1",
                "timestamp": 10,
                "date": "2023-01-01",
                "rating": 5,
                "title": "First review",
                "text": "Clear and practical.",
                "verified_purchase": True,
                "helpful_vote": 3,
            },
            {
                "source": "amazon_reviews_2023",
                "category": "Books",
                "user_id": "A00000000000",
                "timestamp": 1,
                "rating": 1,
            },
        ]

    monkeypatch.setattr(
        export_hf_amazon_user_histories,
        "list_relevant_shards",
        fake_list_relevant_shards,
    )
    monkeypatch.setattr(
        export_hf_amazon_user_histories,
        "read_shard_rows",
        fake_read_shard_rows,
    )

    output = tmp_path / "user_histories.jsonl"
    exit_code = export_hf_amazon_user_histories.main(
        [
            "--user-ids",
            str(user_ids),
            "--repo-id",
            "MatrAIx/MatrAIx",
            "--artifact-prefix",
            "amazon/modal_artifacts/test",
            "--categories",
            "Books",
            "--max-users",
            "1",
            "--output",
            str(output),
        ]
    )

    histories = _read_jsonl(output)
    assert exit_code == 0
    assert histories == [
        {
            "user_id": requested_user,
            "review_count": 2,
            "reviews": [
                {
                    "source": "amazon_reviews_2023",
                    "category": "Books",
                    "user_id": requested_user,
                    "parent_asin": "P1",
                    "asin": "B1",
                    "timestamp": 10,
                    "date": "2023-01-01",
                    "rating": 5,
                    "title": "First review",
                    "text": "Clear and practical.",
                    "verified_purchase": True,
                    "helpful_vote": 3,
                },
                {
                    "source": "amazon_reviews_2023",
                    "category": "Books",
                    "user_id": requested_user,
                    "parent_asin": "P2",
                    "asin": "B2",
                    "timestamp": 20,
                    "date": "2023-01-02",
                    "rating": 4,
                    "title": "Second review",
                    "text": "Useful and durable.",
                    "verified_purchase": True,
                    "helpful_vote": 2,
                },
            ],
        }
    ]


def test_package_owner_scripts_document_portable_data_inputs() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    wiki_wrapper = (
        repo_root / "persona/existing_data_curation/scripts/make_package.sh"
    ).read_text(encoding="utf-8")
    amazon_wrapper = (
        repo_root / "persona/existing_data_curation/scripts/make_amazon_package.sh"
    ).read_text(encoding="utf-8")
    amazon_exporter = (
        repo_root
        / "persona/existing_data_curation/scripts/export_hf_amazon_user_histories.py"
    ).read_text(encoding="utf-8")
    owner_readme = (
        repo_root / "persona/existing_data_curation/README.md"
    ).read_text(encoding="utf-8")
    amazon_manifest = json.loads(
        (
            repo_root / "persona/existing_data_curation/configs/amazon_reviews_2023.json"
        ).read_text(encoding="utf-8")
    )

    checked_text = "\n".join([wiki_wrapper, amazon_wrapper, amazon_exporter, owner_readme])
    assert "/data2/" not in checked_text
    assert "zonglin" not in checked_text
    assert 'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"' in wiki_wrapper
    assert 'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"' in amazon_wrapper
    assert ': "${WIKI_CLEAN_DIR:?Set WIKI_CLEAN_DIR' in wiki_wrapper
    assert '"MatrAIx/MatrAIx"' not in amazon_exporter
    assert "load_default_source_config" in amazon_exporter
    assert amazon_manifest["source"]["repo_id"] == "MatrAIx2026/MatrAIx2026"
    assert amazon_manifest["format"] == "partitioned parquet"


def test_amazon_downstream_workflows_are_subscription_based() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    extraction = (
        repo_root
        / "persona/existing_data_curation/amazon/extraction/infer_amazon_review_dimensions.py"
    )
    prediction = (
        repo_root
        / "persona/existing_data_curation/amazon/evaluation/predict_amazon_persona_holdout_ratings.py"
    )
    evaluation = (
        repo_root
        / "persona/existing_data_curation/amazon/evaluation/evaluate_amazon_persona_rating_holdout.py"
    )
    backend = (
        repo_root
        / "persona/existing_data_curation/amazon/subscription_json_backend.py"
    )

    workflow_files = [extraction, prediction, evaluation, backend]
    for path in workflow_files:
        assert path.exists(), f"missing downstream workflow file: {path}"

    api_needles = ("OPENAI_API_KEY", "api.openai.com", "/v1/chat/completions")
    for path in workflow_files:
        text = path.read_text(encoding="utf-8")
        for needle in api_needles:
            assert needle not in text

    extraction_text = extraction.read_text(encoding="utf-8")
    prediction_text = prediction.read_text(encoding="utf-8")
    backend_text = backend.read_text(encoding="utf-8")

    assert "--llm-backend" in extraction_text
    assert "--llm-backend" in prediction_text
    assert "codex" in backend_text
    assert "claude" in backend_text


def test_build_cv_fold_texts_uses_custom_id_field() -> None:
    from persona.existing_data_curation.scripts.history_package_common import (
        build_cv_fold_texts,
    )

    fold_texts = build_cv_fold_texts(
        [
            ("p0001", "[p0001]\ntext: alpha"),
            ("p0002", "[p0002]\ntext: beta"),
            ("p0003", "[p0003]\ntext: gamma"),
        ],
        2,
        id_field="post_ids",
    )

    assert [fold["fold_id"] for fold in fold_texts] == [1, 2]
    assert fold_texts[0]["post_ids"] == ["p0001", "p0003"]
    assert fold_texts[1]["post_ids"] == ["p0002"]
    assert fold_texts[0]["profile_text"].startswith("=== Fold 1/2 ===")
    assert "[p0003]" in fold_texts[0]["profile_text"]


def test_stackoverflow_evidence_mapping_filters_catalog_categories() -> None:
    from persona.existing_data_curation.scripts.history_package_common import (
        filter_supported_dimensions,
        load_evidence_mapping,
    )

    repo_root = Path(__file__).resolve().parents[3]
    mapping = load_evidence_mapping(
        repo_root
        / "persona/existing_data_curation/configs/stackoverflow_evidence_mapping.json"
    )
    dimensions = [
        {"id": "d1", "category": "Skills: Programming"},
        {"id": "d2", "category": "Linguistic: Communication"},
        {"id": "d3", "category": "External: Datasets"},
        {"id": "d4", "category": "Interests: Food"},
    ]
    filtered = filter_supported_dimensions(dimensions, mapping)
    assert [dim["id"] for dim in filtered] == ["d1", "d2"]

    config = json.loads(
        (
            repo_root
            / "persona/existing_data_curation/configs/stackexchange_persona.json"
        ).read_text(encoding="utf-8")
    )
    assert config["source"]["repo_id"] == "MatrAIx2026/MatrAIx2026"
    assert config["source"]["artifact_prefix"] == "StackExchange_Persona"


def test_stackoverflow_collab_package_builds_extractable_archive(tmp_path: Path) -> None:
    from persona.existing_data_curation.scripts.make_stackoverflow_collab_package import (
        build_stackoverflow_collab_package,
    )
    from persona.existing_data_curation.wiki_collab.core import sha256_file

    histories = tmp_path / "so_histories.jsonl"
    _write_jsonl(
        histories,
        [
            {
                "user_id": "42",
                "posts": [
                    {
                        "post_id": "101",
                        "post_type": "question",
                        "timestamp": 1_704_067_200,
                        "tags": ["python", "pandas"],
                        "title": "How do I merge dataframes safely?",
                        "text": "I compared several approaches before asking here.",
                        "score": 12,
                        "accepted": None,
                    },
                    {
                        "post_id": "102",
                        "post_type": "answer",
                        "timestamp": 1_707_004_800,
                        "tags": ["python"],
                        "title": "",
                        "text": "Use explicit validation and check the docs first.",
                        "score": 30,
                        "accepted": True,
                    },
                ],
            }
        ],
    )

    out_dir = tmp_path / "SO_0_1_carol"
    summary = build_stackoverflow_collab_package(
        user_histories_path=histories,
        dimensions_path=_dimensions_file(tmp_path),
        out_dir=out_dir,
        assignment_id="SO_0_1",
        worker_id="carol",
        dataset_id="so_test",
        dataset_sha256=sha256_file(histories),
        range_start=0,
        range_end=1,
        cv_folds=2,
        min_support_folds=2,
        all_dimensions=True,
        force=True,
    )

    tasks = _read_jsonl(out_dir / "tasks.jsonl")
    assignment = json.loads((out_dir / "assignment.json").read_text())

    assert Path(summary["archive_path"]).is_file()
    assert tasks[0]["source"] == "stackoverflow_persona"
    assert tasks[0]["task_id"] == "stackoverflow_persona:42"
    assert tasks[0]["qid"] == "so_user:42"
    assert tasks[0]["effective_cv_folds"] == 2
    assert len(tasks[0]["cv_fold_texts"]) == 2
    assert tasks[0]["cv_fold_texts"][0]["post_ids"] == ["p0001"]
    assert tasks[0]["tags"] == ["pandas", "python"]
    assert "type: question" in tasks[0]["profile_text"]
    assert "accepted: true" in tasks[0]["profile_text"]
    assert assignment["source"] == "stackoverflow_persona"
    assert assignment["dimensions_scope"] == "all"
    assert assignment["max_posts_per_user"] == 90

    with tarfile.open(summary["archive_path"], "r:gz") as archive:
        names = set(archive.getnames())

    assert "SO_0_1_carol/tasks.jsonl" in names
    assert "SO_0_1_carol/README.md" in names
    assert "SO_0_1_carol/collab_kit/conformance.py" in names

