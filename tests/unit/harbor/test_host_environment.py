"""Tests for the host-native Harbor environment."""

from __future__ import annotations

from pathlib import Path

import pytest

from harbor.environments.host import HostEnvironment
from harbor.models.task.config import EnvironmentConfig
from harbor.models.trial.paths import TrialPaths


_HOST_VERIFIER_ENV = """\
# Shared host/docker verifier path resolution (sourced from test.sh).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERIFIER_DIR="${HARBOR_VERIFIER_DIR:-/logs/verifier}"
if ! mkdir -p "${VERIFIER_DIR}" 2>/dev/null; then
  echo "error: cannot create verifier directory: ${VERIFIER_DIR}" >&2
  exit 1
fi
mkdir -p "${VERIFIER_DIR}"
"""


def _host_env(
    tmp_path: Path,
    *,
    session_id: str,
    tests_dir: Path,
    trial_dir: Path | None = None,
) -> HostEnvironment:
    trial_paths = TrialPaths(trial_dir=trial_dir or (tmp_path / "trial"))
    return HostEnvironment(
        environment_dir=tmp_path / "environment",
        environment_name="shared-survey-form",
        session_id=session_id,
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(),
        tests_dir=tests_dir,
    )


def test_host_environment_resolves_container_paths(tmp_path: Path) -> None:
    tests_dir = tmp_path / "task" / "tests"
    tests_dir.mkdir(parents=True)
    trial_paths = TrialPaths(trial_dir=tmp_path / "trial")
    env = _host_env(tmp_path, session_id="shared-survey-form__abc", tests_dir=tests_dir)

    output = env.resolve_container_path("/app/output/survey_result.json")
    assert output == trial_paths.host_artifact_path("main", "/app/output/survey_result.json").resolve()
    assert env.resolve_container_path("/logs/verifier/reward.txt") == (
        trial_paths.verifier_dir / "reward.txt"
    ).resolve()
    assert env.resolve_container_path("/tests/test_state.py") == (
        tests_dir / "test_state.py"
    ).resolve()

    with pytest.raises(ValueError):
        env.resolve_container_path("/unknown/path")


