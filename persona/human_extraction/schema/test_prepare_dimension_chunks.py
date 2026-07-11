from __future__ import annotations

import copy
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parents[3]
SCRIPT_PATH = (
    REPO_ROOT
    / "persona"
    / "human_extraction"
    / "schema"
    / "prepare_dimension_chunks.py"
)


@pytest.fixture(scope="module")
def chunk_module():
    spec = importlib.util.spec_from_file_location("prepare_dimension_chunks_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_manifest_has_exact_coverage_and_schema_metadata(chunk_module):
    catalog = chunk_module.load_and_validate_catalog(chunk_module.DEFAULT_SOURCE)
    manifest = chunk_module.build_manifest(catalog)

    source_by_id = {dimension["id"]: dimension for dimension in catalog["dimensions"]}
    flattened = [
        dimension_id
        for chunk in manifest["chunks"]
        for dimension_id in chunk["dimension_ids"]
    ]

    assert len(flattened) == 1290
    assert Counter(flattened) == Counter(source_by_id.keys())
    assert manifest["summary"] == {
        **manifest["summary"],
        "chunk_count": 45,
        "covered_dimension_count": 1290,
        "unique_dimension_count": 1290,
        "min_chunk_size": 20,
        "median_chunk_size": 28,
        "max_chunk_size": 40,
    }
    for chunk in manifest["chunks"]:
        assert chunk["size"] == len(chunk["dimension_ids"])
        assert chunk["dimension_ids"] == [dimension["id"] for dimension in chunk["dimensions"]]
        assert [dimension["index"] for dimension in chunk["dimensions"]] == sorted(
            dimension["index"] for dimension in chunk["dimensions"]
        )
        assert all(dimension["values"] for dimension in chunk["dimensions"])
        assert all(source_by_id[dimension["id"]] == dimension for dimension in chunk["dimensions"])


def test_every_size_exception_is_explicit_and_semantic(chunk_module):
    catalog = chunk_module.load_and_validate_catalog(chunk_module.DEFAULT_SOURCE)
    manifest = chunk_module.build_manifest(catalog)

    exception_ids = {
        item["chunk_id"] for item in manifest["summary"]["size_exceptions"]
    }
    assert exception_ids == {
        "expertise_humanities_creative_service",
        "communication_cognitive_style",
        "behavior_preferences_time",
        "culture_country_familiarity",
        "sports_interests",
        "developer_ai_tools_workflows",
    }
    for chunk in manifest["chunks"]:
        outside = not (
            chunk_module.PREFERRED_MIN_SIZE
            <= chunk["size"]
            <= chunk_module.PREFERRED_MAX_SIZE
        )
        assert outside == ("size_exception" in chunk)
        if outside:
            assert len(chunk["size_exception"]) > 40


def test_checked_in_manifest_is_deterministic_and_current(chunk_module):
    catalog = chunk_module.load_and_validate_catalog(chunk_module.DEFAULT_SOURCE)
    first = chunk_module.render_manifest(chunk_module.build_manifest(catalog))
    second = chunk_module.render_manifest(chunk_module.build_manifest(catalog))

    assert first == second
    assert chunk_module.DEFAULT_OUTPUT.read_text(encoding="utf-8") == first
    assert chunk_module.main(["--check"]) == 0

    records = [json.loads(line) for line in first.splitlines()]
    assert len(records) == 45
    assert [record["chunk_id"] for record in records] == [
        chunk["chunk_id"] for chunk in chunk_module.build_manifest(catalog)["chunks"]
    ]
    assert all(record["manifest_context"]["chunk_count"] == 45 for record in records)
    assert all(record["dimensions"] for record in records)


def test_catalog_validation_rejects_duplicate_ids(chunk_module, tmp_path):
    catalog = json.loads(chunk_module.DEFAULT_SOURCE.read_text(encoding="utf-8"))
    invalid = copy.deepcopy(catalog)
    invalid["dimensions"][1]["id"] = invalid["dimensions"][0]["id"]
    source = tmp_path / "dimensions.json"
    source.write_text(json.dumps(invalid), encoding="utf-8")

    with pytest.raises(chunk_module.ValidationError, match="duplicate dimension id"):
        chunk_module.load_and_validate_catalog(source)
