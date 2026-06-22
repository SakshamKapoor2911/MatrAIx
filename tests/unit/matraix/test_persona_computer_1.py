"""Tests for persona-computer-1 CUA backend routing."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from harbor.environments.use_computer import UseComputerEnvironment
from matraix.agents.persona.computer_1 import (
    PersonaComputer1,
    resolve_cua_backend_kind,
)


class _FakeDockerEnvironment:
    upload_file = AsyncMock()

    def type(self):
        return "docker"


def _use_computer_stub(platform: str) -> MagicMock:
    env = MagicMock()
    env._platform = platform
    env.upload_file = AsyncMock()
    env.__class__ = UseComputerEnvironment
    return env


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def personas_0042(repo_root: Path) -> Path:
    return repo_root / "persona" / "datasets" / "bench-dev-2000" / "persona_0042.yaml"


def test_resolve_use_computer_macos() -> None:
    assert resolve_cua_backend_kind(_use_computer_stub("macos")) == "use_computer_desktop"


def test_resolve_use_computer_ubuntu() -> None:
    assert resolve_cua_backend_kind(_use_computer_stub("ubuntu")) == "use_computer_desktop"


def test_resolve_use_computer_ios() -> None:
    assert resolve_cua_backend_kind(_use_computer_stub("ios")) == "ios"


def test_resolve_docker_defaults_to_computer1() -> None:
    assert resolve_cua_backend_kind(_FakeDockerEnvironment()) == "docker_computer1"


def test_resolve_override_ios() -> None:
    assert (
        resolve_cua_backend_kind(_FakeDockerEnvironment(), override="ios")
        == "ios"
    )


def test_persona_computer_1_requires_persona_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="persona_path"):
        PersonaComputer1(logs_dir=tmp_path / "agent")


def test_persona_computer_1_prepends_instruction(
    tmp_path: Path, personas_0042: Path
) -> None:
    agent = PersonaComputer1(
        logs_dir=tmp_path / "agent",
        persona_path=str(personas_0042),
    )
    rendered = agent._render_persona_instruction("Open Settings.")
    assert "0042" in rendered
    assert "Open Settings." in rendered


@pytest.mark.asyncio
async def test_persona_computer_1_routes_ios_to_ios_agent(
    tmp_path: Path, personas_0042: Path
) -> None:
    agent = PersonaComputer1(
        logs_dir=tmp_path / "agent",
        persona_path=str(personas_0042),
    )
    environment = _use_computer_stub("ios")

    mock_delegate = MagicMock()
    mock_delegate.setup = AsyncMock()
    mock_delegate.run = AsyncMock()
    mock_delegate.version = MagicMock(return_value="1.0.0")

    with patch(
        "matraix.agents.persona.computer_1._build_cua_delegate",
        return_value=mock_delegate,
    ) as build:
        context = MagicMock()
        await agent.run("Do the task.", environment, context)

    build.assert_called_once()
    assert build.call_args.args[0] == "ios"
    mock_delegate.run.assert_awaited_once()
    instruction = mock_delegate.run.await_args.args[0]
    assert "0042" in instruction
    assert "Do the task." in instruction


@pytest.mark.asyncio
async def test_persona_computer_1_materializes_book_interest_submission(
    tmp_path: Path, personas_0042: Path
) -> None:
    agent = PersonaComputer1(
        logs_dir=tmp_path / "agent",
        persona_path=str(personas_0042),
        cua_submission_profile="book_interest",
    )
    environment = _FakeDockerEnvironment()

    mock_delegate = MagicMock()
    mock_delegate.setup = AsyncMock()
    mock_delegate.run = AsyncMock()
    mock_delegate.version = MagicMock(return_value="1.0.0")

    with patch(
        "matraix.agents.persona.computer_1._build_cua_delegate",
        return_value=mock_delegate,
    ), patch(
        "matraix.agents.persona.computer_1.materialize_cua_submission_profile",
        new=AsyncMock(return_value=True),
    ) as materialize:
        await agent.run("Browse books.", environment, MagicMock())

    materialize.assert_awaited_once_with(
        "book_interest",
        environment,
        tmp_path / "agent",
        logger=agent.logger,
    )


@pytest.mark.asyncio
async def test_persona_computer_1_routes_docker_to_computer1(
    tmp_path: Path, personas_0042: Path
) -> None:
    agent = PersonaComputer1(
        logs_dir=tmp_path / "agent",
        persona_path=str(personas_0042),
    )
    environment = _FakeDockerEnvironment()

    mock_delegate = MagicMock()
    mock_delegate.setup = AsyncMock()
    mock_delegate.run = AsyncMock()
    mock_delegate.version = MagicMock(return_value="1.0.0")

    with patch(
        "matraix.agents.persona.computer_1._build_cua_delegate",
        return_value=mock_delegate,
    ) as build:
        await agent.setup(environment)

    build.assert_called_once()
    assert build.call_args.args[0] == "docker_computer1"
