from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from playground.host_verifier import maybe_run_host_verifier, source_relative_path


def _artifact_source(tmp_root: Path) -> str:
    return str(tmp_root / "submission")


def _test_sh(artifact_source: str) -> str:
    return f"""\
#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import json
import os
from pathlib import Path

output_root = (
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or os.environ.get("HARBOR_OUTPUT_DIR")
    or {artifact_source!r}
)
decision_path = Path(output_root) / "decision.json"
if not decision_path.is_file():
    raise SystemExit("missing decision.json")

verifier_dir = Path(os.environ.get("HARBOR_VERIFIER_DIR") or "/logs/verifier")
verifier_dir.mkdir(parents=True, exist_ok=True)
(verifier_dir / "reward.txt").write_text("1")
(verifier_dir / "structured_output.json").write_text(json.dumps({{"ok": True}}))
PY
"""


def _write_fake_task(
    repo_root: Path, task_rel: str, *, artifact_source: str, timeout_sec: float = 30.0
) -> None:
    task_dir = repo_root / task_rel
    (task_dir / "tests").mkdir(parents=True, exist_ok=True)
    (task_dir / "task.toml").write_text(
        (
            f'artifacts = ["{artifact_source}"]\n'
            f"[verifier]\ntimeout_sec = {timeout_sec}\n"
        ),
        encoding="utf-8",
    )
    (task_dir / "tests" / "test.sh").write_text(
        _test_sh(artifact_source), encoding="utf-8"
    )


def _write_trial(
    trial_dir: Path,
    task_rel: str,
    *,
    artifact_source: str,
    with_decision: bool,
    with_exception: bool,
) -> None:
    trial_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "config.json").write_text(
        json.dumps({"task": {"path": task_rel}}), encoding="utf-8"
    )
    downloaded_dir = trial_dir / "artifacts" / Path(source_relative_path(artifact_source))
    downloaded_dir.mkdir(parents=True, exist_ok=True)
    if with_decision:
        (downloaded_dir / "decision.json").write_text("{}", encoding="utf-8")

    result_payload: dict = {}
    if with_exception:
        result_payload["exception_info"] = {
            "exception_type": "RewardFileNotFoundError",
            "exception_message": "No reward file found",
        }
    (trial_dir / "result.json").write_text(json.dumps(result_payload), encoding="utf-8")


def test_source_relative_path_matches_harbor_mapping():
    assert str(source_relative_path("/app/output")) == "app/output"


def test_host_verifier_scores_app_output_without_filesystem_staging(tmp_path: Path):
    repo_root = tmp_path / "repo"
    task_rel = "application/tasks/fake-task"
    _write_fake_task(repo_root, task_rel, artifact_source="/app/output")

    trial_dir = tmp_path / "trial"
    _write_trial(
        trial_dir,
        task_rel,
        artifact_source="/app/output",
        with_decision=True,
        with_exception=True,
    )

    ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
    assert ran is True
    assert (trial_dir / "verifier" / "reward.txt").read_text(encoding="utf-8").strip() == "1"


def test_host_verifier_scores_trial_and_clears_stale_exception(tmp_path: Path):
    stage_root = Path(tempfile.mkdtemp(prefix="matraix-host-verifier-test-"))
    artifact_source = _artifact_source(stage_root)
    try:
        repo_root = tmp_path / "repo"
        task_rel = "application/tasks/fake-task"
        _write_fake_task(repo_root, task_rel, artifact_source=artifact_source)

        trial_dir = tmp_path / "trial"
        _write_trial(
            trial_dir,
            task_rel,
            artifact_source=artifact_source,
            with_decision=True,
            with_exception=True,
        )

        ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)

        assert ran is True
        assert (trial_dir / "verifier" / "reward.txt").read_text(encoding="utf-8").strip() == "1"
        assert (trial_dir / "verifier" / "structured_output.json").is_file()

        result = json.loads((trial_dir / "result.json").read_text(encoding="utf-8"))
        assert result["exception_info"] is None
        assert result["verifier_result"] == {"rewards": {"reward": 1.0}}
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def test_host_verifier_skips_when_reward_already_present(tmp_path: Path):
    stage_root = Path(tempfile.mkdtemp(prefix="matraix-host-verifier-test-"))
    artifact_source = _artifact_source(stage_root)
    try:
        repo_root = tmp_path / "repo"
        task_rel = "application/tasks/fake-task"
        _write_fake_task(repo_root, task_rel, artifact_source=artifact_source)

        trial_dir = tmp_path / "trial"
        _write_trial(
            trial_dir,
            task_rel,
            artifact_source=artifact_source,
            with_decision=True,
            with_exception=True,
        )
        verifier_dir = trial_dir / "verifier"
        verifier_dir.mkdir(parents=True, exist_ok=True)
        (verifier_dir / "reward.txt").write_text("1", encoding="utf-8")

        ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
        assert ran is False
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def test_host_verifier_skips_when_nothing_was_submitted(tmp_path: Path):
    stage_root = Path(tempfile.mkdtemp(prefix="matraix-host-verifier-test-"))
    artifact_source = _artifact_source(stage_root)
    try:
        repo_root = tmp_path / "repo"
        task_rel = "application/tasks/fake-task"
        _write_fake_task(repo_root, task_rel, artifact_source=artifact_source)

        trial_dir = tmp_path / "trial"
        _write_trial(
            trial_dir,
            task_rel,
            artifact_source=artifact_source,
            with_decision=False,
            with_exception=True,
        )

        ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
        assert ran is False
        result = json.loads((trial_dir / "result.json").read_text(encoding="utf-8"))
        assert result["exception_info"] is not None
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def test_host_verifier_restores_pre_existing_source_contents(tmp_path: Path):
    stage_root = Path(tempfile.mkdtemp(prefix="matraix-host-verifier-test-"))
    artifact_source = _artifact_source(stage_root)
    try:
        repo_root = tmp_path / "repo"
        task_rel = "application/tasks/fake-task"
        _write_fake_task(repo_root, task_rel, artifact_source=artifact_source)

        trial_dir = tmp_path / "trial"
        _write_trial(
            trial_dir,
            task_rel,
            artifact_source=artifact_source,
            with_decision=True,
            with_exception=True,
        )

        stray = Path(artifact_source)
        stray.mkdir(parents=True, exist_ok=True)
        sentinel = stray / "unrelated-concurrent-file.txt"
        sentinel.write_text("keep-me", encoding="utf-8")

        ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
        assert ran is True
        assert sentinel.is_file()
        assert sentinel.read_text(encoding="utf-8") == "keep-me"
        assert not (stray / "decision.json").is_file()
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)
