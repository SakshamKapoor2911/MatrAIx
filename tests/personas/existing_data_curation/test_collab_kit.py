import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
KIT = REPO_ROOT / "personas/existing_data_curation/wiki_collab/collab_kit"
DIMENSIONS = REPO_ROOT / "personas" / "dimensions+new.json"
if str(KIT) not in sys.path:
    sys.path.insert(0, str(KIT))

import assignment_runner  # noqa: E402  (stdlib-only; its module constants are unused here)
import conformance  # noqa: E402
import harness  # noqa: E402
import solver  # noqa: E402


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


def test_solver_sets_default_codex_command(monkeypatch):
    monkeypatch.delenv("WIKI_COLLAB_CODEX_CMD", raising=False)

    solver._ensure_default_command("codex-acp")

    command = os.environ["WIKI_COLLAB_CODEX_CMD"]
    assert "codex_json_backend.py" in command
    assert sys.executable in command


# --- assignment_runner fixes -------------------------------------------------


def test_completion_counts_units(tmp_path):
    """--validate distinguishes 'format valid' from 'run finished'."""
    (tmp_path / "tasks.jsonl").write_text(
        '{"global_idx":0}\n{"global_idx":1}\n', encoding="utf-8")
    (tmp_path / "dimensions.json").write_text(
        json.dumps([{"id": "a", "category": "C1", "values": []},
                    {"id": "b", "category": "C2", "values": []}]), encoding="utf-8")
    assert assignment_runner._completion(tmp_path) == (0, 4)  # 2 tasks x 2 categories
    (tmp_path / "results.jsonl.progress.jsonl").write_text(
        '{"global_idx":0,"category":"C1","fields":[]}\n'
        '{"global_idx":1,"category":"C2","fields":[]}\n', encoding="utf-8")
    assert assignment_runner._completion(tmp_path) == (2, 4)


def _make_profiles_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "create table profiles(global_idx integer primary key, task_id text, qid text, "
        "title text, source_url text, profile_text text, input_sha256 text)")
    conn.execute(
        "insert into profiles values(0,'t0','Q91','Abraham Lincoln','http://x',"
        "'Lincoln was the 16th US president.','abc')")
    conn.commit()
    conn.close()


def test_assignment_runner_smoke_does_not_touch_real_run(tmp_path):
    """A mock smoke test must leave the real run's checkpoint/settings untouched
    (so 'smoke-test then real run' is not blocked by a poisoned checkpoint)."""
    from personas.existing_data_curation.scripts.make_collab_package import (
        build_collab_package,
    )
    db = tmp_path / "p.sqlite"
    _make_profiles_db(db)
    pkg = tmp_path / "pkg"
    build_collab_package(
        db_path=db, dimensions_path=DIMENSIONS, out_dir=pkg,
        assignment_id="A", worker_id="w", dataset_id="d", dataset_sha256="x",
        range_start=0, range_end=1, categories=["demographic_core"],
        create_archive=False, force=True,
    )
    kit = pkg / "collab_kit"
    driver = (
        "import assignment_runner as ar;"
        "raise SystemExit(ar.run_harness({**ar.DEFAULTS,'backend':'mock',"
        "'model':'mock-model'}, smoke=True))"
    )
    rc = subprocess.run([sys.executable, "-c", driver], cwd=kit).returncode
    assert rc == 0
    # real run untouched...
    assert not (pkg / "results.jsonl").exists()
    assert not (pkg / "results.jsonl.progress.jsonl").exists()
    assert not (pkg / ".wiki_collab_settings.yaml").exists()
    # ...and the throwaway output cleaned up.
    assert not (pkg / ".smoke_results.jsonl").exists()
    assert not (pkg / ".smoke_results.jsonl.progress.jsonl").exists()
