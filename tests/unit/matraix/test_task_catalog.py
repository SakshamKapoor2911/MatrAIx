"""Tests for matraix.task_catalog helpers and on-disk task alignment."""

from __future__ import annotations

from pathlib import Path

import pytest
import toml
from harbor.models.task.config import TaskConfig

from matraix.task_catalog import (
    APPLICATION_TASK_METADATA,
    application_harbor_name,
    build_application_task_toml_dict,
    confounder_values_from_grounding,
    load_grounding_toml,
    persona_bench_harbor_name,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
APPLICATION_TASKS = REPO_ROOT / "application" / "tasks"


def test_confounder_values_from_grounding_toml_shape() -> None:
    grounding = load_grounding_toml(
        "persona/tasks/example-survey_product-feedback",
        repo_root=REPO_ROOT,
    )
    assert grounding is not None
    values = confounder_values_from_grounding(grounding)
    assert values == {
        "socioeconomic_band": "Middle",
        "age_bracket": "25-34",
        "risk_tolerance": "Balanced",
        "tech_savviness": "Comfortable",
    }


@pytest.mark.parametrize(
    "dirname,expected",
    [
        (
            "example-survey_product-feedback",
            "matraix/application-survey-product-feedback",
        ),
        (
            "example-chat-api_support_chatbot",
            "matraix/application-chat-api-support-chatbot",
        ),
    ],
)
def test_application_harbor_names(dirname: str, expected: str) -> None:
    assert application_harbor_name(dirname) == expected


def test_persona_bench_harbor_name_with_dim_index() -> None:
    assert (
        persona_bench_harbor_name(
            "example-survey_product-feedback",
            bench_dim_index=47,
        )
        == "matraix/persona-bench-dim-047-survey-product-feedback"
    )


def _application_task_tomls() -> list[Path]:
    return sorted(
        p
        for p in APPLICATION_TASKS.glob("*/task.toml")
        if not p.parent.name.startswith("_")
    )


@pytest.mark.parametrize(
    "task_toml",
    _application_task_tomls(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_application_task_toml_loads(task_toml: Path) -> None:
    cfg = TaskConfig.model_validate_toml(task_toml.read_text(encoding="utf-8"))
    assert cfg.task is not None
    name = cfg.task.name
    assert name.count("/") == 1, name
    assert name.startswith("matraix/application-"), name


@pytest.mark.parametrize(
    "task_toml",
    _application_task_tomls(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_application_task_toml_matches_catalog(task_toml: Path) -> None:
    dirname = task_toml.parent.name
    assert dirname in APPLICATION_TASK_METADATA, (
        f"{dirname}: add APPLICATION_TASK_METADATA in task_catalog.py"
    )
    expected = build_application_task_toml_dict(dirname)
    actual = toml.loads(task_toml.read_text(encoding="utf-8"))
    assert actual["task"]["name"] == expected["task"]["name"]
    for key in ("type", "domain", "tags"):
        assert actual["metadata"][key] == expected["metadata"][key], key
