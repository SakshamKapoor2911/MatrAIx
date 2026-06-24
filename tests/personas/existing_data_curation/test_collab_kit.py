import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
KIT = REPO_ROOT / "personas/existing_data_curation/wiki_collab/collab_kit"
if str(KIT) not in sys.path:
    sys.path.insert(0, str(KIT))

import conformance  # noqa: E402
import harness  # noqa: E402


def _load(name: str):
    return [json.loads(l) for l in (KIT / "sample" / name).read_text().splitlines() if l.strip()]


def _dims():
    return json.loads((KIT / "sample" / "dimensions.json").read_text())


def test_schemas_are_valid_json():
    for s in ("task.input.schema.json", "result.output.schema.json", "dimensions.schema.json"):
        json.loads((KIT / "schemas" / s).read_text())


def test_sample_results_conform():
    errors, _ = conformance.check_results(_load("results.jsonl"), _dims(), _load("tasks.jsonl"))
    assert errors == []


def test_conformance_catches_violations():
    bad = [
        {
            "global_idx": 0,
            "fields": [
                # value not in allowed values + confidence out of range
                {"field_id": "age_bracket", "value": "ninety", "confidence": 1.5,
                 "evidence": "x", "assignment_type": "direct"},
                # unknown field_id + bad assignment_type
                {"field_id": "not_a_real_dim", "value": "X", "confidence": 0.5,
                 "evidence": "y", "assignment_type": "guess"},
            ],
        }
    ]
    errors, _ = conformance.check_results(bad, _dims())
    joined = " | ".join(errors)
    assert "not in allowed values" in joined
    assert "confidence must be a number in [0,1]" in joined
    assert "not in the dimensions spec" in joined
    assert "assignment_type" in joined


def test_conformance_requires_evidence_for_nonnull_value():
    rec = [{"global_idx": 0, "fields": [
        {"field_id": "age_bracket", "value": "55–64", "confidence": 0.5,
         "evidence": "", "assignment_type": "direct"}]}]
    errors, _ = conformance.check_results(rec, _dims())
    assert any("evidence is empty" in e for e in errors)


def test_duplicate_global_idx_is_an_error():
    recs = [{"global_idx": 0, "fields": []}, {"global_idx": 0, "fields": []}]
    errors, _ = conformance.check_results(recs)
    assert any("duplicate global_idx" in e for e in errors)


def test_harness_mock_run_is_conformant(tmp_path):
    out = tmp_path / "results.jsonl"
    rc = harness.main([
        "--tasks", str(KIT / "sample" / "tasks.jsonl"),
        "--dimensions", str(KIT / "sample" / "dimensions.json"),
        "--out", str(out),
        "--backend", "mock",
    ])
    assert rc == 0
    results = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
    errors, _ = conformance.check_results(results, _dims(), _load("tasks.jsonl"))
    assert errors == []
    # mock returns one (unsupported) field per dimension
    assert len(results[0]["fields"]) == len(_dims())
