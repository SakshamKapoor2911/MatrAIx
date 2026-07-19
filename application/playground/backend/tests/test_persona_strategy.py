"""Tests for per-task persona_strategy.json loading and validation."""

from __future__ import annotations

import json

from backend.service.persona_strategy import (
    load_persona_strategy,
    normalize_persona_strategy,
    validate_persona_strategy_file,
)
from backend.service.task_detail_service import get_task_detail


def test_normalize_persona_strategy_keeps_optional_sample_size() -> None:
    payload = normalize_persona_strategy(
        {
            "schemaVersion": "1.0",
            "defaultMode": "stratified",
            "sources": ["Nemotron"],
            "dimensionFilters": {"age_bracket": ["25-34", "35-44"], "region": "North America"},
            "stratifyFields": ["age_bracket"],
            "sampleSize": 8,
        }
    )
    assert payload["defaultMode"] == "stratified"
    assert payload["sources"] == ["Nemotron"]
    assert payload["dimensionFilters"] == {
        "age_bracket": ["25-34", "35-44"],
        "region": ["North America"],
    }
    assert payload["sampleSize"] == 8
    assert "sampleSizePerValueGroup" not in payload
    assert "seed" not in payload


def test_validate_persona_strategy_rejects_both_quota_fields(tmp_path) -> None:
    (tmp_path / "persona_strategy.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "defaultMode": "stratified",
                "dimensionFilters": {
                    "age_bracket": ["25-34", "35-44"],
                    "region": ["North America"],
                },
                "stratifyFields": ["age_bracket", "region"],
                "sampleSize": 8,
                "sampleSizePerValueGroup": 2,
            }
        ),
        encoding="utf-8",
    )
    errors = validate_persona_strategy_file(tmp_path)
    assert any("XOR" in err or "do not set both" in err for err in errors)

def test_load_persona_strategy_missing_file_returns_none(tmp_path) -> None:
    assert load_persona_strategy(tmp_path) is None


def test_validate_persona_strategy_requires_file(tmp_path) -> None:
    errors = validate_persona_strategy_file(tmp_path)
    assert any("missing required persona_strategy.json" in err for err in errors)


def test_validate_persona_strategy_requires_cohort(tmp_path) -> None:
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


def test_validate_persona_strategy_stratified_needs_axes(tmp_path) -> None:
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


def test_validate_persona_strategy_stratified_axes_in_filters(tmp_path) -> None:
    (tmp_path / "persona_strategy.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "defaultMode": "stratified",
                "dimensionFilters": {"life_stage": ["Early career"]},
                "stratifyFields": ["economic_motivation", "life_stage"],
                "sampleSize": 4,
            }
        ),
        encoding="utf-8",
    )
    errors = validate_persona_strategy_file(tmp_path)
    assert any("dimensionFilters" in err and "economic_motivation" in err for err in errors)


def test_validate_persona_strategy_sample_size_covers_cells(tmp_path) -> None:
    (tmp_path / "persona_strategy.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "defaultMode": "stratified",
                "dimensionFilters": {
                    "life_stage": ["Early career", "Mid-life"],
                    "economic_motivation": ["Cost-sensitive", "Indifferent"],
                },
                "stratifyFields": ["economic_motivation", "life_stage"],
                "sampleSize": 3,
            }
        ),
        encoding="utf-8",
    )
    errors = validate_persona_strategy_file(tmp_path)
    assert any("sampleSize=3" in err and "cell count=4" in err for err in errors)


def test_get_task_detail_includes_persona_strategy(tmp_path) -> None:
    task_dir = tmp_path / "application" / "tasks" / "example-survey-demo"
    task_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        '[metadata]\ntype = "survey"\n[task]\nname = "demo/survey"\n',
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text("# Demo\n\nAnswer in character.\n", encoding="utf-8")
    (task_dir / "persona_strategy.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "defaultMode": "random",
                "dimensionFilters": {"age_bracket": ["18-24", "25-34"]},
                "sampleSize": 6,
            }
        ),
        encoding="utf-8",
    )

    detail = get_task_detail("application/tasks/example-survey-demo", repo_root=tmp_path)
    assert detail["personaStrategy"] is not None
    assert detail["personaStrategy"]["defaultMode"] == "random"
    assert detail["personaStrategy"]["sampleSize"] == 6
    assert detail["personaStrategy"]["dimensionFilters"]["age_bracket"] == ["18-24", "25-34"]
