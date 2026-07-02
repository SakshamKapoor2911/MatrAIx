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
    assert output == trial_paths.host_artifact_path("main", "/app/output/survey_result.json")
    assert env.resolve_container_path("/logs/verifier/reward.txt") == trial_paths.verifier_dir / "reward.txt"
    assert env.resolve_container_path("/tests/test_state.py") == trial_paths.trial_dir / "host_tests" / "test_state.py"

    with pytest.raises(ValueError):
        env.resolve_container_path("/unknown/path")
