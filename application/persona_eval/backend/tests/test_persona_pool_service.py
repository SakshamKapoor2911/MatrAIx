"""Tests for persona pool catalog and sampling."""

from __future__ import annotations

import json
from pathlib import Path

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
        "persona_eval.harbor.persona_eval._repo_root",
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
        "persona_eval.harbor.persona_eval._repo_root",
        lambda: repo,
    )
    service = PersonaPoolService(repo_root=repo)
    detail = service.get_persona_detail("0001")
    assert detail["personaId"] == "0001"
    assert detail["dimensions"]["economic_motivation"] == "Price-sensitive"
    assert "persona_id: '0001'" in detail["yaml"]
    assert "persona-0001" in detail["profileMarkdown"]
    assert "persona_id: '0001'" in detail["profileMarkdown"]
    assert "## Dimensions" not in detail["profileMarkdown"]


def test_get_catalog_and_sample_with_filters(tmp_path, monkeypatch):
    repo = tmp_path
    _write_pool(repo)
    monkeypatch.setattr(
        "persona_eval.harbor.persona_eval._repo_root",
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


def test_list_persona_cards_all_personas(tmp_path, monkeypatch):
    repo = tmp_path
    _write_pool(repo)
    monkeypatch.setattr(
        "persona_eval.harbor.persona_eval._repo_root",
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
