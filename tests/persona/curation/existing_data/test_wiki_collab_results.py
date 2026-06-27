import gzip
import json
import sqlite3
import tarfile
from pathlib import Path

from persona.curation.existing_data.scripts.merge_wiki_results import merge_archives
from persona.curation.existing_data.scripts.validate_wiki_results import (
    validate_result_archive,
)
from persona.curation.existing_data.wiki_collab.core import Assignment


def _make_dataset(path: Path) -> None:
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
    conn.execute(
        "insert into profiles values (?,?,?,?,?,?,?)",
        (
            0,
            "wiki_profile:0000000000",
            "Q1",
            "Alpha Person",
            "https://example.test/alpha",
            "Alpha text",
            "i" * 64,
        ),
    )
    conn.commit()
    conn.close()


def _write_archive(path: Path, *, global_idx: int = 0, input_sha256: str = "i" * 64) -> None:
    work = path.parent / "work"
    work.mkdir()
    result_row = {
        "global_idx": global_idx,
        "task_id": "wiki_profile:0000000000",
        "qid": "Q1",
        "status": "succeeded",
        "input_sha256": input_sha256,
        "provenance": {
            "worker_id": "alice",
            "backend": "mock",
            "provider": "mock",
            "requested_model": "mock-model",
            "reported_model": "mock-model",
            "model_source": "runner",
            "model_confidence": "exact",
            "prompt_sha256": "p" * 64,
            "protocol_sha256": "r" * 64,
            "runner_version": "0.1.0",
            "effort": "high",
        },
        "fields": [
            {
                "field_id": "domain",
                "value": "science",
                "confidence": 0.9,
                "evidence": "Alpha text",
                "assignment_type": "summary_inference",
            }
        ],
    }
    manifest = {
        "worker_id": "alice",
        "dataset_id": "dataset-v1",
        "dataset_sha256": "d" * 64,
        "protocol_id": "persona_attribution_v1",
        "protocol_sha256": "r" * 64,
        "range_start": 0,
        "range_end": 1,
        "backend": "mock",
        "provider": "mock",
        "requested_model": "mock-model",
        "reported_models": {"mock-model": 1},
        "auth_mode": "none",
        "concurrency": 2,
        "runner_version": "0.1.0",
        "effort": "high",
        "succeeded": 1,
        "failed": 0,
    }
    with gzip.open(work / "results.jsonl.gz", "wt", encoding="utf-8") as fh:
        fh.write(json.dumps(result_row, ensure_ascii=False) + "\n")
    with gzip.open(work / "failures.jsonl.gz", "wt", encoding="utf-8") as fh:
        pass
    (work / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with tarfile.open(path, "w:gz") as tar:
        tar.add(work / "results.jsonl.gz", arcname="results.jsonl.gz")
        tar.add(work / "failures.jsonl.gz", arcname="failures.jsonl.gz")
        tar.add(work / "run_manifest.json", arcname="run_manifest.json")


def _assignment() -> Assignment:
    return Assignment(
        assignment_id="A0001",
        worker_id="alice",
        dataset_id="dataset-v1",
        dataset_sha256="d" * 64,
        protocol_id="persona_attribution_v1",
        protocol_sha256="r" * 64,
        range_start=0,
        range_end=1,
        status="assigned",
    )


def test_validate_result_archive_accepts_well_formed_archive(tmp_path: Path):
    db = tmp_path / "profiles.sqlite"
    archive = tmp_path / "results.tar.gz"
    _make_dataset(db)
    _write_archive(archive)

    report = validate_result_archive(
        archive_path=archive,
        db_path=db,
        assignment=_assignment(),
        expected_prompt_sha256="p" * 64,
    )

    assert report.accepted
    assert report.valid_rows == 1
    assert report.errors == []


def test_validate_result_archive_rejects_out_of_range_row(tmp_path: Path):
    db = tmp_path / "profiles.sqlite"
    archive = tmp_path / "results.tar.gz"
    _make_dataset(db)
    _write_archive(archive, global_idx=2)

    report = validate_result_archive(
        archive_path=archive,
        db_path=db,
        assignment=_assignment(),
        expected_prompt_sha256="p" * 64,
    )

    assert not report.accepted
    assert any("outside assignment range" in error for error in report.errors)


def test_merge_archives_refuses_duplicate_global_idx(tmp_path: Path):
    db = tmp_path / "profiles.sqlite"
    archive = tmp_path / "results.tar.gz"
    out = tmp_path / "merged.jsonl.gz"
    _make_dataset(db)
    _write_archive(archive)

    first = merge_archives([archive], out)
    second = merge_archives([archive], out)

    assert first["written_rows"] == 1
    assert second["written_rows"] == 0
    assert second["duplicate_rows"] == 1

    with gzip.open(out, "rt", encoding="utf-8") as fh:
        assert sum(1 for _ in fh) == 1
