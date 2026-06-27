#!/usr/bin/env python3
"""Sample personas and write a multi-trial Harbor job YAML."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

from personabench.persona_job import (
    DEFAULT_DATASET,
    DEFAULT_STRATIFY_FIELDS,
    SMOKE_PERSONA_PATH,
    build_job_config,
    parse_stratify_field_args,
)
from personabench.task_catalog import (
    confounder_values_from_grounding,
    get_task_grounding_spec,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JOBS_DIR = REPO_ROOT / "configs" / "jobs" / "persona-task-grounding-job-recipe"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "persona-job"


def _resolve_fields(args: argparse.Namespace) -> tuple[list[str], list[str] | None]:
    """Return (probe_fields, stratify_fields for sampling)."""
    explicit = parse_stratify_field_args(args.stratify)
    probe_fields = explicit or list(DEFAULT_STRATIFY_FIELDS)

    if args.probe_value is not None:
        return probe_fields, None
    if args.no_stratify:
        return probe_fields, None
    if explicit:
        return probe_fields, explicit
    return probe_fields, list(DEFAULT_STRATIFY_FIELDS)


def _uses_per_value_group_sampling(
    *,
    probe_value: str | None,
    stratify_fields: list[str] | None,
    no_stratify: bool,
) -> bool:
    if probe_value is not None or no_stratify:
        return False
    return bool(stratify_fields)


def _default_job_name(
    *,
    task: str,
    probe_dimension: str,
    probe_value: str | None,
    stratify_fields: list[str] | None,
    per_value_group: int,
    sample_size_total: int | None,
) -> str:
    task_slug = _slug(Path(task).name)
    if probe_value is not None:
        dim_slug = _slug(probe_dimension.split(".")[-1])
        value_slug = _slug(probe_value)
        total = sample_size_total if sample_size_total is not None else per_value_group
        return f"{task_slug}-{dim_slug}-{value_slug}-n{total}"
    if stratify_fields:
        dim_slug = "-".join(_slug(field.split(".")[-1]) for field in stratify_fields)
        return f"{task_slug}-{dim_slug}-pg{per_value_group}"
    total = sample_size_total if sample_size_total is not None else per_value_group
    return f"{task_slug}-n{total}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        required=True,
        help="Harbor task path (e.g. persona/tasks/example-survey_product-feedback)",
    )
    parser.add_argument(
        "--stratify",
        action="append",
        default=[],
        metavar="FIELD",
        help=(
            "Persona field(s) to stratify on. First field is also the grounding probe. "
            f"Default: {', '.join(DEFAULT_STRATIFY_FIELDS)}. "
            "Use --no-stratify for random sampling (probe still uses first field)."
        ),
    )
    parser.add_argument(
        "--probe-value",
        default=None,
        help="Optional: restrict pool to personas with this value on the probe field",
    )
    parser.add_argument(
        "--no-stratify",
        action="store_true",
        help="Random sample from pool instead of stratifying",
    )
    parser.add_argument(
        "--no-controlled-probe",
        action="store_true",
        help="Disable anchor-based controlled-probe cohort (legacy opt-out)",
    )
    parser.add_argument(
        "--controlled-probe",
        action="store_true",
        help=(
            "Force anchor-based controlled-probe cohort (clone one persona, vary probe only). "
            "Default when the task catalog has no confounders."
        ),
    )
    parser.add_argument(
        "--anchor-persona",
        default=SMOKE_PERSONA_PATH,
        help=f"Anchor persona for controlled-probe jobs (default: {SMOKE_PERSONA_PATH})",
    )
    parser.add_argument(
        "--sample-size-per-value-group",
        type=int,
        default=1,
        help=(
            "Personas to sample per probe/stratify value group (default: 1). "
            "Total trials = this × number of value groups."
        ),
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help=(
            "Total personas/trials for random sampling or --probe-value filtering only. "
            "Ignored when stratifying or using controlled-probe cohorts."
        ),
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help=f"Persona dataset directory (default: {DEFAULT_DATASET})",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--n-concurrent-trials",
        type=int,
        default=1,
        help="Harbor parallel trial concurrency (default: 1)",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Job basename for output YAML (default: derived from task + fields)",
    )
    parser.add_argument(
        "--job-name",
        default=None,
        help="Harbor job_name / jobs/<job_name>/ directory (default: same as --name)",
    )
    parser.add_argument("--agent-name", default="persona-claude-code")
    parser.add_argument("--model-name", default="anthropic/claude-sonnet-4-6")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output job YAML (default: configs/jobs/persona-task-grounding-job-recipe/<name>.yaml)",
    )
    args = parser.parse_args()

    probe_fields, stratify_fields = _resolve_fields(args)
    probe_dimension = probe_fields[0]
    per_value_group = args.sample_size_per_value_group

    job_slug = args.name or _default_job_name(
        task=args.task,
        probe_dimension=probe_dimension,
        probe_value=args.probe_value,
        stratify_fields=stratify_fields,
        per_value_group=per_value_group,
        sample_size_total=args.sample_size,
    )
    job_name = args.job_name or job_slug

    grounding = get_task_grounding_spec(args.task, repo_root=REPO_ROOT)
    catalog_confounders = confounder_values_from_grounding(grounding or {})
    if args.controlled_probe:
        use_controlled_probe = True
    elif args.no_controlled_probe:
        use_controlled_probe = False
    elif catalog_confounders and args.probe_value is None and not args.no_stratify:
        use_controlled_probe = False
    else:
        use_controlled_probe = True

    spec = {
        "name": job_slug,
        "probe": {
            "dimension": probe_dimension,
            **({"value": args.probe_value} if args.probe_value is not None else {}),
        },
        "stratify_fields": stratify_fields,
        "controlled_probe": use_controlled_probe,
        "anchor_persona": args.anchor_persona,
        "sample_size_per_value_group": per_value_group,
        **({"sample_size": args.sample_size} if args.sample_size is not None else {}),
        "seed": args.seed,
        "persona_pool": args.dataset,
        "task": args.task,
        **({"grounding": grounding} if grounding else {}),
        "agent": {
            "name": args.agent_name,
            "model_name": args.model_name,
        },
        "job": {
            "job_name": job_name,
            "jobs_dir": "jobs",
            "n_attempts": 1,
            "n_concurrent_trials": args.n_concurrent_trials,
            "timeout_multiplier": 1.0,
            "environment": {"type": "docker", "delete": True},
        },
    }

    job_config = build_job_config(spec, repo_root=REPO_ROOT)
    meta = job_config.pop("_job_meta")

    out_path = args.out
    if out_path is None:
        DEFAULT_JOBS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = DEFAULT_JOBS_DIR / f"{job_slug}.yaml"
    elif not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.probe_value is not None:
        probe_line = f"probe={probe_dimension}={args.probe_value} (filtered pool)"
    elif stratify_fields:
        if meta.get("confounder_probe"):
            confounder_line = ", ".join(
                f"{key}={value}" for key, value in meta.get("confounders", {}).items()
            )
            probe_line = (
                f"probe={probe_dimension} | confounders=[{confounder_line}] "
                f"| filtered_pool={meta.get('filtered_pool_size', meta['matched_pool_size'])}"
            )
            if meta.get("synthesized_trials"):
                probe_line += f" | synthesized={meta['synthesized_trials']}"
        elif meta.get("controlled_probe"):
            probe_line = (
                f"probe={probe_dimension} | controlled cohort from "
                f"{meta.get('anchor_persona_id')} @ {args.anchor_persona}"
            )
        else:
            probe_line = (
                f"probe={probe_dimension} | stratify={', '.join(stratify_fields)}"
            )
    else:
        probe_line = f"probe={probe_dimension} | stratify=none (random)"

    per_group = meta.get("sample_size_per_value_group", per_value_group)
    sample_line = (
        f"per_value_group={per_group} | total_trials={meta['sample_size']}"
        if _uses_per_value_group_sampling(
            probe_value=args.probe_value,
            stratify_fields=stratify_fields,
            no_stratify=args.no_stratify,
        )
        else f"total_trials={meta['sample_size']}"
    )
    pool_size = meta.get("filtered_pool_size", meta["matched_pool_size"])
    header = (
        f"# Generated by persona/scripts/generate_persona_job.py\n"
        f"# Task: {args.task}\n"
        f"# {probe_line} | {sample_line} | pool={pool_size} | "
        f"seed={meta['seed']}\n"
        f"# Personas: {', '.join(meta['selected_persona_ids'])}\n"
        f"#\n"
        f"#   uv run harbor run -c {out_path.relative_to(REPO_ROOT)}\n"
        f"#   uv run python persona/reporting/eval_grounding_job.py jobs/{job_name} \\\n"
        f"#     --meta {out_path.with_suffix('.meta.json').relative_to(REPO_ROOT)}\n\n"
    )
    out_path.write_text(
        header + yaml.safe_dump(job_config, sort_keys=False),
        encoding="utf-8",
    )

    sidecar = out_path.with_suffix(".meta.json")
    sidecar.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    pool_size = meta.get("filtered_pool_size", meta["matched_pool_size"])
    print(
        f"Matched {pool_size} personas; "
        f"selected {meta['sample_size']} trials "
        f"(per_value_group={meta.get('sample_size_per_value_group', 'n/a')})"
    )
    print(f"Job: {out_path}")
    print(f"Meta: {sidecar}")
    print(f"Run: uv run harbor run -c {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
