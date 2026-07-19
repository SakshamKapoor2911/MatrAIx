from __future__ import annotations

import pathlib
import tomllib


ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_persona_agents_use_matraix_namespace() -> None:
    """Ensure no leftover 'personabench' references in agent files."""
    agent_files = [
        path
        for path in (ROOT / "environment/agents/matraix/agents").rglob("*")
        if path.is_file() and path.suffix in {".j2", ".py"}
    ]

    assert agent_files
    for path in agent_files:
        text = path.read_text(encoding="utf-8")
        assert "personabench" not in text.lower(), path


def test_harbor_factory_registers_matraix_persona_agents() -> None:
    factory_source = (
        ROOT / "environment/runtime/harbor/agents/factory.py"
    ).read_text()

    expected_imports = [
        "matraix.agents.persona.claude_code:PersonaClaudeCode",
        "matraix.agents.persona.computer_1:PersonaComputer1",
        "matraix.agents.persona.openhands_sdk:PersonaOpenHandsSDK",
        "matraix.agents.installed.browser_use:BrowserUseHarborAgent",
        "matraix.agents.installed.cocoa:CocoaHarborAgent",
        "matraix.agents.persona.browser_use:PersonaBrowserUse",
        "matraix.agents.persona.cocoa:PersonaCocoa",
        "matraix.agents.persona.gemini_cli:PersonaGeminiCli",
        "matraix.agents.persona.codex:PersonaCodex",
    ]

    for import_path in expected_imports:
        assert import_path in factory_source


def test_persona_agent_templates_are_packaged() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["tool"]["setuptools"]["package-data"]["matraix"] == [
        "agents/persona/templates/*.j2",
    ]


def test_installed_runtime_packages_do_not_import_environment_namespace() -> None:
    """Installed ``harbor.*`` / ``matraix.agents.*`` must not rely on repo-root ``environment.*`` imports."""
    roots = [
        ROOT / "environment/agents/matraix/agents",
        ROOT / "environment/runtime/harbor",
    ]
    for root in roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "environment.integrations" not in text, path
            assert "playground.local" not in text, path
            assert "from environment." not in text, path
            assert "import environment." not in text, path


def test_persona_loader_reads_sample_dataset() -> None:
    from matraix.agents.persona.loader import load_persona

    persona = load_persona(ROOT / "persona/datasets/bench-dev-sample/persona_0001.yaml")

    assert persona.schema_version == "v2"
    assert persona.persona_id == "0001"
    assert persona.dimensions["domain"] == "Software & AI"


def test_resolve_desktop_cua_provider_from_model_and_backend() -> None:
    from matraix.agents.persona.computer_1 import resolve_desktop_cua_provider

    assert resolve_desktop_cua_provider("openai/gpt-5.5") == "openai"
    assert resolve_desktop_cua_provider("gpt-5.4") == "openai"
    assert resolve_desktop_cua_provider("gemini/gemini-2.5-computer-use-preview") == "gemini"
    assert resolve_desktop_cua_provider("anthropic/claude-sonnet-4-6") == "anthropic"
    assert resolve_desktop_cua_provider(None) == "anthropic"
    assert resolve_desktop_cua_provider(
        "anthropic/claude-sonnet-4-6", cua_backend="openai"
    ) == "openai"
    assert resolve_desktop_cua_provider(
        "openai/gpt-5.5", cua_backend="anthropic"
    ) == "anthropic"
