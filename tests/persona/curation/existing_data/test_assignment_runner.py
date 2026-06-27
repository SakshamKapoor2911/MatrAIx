import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from persona.curation.existing_data.scripts.make_collab_package import (
    build_collab_package,
)
from persona.curation.existing_data.wiki_collab.core import (
    compute_input_sha256,
    profile_input_payload,
)


def _make_db(path: Path) -> None:
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
            "source_url": f"https://example.test/{idx}",
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
    path.write_text(
        json.dumps(
            {
                "dimensions": [
                    {
                        "id": "domain",
                        "label": "Domain",
                        "description": "Primary domain.",
                        "category": "Expertise: Domains",
                        "values": ["Politics", "Science"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def make_package(tmp_path: Path) -> Path:
    db = tmp_path / "profiles.sqlite"
    dims = tmp_path / "dimensions.json"
    out_dir = tmp_path / "package"
    _make_db(db)
    _write_dimensions(dims)
    build_collab_package(
        db_path=db,
        dimensions_path=dims,
        out_dir=out_dir,
        assignment_id="A0001",
        worker_id="alice",
        dataset_id="wiki-test-v1",
        dataset_sha256="d" * 64,
        range_start=0,
        range_end=2,
        categories=None,
        create_archive=False,
    )
    return out_dir


def run_runner(package: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(package / "collab_kit" / "assignment_runner.py"), *args],
        cwd=package,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_status_reports_manifest_and_progress(tmp_path: Path):
    package = make_package(tmp_path)

    proc = run_runner(package, "--status")

    assert proc.returncode == 0
    assert "Integrity: PASS" in proc.stdout
    assert "Progress:" in proc.stdout


def test_run_assignment_prefers_existing_python_over_uv(tmp_path: Path):
    package = make_package(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_uv = fake_bin / "uv"
    fake_uv.write_text("#!/usr/bin/env bash\nexit 66\n", encoding="utf-8")
    fake_uv.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
    }
    proc = subprocess.run(
        [str(package / "run_assignment.sh"), "--status"],
        cwd=package,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "Integrity: PASS" in proc.stdout
    assert "Progress:" in proc.stdout


def test_mock_run_writes_yaml_settings_results_and_validates(tmp_path: Path):
    package = make_package(tmp_path)

    proc = run_runner(
        package,
        "--backend",
        "mock",
        "--model",
        "mock-model",
        "--effort",
        "high",
        "--jobs",
        "2",
        "--yes",
        "--run",
    )

    assert proc.returncode == 0, proc.stderr
    assert (package / ".wiki_collab_settings.yaml").exists()
    assert "PASS conformance" in proc.stdout
    assert (package / "results.jsonl").exists()
    manifest = json.loads((package / "package_manifest.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (package / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows[0]["input_sha256"]
    assert rows[0]["run"]["assignment"]["assignment_id"] == "A0001"
    assert (
        rows[0]["run"]["assignment"]["tasks_sha256"]
        == manifest["files"]["tasks.jsonl"]["sha256"]
    )


def test_runner_rejects_modified_tasks_file(tmp_path: Path):
    package = make_package(tmp_path)
    with (package / "tasks.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("\n")

    proc = run_runner(package, "--status")

    assert proc.returncode == 1
    assert "tasks.jsonl" in proc.stderr
    assert "manifest mismatch" in proc.stderr


def test_existing_progress_allows_model_change_without_restart(tmp_path: Path):
    package = make_package(tmp_path)
    first = run_runner(
        package,
        "--backend",
        "mock",
        "--model",
        "mock-model",
        "--yes",
        "--run",
    )
    assert first.returncode == 0, first.stderr

    proc = run_runner(
        package,
        "--backend",
        "mock",
        "--model",
        "other-model",
        "--yes",
        "--run",
    )

    assert proc.returncode == 0, proc.stderr
    rows = [
        json.loads(line)
        for line in (package / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert {row["run"]["model"] for row in rows} == {"mock-model"}
