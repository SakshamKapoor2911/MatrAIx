#!/usr/bin/env python3
"""Aggregate per-trial grounding.json files into a job-level report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from personabench.persona_grounding import (
    build_job_grounding_report,
    discover_trial_dirs,
    load_trial_grounding,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "job_dir",
        type=Path,
        help="Harbor job directory (e.g. jobs/example-survey-product-feedback-age-group-n1)",
    )
    parser.add_argument(
        "--meta",
        type=Path,
        required=True,
        help=(
            "Job meta JSON sidecar (e.g. "
            "configs/jobs/persona-task-grounding-job-recipe/example-survey-product-feedback-age-group-n1.meta.json)"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output report path (default: <job_dir>/persona_grounding_report.json)",
    )
    args = parser.parse_args()

    job_dir = args.job_dir if args.job_dir.is_absolute() else REPO_ROOT / args.job_dir
    if not job_dir.is_dir():
        raise SystemExit(f"Job directory not found: {job_dir}")

    meta_path = args.meta if args.meta.is_absolute() else REPO_ROOT / args.meta
    if not meta_path.is_file():
        raise SystemExit(f"Meta file not found: {meta_path}")

    job_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    trial_reports = [
        load_trial_grounding(trial_dir) for trial_dir in discover_trial_dirs(job_dir)
    ]

    report = build_job_grounding_report(trial_reports, job_meta=job_meta)

    out_path = args.out or (job_dir / "persona_grounding_report.json")
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(report["conclusion"])
    print(
        f"dim_grounding_mean={report['dim_grounding_mean']:.2f} "
        f"pass_rate={report['dim_grounding_pass_rate']:.0%} "
        f"counterfactual_rate={report['counterfactual_rate']:.0%}"
    )
    print(f"Report: {out_path}")


if __name__ == "__main__":
    main()
