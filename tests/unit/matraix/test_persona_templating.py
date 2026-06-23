"""Tests for persona Jinja2 templates."""

from pathlib import Path

from matraix.agents.persona.loader import load_persona
from matraix.agents.persona.templating import (
    PERSONA_INSTRUCTION_TEMPLATE,
    PERSONA_SYSTEM_TEMPLATE,
    default_templates_dir,
    render_persona_template,
    resolve_persona_template,
)


def test_default_templates_dir() -> None:
    templates = default_templates_dir()
    assert templates.is_dir()
    assert (templates / PERSONA_SYSTEM_TEMPLATE).is_file()
    assert (templates / PERSONA_INSTRUCTION_TEMPLATE).is_file()


def test_render_v0_system_template(tmp_path: Path) -> None:
    path = tmp_path / "v0.yaml"
    path.write_text(
        "display_name: Test User\n"
        "summary: Survey participant.\n"
        "system_prompt: You are Test User.\n"
    )
    persona = load_persona(path)
    template_path = resolve_persona_template(persona, None, PERSONA_SYSTEM_TEMPLATE)
    text = render_persona_template(template_path, persona)
    assert "You are Test User." in text
    assert "Survey participant." in text


def test_render_v1_instruction_template(personas_0042: Path) -> None:
    persona = load_persona(personas_0042)
    path = resolve_persona_template(persona, None, PERSONA_INSTRUCTION_TEMPLATE)
    text = render_persona_template(path, persona, instruction="Buy the plan.")
    assert "0042" in text
    assert "indifferent" in text.lower()
    assert "## Task instruction" in text
    assert "Buy the plan." in text


def test_render_v1_domains_template(personas_0042: Path) -> None:
    persona = load_persona(personas_0042)
    path = resolve_persona_template(persona, None, PERSONA_SYSTEM_TEMPLATE)
    text = render_persona_template(path, persona)
    assert "## Who you are" in text
    assert "between 55 and 64" in text
    assert "indifferent" in text.lower()
    assert "My life-age band is" not in text
    assert "Stay in character" in text


def test_render_psychology_without_values_key(tmp_path: Path) -> None:
    """Matrix-demo personas omit psychology.values; must not hit dict.values method."""
    path = tmp_path / "minimal.yaml"
    path.write_text(
        "persona_id: '0099'\n"
        "psychology:\n"
        "  risk_tolerance: low\n"
        "  motivation_drivers:\n"
        "    - curiosity\n"
    )
    persona = load_persona(path)
    template_path = resolve_persona_template(persona, None, PERSONA_SYSTEM_TEMPLATE)
    text = render_persona_template(template_path, persona)
    assert "Risk tolerance: low" in text
    assert "Motivation: curiosity" in text
    assert "Values:" not in text


def test_custom_template_override(tmp_path: Path) -> None:
    persona_path = tmp_path / "v0.yaml"
    persona_path.write_text("display_name: Test User\nsummary: Example.\n")
    custom = tmp_path / "custom.md.j2"
    custom.write_text("PROFILE={{ display_name }}\nTASK={{ instruction }}\n")
    persona = load_persona(persona_path)
    path = resolve_persona_template(persona, custom, PERSONA_INSTRUCTION_TEMPLATE)
    text = render_persona_template(path, persona, instruction="Go.")
    assert text.strip() == "PROFILE=Test User\nTASK=Go."
