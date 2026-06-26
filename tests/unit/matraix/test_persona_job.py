import json
import shutil
from collections import Counter
from pathlib import Path

from matraix.persona_job import DEFAULT_DATASET, SMOKE_PERSONA_PATH, build_job_config

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "persona" / "datasets" / "bench-dev-2000" / "manifest.json"


def test_build_job_config_controlled_probe_cohort(tmp_path: Path) -> None:
    spec = {
        "name": "test-controlled-economic",
        "probe": {"dimension": "dimensions.economic_motivation"},
        "stratify_fields": ["dimensions.economic_motivation"],
        "controlled_probe": True,
        "anchor_persona": SMOKE_PERSONA_PATH,
        "sample_size_per_value_group": 1,
        "seed": 42,
        "persona_pool": DEFAULT_DATASET,
        "task": "persona/tasks/example-survey_product-feedback",
        "agent": {
            "name": "persona-claude-code",
            "model_name": "anthropic/claude-sonnet-4-6",
        },
    }
    job = build_job_config(spec, repo_root=REPO_ROOT)
    meta = job.pop("_job_meta")

    assert meta["controlled_probe"] is True
    assert meta["anchor_persona_id"] == "0001"
    assert meta["sample_size_per_value_group"] == 1
    assert meta["sample_size"] == 4
    assert len(job["agents"]) == 4
    assert job["verifier"]["env"]["MATRAIX_PROBE_DIMENSION"] == (
        "dimensions.economic_motivation"
    )
    assert "MATRAIX_PROBE_VALUE" not in job["verifier"]["env"]

    paths = {agent["kwargs"]["persona_path"] for agent in job["agents"]}
    assert len(paths) == 4
    for rel_path in paths:
        assert Path(rel_path).as_posix().startswith(
            "persona/datasets/_generated/cohorts/"
        )

    shutil.rmtree(REPO_ROOT / "persona" / "datasets" / "_generated", ignore_errors=True)


def test_build_job_config_controlled_probe_scales_per_value_group() -> None:
    spec = {
        "name": "test-controlled-economic-pg2",
        "probe": {"dimension": "dimensions.economic_motivation"},
        "stratify_fields": ["dimensions.economic_motivation"],
        "controlled_probe": True,
        "anchor_persona": SMOKE_PERSONA_PATH,
        "sample_size_per_value_group": 2,
        "seed": 42,
        "persona_pool": DEFAULT_DATASET,
        "task": "persona/tasks/example-survey_product-feedback",
        "agent": {
            "name": "persona-claude-code",
            "model_name": "anthropic/claude-sonnet-4-6",
        },
    }
    job = build_job_config(spec, repo_root=REPO_ROOT)
    meta = job.pop("_job_meta")

    assert meta["sample_size_per_value_group"] == 2
    assert meta["sample_size"] == 8
    assert len(job["agents"]) == 8

    shutil.rmtree(REPO_ROOT / "persona" / "datasets" / "_generated", ignore_errors=True)


def test_build_job_config_stratifies_when_control_disabled() -> None:
    spec = {
        "name": "test-economic-stratify",
        "probe": {"dimension": "dimensions.economic_motivation"},
        "stratify_fields": ["dimensions.economic_motivation"],
        "controlled_probe": False,
        "confounders": {},
        "sample_size_per_value_group": 1,
        "seed": 42,
        "persona_pool": DEFAULT_DATASET,
        "task": "persona/tasks/example-survey_product-feedback",
        "agent": {
            "name": "persona-claude-code",
            "model_name": "anthropic/claude-sonnet-4-6",
        },
    }
    job = build_job_config(spec, repo_root=REPO_ROOT)
    meta = job.pop("_job_meta")

    assert meta["controlled_probe"] is False
    assert meta["confounder_probe"] is False
    assert meta["matched_pool_size"] == 2002
    assert len(job["agents"]) == 4

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_id = {p["persona_id"]: p for p in manifest["personas"]}
    motivations = [
        by_id[persona_id]["dimensions"]["economic_motivation"]
        for persona_id in meta["selected_persona_ids"]
    ]
    assert len(Counter(motivations)) == 4


