import gzip
import json
import sqlite3
import tarfile
from pathlib import Path

from persona.curation.existing_data.worker_kit.run_range import run_range


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
    for idx in range(5):
        conn.execute(
            "insert into profiles values (?,?,?,?,?,?,?)",
            (
                idx,
                f"wiki_profile:{idx:010d}",
                f"Q{idx}",
                f"Person {idx}",
                f"https://example.test/{idx}",
                f"Profile text {idx}",
                f"{idx}" * 64,
            ),
        )
    conn.commit()
    conn.close()


def _make_protocol(path: Path) -> None:
    path.mkdir()
    (path / "prompt.md").write_text("Extract JSON for {{input_json}}", encoding="utf-8")
    (path / "output.schema.json").write_text(
        json.dumps({"type": "object"}), encoding="utf-8"
    )
    (path / "protocol_manifest.json").write_text(
        json.dumps(
            {
                "protocol_id": "persona_attribution_v1",
                "protocol_version": "1.0.0",
                "prompt_file": "prompt.md",
                "output_schema_file": "output.schema.json",
            }
        ),
        encoding="utf-8",
    )


def test_mock_run_range_writes_archive_with_results_and_manifest(tmp_path: Path):
    db = tmp_path / "profiles.sqlite"
    protocol = tmp_path / "protocol"
    out_dir = tmp_path / "out"
    _make_dataset(db)
    _make_protocol(protocol)

    archive = run_range(
        db_path=db,
        protocol_dir=protocol,
        range_start=1,
        range_end=4,
        backend_name="mock",
        model="mock-model",
        concurrency=3,
        worker_id="alice",
        out_dir=out_dir,
        dataset_id="dataset-v1",
        dataset_sha256="d" * 64,
    )

    assert archive.exists()
    with tarfile.open(archive, "r:gz") as tar:
        names = sorted(member.name for member in tar.getmembers())
        assert names == ["failures.jsonl.gz", "results.jsonl.gz", "run_manifest.json"]
        tar.extract("results.jsonl.gz", path=out_dir)
        tar.extract("run_manifest.json", path=out_dir)

    with gzip.open(out_dir / "results.jsonl.gz", "rt", encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert [row["global_idx"] for row in rows] == [1, 2, 3]
    assert all(row["provenance"]["backend"] == "mock" for row in rows)
    assert manifest["succeeded"] == 3
    assert manifest["concurrency"] == 3
