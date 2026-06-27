import json
import sqlite3
import tarfile
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
    for idx, title in enumerate(["Alpha Person", "Beta Person", "Gamma Person"]):
        row = {
            "global_idx": idx,
            "task_id": f"wiki_profile:{idx:010d}",
            "qid": f"Q{idx}",
            "title": title,
            "source_url": f"https://example.test/{idx}",
            "profile_text": f"{title} was a public figure.",
        }
        sha = compute_input_sha256(profile_input_payload(row))
        conn.execute(
            "insert into profiles values (?,?,?,?,?,?,?)",
            (
                row["global_idx"],
                row["task_id"],
                row["qid"],
                row["title"],
                row["source_url"],
                row["profile_text"],
                sha,
            ),
        )
    conn.commit()
    conn.close()


def _write_dimensions(path: Path) -> None:
    payload = {
        "schemaVersion": "2.0",
        "dimensions": [
            {
                "id": "age_bracket",
                "label": "Age bracket",
                "description": "Life-age band.",
                "category": "Demographic: Core",
                "values": ["18-24", "25-34"],
            },
            {
                "id": "domain",
                "label": "Domain",
                "description": "Primary domain.",
                "category": "Expertise: Domains",
                "values": ["Politics", "Science"],
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_build_collab_package_writes_worker_facing_files(tmp_path: Path):
    db = tmp_path / "profiles.sqlite"
    dimensions = tmp_path / "dimensions.json"
    out_dir = tmp_path / "package"
    _make_db(db)
    _write_dimensions(dimensions)

    summary = build_collab_package(
        db_path=db,
        dimensions_path=dimensions,
        out_dir=out_dir,
        assignment_id="A0001",
        worker_id="alice",
        dataset_id="wiki-test-v1",
        dataset_sha256="d" * 64,
        range_start=0,
        range_end=2,
        categories=None,
        create_archive=True,
    )

    assert summary["task_count"] == 2
    assert summary["dimension_count"] == 2
    assert summary["archive_path"].endswith(".tar.gz")
    assert (out_dir / "assignment.json").exists()
    assert (out_dir / "tasks.jsonl").exists()
    assert (out_dir / "dimensions.json").exists()
    assert (out_dir / "README.md").exists()
    assert (out_dir / "run_assignment.sh").exists()
    assert (out_dir / "package_manifest.json").exists()
    assert (out_dir / "collab_kit" / "solver.py").exists()
    assert not list((out_dir / "collab_kit").rglob("__pycache__"))

    assignment = json.loads((out_dir / "assignment.json").read_text(encoding="utf-8"))
    assert assignment["assignment_id"] == "A0001"
    assert assignment["worker_id"] == "alice"
    assert assignment["range_start"] == 0
    assert assignment["range_end"] == 2
    assert assignment["task_count"] == 2
    assert assignment["dimension_count"] == 2
    assert len(assignment["tasks_sha256"]) == 64
    assert len(assignment["dimensions_sha256"]) == 64

    tasks = _jsonl(out_dir / "tasks.jsonl")
    assert [task["global_idx"] for task in tasks] == [0, 1]
    assert all(len(task["input_sha256"]) == 64 for task in tasks)

    manifest = json.loads((out_dir / "package_manifest.json").read_text(encoding="utf-8"))
    assert manifest["assignment"]["assignment_id"] == "A0001"
    assert manifest["assignment"]["range_start"] == 0
    assert manifest["assignment"]["range_end"] == 2
    assert manifest["files"]["tasks.jsonl"]["mode"] == "immutable"
    assert len(manifest["files"]["tasks.jsonl"]["sha256"]) == 64
    assert manifest["files"]["dimensions.json"]["mode"] == "immutable"
    assert manifest["files"]["collab_kit/solver.py"]["mode"] == "editable"

    with tarfile.open(summary["archive_path"], "r:gz") as tar:
        names = [member.name for member in tar.getmembers()]
    assert len(names) == len(set(names))
    # Every member must live under a single top-level folder named after the
    # package, so extracting the archive never scatters files into the cwd.
    top_levels = {name.split("/", 1)[0] for name in names}
    assert top_levels == {out_dir.name}
    assert f"{out_dir.name}/assignment.json" in names
    assert f"{out_dir.name}/tasks.jsonl" in names
    assert f"{out_dir.name}/dimensions.json" in names
    assert f"{out_dir.name}/run_assignment.sh" in names
    assert f"{out_dir.name}/package_manifest.json" in names
    assert f"{out_dir.name}/collab_kit/solver.py" in names
    assert f"{out_dir.name}/collab_kit/sample/results.jsonl" in names
    assert not any("__pycache__" in name for name in names)


def test_build_collab_package_can_filter_dimensions_by_category_slug(tmp_path: Path):
    db = tmp_path / "profiles.sqlite"
    dimensions = tmp_path / "dimensions.json"
    out_dir = tmp_path / "package"
    _make_db(db)
    _write_dimensions(dimensions)

    summary = build_collab_package(
        db_path=db,
        dimensions_path=dimensions,
        out_dir=out_dir,
        assignment_id="A0002",
        worker_id="bob",
        dataset_id="wiki-test-v1",
        dataset_sha256="d" * 64,
        range_start=1,
        range_end=3,
        categories=["expertise_domains"],
        create_archive=False,
    )

    packaged_dimensions = json.loads((out_dir / "dimensions.json").read_text(encoding="utf-8"))
    assert summary["dimension_count"] == 1
    assert [dim["id"] for dim in packaged_dimensions] == ["domain"]
