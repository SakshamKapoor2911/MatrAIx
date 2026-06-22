from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from matraix.application_job import build_application_job_config
from matraix.persona_job import DEFAULT_DATASET

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "persona" / "datasets" / "bench-dev-2000" / "manifest.json"


def test_build_application_job_random_sample() -> None:
    spec = {
        "name": "test-app-random",
        "stratify_fields": [],
        "sample_size": 10,
        "seed": 42,
        "persona_pool": DEFAULT_DATASET,
        "task": "application/tasks/example-survey_product-feedback",
        "agent": {
            "name": "persona-claude-code",
            "model_name": "anthropic/claude-sonnet-4-6",
        },
    }
    job = build_application_job_config(spec, repo_root=REPO_ROOT)
    meta = job.pop("_job_meta")

    assert meta["matched_pool_size"] == 2002
    assert len(job["agents"]) == 10
    assert meta["sample_size"] == 10
    assert "verifier" not in job
    assert job["tasks"][0]["path"].startswith("application/tasks/")


def test_build_application_job_stratify_one_field() -> None:
    spec = {
        "name": "test-app-age-bracket",
        "stratify_fields": ["dimensions.age_bracket"],
        "sample_size_per_value_group": 2,
        "seed": 42,
        "persona_pool": DEFAULT_DATASET,
        "task": "application/tasks/example-survey_product-feedback",
        "agent": {
            "name": "persona-claude-code",
            "model_name": "anthropic/claude-sonnet-4-6",
        },
    }
    job = build_application_job_config(spec, repo_root=REPO_ROOT)
    meta = job.pop("_job_meta")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_id = {p["persona_id"]: p for p in manifest["personas"]}
    age_brackets = [
        by_id[persona_id]["dimensions"]["age_bracket"]
        for persona_id in meta["selected_persona_ids"]
    ]
    assert len(job["agents"]) == 14
    assert meta["sample_size_per_value_group"] == 2
    assert len(Counter(age_brackets)) == 7


def test_build_application_job_stratify_two_fields() -> None:
    spec = {
        "name": "test-app-two-fields",
        "stratify_fields": [
            "dimensions.age_bracket",
            "dimensions.economic_motivation",
        ],
        "sample_size_per_value_group": 1,
        "seed": 42,
        "persona_pool": DEFAULT_DATASET,
        "task": "application/tasks/example-survey_product-feedback",
        "agent": {
            "name": "persona-claude-code",
            "model_name": "anthropic/claude-sonnet-4-6",
        },
    }
    job = build_application_job_config(spec, repo_root=REPO_ROOT)
    meta = job.pop("_job_meta")

    assert meta["sample_size_per_value_group"] == 1
    assert len(meta["selected_persona_ids"]) >= 20
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_id = {p["persona_id"]: p for p in manifest["personas"]}
    buckets = Counter(
        (
            by_id[persona_id]["dimensions"]["age_bracket"],
            by_id[persona_id]["dimensions"]["economic_motivation"],
        )
        for persona_id in meta["selected_persona_ids"]
    )
    assert len(buckets) >= 15
