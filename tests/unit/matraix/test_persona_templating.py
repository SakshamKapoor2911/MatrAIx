"""Tests for persona Jinja2 templates."""

from pathlib import Path

from matraix.agents.persona.loader import load_persona
from matraix.agents.persona.templating import (
    PERSONA_INSTRUCTION_TEMPLATE,
    PERSONA_SYSTEM_TEMPLATE,
    render_persona_template,
    resolve_persona_template,
    templates_dir_for_persona,
)


def test_templates_dir_next_to_examples(personas_0042: Path) -> None:
    persona = load_persona(personas_0042)
    assert templates_dir_for_persona(persona) == personas_0042.parents[1] / "templates"


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
    assert "Product Manager" in text
    assert "## Task instruction" in text
    assert "Buy the plan." in text


def test_render_v1_domains_template(personas_0042: Path) -> None:
    persona = load_persona(personas_0042)
    path = resolve_persona_template(persona, None, PERSONA_SYSTEM_TEMPLATE)
    text = render_persona_template(path, persona)
    assert "## Demographics" in text
    assert "Product Manager" in text
    assert "## Psychology" in text
    assert "openness=0.72" in text
    assert "## Communication" in text
    assert "## Preferences" in text
    assert "Stay in character" in text


def test_custom_template_override(tmp_path: Path) -> None:
    persona_path = tmp_path / "v0.yaml"
    persona_path.write_text("display_name: Test User\nsummary: Example.\n")
    custom = tmp_path / "custom.md.j2"
    custom.write_text("PROFILE={{ display_name }}\nTASK={{ instruction }}\n")
    persona = load_persona(persona_path)
    path = resolve_persona_template(persona, custom, PERSONA_INSTRUCTION_TEMPLATE)
    text = render_persona_template(path, persona, instruction="Go.")
    assert text.strip() == "PROFILE=Test User\nTASK=Go."