def test_build_job_config_confounder_probe_from_catalog() -> None:
    spec = {
        "name": "test-confounder-economic",
        "probe": {"dimension": "dimensions.economic_motivation"},
        "stratify_fields": ["dimensions.economic_motivation"],
        "controlled_probe": False,
        "sample_size_per_value_group": 1,
        "seed": 42,
        "persona_pool": DEFAULT_DATASET,
        "task": "persona/tasks/example-survey_product-feedback",
        "agent": {
            "name": "persona-claude-code",
            "model_name": "anthropic/claude-sonnet-4-6",
        },
    }
    job = build_job_config(spec, repo_root=REPO_ROOT)
    meta = job.pop("_job_meta")

    assert meta["confounder_probe"] is True
    assert meta["controlled_probe"] is False
    assert meta["confounders"]["socioeconomic_band"] == "Middle"
    assert meta["confounders"]["age_bracket"] == "25-34"
    assert meta["sample_size"] == 4
    assert len(job["agents"]) == 4

    import yaml

    confounder_keys = set(meta["confounders"])
    motivations: list[str] = []
    for agent in job["agents"]:
        rel = agent["kwargs"]["persona_path"]
        dims = yaml.safe_load((REPO_ROOT / rel).read_text())["dimensions"]
        for key in confounder_keys:
            assert dims[key] == meta["confounders"][key]
        motivations.append(dims["economic_motivation"])
    assert len(set(motivations)) == 4

    shutil.rmtree(REPO_ROOT / "persona" / "datasets" / "_generated", ignore_errors=True)


def test_build_job_config_confounder_probe_synthesizes_shortage() -> None:
    spec = {
        "name": "test-confounder-economic-pg2",
        "probe": {"dimension": "dimensions.economic_motivation"},
        "stratify_fields": ["dimensions.economic_motivation"],
        "controlled_probe": False,
        "sample_size_per_value_group": 3,
        "seed": 42,
        "persona_pool": "persona/datasets/bench-dev-2000",
        "task": "persona/tasks/example-survey_product-feedback",
        "agent": {
            "name": "persona-claude-code",
            "model_name": "anthropic/claude-sonnet-4-6",
        },
    }
    job = build_job_config(spec, repo_root=REPO_ROOT)
    meta = job.pop("_job_meta")

    assert meta["confounder_probe"] is True
    assert meta["sample_size"] == 12
    assert meta.get("synthesized_trials", 0) >= 1

    shutil.rmtree(REPO_ROOT / "persona" / "datasets" / "_generated", ignore_errors=True)


def test_build_job_config_random_when_no_stratify() -> None:
    spec = {
        "name": "test-random",
        "probe": {"dimension": "dimensions.economic_motivation"},
        "stratify_fields": None,
        "controlled_probe": False,
        "sample_size": 10,
        "seed": 42,
        "persona_pool": DEFAULT_DATASET,
        "task": "persona/tasks/example-survey_product-feedback",
        "agent": {
            "name": "persona-claude-code",
            "model_name": "anthropic/claude-sonnet-4-6",
        },
    }
    job = build_job_config(spec, repo_root=REPO_ROOT)
    meta = job.pop("_job_meta")
    assert meta["stratify_fields"] == []
    assert len(job["agents"]) == 10


def test_build_job_config_optional_probe_value_filter() -> None:
    spec = {
        "name": "test-economic-slice",
        "probe": {
            "dimension": "dimensions.economic_motivation",
            "value": "Cost-sensitive",
        },
        "sample_size": 10,
        "seed": 42,
        "persona_pool": DEFAULT_DATASET,
        "task": "persona/tasks/example-survey_product-feedback",
        "agent": {
            "name": "persona-claude-code",
            "model_name": "anthropic/claude-sonnet-4-6",
        },
    }
    job = build_job_config(spec, repo_root=REPO_ROOT)
    meta = job.pop("_job_meta")

    assert meta["matched_pool_size"] >= 200
    assert job["verifier"]["env"]["MATRAIX_PROBE_VALUE"] == "Cost-sensitive"

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_id = {p["persona_id"]: p for p in manifest["personas"]}
    for persona_id in meta["selected_persona_ids"]:
        assert (
            by_id[persona_id]["dimensions"]["economic_motivation"] == "Cost-sensitive"
        )
