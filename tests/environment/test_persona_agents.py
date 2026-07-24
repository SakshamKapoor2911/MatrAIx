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


def test_correct_anthropic_cua_create_kwargs_opus_4_8_uses_new_tool() -> None:
    from matraix.agents.persona.use_computer_cua_protocol import (
        correct_anthropic_cua_create_kwargs,
    )

    # use-computer 0.0.44 would have sent the legacy tool for opus-4-8.
    corrected = correct_anthropic_cua_create_kwargs(
        {
            "model": "claude-opus-4-8",
            "betas": ["computer-use-2025-01-24"],
            "tools": [
                {
                    "type": "computer_20250124",
                    "name": "computer",
                    "display_width_px": 1280,
                    "display_height_px": 800,
                }
            ],
        }
    )
    assert corrected["betas"] == ["computer-use-2025-11-24"]
    assert corrected["tools"][0]["type"] == "computer_20251124"
    assert corrected["tools"][0]["name"] == "computer"


def test_correct_anthropic_cua_create_kwargs_haiku_4_5_stays_legacy() -> None:
    from matraix.agents.persona.use_computer_cua_protocol import (
        correct_anthropic_cua_create_kwargs,
    )

    corrected = correct_anthropic_cua_create_kwargs(
        {
            "model": "claude-haiku-4-5",
            "betas": ["computer-use-2025-01-24"],
            "tools": [{"type": "computer_20250124", "name": "computer"}],
        }
    )
    assert corrected["betas"] == ["computer-use-2025-01-24"]
    assert corrected["tools"][0]["type"] == "computer_20250124"


def test_apply_use_computer_anthropic_cua_protocol_patch_is_idempotent() -> None:
    from matraix.agents.persona.use_computer_cua_protocol import (
        apply_use_computer_anthropic_cua_protocol_patch,
    )

    first = apply_use_computer_anthropic_cua_protocol_patch()
    second = apply_use_computer_anthropic_cua_protocol_patch()
    # First call may be True (newly applied) or False if another test already
    # patched; second must always be False (idempotent).
    assert second is False
    assert first in {True, False}
