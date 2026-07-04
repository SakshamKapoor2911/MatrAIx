"""Tests for the host-native Harbor environment."""

from __future__ import annotations

from pathlib import Path

import pytest

from harbor.environments.host import HostEnvironment
from harbor.models.task.config import EnvironmentConfig
from harbor.models.trial.paths import TrialPaths


def test_host_environment_resolves_container_paths(tmp_path: Path) -> None:
    trial_dir = tmp_path / "trial"
    trial_paths = TrialPaths(trial_dir=trial_dir)
    env = HostEnvironment(
        environment_dir=tmp_path / "environment",
        environment_name="persona-survey",
        session_id="persona-survey__abc",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(),
    )

    output = env.resolve_container_path("/app/output/survey_result.json")
    assert output == trial_paths.host_artifact_path("main", "/app/output/survey_result.json").resolve()
    assert env.resolve_container_path("/logs/verifier/reward.txt") == (trial_paths.verifier_dir / "reward.txt").resolve()
    assert env.resolve_container_path("/tests/test_state.py") == (trial_paths.trial_dir / "host_tests" / "test_state.py").resolve()

    with pytest.raises(ValueError):
        env.resolve_container_path("/unknown/path")


@pytest.mark.asyncio
async def test_host_exec_exports_verifier_and_tests_dirs(tmp_path: Path) -> None:
    trial_dir = tmp_path / "trial"
    trial_paths = TrialPaths(trial_dir=trial_dir)
    tests_root = trial_dir / "host_tests"
    tests_root.mkdir(parents=True)
    (tests_root / "probe.sh").write_text(
        '#!/usr/bin/env bash\n'
        'printf "tests=%s\\n" "${HARBOR_TESTS_DIR:-}"\n'
        'printf "verifier=%s\\n" "${HARBOR_VERIFIER_DIR:-}"\n'
        'printf "output=%s\\n" "${PERSONABENCH_OUTPUT_DIR:-}"\n',
        encoding="utf-8",
    )
    env = HostEnvironment(
        environment_dir=tmp_path / "environment",
        environment_name="persona-survey",
        session_id="persona-survey__probe",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(),
    )
    output_dir = env.resolve_container_path("/app/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = await env.exec("bash /tests/probe.sh")
    assert result.return_code == 0
    stdout = result.stdout or ""
    assert f"tests={tests_root.resolve()}" in stdout
    assert f"verifier={trial_paths.verifier_dir.resolve()}" in stdout
    assert f"output={output_dir}" in stdout


def test_host_rewrite_command_paths_rewrites_verifier_stdout(tmp_path: Path) -> None:
    trial_paths = TrialPaths(trial_dir=tmp_path / "trial")
    env = HostEnvironment(
        environment_dir=tmp_path / "environment",
        environment_name="persona-survey",
        session_id="persona-survey__rewrite",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(),
    )
    command = "('/tests/test.sh') > '/logs/verifier/test-stdout.txt' 2>&1"
    rewritten = env._normalize_shell_invocation(env._rewrite_command_paths(command))
    assert "/tests/" not in rewritten
    assert "/logs/verifier" not in rewritten
    assert str((trial_paths.trial_dir / "host_tests" / "test.sh").resolve()) in rewritten
    assert str((trial_paths.verifier_dir / "test-stdout.txt").resolve()) in rewritten
    assert rewritten.startswith("bash ")


@pytest.mark.asyncio
async def test_host_exec_with_relative_trial_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    trial_dir = Path("jobs/trial-relative")
    absolute_trial = repo / trial_dir
    trial_paths = TrialPaths(trial_dir=trial_dir)
    tests_root = absolute_trial / "host_tests"
    tests_root.mkdir(parents=True)
    output_dir = trial_paths.host_artifact_path("main", "/app/output")
    output_dir.mkdir(parents=True)
    (tests_root / "test.sh").write_text(
        '#!/usr/bin/env bash\n'
        "set -euo pipefail\n"
        'source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"\n'
        'echo 1 > "${VERIFIER_DIR}/reward.txt"\n',
        encoding="utf-8",
    )
    (tests_root / "verifier_env.sh").write_text(
        (Path(__file__).resolve().parents[3]
         / "application/tasks/persona-survey/tests/verifier_env.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    monkeypatch.chdir(repo)
    env = HostEnvironment(
        environment_dir=repo / "environment",
        environment_name="persona-survey",
        session_id="persona-survey__relative",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(),
    )
    command = "('/tests/test.sh') > '/logs/verifier/test-stdout.txt' 2>&1"
    result = await env.exec(command)
    assert result.return_code == 0
    assert (absolute_trial / "verifier" / "reward.txt").read_text(encoding="utf-8").strip() == "1"


@pytest.mark.asyncio
async def test_host_download_dir_noops_when_source_equals_destination(tmp_path: Path) -> None:
    trial_paths = TrialPaths(trial_dir=tmp_path / "trial")
    output_dir = trial_paths.host_artifact_path("main", "/app/output")
    output_dir.mkdir(parents=True)
    (output_dir / "transcript.json").write_text('{"domain":"movie","turns":[]}', encoding="utf-8")
    env = HostEnvironment(
        environment_dir=tmp_path / "environment",
        environment_name="recommender-agent_chat_api",
        session_id="recommender-agent_chat_api__noop",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(),
    )
    await env.download_dir("/app/output", output_dir)
    assert (output_dir / "transcript.json").is_file()


@pytest.mark.asyncio
async def test_host_exec_runs_verifier_style_command(tmp_path: Path) -> None:
    trial_dir = tmp_path / "trial"
    trial_paths = TrialPaths(trial_dir=trial_dir)
    tests_root = trial_dir / "host_tests"
    tests_root.mkdir(parents=True)
    output_dir = trial_paths.host_artifact_path("main", "/app/output")
    output_dir.mkdir(parents=True)
    (tests_root / "test.sh").write_text(
        '#!/usr/bin/env bash\n'
        "set -euo pipefail\n"
        'source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"\n'
        'echo 1 > "${VERIFIER_DIR}/reward.txt"\n',
        encoding="utf-8",
    )
    (tests_root / "verifier_env.sh").write_text(
        (Path(__file__).resolve().parents[3]
         / "application/tasks/persona-survey/tests/verifier_env.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    env = HostEnvironment(
        environment_dir=tmp_path / "environment",
        environment_name="persona-survey",
        session_id="persona-survey__verify",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(),
    )
    command = "('/tests/test.sh') > '/logs/verifier/test-stdout.txt' 2>&1"
    result = await env.exec(command)
    assert result.return_code == 0
    assert (trial_paths.verifier_dir / "reward.txt").read_text(encoding="utf-8").strip() == "1"
    assert (trial_paths.verifier_dir / "test-stdout.txt").is_file()
