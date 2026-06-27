import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / "persona/curation/existing_data/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import merge_collab_results as mcr  # noqa: E402


def _field(fid, val, conf=0.5):
    return {
        "field_id": fid,
        "value": val,
        "confidence": conf,
        "evidence": "quote" if val is not None else "",
        "assignment_type": "direct" if val is not None else "unsupported",
    }


def _record(gi, fields, model="m1", effort="high"):
    return {
        "global_idx": gi,
        "task_id": f"t{gi}",
        "qid": f"Q{gi}",
        "model": model,
        "run": {"backend": "b", "model": model, "effort": effort, "runner_version": "1.0.0"},
        "fields": fields,
    }


def _write(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def _manifest(
    assignment_id: str,
    worker_id: str,
    range_start: int,
    range_end: int,
    *,
    tasks_sha256: str = "t" * 64,
    dimensions_sha256: str = "d" * 64,
):
    return {
        "assignment": {
            "assignment_id": assignment_id,
            "worker_id": worker_id,
            "range_start": range_start,
            "range_end": range_end,
        },
        "files": {
            "tasks.jsonl": {"sha256": tasks_sha256},
            "dimensions.json": {"sha256": dimensions_sha256},
        },
    }


def _manifest_sha(manifest: dict) -> str:
    return mcr.package_manifest_sha256(manifest)


def _attach_assignment(
    rec,
    assignment_id: str,
    worker_id: str,
    range_start: int,
    range_end: int,
    *,
    tasks_sha256: str = "t" * 64,
    dimensions_sha256: str = "d" * 64,
    package_manifest_sha256: str | None = None,
):
    rec["run"]["assignment"] = {
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "range_start": range_start,
        "range_end": range_end,
        "tasks_sha256": tasks_sha256,
        "dimensions_sha256": dimensions_sha256,
    }
    if package_manifest_sha256 is not None:
        rec["run"]["assignment"]["package_manifest_sha256"] = package_manifest_sha256
    return rec


def _identity_db(tmp_path: Path, *, input_sha256: str = "a" * 64) -> Path:
    db = tmp_path / "profiles.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        create table profiles (
          global_idx integer primary key,
          task_id text not null,
          qid text not null,
          input_sha256 text not null
        )
        """
    )
    conn.execute("insert into profiles values (?,?,?,?)", (0, "t0", "Q0", input_sha256))
    conn.commit()
    conn.close()
    return db


def test_disjoint_merge_collects_all_and_tallies_provenance(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _write(a, [_record(0, [_field("region", "North America")]),
              _record(1, [_field("region", "East Asia")])])
    _write(b, [_record(2, [_field("region", "Western Europe")], effort="max")])

    records, report = mcr.merge_results([a, b], dimensions=None, db_path=None)

    assert report["accepted"]
    assert report["merged_profiles"] == 3
    assert {r["global_idx"] for r in records} == {0, 1, 2}
    assert report["provenance"]["models"] == {"m1": 3}
    assert report["provenance"]["efforts"] == {"high": 2, "max": 1}


def test_merge_tallies_mixed_unit_runs(tmp_path):
    result = tmp_path / "mixed.jsonl"
    run_a = {"backend": "claude-code-acp", "model": "claude-opus-4-8", "effort": "high", "runner_version": "1.0.0"}
    run_b = {"backend": "codex-acp", "model": "gpt-5.5", "effort": "high", "runner_version": "1.0.0"}
    rec = _record(
        0,
        [
            {**_field("region", "North America"), "run": run_a},
            {**_field("gender_identity", "Man"), "run": run_b},
        ],
        model="mixed",
    )
    rec["run"] = {
        "backend": "mixed",
        "model": "mixed",
        "effort": "mixed",
        "runner_version": "1.0.0",
        "mixed_provenance": True,
        "unit_runs": [run_a, run_b],
    }
    _write(result, [rec])

    records, report = mcr.merge_results([result], dimensions=None, db_path=None)

    assert report["accepted"]
    assert report["provenance"]["models"] == {
        "claude-opus-4-8": 1,
        "gpt-5.5": 1,
    }
    assert {field["run"]["model"] for field in records[0]["fields"]} == {
        "claude-opus-4-8",
        "gpt-5.5",
    }


def test_same_profile_across_files_unions_fields(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _write(a, [_record(0, [_field("region", "North America")])])
    _write(b, [_record(0, [_field("gender_identity", "Man")])])

    records, report = mcr.merge_results([a, b], dimensions=None, db_path=None)

    assert report["merged_profiles"] == 1
    assert report["multi_source_profiles"] == 1
    fids = {f["field_id"] for f in records[0]["fields"]}
    assert fids == {"region", "gender_identity"}


def test_value_conflict_keeps_higher_confidence_and_is_reported(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _write(a, [_record(0, [_field("region", "North America", conf=0.3)])])
    _write(b, [_record(0, [_field("region", "East Asia", conf=0.9)])])

    records, report = mcr.merge_results([a, b], dimensions=None, db_path=None)

    assert len(report["conflicts"]) == 1
    region = next(f for f in records[0]["fields"] if f["field_id"] == "region")
    assert region["value"] == "East Asia"  # higher confidence wins


def test_merge_rejects_input_sha256_mismatch(tmp_path):
    db = _identity_db(tmp_path, input_sha256="a" * 64)
    result = tmp_path / "result.jsonl"
    rec = _record(0, [_field("region", "North America")])
    rec["input_sha256"] = "b" * 64
    _write(result, [rec])

    _records, report = mcr.merge_results([result], dimensions=None, db_path=db)

    assert not report["accepted"]
    assert any("input_sha256 mismatch" in error for error in report["errors"])


def test_merge_rejects_missing_input_sha256_when_dataset_has_hash(tmp_path):
    db = _identity_db(tmp_path, input_sha256="a" * 64)
    result = tmp_path / "result.jsonl"
    _write(result, [_record(0, [_field("region", "North America")])])

    _records, report = mcr.merge_results([result], dimensions=None, db_path=db)

    assert not report["accepted"]
    assert any("has no returned input_sha256" in error for error in report["errors"])


def test_merge_rejects_assignment_hash_mismatch(tmp_path):
    result = tmp_path / "result.jsonl"
    manifest = _manifest("A0001", "alice", 0, 1, tasks_sha256="good")
    rec = _record(0, [_field("region", "North America")])
    _attach_assignment(
        rec,
        "A0001",
        "alice",
        0,
        1,
        tasks_sha256="bad",
        package_manifest_sha256=_manifest_sha(manifest),
    )
    _write(result, [rec])

    _records, report = mcr.merge_results(
        [result],
        dimensions=None,
        db_path=None,
        package_manifests=[manifest],
    )

    assert not report["accepted"]
    assert any("tasks_sha256 mismatch" in error for error in report["errors"])


def test_merge_binds_package_manifests_to_result_files_in_order(tmp_path):
    alice_result = tmp_path / "alice.jsonl"
    bob_result = tmp_path / "bob.jsonl"
    alice_manifest = _manifest("A0001", "alice", 0, 1)
    bob_manifest = _manifest("B0001", "bob", 1, 2)
    alice_claims_bob = _attach_assignment(
        _record(1, [_field("region", "North America")]),
        "B0001",
        "bob",
        1,
        2,
        package_manifest_sha256=_manifest_sha(bob_manifest),
    )
    bob_claims_alice = _attach_assignment(
        _record(0, [_field("region", "East Asia")]),
        "A0001",
        "alice",
        0,
        1,
        package_manifest_sha256=_manifest_sha(alice_manifest),
    )
    _write(alice_result, [alice_claims_bob])
    _write(bob_result, [bob_claims_alice])

    _records, report = mcr.merge_results(
        [alice_result, bob_result],
        dimensions=None,
        db_path=None,
        package_manifests=[alice_manifest, bob_manifest],
    )

    assert not report["accepted"]
    assert any("assignment_id mismatch" in error for error in report["errors"])


def test_merge_rejects_package_manifest_sha256_mismatch(tmp_path):
    result = tmp_path / "result.jsonl"
    manifest = _manifest("A0001", "alice", 0, 1)
    actual_manifest_sha = _manifest_sha(manifest)
    manifest[mcr.MANIFEST_FILE_SHA_KEY] = actual_manifest_sha
    rec = _attach_assignment(
        _record(0, [_field("region", "North America")]),
        "A0001",
        "alice",
        0,
        1,
        package_manifest_sha256="0" * 64,
    )
    assert actual_manifest_sha != rec["run"]["assignment"]["package_manifest_sha256"]
    _write(result, [rec])

    _records, report = mcr.merge_results(
        [result],
        dimensions=None,
        db_path=None,
        package_manifests=[manifest],
    )

    assert not report["accepted"]
    assert any("package_manifest_sha256 mismatch" in error for error in report["errors"])