@pytest.mark.asyncio
async def test_host_exec_exports_verifier_and_tests_dirs(tmp_path: Path) -> None:
    tests_dir = tmp_path / "task" / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "probe.sh").write_text(
        '#!/usr/bin/env bash\n'
        'printf "tests=%s\\n" "${HARBOR_TESTS_DIR:-}"\n'
        'printf "verifier=%s\\n" "${HARBOR_VERIFIER_DIR:-}"\n'
        'printf "output=%s\\n" "${PLAYGROUND_OUTPUT_DIR:-}"\n',
        encoding="utf-8",
    )
    env = _host_env(tmp_path, session_id="shared-survey-form__probe", tests_dir=tests_dir)
    output_dir = env.resolve_container_path("/app/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = await env.exec("bash /tests/probe.sh")
    assert result.return_code == 0
    stdout = result.stdout or ""
    assert f"tests={tests_dir.resolve()}" in stdout
    assert f"verifier={env.trial_paths.verifier_dir.resolve()}" in stdout
    assert f"output={output_dir}" in stdout


def test_host_rewrite_command_paths_rewrites_verifier_stdout(tmp_path: Path) -> None:
    tests_dir = tmp_path / "task" / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    trial_paths = TrialPaths(trial_dir=tmp_path / "trial")
    env = _host_env(tmp_path, session_id="shared-survey-form__rewrite", tests_dir=tests_dir)
    command = "('/tests/test.sh') > '/logs/verifier/test-stdout.txt' 2>&1"
    rewritten = env._normalize_shell_invocation(env._rewrite_command_paths(command))
    assert "'/tests/" not in rewritten
    assert "'/logs/verifier" not in rewritten
    assert str((tests_dir / "test.sh").resolve()) in rewritten
    assert str((trial_paths.verifier_dir / "test-stdout.txt").resolve()) in rewritten
    assert rewritten.startswith("bash ")


@pytest.mark.asyncio
async def test_host_exec_with_relative_trial_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    tests_dir = repo / "application" / "tasks" / "example-survey" / "tests"
    tests_dir.mkdir(parents=True)
    trial_dir = Path("jobs/trial-relative")
    absolute_trial = repo / trial_dir
    trial_paths = TrialPaths(trial_dir=trial_dir)
    monkeypatch.chdir(repo)
    output_dir = trial_paths.host_artifact_path("main", "/app/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "test.sh").write_text(
        '#!/usr/bin/env bash\n'
        "set -euo pipefail\n"
        'source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"\n'
        'echo 1 > "${VERIFIER_DIR}/reward.txt"\n',
        encoding="utf-8",
    )
    (tests_dir / "verifier_env.sh").write_text(_HOST_VERIFIER_ENV, encoding="utf-8")
    env = _host_env(
        repo,
        session_id="shared-survey-form__relative",
        tests_dir=tests_dir,
        trial_dir=trial_dir,
    )
    command = "('/tests/test.sh') > '/logs/verifier/test-stdout.txt' 2>&1"
    result = await env.exec(command)
    assert result.return_code == 0
    assert (absolute_trial / "verifier" / "reward.txt").read_text(encoding="utf-8").strip() == "1"
    assert not (absolute_trial / "host_tests").exists()


@pytest.mark.asyncio
async def test_host_upload_dir_skips_repo_tests(tmp_path: Path) -> None:
    tests_dir = tmp_path / "task" / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    env = _host_env(tmp_path, session_id="shared-survey-form__upload", tests_dir=tests_dir)
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "test.sh").write_text("#!/usr/bin/env bash\necho overwritten\n", encoding="utf-8")

    await env.upload_dir(staging, "/tests")
    assert (tests_dir / "test.sh").read_text(encoding="utf-8") == "#!/usr/bin/env bash\n"


@pytest.mark.asyncio
async def test_host_download_dir_noops_when_source_equals_destination(tmp_path: Path) -> None:
    trial_paths = TrialPaths(trial_dir=tmp_path / "trial")
    output_dir = trial_paths.host_artifact_path("main", "/app/output")
    output_dir.mkdir(parents=True)
    (output_dir / "transcript.json").write_text('{"domain":"movie","turns":[]}', encoding="utf-8")
    tests_dir = tmp_path / "task" / "tests"
    tests_dir.mkdir(parents=True)
    env = _host_env(tmp_path, session_id="chat_recai__noop", tests_dir=tests_dir)
    await env.download_dir("/app/output", output_dir)
    assert (output_dir / "transcript.json").is_file()


@pytest.mark.asyncio
async def test_host_exec_runs_verifier_style_command(tmp_path: Path) -> None:
    tests_dir = tmp_path / "task" / "tests"
    tests_dir.mkdir(parents=True)
    trial_paths = TrialPaths(trial_dir=tmp_path / "trial")
    output_dir = trial_paths.host_artifact_path("main", "/app/output")
    output_dir.mkdir(parents=True)
    (tests_dir / "test.sh").write_text(
        '#!/usr/bin/env bash\n'
        "set -euo pipefail\n"
        'source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"\n'
        'echo 1 > "${VERIFIER_DIR}/reward.txt"\n',
        encoding="utf-8",
    )
    (tests_dir / "verifier_env.sh").write_text(_HOST_VERIFIER_ENV, encoding="utf-8")
    env = _host_env(tmp_path, session_id="shared-survey-form__verify", tests_dir=tests_dir)
    command = "('/tests/test.sh') > '/logs/verifier/test-stdout.txt' 2>&1"
    result = await env.exec(command)
    assert result.return_code == 0
    assert (trial_paths.verifier_dir / "reward.txt").read_text(encoding="utf-8").strip() == "1"
    assert (trial_paths.verifier_dir / "test-stdout.txt").is_file()
    assert not (trial_paths.trial_dir / "host_tests").exists()
