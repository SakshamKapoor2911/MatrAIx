import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "personas/existing_data_curation/scripts"
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
