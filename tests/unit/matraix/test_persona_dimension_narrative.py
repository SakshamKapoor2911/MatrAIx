"""Communication-style narrative must join catalog label + value cleanly."""

from __future__ import annotations

import re

from matraix.agents.persona.loader import load_persona
from matraix.persona_dimension_catalog import build_dimension_narrative


def test_communication_style_uses_label_value_pairs():
    persona = load_persona("persona/datasets/bench-dev-sample/persona_0001.yaml")
    paragraphs = build_dimension_narrative(persona.dimensions)
    style = paragraphs[-1]

    assert "verbosity: rambling" in style
    assert "formality: very formal" in style
    assert "directness: indirect" in style
    assert "visual vs verbal thinking: strongly visual" in style
    assert "question-asking: asks often" in style

    # No accidental adjacent-word echoes from "{value} {label}" joins.
    assert re.search(r"\b(\w+)\s+\1\b", style, flags=re.I) is None
    assert "visual visual" not in style
    assert "indirect directness" not in style
    assert "asks often question-asking" not in style
