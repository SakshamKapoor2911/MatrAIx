import gzip
import json
import sqlite3
from pathlib import Path

from persona.curation.existing_data.scripts.build_wiki_profile_db import (
    build_profile_database,
)
from persona.curation.existing_data.scripts.make_wiki_assignments import (
    build_assignments,
)
from persona.curation.existing_data.wiki_collab.core import load_jsonl


def _write_clean_pages(path: Path) -> None:
    rows = [
        {
            "page_id": 2,
            "qid": "Q2",
            "title": "Beta Person",
            "source_url": "https://en.wikipedia.org/wiki/Beta_Person",
            "plain_text": "Beta lead text.",
        },
        {
            "page_id": 1,
            "qid": "Q1",
            "title": "Alpha Person",
            "source_url": "https://en.wikipedia.org/wiki/Alpha_Person",
            "plain_text": "Alpha lead text.",
        },
    ]
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_build_profile_database_assigns_stable_global_indices(tmp_path: Path):
    source_dir = tmp_path / "clean"
    source_dir.mkdir()
    _write_clean_pages(source_dir / "part-00000.jsonl.gz")
    out_db = tmp_path / "profiles.sqlite"
    manifest_path = tmp_path / "dataset_manifest.json"

    manifest = build_profile_database(
        clean_dir=source_dir,
        out_db=out_db,
        manifest_path=manifest_path,
        dataset_id="wiki-test-v1",
    )

    assert manifest["row_count"] == 2
    assert manifest["dataset_id"] == "wiki-test-v1"
    assert manifest_path.exists()

    conn = sqlite3.connect(out_db)
    rows = conn.execute(
        "select global_idx, page_id, qid, title, task_id, input_sha256 from profiles order by global_idx"
    ).fetchall()
    conn.close()

    assert rows[0][0:5] == (
        0,
        1,
        "Q1",
        "Alpha Person",
        "wiki_profile:0000000000",
    )
    assert rows[1][0:5] == (
        1,
        2,
        "Q2",
        "Beta Person",
        "wiki_profile:0000000001",
    )
    assert len(rows[0][5]) == 64


def test_build_assignments_cover_rows_without_overlap(tmp_path: Path):
    assignments = build_assignments(
        workers=["alice", "bob", "carol"],
        dataset_id="wiki-test-v1",
        dataset_sha256="d" * 64,
        protocol_id="persona_attribution_v1",
        protocol_sha256="p" * 64,
        row_count=7,
        chunk_size=3,
    )

    assert [(a.worker_id, a.range_start, a.range_end) for a in assignments] == [
        ("alice", 0, 3),
        ("bob", 3, 6),
        ("carol", 6, 7),
    ]

    out_path = tmp_path / "assignments.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for assignment in assignments:
            fh.write(json.dumps(assignment.to_dict(), sort_keys=True) + "\n")

    rows = list(load_jsonl(out_path))
    assert rows[2]["assignment_id"] == "A0003"

