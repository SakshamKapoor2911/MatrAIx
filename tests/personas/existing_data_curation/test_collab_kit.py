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


def _base_args(out):
    return [
        "--tasks", str(KIT / "sample" / "tasks.jsonl"),
        "--dimensions", str(KIT / "sample" / "dimensions.json"),
        "--out", str(out),
    ]


def test_harness_resumes_after_failure(tmp_path, monkeypatch):
    """A failed unit (e.g. quota exhausted) stays pending; re-running finishes it."""
    out = tmp_path / "results.jsonl"
    args = _base_args(out) + ["--backend", "mock", "--jobs", "1"]

    failed_once = {"done": False}

    def flaky(profile, dims, **kw):
        if not failed_once["done"]:
            failed_once["done"] = True
            raise RuntimeError("simulated quota exhaustion")
        return [{"field_id": str(d["id"]), "value": None, "confidence": 0.0,
                 "evidence": "", "assignment_type": "unsupported"} for d in dims]

    monkeypatch.setattr(harness.solver, "attribute", flaky)

    rc1 = harness.main(args)
    assert rc1 == 1  # at least one unit failed -> NOT COMPLETE
    assert out.with_name(out.name + ".progress.jsonl").exists()

    rc2 = harness.main(args)  # same command resumes the pending unit(s)
    assert rc2 == 0
    results = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
    errors, _ = conformance.check_results(results, _dims(), _load("tasks.jsonl"))
    assert errors == []


def test_harness_status_reports_without_running(tmp_path, monkeypatch, capsys):
    out = tmp_path / "results.jsonl"
    called = {"n": 0}

    def counting(profile, dims, **kw):
        called["n"] += 1
        return [{"field_id": str(d["id"]), "value": None, "confidence": 0.0,
                 "evidence": "", "assignment_type": "unsupported"} for d in dims]

    monkeypatch.setattr(harness.solver, "attribute", counting)
    rc = harness.main(_base_args(out) + ["--status"])
    assert rc == 0
    assert called["n"] == 0  # --status attempts no work
    assert "Progress:" in capsys.readouterr().out


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
