import json
import sqlite3
from pathlib import Path

from persona.curation.existing_data.wiki_collab.core import (
    compute_input_sha256,
    profile_input_payload,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _make_wiki_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        create table profiles (
          global_idx integer primary key,
          task_id text not null,
          qid text not null,
          title text not null,
          source_url text not null,
          profile_text text not null,
          input_sha256 text not null
        )
        """
    )
    for idx, title in enumerate(["Alpha Person", "Beta Person"]):
        row = {
            "global_idx": idx,
            "task_id": f"wiki_profile:{idx:010d}",
            "qid": f"Q{idx}",
            "title": title,
            "source_url": f"https://example.test/wiki/{idx}",
            "profile_text": f"{title} was a public figure.",
        }
        conn.execute(
            "insert into profiles values (?,?,?,?,?,?,?)",
            (
                row["global_idx"],
                row["task_id"],
                row["qid"],
                row["title"],
                row["source_url"],
                row["profile_text"],
                compute_input_sha256(profile_input_payload(row)),
            ),
        )
    conn.commit()
    conn.close()


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


def _write_amazon_mapping(path: Path) -> None:
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


def _write_amazon_histories(path: Path) -> None:
    _write_jsonl(
        path,
        [
            {
                "user_id": "USER_A",
                "reviews": [
                    {
                        "review_id": "a1",
                        "timestamp": 1_701_000_000_000,
                        "category": "Books",
                        "rating": 5,
                        "title": "First book",
                        "text": "I compare translations and keep detailed notes.",
                    },
                    {
                        "review_id": "a2",
                        "timestamp": 1_702_000_000_000,
                        "category": "Kitchen",
                        "rating": 4,
                        "title": "Scale",
                        "text": "Accurate enough for recipe testing every weekend.",
                    },
                ],
            }
        ],
    )


def test_unified_generator_can_build_wiki_package(tmp_path: Path, capsys):
    from persona.curation.existing_data.scripts.make_package import main

    db = tmp_path / "profiles.sqlite"
    dimensions = tmp_path / "dimensions.json"
    out_dir = tmp_path / "wiki_package"
    _make_wiki_db(db)
    _write_dimensions(dimensions)

    status = main(
        [
            "--source",
            "wiki",
            "--db",
            str(db),
            "--dimensions",
            str(dimensions),
            "--range",
            "0:2",
            "--out-dir",
            str(out_dir),
            "--assignment-id",
            "WIKI-A0001",
            "--worker-id",
            "alice",
            "--dataset-id",
            "wiki-test-v1",
            "--dataset-sha256",
            "d" * 64,
            "--categories",
            "expertise_domains",
            "--no-archive",
            "--force",
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    assert status == 0
    assert summary["package_dir"] == str(out_dir)
    assert summary["archive_path"] is None
    assert summary["task_count"] == 2
    assert summary["dimension_count"] == 1

    assignment = json.loads((out_dir / "assignment.json").read_text(encoding="utf-8"))
    assert assignment["assignment_id"] == "WIKI-A0001"
    assert assignment["worker_id"] == "alice"
    assert assignment["dataset_id"] == "wiki-test-v1"
    assert assignment["categories"] == ["expertise_domains"]
    assert "source" not in assignment

    tasks = _read_jsonl(out_dir / "tasks.jsonl")
    assert [task["task_id"] for task in tasks] == [
        "wiki_profile:0000000000",
        "wiki_profile:0000000001",
    ]

    packaged_dimensions = json.loads((out_dir / "dimensions.json").read_text(encoding="utf-8"))
    assert [dimension["id"] for dimension in packaged_dimensions] == ["domain"]


def test_unified_generator_can_build_amazon_package(tmp_path: Path, capsys):
    from persona.curation.existing_data.scripts.make_package import main

    histories = tmp_path / "user_histories.jsonl"
    dimensions = tmp_path / "dimensions.json"
    mapping = tmp_path / "mapping.json"
    out_dir = tmp_path / "amazon_package"
    _write_amazon_histories(histories)
    _write_dimensions(dimensions)
    _write_amazon_mapping(mapping)

    status = main(
        [
            "--source",
            "amazon",
            "--user-histories",
            str(histories),
            "--dimensions",
            str(dimensions),
            "--range",
            "0:1",
            "--out-dir",
            str(out_dir),
            "--assignment-id",
            "AMZ-A0001",
            "--worker-id",
            "bob",
            "--dataset-id",
            "amazon-test-v1",
            "--dataset-sha256",
            "a" * 64,
            "--evidence-mapping",
            str(mapping),
            "--no-archive",
            "--force",
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    assert status == 0
    assert summary["package_dir"] == str(out_dir)
    assert summary["archive_path"] is None
    assert summary["task_count"] == 1
    assert summary["dimension_count"] == 2

    assignment = json.loads((out_dir / "assignment.json").read_text(encoding="utf-8"))
    assert assignment["source"] == "amazon_reviews_2023"
    assert assignment["assignment_id"] == "AMZ-A0001"
    assert assignment["worker_id"] == "bob"
    assert assignment["dataset_id"] == "amazon-test-v1"
    assert assignment["dimensions_scope"] == "amazon_supported"
    assert assignment["cv_folds"] == 3

    tasks = _read_jsonl(out_dir / "tasks.jsonl")
    assert [task["task_id"] for task in tasks] == ["amazon_reviews_2023:USER_A"]
    assert tasks[0]["source"] == "amazon_reviews_2023"
    assert tasks[0]["effective_cv_folds"] == 2

    packaged_dimensions = json.loads((out_dir / "dimensions.json").read_text(encoding="utf-8"))
    assert [dimension["id"] for dimension in packaged_dimensions] == [
        "domain",
        "core_demo",
    ]
