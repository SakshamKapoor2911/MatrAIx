"""Tests for persona pool catalog and sampling."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.service.persona_pool_service import PersonaPoolService


def _write_pool(repo: Path) -> None:
    pool = repo / "persona" / "datasets" / "bench-dev-sample"
    pool.mkdir(parents=True)
    (pool / "persona_0001.yaml").write_text(
        "persona_id: '0001'\nversion: '1.0'\nsource: Nemotron\ndimensions:\n  economic_motivation: Price-sensitive\n",
        encoding="utf-8",
    )
    (pool / "persona_0002.yaml").write_text(
        "persona_id: '0002'\nversion: '1.0'\nsource: OASIS\ndimensions:\n  economic_motivation: Indifferent\n",
        encoding="utf-8",
    )
    (pool / "manifest.json").write_text(
        json.dumps(
            {
                "count": 2,
                "smoke_persona_id": "0001",
                "schema_version": "1.0",
                "source_counts": {"Nemotron": 1, "OASIS": 1},
                "dimension_categories": "persona/schema/dimension_categories.json",
                "personas": [
                    {
                        "persona_id": "0001",
                        "path": "persona/datasets/bench-dev-sample/persona_0001.yaml",
                        "source": "Nemotron",
                        "dimensions": {"economic_motivation": "Price-sensitive"},
                    },
                    {
                        "persona_id": "0002",
                        "path": "persona/datasets/bench-dev-sample/persona_0002.yaml",
                        "source": "OASIS",
                        "dimensions": {"economic_motivation": "Indifferent"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    schema = repo / "persona" / "schema"
    schema.mkdir(parents=True)
    (schema / "dimension_categories.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "personaSources": ["Nemotron", "OASIS"],
                "devProfile": {
                    "dimensionCount": 1,
                    "groups": [
                        {
                            "id": "values",
                            "label": "Values",
                            "dimensionIds": ["economic_motivation"],
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    dims = schema / "dimensions.json"
    dims.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "dimensions": [
                    {
                        "id": "economic_motivation",
                        "label": "Economic motivation",
                        "values": ["Price-sensitive", "Indifferent"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_save_list_and_resolve_cohort(tmp_path, monkeypatch):
    repo = tmp_path
    _write_pool(repo)
    monkeypatch.setattr(
        "playground.harbor.playground._repo_root",
        lambda: repo,
    )
    service = PersonaPoolService(repo_root=repo)

    saved = service.save_cohort(
        cohort_id="nemotron-price-sensitive",
        name="Nemotron price-sensitive",
        kind="recipe",
        seed=7,
        sample_size=1,
        sources=["Nemotron"],
        dimension_filters={"economic_motivation": "Price-sensitive"},
    )
    assert saved["cohortId"] == "nemotron-price-sensitive"
    assert (repo / "persona/datasets/cohorts/nemotron-price-sensitive/cohort.json").is_file()

    listed = service.list_cohorts()
    assert len(listed) == 1
    assert listed[0]["cohortId"] == "nemotron-price-sensitive"

    frozen = service.save_cohort(
        cohort_id="frozen-pair",
        kind="frozen",
        seed=1,
        sample_size=1,
        dimension_filters={"economic_motivation": "Indifferent"},
    )
    assert frozen["personaIds"] == ["0002"]

    resolved = service.resolve_cohort_launch("frozen-pair")
    assert resolved["personaIds"] == ["0002"]


def test_get_persona_detail(tmp_path, monkeypatch):
    repo = tmp_path
    _write_pool(repo)
    monkeypatch.setattr(
        "playground.harbor.playground._repo_root",
        lambda: repo,
    )
    service = PersonaPoolService(repo_root=repo)
    detail = service.get_persona_detail("0001")
    assert detail["personaId"] == "0001"
    assert detail["dimensions"]["economic_motivation"] == "Price-sensitive"
    assert "persona_id: '0001'" in detail["yaml"]
    assert detail["name"] and "persona-" not in detail["name"]
    assert not detail["profileMarkdown"].startswith("#")
    assert "## Dimensions" not in detail["profileMarkdown"]


def test_get_catalog_and_sample_with_filters(tmp_path, monkeypatch):
    repo = tmp_path
    _write_pool(repo)
    monkeypatch.setattr(
        "playground.harbor.playground._repo_root",
        lambda: repo,
    )
    service = PersonaPoolService(repo_root=repo)
    catalog = service.get_catalog()
    assert catalog["count"] == 2
    assert catalog["smokePersonaId"] == "0001"
    assert catalog["dimensionCategories"]["devProfile"]["groups"]

    matched = service.filter_pool(sources=["Nemotron"])
    assert len(matched) == 1
    assert matched[0]["persona_id"] == "0001"

    sampled = service.sample_pool(
        sample_size=1,
        seed=7,
        dimension_filters={"economic_motivation": "Indifferent"},
    )
    assert sampled["matchedCount"] == 1
    assert sampled["personaIds"] == ["0002"]

    stratified = service.sample_pool(
        sample_size=2,
        seed=7,
        stratify_fields=["economic_motivation"],
        sample_size_per_value_group=1,
    )
    assert stratified["matchedCount"] == 2
    assert set(stratified["personaIds"]) == {"0001", "0002"}
    assert stratified["stratifyFields"] == ["economic_motivation"]

    with pytest.raises(ValueError, match="generate_dev_personas.py --strategy") as excinfo:
        service.sample_pool(
            sample_size=99,
            seed=7,
            task_path="application/tasks/example-survey_product-feedback",
            auto_ensure_strategy_pool=False,
        )
    assert "example-survey_product-feedback/persona_strategy.json" in str(excinfo.value)

    # Without filters, auto-ensure cannot invent coverage either.
    with pytest.raises(ValueError, match="generate_dev_personas.py --strategy"):
        service.sample_pool(
            sample_size=99,
            seed=7,
            task_path="application/tasks/example-survey_product-feedback",
            auto_ensure_strategy_pool=True,
        )


def test_sample_pool_per_value_group_not_truncated_by_sample_size(tmp_path, monkeypatch):
    """sampleSizePerValueGroup is primary; sample_size must not clip N×cells."""
    repo = tmp_path
    pool = repo / "persona" / "datasets" / "bench-dev-sample"
    pool.mkdir(parents=True)
    personas = [
        ("0001", "Nemotron", "Price-sensitive"),
        ("0002", "Nemotron", "Price-sensitive"),
        ("0003", "OASIS", "Indifferent"),
        ("0004", "OASIS", "Indifferent"),
    ]
    manifest_rows = []
    for pid, source, motivation in personas:
        (pool / f"persona_{pid}.yaml").write_text(
            f"persona_id: '{pid}'\nversion: '1.0'\nsource: {source}\n"
            f"dimensions:\n  economic_motivation: {motivation}\n",
            encoding="utf-8",
        )
        manifest_rows.append(
            {
                "persona_id": pid,
                "path": f"persona/datasets/bench-dev-sample/persona_{pid}.yaml",
                "source": source,
                "dimensions": {"economic_motivation": motivation},
            }
        )
    (pool / "manifest.json").write_text(
        json.dumps(
            {
                "count": 4,
                "smoke_persona_id": "0001",
                "schema_version": "1.0",
                "source_counts": {"Nemotron": 2, "OASIS": 2},
                "dimension_categories": "persona/schema/dimension_categories.json",
                "personas": manifest_rows,
            }
        ),
        encoding="utf-8",
    )
    schema = repo / "persona" / "schema"
    schema.mkdir(parents=True)
    (schema / "dimension_categories.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "personaSources": ["Nemotron", "OASIS"],
                "devProfile": {
                    "dimensionCount": 1,
                    "groups": [
                        {
                            "id": "values",
                            "label": "Values",
                            "dimensionIds": ["economic_motivation"],
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (schema / "dimensions.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "dimensions": [
                    {
                        "id": "economic_motivation",
                        "label": "Economic motivation",
                        "values": ["Price-sensitive", "Indifferent"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "playground.harbor.playground._repo_root",
        lambda: repo,
    )
    service = PersonaPoolService(repo_root=repo)

    # sample_size=2 would previously clip the 2×2=4 per-cell cohort down to 2.
    result = service.sample_pool(
        sample_size=2,
        seed=7,
        stratify_fields=["economic_motivation"],
        sample_size_per_value_group=2,
    )
    assert result["matchedCount"] == 4
    assert result["sampleSize"] == 4
    assert set(result["personaIds"]) == {"0001", "0002", "0003", "0004"}


def test_sample_pool_stratified_without_per_cell_caps_at_sample_size(tmp_path, monkeypatch):
    """sampleSize-only stratified: spread ceil(N/cells) then clip to sampleSize."""
    repo = tmp_path
    pool = repo / "persona" / "datasets" / "bench-dev-sample"
    pool.mkdir(parents=True)
    # 3 strata × 3 people so ceil(8/3)=3 per cell fits, then clip to 8.
    personas = [
        ("0001", "A", "18-24"),
        ("0002", "A", "18-24"),
        ("0003", "A", "18-24"),
        ("0004", "B", "25-34"),
        ("0005", "B", "25-34"),
        ("0006", "B", "25-34"),
        ("0007", "C", "35-44"),
        ("0008", "C", "35-44"),
        ("0009", "C", "35-44"),
    ]
    manifest_rows = []
    for pid, source, age in personas:
        (pool / f"persona_{pid}.yaml").write_text(
            f"persona_id: '{pid}'\nversion: '1.0'\nsource: {source}\n"
            f"dimensions:\n  age_bracket: {age}\n",
            encoding="utf-8",
        )
        manifest_rows.append(
            {
                "persona_id": pid,
                "path": f"persona/datasets/bench-dev-sample/persona_{pid}.yaml",
                "source": source,
                "dimensions": {"age_bracket": age},
            }
        )
    (pool / "manifest.json").write_text(
        json.dumps(
            {
                "count": 9,
                "smoke_persona_id": "0001",
                "schema_version": "1.0",
                "source_counts": {"A": 3, "B": 3, "C": 3},
                "dimension_categories": "persona/schema/dimension_categories.json",
                "personas": manifest_rows,
            }
        ),
        encoding="utf-8",
    )
    schema = repo / "persona" / "schema"
    schema.mkdir(parents=True)
    (schema / "dimension_categories.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "categories": [
                    {"id": "demo", "label": "Demo", "dimensionIds": ["age_bracket"]}
                ],
            }
        ),
        encoding="utf-8",
    )
    (schema / "dimensions.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "dimensions": [
                    {
                        "id": "age_bracket",
                        "label": "Age",
                        "values": ["18-24", "25-34", "35-44"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "playground.harbor.playground._repo_root",
        lambda: repo,
    )
    service = PersonaPoolService(repo_root=repo)

    result = service.sample_pool(
        sample_size=8,
        seed=7,
        dimension_filters={"age_bracket": ["18-24", "25-34", "35-44"]},
        stratify_fields=["age_bracket"],
        sample_size_per_value_group=None,
        auto_ensure_strategy_pool=False,
    )
    assert result["matchedCount"] == 9
    assert result["sampleSize"] == 8
    assert len(result["personaIds"]) == 8


def test_sample_pool_rejects_sample_size_below_cell_count(tmp_path, monkeypatch):
    repo = tmp_path
    _write_pool(repo)
    monkeypatch.setattr(
        "playground.harbor.playground._repo_root",
        lambda: repo,
    )
    service = PersonaPoolService(repo_root=repo)
    try:
        service.sample_pool(
            sample_size=1,
            seed=7,
            dimension_filters={"economic_motivation": ["Price-sensitive", "Indifferent"]},
            stratify_fields=["economic_motivation"],
            sample_size_per_value_group=None,
            auto_ensure_strategy_pool=False,
        )
        raise AssertionError("expected sampleSize below cell count to fail")
    except ValueError as exc:
        assert "below the stratified cell count=2" in str(exc)


def test_sample_pool_auto_ensures_strategy_coverage(tmp_path, monkeypatch):
    """When filters undershoot the fixture, sample_pool synthesizes a local pool."""
    repo = tmp_path
    _write_pool(repo)
    monkeypatch.setattr(
        "playground.harbor.playground._repo_root",
        lambda: repo,
    )
    service = PersonaPoolService(repo_root=repo)

    # Only one Price-sensitive persona in the fixture — ask for more than that.
    sampled = service.sample_pool(
        sample_size=4,
        seed=7,
        dimension_filters={"economic_motivation": ["Price-sensitive"]},
        task_path="application/tasks/example-survey_product-feedback",
        auto_ensure_strategy_pool=True,
    )
    assert sampled["poolEnsured"] is True
    assert sampled["sampleSize"] == 4
    assert len(sampled["personaIds"]) == 4
    assert str(sampled["pool"]).startswith("persona/datasets/_generated/")
    assert (repo / sampled["pool"] / "manifest.json").is_file()

    # Second call should reuse the generated pool when it already covers the request.
    reused = service.sample_pool(
        sample_size=4,
        seed=7,
        dimension_filters={"economic_motivation": ["Price-sensitive"]},
        task_path="application/tasks/example-survey_product-feedback",
        auto_ensure_strategy_pool=True,
    )
    assert reused["poolEnsured"] is True
    assert reused["poolReused"] is True
    assert reused["pool"] == sampled["pool"]


def test_sample_pool_auto_ensures_incomplete_stratify_cells(tmp_path, monkeypatch):
    """Missing stratify cells synthesize a local pool instead of returning a partial cohort."""
    repo = tmp_path
    _write_pool(repo)
    monkeypatch.setattr(
        "playground.harbor.playground._repo_root",
        lambda: repo,
    )
    service = PersonaPoolService(repo_root=repo)

    # Fixture only has Price-sensitive + Indifferent once each, but asking for
    # N=2 per cell must top up — and requesting both values in filters makes
    # empty/thin cells detectable before silent partial return.
    sampled = service.sample_pool(
        sample_size=4,
        seed=7,
        dimension_filters={"economic_motivation": ["Price-sensitive", "Indifferent"]},
        stratify_fields=["economic_motivation"],
        sample_size_per_value_group=2,
        task_path="application/tasks/example-survey_product-feedback",
        auto_ensure_strategy_pool=True,
    )
    assert sampled["poolEnsured"] is True
    assert sampled["sampleSize"] == 4
    assert len(sampled["personaIds"]) == 4
    assert str(sampled["pool"]).startswith("persona/datasets/_generated/")


def test_list_persona_cards_all_personas(tmp_path, monkeypatch):
    repo = tmp_path
    _write_pool(repo)
    monkeypatch.setattr(
        "playground.harbor.playground._repo_root",
        lambda: repo,
    )
    service = PersonaPoolService(repo_root=repo)

    shuffled = service.list_persona_cards(limit=2, seed=99)
    assert len(shuffled["personas"]) == 2

    all_cards = service.list_persona_cards(limit=2, all_personas=True)
    assert [card["personaId"] for card in all_cards["personas"]] == ["0001", "0002"]

    page_two = service.list_persona_cards(limit=1, offset=1, all_personas=True)
    assert [card["personaId"] for card in page_two["personas"]] == ["0002"]

    full_pool = service.list_persona_cards(limit=500, all_personas=True)
    assert [card["personaId"] for card in full_pool["personas"]] == ["0001", "0002"]
