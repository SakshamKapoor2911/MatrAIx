"""Tests for persona YAML loading."""

from pathlib import Path

import pytest

from matraix.agents.persona.loader import SCHEMA_V0, SCHEMA_V2, load_persona, resolve_persona_path


def test_load_v0_schema(tmp_path: Path) -> None:
    path = tmp_path / "v0.yaml"
    path.write_text(
        "display_name: Test User\n"
        "summary: A test persona for surveys.\n"
        "system_prompt: You are Test User.\n"
    )
    persona = load_persona(path)
    assert persona.schema_version == SCHEMA_V0
    assert persona.display_name == "Test User"
    assert persona.summary is not None
    assert "survey" in persona.summary.lower()
    assert persona.system_prompt is not None
    assert "Test User" in persona.system_prompt
    assert not persona.has_domains()


def test_load_persona_0042_example(personas_0042: Path) -> None:
    persona = load_persona(personas_0042)
    assert persona.schema_version == SCHEMA_V2
    assert persona.persona_id == "0042"
    assert persona.dimensions["age_bracket"] == "55-64"
    assert persona.dimensions["economic_motivation"] == "Indifferent"
    assert persona.dimensions["life_stage"] == "Career change"
    assert persona.has_domains()
    assert persona.has_dimensions_schema()
    assert persona.system_prompt is None


def test_resolve_relative_path(personas_0042: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(personas_0042.parents[3])
    resolved = resolve_persona_path("persona/datasets/bench-dev-2000/persona_0042.yaml")
    assert resolved == personas_0042.resolve()


def test_missing_persona_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_persona("/tmp/does-not-exist-persona.yaml")


def test_persona_requires_content(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("{}\n")
    with pytest.raises(ValueError, match="must define"):
        load_persona(path)
