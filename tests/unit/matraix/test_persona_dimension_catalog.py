"""Tests for catalog-driven persona dimension rendering."""

from __future__ import annotations

from matraix.persona_dimension_catalog import build_dimension_narrative


def test_build_narrative_reads_like_biography() -> None:
    dims = {
        "age_bracket": "25-34",
        "region": "South Asia",
        "gender_identity": "Woman",
        "life_stage": "Early career",
        "domain": "Software & AI",
        "economic_motivation": "Value-driven",
        "cog_verbosity": "Concise",
    }
    paragraphs = build_dimension_narrative(dims)
    text = " ".join(paragraphs)
    assert len(paragraphs) >= 3
    assert "between 25 and 34" in text
    assert "South Asia" in text
    assert "value-driven" in text.lower()
    assert not text.startswith("- ")


def test_build_narrative_covers_full_persona_0001() -> None:
    from pathlib import Path

    import yaml

    payload = yaml.safe_load(
        Path("persona/datasets/bench-dev-2000/persona_0001.yaml").read_text(
            encoding="utf-8"
        )
    )
    paragraphs = build_dimension_narrative(payload["dimensions"])
    text = " ".join(paragraphs).lower()
    assert len(paragraphs) >= 5
    assert "eastern europe" in text
    assert "mandarin" in text
    assert "indifferent" in text
    assert "brainstorm" in text
