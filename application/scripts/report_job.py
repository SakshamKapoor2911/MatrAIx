#!/usr/bin/env python3
"""Build or refresh job-level reporting artifacts for one completed Harbor job."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _repo_imports import REPO_ROOT, ensure_application_script_imports

ensure_application_script_imports()

from backend.service.job_aggregation import (  # noqa: E402
    DEFAULT_REPORTING_LLM_MODEL,
    REPORTING_LLM_MODEL_ENV,
    build_job_aggregation,
    job_aggregation_artifact_path,
    reporting_status_artifact_path,
    write_reporting_status_artifact,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _reporting_model() -> str:
    return (
        os.environ.get(REPORTING_LLM_MODEL_ENV, "").strip()
        or DEFAULT_REPORTING_LLM_MODEL
    )


def resolve_job_dir(job: str, *, repo_root: Path) -> Path:
    candidate = Path(job)
    if candidate.is_absolute():
        return candidate
    normalized = job.replace("\\", "/").strip()
    if normalized.startswith("jobs/"):
        return repo_root / normalized
    return repo_root / "jobs" / normalized


def run_job_reporting(
    job_dir: Path,
    *,
    repo_root: Path,
    enable_llm: bool,
    llm_client: Any | None = None,
) -> dict[str, Any]:
    if not job_dir.is_dir():
        raise FileNotFoundError("Job directory not found: {}".format(job_dir))

    status_path = reporting_status_artifact_path(job_dir)
    if enable_llm:
        write_reporting_status_artifact(
            job_dir,
            {
                "status": "running",
                "startedAt": _utc_now(),
                "model": _reporting_model(),
            },
        )
    try:
        aggregation = build_job_aggregation(
            job_dir,
            repo_root=repo_root,
            llm_client=llm_client,
            enable_llm=enable_llm,
        )
        if aggregation is None:
            raise ValueError("Aggregation not available for job: {}".format(job_dir.name))
    except Exception as exc:
        if enable_llm:
            write_reporting_status_artifact(
                job_dir,
                {
                    "status": "failed",
                    "startedAt": _utc_now(),
                    "finishedAt": _utc_now(),
                    "model": _reporting_model(),
                    "error": str(exc),
                },
            )
        raise
    if enable_llm and status_path.is_file():
        status_path.unlink()
    return aggregation


def _print_summary(aggregation: dict[str, Any], *, job_dir: Path, repo_root: Path) -> None:
    reporting = aggregation.get("reporting") if isinstance(aggregation, dict) else None
    reporting = reporting if isinstance(reporting, dict) else {}
    coverage = aggregation.get("coverage") if isinstance(aggregation, dict) else None
    coverage = coverage if isinstance(coverage, dict) else {}
    print("Job:", _display_path(job_dir, repo_root=repo_root))
    print("Aggregation:", _display_path(job_aggregation_artifact_path(job_dir), repo_root=repo_root))
    print(
        "Coverage: {}/{} artifacts ready".format(
            coverage.get("artifactReadyTrials", 0),
            coverage.get("trialCount", 0),
        )
    )
    print(
        "Reporting: {} | total={} completed={} ready={} failed={}".format(
            reporting.get("status", "unknown"),
            reporting.get("totalUnits", 0),
            reporting.get("completedUnits", 0),
            reporting.get("readyUnits", 0),
            reporting.get("failedUnits", 0),
        )
    )
    if reporting.get("model"):
        print("Model:", reporting["model"])
    if reporting.get("error"):
        print("Error:", reporting["error"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "job",
        help="Job directory path or job name (e.g. jobs/my-job or my-job)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root used for relative job paths and task reporting config",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Refresh aggregation only; skip live LLM summary/judge execution",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the final aggregation payload as JSON",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    job_dir = resolve_job_dir(args.job, repo_root=repo_root).resolve()
    aggregation = run_job_reporting(
        job_dir,
        repo_root=repo_root,
        enable_llm=not args.no_llm,
    )
    if args.json:
        print(json.dumps(aggregation, ensure_ascii=False, indent=2))
        return
    _print_summary(aggregation, job_dir=job_dir, repo_root=repo_root)


if __name__ == "__main__":
    main()
