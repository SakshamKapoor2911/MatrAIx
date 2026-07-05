#!/usr/bin/env python3
"""Sample personas and write a multi-trial Harbor job YAML for application tasks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

from personabench.application_job import (
    build_application_job_config,
    collect_run_env_exports,
)
from personabench.persona_job import DEFAULT_DATASET, parse_stratify_field_args

from _repo_imports import REPO_ROOT, ensure_application_script_imports

DEFAULT_JOBS_DIR = REPO_ROOT / "configs" / "jobs" / "application-task-job-recipe"
_EXECUTION_MODES = frozenset({"auto", "force_docker", "smoke"})


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "application-job"


def _default_job_name(
    *,
    task: str,
    stratify_fields: list[str],
    sample_size: int,
    execution_mode: str,
) -> str:
    task_slug = _slug(Path(task).name)
    mode_suffix = "" if execution_mode == "auto" else f"-{execution_mode}"
    if stratify_fields:
        dim_slug = "-".join(_slug(field.split(".")[-1]) for field in stratify_fields)
        return f"{task_slug}{mode_suffix}-{dim_slug}-n{sample_size}"
    return f"{task_slug}{mode_suffix}-n{sample_size}"


def _format_run_env_comment(exports: list[tuple[str, str]]) -> str:
    if not exports:
        return ""
    lines = ["# Run (after exporting API keys):"]
    lines.append("#   export ANTHROPIC_API_KEY=...")
    if any(name == "MATRIX_CHATBOT_TASK_PATH" for name, _ in exports):
        lines.append("#   export OPENAI_API_KEY=...   # user-sim engine default")
    for name, value in exports:
        lines.append(f"#   export {name}={value}")
    lines.append(f"#   uv run harbor run -c <this-file>")
    lines.append("#")
    return "\n".join(lines) + "\n"


def _resolve_auto_launch(
    *,
    task_path: str,
    execution_mode: str,
    agent_name: str | None,
    repo_root: Path,
) -> tuple[str, str]:
    ensure_application_script_imports()
    from backend.service.harbor_job_service import resolve_agent_name, resolve_trial_profile

    trial_profile = resolve_trial_profile(
        task_path,
        mode=execution_mode,
        repo_root=repo_root,
    )
    agent = resolve_agent_name(
        task_path,
        repo_root=repo_root,
        explicit=agent_name,
        mode=execution_mode,
        trial_profile=trial_profile,
    )
    return trial_profile, agent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        required=True,
        help="Application task path (e.g. application/tasks/example-survey_product-feedback)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=1,
        help="Number of personas / trials (default: 1)",
    )
    parser.add_argument(
        "--persona-ids",
        nargs="*",
        default=[],
        metavar="ID",
        help="Explicit persona ids (pool or application/persona_eval catalog). Skips random sampling.",
    )
    parser.add_argument(
        "--stratify",
        action="append",
        default=[],
        metavar="FIELD",
        help=(
            "Stratify sampling by persona field(s). Repeat or comma-separate. "
            "Default: random sample from the pool (no stratification). "
            "Pass --stratify to balance across field values."
        ),
    )
    parser.add_argument(
        "--no-stratify",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help=f"Persona dataset directory (default: {DEFAULT_DATASET})",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--execution-mode",
        choices=sorted(_EXECUTION_MODES),
        default="auto",
        help=(
            "Harbor execution mode. 'auto' picks native host survey/chat profiles when "
            "applicable (default: auto)."
        ),
    )
    parser.add_argument(
        "--cua-backend",
        default=None,
        help="CUA backend override (e.g. macos, ios, docker) when execution-mode is auto.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Job basename for output YAML (default: derived from task + stratify fields)",
    )
    parser.add_argument(
        "--job-name",
        default=None,
        help="Harbor job_name / jobs/<job_name>/ directory (default: same as --name)",
    )
    parser.add_argument(
        "--agent-name",
        default=None,
        help="Override Harbor agent (default: derived from task + execution mode)",
    )
    parser.add_argument("--model-name", default="anthropic/claude-sonnet-4-6")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output job YAML (default: configs/jobs/application-task-job-recipe/<name>.yaml)",
    )
    args = parser.parse_args()

    explicit_stratify = parse_stratify_field_args(args.stratify)
    if explicit_stratify:
        stratify_fields = explicit_stratify
    else:
        stratify_fields = []

    persona_ids = [value.strip() for value in args.persona_ids if value.strip()]
    if persona_ids and stratify_fields:
        parser.error("--persona-ids cannot be combined with --stratify")

    execution_mode = args.execution_mode
    trial_profile, resolved_agent = _resolve_auto_launch(
        task_path=args.task,
        execution_mode=execution_mode,
        agent_name=args.agent_name,
        repo_root=REPO_ROOT,
    )
    agent_name = args.agent_name or resolved_agent

    job_slug = args.name or _default_job_name(
        task=args.task,
        stratify_fields=stratify_fields,
        sample_size=len(persona_ids) if persona_ids else args.sample_size,
        execution_mode=execution_mode,
    )
    job_name = args.job_name or job_slug

    spec: dict[str, object] = {
        "name": job_slug,
        "stratify_fields": stratify_fields,
        "seed": args.seed,
        "persona_pool": args.dataset,
        "task": args.task,
        "execution_mode": execution_mode,
        "trial_profile": trial_profile,
        "agent": {
            "name": agent_name,
            "model_name": args.model_name,
        },
        "job": {
            "job_name": job_name,
            "jobs_dir": "jobs",
            "n_attempts": 1,
            "n_concurrent_trials": 1,
            "timeout_multiplier": 1.0,
        },
    }
    if persona_ids:
        spec["persona_ids"] = persona_ids
    else:
        spec["sample_size"] = args.sample_size
    if args.cua_backend:
        spec["cua_backend"] = args.cua_backend

    if execution_mode == "force_docker" and not args.cua_backend:
        spec["job"]["environment"] = {"type": "docker", "delete": True}

    job_config = build_application_job_config(spec, repo_root=REPO_ROOT)
    meta = job_config.pop("_job_meta")

    if args.cua_backend:
        from personabench.application_job import resolve_job_environment

        job_config["environment"] = resolve_job_environment(
            execution_mode=execution_mode,
            trial_profile=trial_profile,
            cua_backend=args.cua_backend,
        )

    out_path = args.out
    if out_path is None:
        DEFAULT_JOBS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = DEFAULT_JOBS_DIR / f"{job_slug}.yaml"
    elif not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    run_env_exports = collect_run_env_exports(
        trial_profile=trial_profile,
        task_path=args.task,
        repo_root=REPO_ROOT,
    )
    stratify_line = (
        ", ".join(stratify_fields) if stratify_fields else "none (random sample)"
    )
    header = (
        f"# Generated by application/scripts/generate_application_job.py\n"
        f"# Task: {args.task}\n"
        f"# Execution mode: {execution_mode} | trial profile: {trial_profile}\n"
        f"# Agent: {agent_name} | harbor task: {job_config['tasks'][0]['path']}\n"
        f"# Stratify: {stratify_line} | "
        f"sample={meta['sample_size']} from pool={meta['matched_pool_size']} | "
        f"seed={meta['seed']}\n"
        f"# Personas: {', '.join(meta['selected_persona_ids'])}\n"
        f"#\n"
        f"{_format_run_env_comment(run_env_exports)}"
    )
    out_path.write_text(
        header + yaml.safe_dump(job_config, sort_keys=False),
        encoding="utf-8",
    )

    sidecar = out_path.with_suffix(".meta.json")
    sidecar.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(
        f"Matched {meta['matched_pool_size']} personas; selected {meta['sample_size']}"
    )
    print(f"Execution mode: {execution_mode} | trial profile: {trial_profile}")
    print(f"Agent: {agent_name} | harbor task: {job_config['tasks'][0]['path']}")
    print(f"Job: {out_path}")
    print(f"Meta: {sidecar}")
    print("Run:")
    print("  export ANTHROPIC_API_KEY=...")
    if any(name == "MATRIX_CHATBOT_TASK_PATH" for name, _ in run_env_exports):
        print("  export OPENAI_API_KEY=...   # user-sim engine default")
    for name, value in run_env_exports:
        print(f"  export {name}={value}")
    print(f"  uv run harbor run -c {_display_path(out_path)}")


if __name__ == "__main__":
    main()
