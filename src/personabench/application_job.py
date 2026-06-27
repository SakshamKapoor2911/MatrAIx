"""Build multi-persona Harbor job configs for application task runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from personabench.persona_job import (
    load_manifest,
    sample_personas,
    sample_personas_stratified,
)

DEFAULT_APPLICATION_JOBS_DIR = "configs/jobs/application-task-job-recipe"


def select_personas(
    pool: list[dict[str, Any]],
    *,
    sample_size: int | None,
    sample_size_per_value_group: int,
    seed: int,
    stratify_fields: list[str] | None,
    repo_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (matched pool, chosen personas)."""
    matched = pool
    if stratify_fields:
        chosen = sample_personas_stratified(
            pool,
            stratify_fields=stratify_fields,
            sample_size_per_value_group=sample_size_per_value_group,
            seed=seed,
            repo_root=repo_root,
        )
    else:
        total = int(
            sample_size if sample_size is not None else sample_size_per_value_group
        )
        chosen = sample_personas(matched, sample_size=total, seed=seed)
    return matched, chosen


def build_application_job_config(
    spec: dict[str, Any], *, repo_root: Path
) -> dict[str, Any]:
    pool_dir = repo_root / spec["persona_pool"]
    per_value_group = int(spec.get("sample_size_per_value_group", 1))
    sample_size_total = spec.get("sample_size")
    seed = int(spec.get("seed", 42))
    stratify_fields = list(spec.get("stratify_fields") or [])

    pool = load_manifest(pool_dir, repo_root=repo_root)
    matched, chosen = select_personas(
        pool,
        sample_size=sample_size_total,
        sample_size_per_value_group=per_value_group,
        seed=seed,
        stratify_fields=stratify_fields or None,
        repo_root=repo_root,
    )

    agent_spec = spec["agent"]
    job_spec = spec.get("job", {})
    job_slug = spec.get("name", "application-task-job")

    agents = [
        {
            "name": agent_spec["name"],
            "model_name": agent_spec["model_name"],
            "kwargs": {"persona_path": entry["path"]},
        }
        for entry in chosen
    ]

    job: dict[str, Any] = {
        "job_name": job_spec.get("job_name", job_slug),
        "jobs_dir": job_spec.get("jobs_dir", "jobs"),
        "n_attempts": job_spec.get("n_attempts", 1),
        "timeout_multiplier": job_spec.get("timeout_multiplier", 1.0),
        "n_concurrent_trials": job_spec.get("n_concurrent_trials", 1),
        "quiet": job_spec.get("quiet", False),
        "environment": job_spec.get(
            "environment",
            {"type": "docker", "delete": True},
        ),
        "agents": agents,
        "tasks": [{"path": spec["task"]}],
        "_job_meta": {
            "job_slug": job_slug,
            "task": spec["task"],
            "sample_size": len(chosen),
            "sample_size_per_value_group": per_value_group,
            "seed": seed,
            "stratify_fields": stratify_fields,
            "matched_pool_size": len(matched),
            "selected_persona_ids": [entry["persona_id"] for entry in chosen],
        },
    }
    verifier = spec.get("verifier")
    if verifier:
        job["verifier"] = verifier
    return job
