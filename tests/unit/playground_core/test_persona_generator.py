"""Tests for synthetic persona consistency and generation."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from matraix.persona_consistency import validate_dimensions
from matraix.persona_generator import generate_persona_pool

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "persona" / "datasets" / "bench-dev-sample" / "manifest.json"


def test_generate_dimensions_respects_fixed_life_stage_without_age() -> None:
    """Fixed life_stage must pick a compatible age (no empty seniority lists)."""
    import random

    from matraix.persona_consistency import LIFE_STAGE_BY_AGE, validate_dimensions
    from matraix.persona_generator import (
        generate_persona_dimensions,
        load_catalog_values,
    )
    from matraix.persona_consistency import load_dev_dimension_ids

    catalog = load_catalog_values()
    dev_ids = load_dev_dimension_ids()
    rng = random.Random(0)
    for life_stage in ("Student", "Mid-life", "Career change", "Retirement"):
        dims = generate_persona_dimensions(
            rng=rng,
            catalog=catalog,
            dev_dimension_ids=dev_ids,
            fixed_dimensions={"life_stage": life_stage, "values_priority": "Autonomy"},
        )
        assert dims["life_stage"] == life_stage
        assert life_stage in LIFE_STAGE_BY_AGE[dims["age_bracket"]]
        assert validate_dimensions(dims) == []


def test_validate_rejects_counterfactual_combo() -> None:
    errors = validate_dimensions(
        {
            "age_bracket": "18-24",
            "life_stage": "Retirement",
            "seniority": "Retired",
            "years_experience": "20+",
            "highest_education": "Secondary",
        }
    )
    assert errors
    assert any("life_stage" in err for err in errors)


def test_validate_accepts_v2_age_bracket_dash_style() -> None:
    assert (
        validate_dimensions(
            {
                "age_bracket": "18–24",
                "life_stage": "Early career",
                "seniority": "Entry",
                "years_experience": "0-2",
                "highest_education": "Bachelor's",
            }
        )
        == []
    )


def test_dev_dimension_ids_include_core_catalog_fields() -> None:
    from matraix.persona_consistency import load_dev_dimension_ids

    dev_ids = set(load_dev_dimension_ids())

    assert {
        "age_bracket",
        "socioeconomic_band",
        "tech_savviness",
        "risk_tolerance",
        "economic_motivation",
        "lstyle_diet_type",
        "health_dietary_restriction",
        "habit_meal_prepping",
        "habit_skipping_breakfast",
        "habit_late_night_snacking",
        "att_veganism",
        "fam_nutrition",
    } <= dev_ids
    assert any(dim_id.startswith("cuis_") for dim_id in dev_ids)
    assert len(dev_ids) == 124


def test_generate_pool_has_no_violations() -> None:
    personas = generate_persona_pool(count=50, seed=99)
    for entry in personas:
        assert validate_dimensions(entry["dimensions"]) == []
        assert entry.get("source") in {"Nemotron", "OASIS", "PersonaHub", "PRIMEX"}
        assert entry.get("version") == "1.0"
        assert "lstyle_diet_type" in entry["dimensions"]
        assert "health_dietary_restriction" in entry["dimensions"]
        assert "habit_meal_prepping" in entry["dimensions"]
        assert any(key.startswith("cuis_") for key in entry["dimensions"])


def test_top_up_strata_adds_consistent_personas() -> None:
    from matraix.persona_generator import (
        build_probe_strata,
        generate_persona_pool,
        top_up_strata,
        load_catalog_values,
    )
    from matraix.persona_consistency import load_dev_dimension_ids

    confounders = {
        "socioeconomic_band": "Middle",
        "age_bracket": "25-34",
        "risk_tolerance": "Balanced",
        "tech_savviness": "Comfortable",
    }
    strata = build_probe_strata(
        confounders=confounders,
        probe_dimension="dimensions.economic_motivation",
        probe_values=["Cost-sensitive", "Indifferent"],
    )
    personas = generate_persona_pool(count=50, seed=1, smoke_persona_id="0001")
    catalog = load_catalog_values()
    dev_ids = load_dev_dimension_ids()
    import random

    topped = top_up_strata(
        personas,
        strata=strata,
        min_per_stratum=2,
        rng=random.Random(99),
        catalog=catalog,
        dev_dimension_ids=dev_ids,
        catalog_path="persona/schema/dimensions.json",
    )
    assert len(topped) > len(personas)
    for stratum in strata:
        matches = [
            entry
            for entry in topped
            if all(entry["dimensions"].get(k) == v for k, v in stratum.items())
        ]
        assert len(matches) >= 2
        for entry in matches:
            assert validate_dimensions(entry["dimensions"]) == []


def test_build_filter_strata_cartesian() -> None:
    from matraix.persona_generator import build_filter_strata

    strata = build_filter_strata(
        {
            "age_bracket": ["25-34", "35-44"],
            "life_stage": ["Early career"],
        }
    )
    assert len(strata) == 2
    assert {"age_bracket": "25-34", "life_stage": "Early career"} in strata
    assert {"age_bracket": "35-44", "life_stage": "Early career"} in strata


def test_generate_pool_strategy_top_up_only() -> None:
    from matraix.persona_generator import (
        build_filter_strata,
        filter_feasible_strata,
        generate_persona_pool,
    )

    strata = build_filter_strata(
        {
            "age_bracket": ["25-34", "35-44"],
            "life_stage": ["Early career", "Mid-life"],
        }
    )
    strata, dropped = filter_feasible_strata(strata)
    assert dropped  # some age × life_stage pairs are inconsistent
    assert strata
    personas = generate_persona_pool(
        count=0,
        seed=7,
        stratum_top_up=strata,
        min_per_stratum=2,
        include_smoke=False,
    )
    assert len(personas) >= 2 * len(strata)
    for stratum in strata:
        matches = [
            entry
            for entry in personas
            if all(entry["dimensions"].get(k) == v for k, v in stratum.items())
        ]
        assert len(matches) >= 2
        for entry in matches:
            assert validate_dimensions(entry["dimensions"]) == []


def test_checked_in_sample_manifest_is_consistent() -> None:
    from matraix.persona_consistency import load_dev_dimension_ids

    food_dims = {
        "lstyle_diet_type",
        "health_dietary_restriction",
        "habit_meal_prepping",
        "habit_skipping_breakfast",
        "habit_late_night_snacking",
        "att_veganism",
        "fam_nutrition",
    }
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["count"] == len(manifest["personas"])
    assert manifest["count"] >= 2
    assert manifest.get("schema_version") == "1.0"
    assert manifest.get("dimension_count") == 124
    assert set(manifest["dimension_ids"]) == set(load_dev_dimension_ids())
    assert food_dims <= set(manifest["dimension_ids"])
    for entry in manifest["personas"]:
        rel_path = entry if isinstance(entry, str) else entry["path"]
        if not isinstance(rel_path, str):
            rel_path = rel_path.split("/")[-1]
        yaml_path = MANIFEST.parent / Path(rel_path).name
        payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert validate_dimensions(payload["dimensions"]) == []
        assert payload.get("version") == "1.0"
        assert payload.get("source") in {"Nemotron", "OASIS", "PersonaHub", "PRIMEX"}
        assert len(payload["dimensions"]) == 124
        assert food_dims <= set(payload["dimensions"])
        if isinstance(entry, dict) and isinstance(entry.get("dimensions"), dict):
            assert food_dims <= set(entry["dimensions"])
