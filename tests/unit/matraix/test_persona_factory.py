"""Tests for persona agent registration and metadata."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from harbor.agents.factory import AgentFactory
from harbor.models.agent.name import AgentName
from matraix.agents.persona.browser_use import PersonaBrowserUse
from matraix.agents.persona.claude_code import PersonaClaudeCode
from matraix.agents.persona.codex import PersonaCodex
from matraix.agents.persona.cocoa import PersonaCocoa
from matraix.agents.persona.computer_1 import PersonaComputer1
from matraix.agents.persona.gemini_cli import PersonaGeminiCli
from matraix.agents.persona.openhands_sdk import PersonaOpenHandsSDK


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("agent_name", "agent_cls", "import_path"),
    [
        (
            AgentName.PERSONA_CLAUDE_CODE,
            PersonaClaudeCode,
            "matraix.agents.persona.claude_code:PersonaClaudeCode",
        ),
        (
            AgentName.PERSONA_GEMINI_CLI,
            PersonaGeminiCli,
            "matraix.agents.persona.gemini_cli:PersonaGeminiCli",
        ),
        (
            AgentName.PERSONA_CODEX,
            PersonaCodex,
            "matraix.agents.persona.codex:PersonaCodex",
        ),
        (
            AgentName.PERSONA_COMPUTER_1,
            PersonaComputer1,
            "matraix.agents.persona.computer_1:PersonaComputer1",
        ),
        (
            AgentName.PERSONA_OPENHANDS_SDK,
            PersonaOpenHandsSDK,
            "matraix.agents.persona.openhands_sdk:PersonaOpenHandsSDK",
        ),
        (
            AgentName.PERSONA_BROWSER_USE,
            PersonaBrowserUse,
            "matraix.agents.persona.browser_use:PersonaBrowserUse",
        ),
        (
            AgentName.PERSONA_COCOA,
            PersonaCocoa,
            "matraix.agents.persona.cocoa:PersonaCocoa",
        ),
    ],
)
def test_factory_registration(agent_name, agent_cls, import_path) -> None:
    assert agent_name.value in AgentName.values()
    assert AgentFactory._AGENT_MAP[agent_name] == import_path
    assert AgentFactory.get_agent_class(agent_name) is agent_cls
    assert agent_cls.name() == agent_name.value


def test_persona_claude_code_requires_persona_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="persona_path"):
        PersonaClaudeCode(logs_dir=tmp_path / "agent")


def test_persona_claude_code_injects_append_system_prompt(
    tmp_path: Path, personas_0042: Path
) -> None:
    agent = PersonaClaudeCode(
        logs_dir=tmp_path / "agent",
        persona_path=str(personas_0042),
        append_system_prompt="Extra rules.",
    )
    assert "0042" in agent._resolved_flags["append_system_prompt"]
    assert "between 55 and 64" in agent._resolved_flags["append_system_prompt"]
    assert "Extra rules." in agent._resolved_flags["append_system_prompt"]


@pytest.mark.asyncio
async def test_persona_claude_code_writes_meta(
    tmp_path: Path, personas_0042: Path
) -> None:
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    agent = PersonaClaudeCode(
        logs_dir=agent_dir,
        persona_path=str(personas_0042),
    )

    with patch.object(
        PersonaClaudeCode,
        "run",
        new_callable=AsyncMock,
        wraps=PersonaClaudeCode.run,
    ):
        # Call mixin path directly to avoid full claude install
        agent._write_persona_meta()

    meta_path = tmp_path / "persona_meta.json"
    assert meta_path.is_file()
    meta = json.loads(meta_path.read_text())
    assert meta["agent"] == "persona-claude-code"
    assert meta["display_name"] == "persona-0042"
    assert Path(meta["persona_path"]).as_posix().endswith(
        "persona/datasets/bench-dev-2000/persona_0042.yaml"
    )


def test_persona_browser_use_injects_persona_system(
    tmp_path: Path, personas_0042: Path
) -> None:
    agent = PersonaBrowserUse(
        logs_dir=tmp_path / "agent",
        persona_path=str(personas_0042),
    )
    system = agent._render_persona_system()
    assert "0042" in system
    assert "between 55 and 64" in system


def test_persona_openhands_sdk_prepends_instruction(
    tmp_path: Path, personas_0042: Path
) -> None:
    agent = PersonaOpenHandsSDK(
        logs_dir=tmp_path / "agent",
        persona_path=str(personas_0042),
    )
    rendered = agent.render_instruction("Do the task.")
    assert "0042" in rendered
    assert "between 55 and 64" in rendered
    assert "## Task instruction" in rendered
    assert "Do the task." in rendered


def test_persona_cocoa_prepends_instruction(
    tmp_path: Path, personas_0042: Path
) -> None:
    agent = PersonaCocoa(
        logs_dir=tmp_path / "agent",
        persona_path=str(personas_0042),
    )
    rendered = agent.render_instruction("Do the task.")
    assert "0042" in rendered
    assert "between 55 and 64" in rendered
    assert "## Task instruction" in rendered
    assert "Do the task." in rendered


@pytest.mark.parametrize("agent_cls", [PersonaGeminiCli, PersonaCodex])
def test_persona_cli_agents_prepends_instruction(
    tmp_path: Path, personas_0042: Path, agent_cls: type
) -> None:
    agent = agent_cls(
        logs_dir=tmp_path / "agent",
        persona_path=str(personas_0042),
    )
    rendered = agent.render_instruction("Do the task.")
    assert "0042" in rendered
    assert "between 55 and 64" in rendered
    assert "## Task instruction" in rendered
    assert "Do the task." in rendered
