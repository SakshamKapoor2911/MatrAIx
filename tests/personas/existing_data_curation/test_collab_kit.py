import io
import json
import os
import shlex
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
import backends  # noqa: E402
import conformance  # noqa: E402
import codex_json_backend  # noqa: E402
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


def test_harness_can_resume_with_different_model_and_preserve_unit_provenance(
    tmp_path, monkeypatch
):
    out = tmp_path / "results.jsonl"
    tasks = tmp_path / "tasks.jsonl"
    dims = tmp_path / "dimensions.json"
    tasks.write_text('{"global_idx":0,"task_id":"t0","qid":"Q0"}\n', encoding="utf-8")
    dims.write_text(
        json.dumps(
            [
                {"id": "field_a", "category": "C1", "values": []},
                {"id": "field_b", "category": "C2", "values": []},
            ]
        ),
        encoding="utf-8",
    )
    base = [
        "--tasks",
        str(tasks),
        "--dimensions",
        str(dims),
        "--out",
        str(out),
        "--backend",
        "mock",
        "--jobs",
        "1",
        "--max-failures",
        "1",
    ]

    def first_model(profile, dims_batch, **kw):
        if dims_batch[0]["category"] == "C2":
            raise RuntimeError("quota exhausted")
        return [
            {
                "field_id": "field_a",
                "value": None,
                "confidence": 0.0,
                "evidence": "",
                "assignment_type": "unsupported",
            }
        ]

    monkeypatch.setattr(harness.solver, "attribute", first_model)
    assert harness.main(base + ["--model", "first-model"]) == 1
    progress_rows = [
        json.loads(line)
        for line in out.with_name(out.name + ".progress.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert progress_rows[0]["run"]["model"] == "first-model"

    def second_model(profile, dims_batch, **kw):
        return [
            {
                "field_id": "field_b",
                "value": None,
                "confidence": 0.0,
                "evidence": "",
                "assignment_type": "unsupported",
            }
        ]

    monkeypatch.setattr(harness.solver, "attribute", second_model)
    assert harness.main(base + ["--model", "second-model"]) == 0
    rows = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    assert rows[0]["model"] == "mixed"
    assert rows[0]["run"]["mixed_provenance"] is True
    assert {run["model"] for run in rows[0]["run"]["unit_runs"]} == {
        "first-model",
        "second-model",
    }
    assert {field["field_id"]: field["run"]["model"] for field in rows[0]["fields"]} == {
        "field_a": "first-model",
        "field_b": "second-model",
    }


def test_harness_stops_after_failure_budget(tmp_path, monkeypatch, capsys):
    out = tmp_path / "results.jsonl"
    tasks = tmp_path / "tasks.jsonl"
    dims = tmp_path / "dimensions.json"
    tasks.write_text(
        '{"global_idx":0}\n{"global_idx":1}\n{"global_idx":2}\n',
        encoding="utf-8",
    )
    dims.write_text(
        json.dumps([{"id": "source_entity_type", "category": "C", "values": ["wiki_person"]}]),
        encoding="utf-8",
    )
    calls = {"n": 0}

    def always_fails(profile, dims, **kw):
        calls["n"] += 1
        raise RuntimeError("quota exhausted")

    monkeypatch.setattr(harness.solver, "attribute", always_fails)

    rc = harness.main(
        ["--tasks", str(tasks), "--dimensions", str(dims), "--out", str(out)]
        + ["--backend", "mock", "--jobs", "1", "--max-failures", "2"]
    )

    assert rc == 1
    assert calls["n"] == 2
    assert "Stopping after 2 failed unit(s)" in capsys.readouterr().err


def test_harness_writes_failures_log_for_owner(tmp_path, monkeypatch):
    """Failures are persisted to <out>.failures.jsonl (with the full per-unit
    error + context) so a worker can send them to the owner; --restart clears it."""
    out = tmp_path / "results.jsonl"
    tasks = tmp_path / "tasks.jsonl"
    dims = tmp_path / "dimensions.json"
    tasks.write_text('{"global_idx":0}\n', encoding="utf-8")
    dims.write_text(json.dumps([{"id": "x", "category": "C", "values": []}]), encoding="utf-8")
    base = ["--tasks", str(tasks), "--dimensions", str(dims), "--out", str(out),
            "--backend", "mock", "--jobs", "1"]

    def boom(profile, dims, **kw):
        raise RuntimeError("claude-code-acp exited 1: 401 Unauthorized\n[claude stdout]\n{...}")

    monkeypatch.setattr(harness.solver, "attribute", boom)
    assert harness.main(base) == 1

    fl = harness.failures_path(out)
    recs = [json.loads(l) for l in fl.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert recs and recs[0]["global_idx"] == 0 and recs[0]["category"] == "C"
    assert recs[0]["backend"] == "mock"
    assert "401 Unauthorized" in recs[0]["error"]  # full error preserved, not blank

    # A clean run from scratch clears the stale failures log and writes no new one.
    monkeypatch.setattr(harness.solver, "attribute", lambda p, d, **k: [
        {"field_id": str(x["id"]), "value": None, "confidence": 0.0,
         "evidence": "", "assignment_type": "unsupported"} for x in d])
    assert harness.main(base + ["--restart"]) == 0
    assert not fl.exists()  # no empty failures file on a clean run


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


def test_collab_backend_registry_is_limited_to_package_choices():
    assert sorted(backends.BACKENDS) == ["claude-code-acp", "codex-acp", "mock"]
    assert backends.create_backend("codex-acp", None).effort == "high"


def test_solver_sets_default_codex_command(monkeypatch):
    monkeypatch.delenv("WIKI_COLLAB_CODEX_CMD", raising=False)

    solver._ensure_default_command("codex-acp")

    command = os.environ["WIKI_COLLAB_CODEX_CMD"]
    assert "codex_json_backend.py" in command
    assert sys.executable in command


def test_solver_default_adapter_command_quotes_paths_with_spaces(monkeypatch, tmp_path):
    monkeypatch.delenv("WIKI_COLLAB_CODEX_CMD", raising=False)
    fake_kit = tmp_path / "pkg with spaces" / "collab_kit"
    fake_kit.mkdir(parents=True)
    monkeypatch.setattr(solver, "KIT_DIR", fake_kit)

    solver._ensure_default_command("codex-acp")

    argv = shlex.split(os.environ["WIKI_COLLAB_CODEX_CMD"])
    assert argv == [sys.executable, str(fake_kit / "codex_json_backend.py")]


def test_codex_json_backend_passes_reasoning_effort(monkeypatch):
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        output_path = Path(cmd[cmd.index("--output-last-message") + 1])
        output_path.write_text(json.dumps({"fields": []}), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(codex_json_backend.subprocess, "run", fake_run)
    monkeypatch.setattr(codex_json_backend.sys, "stdin", io.StringIO("prompt"))
    monkeypatch.setenv("WIKI_COLLAB_CODEX_BIN", "codex-test")
    monkeypatch.setenv("WIKI_COLLAB_REQUESTED_MODEL", "gpt-5.5")
    monkeypatch.setenv("WIKI_COLLAB_EFFORT", "xhigh")

    rc = codex_json_backend.main()

    assert rc == 0
    assert "model_reasoning_effort=xhigh" in captured["cmd"]


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


def test_configure_interactive_uses_codex_choices(tmp_path, monkeypatch):
    monkeypatch.setattr(assignment_runner, "SETTINGS_PATH", tmp_path / "settings.yaml")
    answers = iter(["1", "3", "2"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    settings = assignment_runner.configure_interactive({})

    assert settings["backend"] == "codex-acp"
    assert settings["model"] == "gpt-5.5"
    assert settings["effort"] == "xhigh"
    assert settings["jobs"] == "2"
    assert settings["command_override"] == ""


def test_effort_menu_excludes_too_low_options():
    for choices in assignment_runner.EFFORT_CHOICES_BY_BACKEND.values():
        values = {value for value, _description in choices}
        assert "minimal" not in values
        assert "low" not in values


def test_configure_interactive_normalizes_old_low_effort(tmp_path, monkeypatch):
    monkeypatch.setattr(assignment_runner, "SETTINGS_PATH", tmp_path / "settings.yaml")
    # The wizard now runs without a "keep these settings?" gate; accepting the
    # defaults at each step (backend, effort, jobs) must surface the normalized
    # effort ("low" is no longer valid -> defaults to "high"), never "low".
    answers = iter(["", "", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    settings = assignment_runner.configure_interactive({
        "backend": "codex-acp",
        "model": "gpt-5.5",
        "effort": "low",
        "jobs": "4",
        "command_override": "",
    })

    assert settings["backend"] == "codex-acp"
    assert settings["effort"] == "high"


def test_configure_interactive_uses_claude_choices(tmp_path, monkeypatch):
    monkeypatch.setattr(assignment_runner, "SETTINGS_PATH", tmp_path / "settings.yaml")
    # backend=claude(2), effort=max(4), jobs= typed directly as "8"
    answers = iter(["2", "4", "8"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    settings = assignment_runner.configure_interactive({})

    assert settings["backend"] == "claude-code-acp"
    assert settings["model"] == "claude-opus-4-8"
    assert settings["effort"] == "max"
    assert settings["jobs"] == "8"
    assert settings["command_override"] == ""


def test_prompt_jobs_accepts_custom_number(monkeypatch):
    answers = iter(["12"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert assignment_runner._prompt_jobs("4") == "12"


def test_prompt_jobs_enter_keeps_default(monkeypatch):
    answers = iter([""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert assignment_runner._prompt_jobs("6") == "6"


def test_prompt_jobs_reprompts_until_in_range(monkeypatch):
    # too low, then above MAX_JOBS, then a valid value
    answers = iter(["0", str(assignment_runner.MAX_JOBS + 1), "3"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert assignment_runner._prompt_jobs("4") == "3"


def test_assignment_runner_no_longer_accepts_install_uv_flag():
    try:
        assignment_runner.parse_args(["--install-uv"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("--install-uv should not be accepted")


def test_configured_settings_normalizes_disallowed_direct_values(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "backend: openai-api\nmodel: old-model\neffort: low\njobs: 99\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(assignment_runner, "SETTINGS_PATH", settings_path)
    args = assignment_runner.parse_args(["--run"])

    settings = assignment_runner.configured_settings(args)

    assert settings["backend"] == "codex-acp"
    assert settings["model"] == "gpt-5.5"
    assert settings["effort"] == "high"
    # jobs is now free-form numeric, clamped into [1, MAX_JOBS] (99 -> 32)
    assert settings["jobs"] == str(assignment_runner.MAX_JOBS)


def test_check_progress_settings_rejects_missing_active_run(tmp_path, monkeypatch):
    progress_path = tmp_path / "results.jsonl.progress.jsonl"
    active_path = tmp_path / ".wiki_collab_active_run.yaml"
    progress_path.write_text('{"global_idx":0,"category":"C","fields":[]}\n', encoding="utf-8")
    monkeypatch.setattr(assignment_runner, "PROGRESS_PATH", progress_path)
    monkeypatch.setattr(assignment_runner, "ACTIVE_RUN_PATH", active_path)

    try:
        assignment_runner._check_progress_settings(
            assignment_runner.DEFAULTS,
            restart=False,
            warnings=[],
        )
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("progress without active-run metadata should be rejected")


def test_print_environment_checks_selected_backend_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(assignment_runner, "SETTINGS_PATH", tmp_path / "settings.yaml")
    monkeypatch.setattr(assignment_runner, "ensure_integrity", lambda root: [])

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 127, stdout="", stderr="missing")

    monkeypatch.setattr(assignment_runner.subprocess, "run", fake_run)

    rc = assignment_runner.print_environment(tmp_path)

    assert rc == 1
    captured = capsys.readouterr()
    assert "Codex CLI" in captured.out
    assert "FAIL" in captured.out


def test_confirm_real_run_gates_non_mock(monkeypatch):
    """--yes is meaningful: mock never prompts, --yes proceeds, an interactive
    run honors y/N, and a non-interactive run without --yes is refused."""
    ar = assignment_runner

    class _FakeStdin:
        def __init__(self, tty):
            self._tty = tty

        def isatty(self):
            return self._tty

    assert ar._confirm_real_run({"backend": "mock"}, assume_yes=False) is True
    assert ar._confirm_real_run(
        {"backend": "codex-acp", "model": "gpt-5.5", "effort": "high"}, assume_yes=True) is True

    monkeypatch.setattr(ar.sys, "stdin", _FakeStdin(False))
    assert ar._confirm_real_run({"backend": "codex-acp"}, assume_yes=False) is False  # refuse

    monkeypatch.setattr(ar.sys, "stdin", _FakeStdin(True))
    monkeypatch.setattr("builtins.input", lambda *a, **k: "y")
    assert ar._confirm_real_run({"backend": "codex-acp"}, assume_yes=False) is True
    monkeypatch.setattr("builtins.input", lambda *a, **k: "n")
    assert ar._confirm_real_run({"backend": "codex-acp"}, assume_yes=False) is False


def test_main_run_refuses_real_backend_without_yes(tmp_path, monkeypatch):
    """A bare `--run` (default backend codex-acp) on a non-interactive shell must
    NOT silently start a real run — it returns 1 before reaching run_harness."""
    monkeypatch.setattr(assignment_runner, "SETTINGS_PATH", tmp_path / "none.yaml")

    class _FakeStdin:
        def isatty(self):
            return False

    monkeypatch.setattr(assignment_runner.sys, "stdin", _FakeStdin())
    assert assignment_runner.main(["--run"]) == 1
