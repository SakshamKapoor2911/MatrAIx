from __future__ import annotations

import pathlib
import tomllib


ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_persona_agents_use_personabench_namespace() -> None:
    agent_files = [
        path
        for path in (ROOT / "src/personabench/agents").rglob("*")
        if path.is_file() and path.suffix in {".j2", ".py"}
    ]

    assert agent_files
    for path in agent_files:
        text = path.read_text(encoding="utf-8")
        assert "matraix" not in text.lower(), path


def test_harbor_factory_registers_personabench_persona_agents() -> None:
    factory_source = (ROOT / "src/harbor/agents/factory.py").read_text()

    expected_imports = [
        "personabench.agents.persona.claude_code:PersonaClaudeCode",
        "personabench.agents.persona.computer_1:PersonaComputer1",
        "personabench.agents.persona.openhands_sdk:PersonaOpenHandsSDK",
        "personabench.agents.installed.browser_use:BrowserUseHarborAgent",
        "personabench.agents.installed.cocoa:CocoaHarborAgent",
        "personabench.agents.persona.browser_use:PersonaBrowserUse",
        "personabench.agents.persona.cocoa:PersonaCocoa",
        "personabench.agents.persona.gemini_cli:PersonaGeminiCli",
        "personabench.agents.persona.codex:PersonaCodex",
    ]

    for import_path in expected_imports:
        assert import_path in factory_source


def test_persona_agent_templates_are_packaged() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["tool"]["setuptools"]["package-data"]["personabench"] == [
        "agents/persona/templates/*.j2",
    ]


def test_persona_loader_reads_sample_dataset() -> None:
    from personabench.agents.persona.loader import load_persona

    persona = load_persona(ROOT / "persona/datasets/bench-dev-sample/persona_0001.yaml")

    assert persona.schema_version == "v2"
    assert persona.persona_id == "0001"
    assert persona.dimensions["domain"] == "Software & AI"
