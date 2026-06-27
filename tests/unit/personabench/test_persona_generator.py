"""Tests for synthetic persona consistency and generation."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from personabench.persona_consistency import validate_dimensions
from personabench.persona_generator import generate_persona_pool

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "persona" / "datasets" / "bench-dev-sample" / "manifest.json"


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
    from personabench.persona_consistency import load_dev_dimension_ids

    dev_ids = set(load_dev_dimension_ids())

    assert {
        "age_bracket",
        "socioeconomic_band",
        "tech_savviness",
        "risk_tolerance",
        "economic_motivation",
    } <= dev_ids


def test_generate_pool_has_no_violations() -> None:
    personas = generate_persona_pool(count=50, seed=99)
    for entry in personas:
        assert validate_dimensions(entry["dimensions"]) == []


def test_top_up_strata_adds_consistent_personas() -> None:
    from personabench.persona_generator import (
        build_probe_strata,
        generate_persona_pool,
        top_up_strata,
        load_catalog_values,
    )
    from personabench.persona_consistency import load_dev_dimension_ids

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


def test_checked_in_sample_manifest_is_consistent() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["count"] == len(manifest["personas"])
    assert manifest["count"] >= 2
    for entry in manifest["personas"]:
        rel_path = entry if isinstance(entry, str) else entry["path"]
        payload = yaml.safe_load((MANIFEST.parent / rel_path).read_text(encoding="utf-8"))
        assert validate_dimensions(payload["dimensions"]) == []
