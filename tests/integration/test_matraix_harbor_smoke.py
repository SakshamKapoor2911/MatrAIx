"""MatrAIx harbor-smoke: oracle + hello-world in Docker (no API key)."""

from __future__ import annotations

from pathlib import Path

import pytest

from harbor.models.agent.name import AgentName
from harbor.models.environment_type import EnvironmentType
from harbor.models.trial.config import (
    AgentConfig,
    EnvironmentConfig,
    TaskConfig,
    TrialConfig,
)
from harbor.trial.trial import Trial

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.matraix_smoke,
]


async def test_harbor_smoke_hello_world_oracle(tmp_path: Path) -> None:
    """Same path as configs/jobs/example-job-recipe/harbor-smoke-local.yaml."""
    config = TrialConfig(
        task=TaskConfig(path=Path("examples/tasks/hello-world")),
        agent=AgentConfig(name=AgentName.ORACLE.value),
        environment=EnvironmentConfig(
            type=EnvironmentType.DOCKER,
            force_build=True,
            delete=True,
        ),
        trials_dir=tmp_path / "trials",
    )

    trial = await Trial.create(config=config)
    result = await trial.run()

    assert result.exception_info is None
    assert result.verifier_result is not None
    assert result.verifier_result.rewards is not None
    assert result.verifier_result.rewards.get("reward") == 1.0
