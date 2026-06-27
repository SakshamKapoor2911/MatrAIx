from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
from harbor.models.task.config import TaskConfig

from personabench.task_catalog import (
    EXAMPLE_TASK_METADATA,
    build_persona_task_toml_dict,
    load_grounding_toml,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PERSONA_TASKS = REPO_ROOT / "persona" / "tasks"
DIMENSIONS_JSON = REPO_ROOT / "persona" / "schema" / "dimensions.json"


def _persona_task_tomls() -> list[Path]:
    return sorted(
        p
        for p in PERSONA_TASKS.glob("*/task.toml")
        if not p.parent.name.startswith("_")
    )


@pytest.mark.parametrize(
    "task_toml",
    _persona_task_tomls(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_persona_validation_task_toml_loads(task_toml: Path) -> None:
    cfg = TaskConfig.model_validate_toml(task_toml.read_text(encoding="utf-8"))
    assert cfg.task is not None
    name = cfg.task.name
    assert name.count("/") == 1, name
    assert name.startswith("personabench/persona-bench-"), name
    meta = cfg.metadata if isinstance(cfg.metadata, dict) else cfg.metadata.model_dump()
    assert meta.get("domain") in {
        "software",
        "finance",
        "healthcare",
        "commerce-retail",
    }, meta.get("domain")
    tags = meta.get("tags", [])
    assert "matraix" not in tags and "persona" not in tags


@pytest.mark.parametrize(
    "task_toml",
    _persona_task_tomls(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_persona_task_toml_matches_catalog(task_toml: Path) -> None:
    dirname = task_toml.parent.name
    assert dirname in EXAMPLE_TASK_METADATA, (
        f"{dirname}: add EXAMPLE_TASK_METADATA in task_catalog.py"
    )
    expected = build_persona_task_toml_dict(dirname)
    actual = tomllib.loads(task_toml.read_text(encoding="utf-8"))

    assert actual["task"]["name"] == expected["task"]["name"]
    for key in ("type", "domain", "tags"):
        assert actual["metadata"][key] == expected["metadata"][key], key


def test_persona_bench_dim_index_matches_dimensions_json() -> None:
    dims = json.loads(DIMENSIONS_JSON.read_text(encoding="utf-8"))["dimensions"]
    id_by_index = {d["index"]: d["id"] for d in dims}
    for dirname, spec in EXAMPLE_TASK_METADATA.items():
        if not dirname.startswith("example-"):
            continue
        if not (REPO_ROOT / "persona" / "tasks" / dirname).is_dir():
            continue
        index = spec.get("bench_dim_index")
        if index is None:
            continue
        dim_id = spec.get("bench_dim_id")
        if dim_id is not None:
            assert id_by_index[int(index)] == dim_id, dirname
        grounding = load_grounding_toml(
            f"persona/tasks/{dirname}",
            repo_root=REPO_ROOT,
        )
        assert grounding is not None, f"{dirname}: missing grounding.toml"
        probe = str(grounding["probe_dimension"])
        assert probe == f"dimensions.{dim_id}", (
            f"{dirname}: grounding.toml probe_dimension must match catalog bench_dim_id"
        )
