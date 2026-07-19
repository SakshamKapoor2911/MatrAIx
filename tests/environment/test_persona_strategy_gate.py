"""Unit tests for persona_strategy.json CI validation helpers."""

from __future__ import annotations

import json
from pathlib import Path


def test_validate_persona_strategy_requires_file(tmp_path: Path) -> None:
    from backend.service.persona_strategy import validate_persona_strategy_file

    errors = validate_persona_strategy_file(tmp_path)
    assert any("missing required persona_strategy.json" in err for err in errors)


def test_validate_persona_strategy_requires_cohort(tmp_path: Path) -> None:
    from backend.service.persona_strategy import validate_persona_strategy_file

    (tmp_path / "persona_strategy.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "defaultMode": "random",
                "dimensionFilters": {},
            }
        ),
        encoding="utf-8",
    )
    errors = validate_persona_strategy_file(tmp_path, require_cohort=True)
    assert any("target cohort" in err for err in errors)

    errors_relaxed = validate_persona_strategy_file(tmp_path, require_cohort=False)
    assert errors_relaxed == []


def test_validate_persona_strategy_stratified_needs_axes(tmp_path: Path) -> None:
    from backend.service.persona_strategy import validate_persona_strategy_file

    (tmp_path / "persona_strategy.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "defaultMode": "stratified",
                "dimensionFilters": {"region": ["Oceania"]},
            }
        ),
        encoding="utf-8",
    )
    errors = validate_persona_strategy_file(tmp_path)
    assert any("stratifyFields" in err for err in errors)
