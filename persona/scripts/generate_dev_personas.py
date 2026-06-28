#!/usr/bin/env python3
"""Generate a local dev persona pool from the MatrAIx dimension schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from personabench.persona_consistency import validate_dimensions
from personabench.persona_dimension_catalog import values_for_dimension
from personabench.persona_generator import (
    build_probe_strata,
    generate_persona_pool,
    write_persona_dataset,
)
from personabench.task_catalog import (
    confounder_values_from_grounding,
    get_task_grounding_spec,
    probe_dimension_from_grounding,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COUNT = 2000
DEFAULT_GENERATED_DATASETS_DIR = REPO_ROOT / "persona" / "datasets" / "_generated"


def _default_out_dir(count: int) -> Path:
    return DEFAULT_GENERATED_DATASETS_DIR / f"bench-dev-{count}"


def _stratum_top_up_from_task(
    task_path: str,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    grounding = get_task_grounding_spec(task_path, repo_root=REPO_ROOT)
    if not grounding:
        raise SystemExit(f"No grounding.toml (or catalog grounding) for {task_path!r}")
    confounders = confounder_values_from_grounding(grounding)
    probe_dimension = probe_dimension_from_grounding(grounding)
    if not confounders or not probe_dimension:
        raise SystemExit(
            f"Task {task_path!r} grounding must define confounders and probe_dimension"
        )
    probe_key = probe_dimension.removeprefix("dimensions.")
    probe_values = values_for_dimension(probe_key)
    if not probe_values:
        raise SystemExit(f"No catalog values for probe dimension {probe_key!r}")
    return build_probe_strata(
        confounders=confounders,
        probe_dimension=probe_dimension,
        probe_values=probe_values,
    ), grounding


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: persona/datasets/_generated/bench-dev-<count>)",
    )
    parser.add_argument("--smoke-id", default="0042")
    parser.add_argument(
        "--task",
        default=None,
        help=(
            "Optional Harbor task path; when set with --stratum-min, top up personas "
            "for each catalog confounder × probe value cell"
        ),
    )
    parser.add_argument(
        "--stratum-min",
        type=int,
        default=0,
        help="Minimum personas per confounder×probe stratum when --task is set (default: 0)",
    )
    args = parser.parse_args()

    out = args.out if args.out is not None else _default_out_dir(args.count)
    if not out.is_absolute():
        out = REPO_ROOT / out

    stratum_top_up: list[dict[str, str]] | None = None
    grounding_meta: dict[str, object] | None = None
    if args.task:
        if args.stratum_min < 1:
            raise SystemExit("--task requires --stratum-min >= 1")
        stratum_top_up, grounding_meta = _stratum_top_up_from_task(args.task)

    personas = generate_persona_pool(
        count=args.count,
        seed=args.seed,
        smoke_persona_id=args.smoke_id,
        stratum_top_up=stratum_top_up,
        min_per_stratum=args.stratum_min,
    )

    violations = 0
    for entry in personas:
        errors = validate_dimensions(entry["dimensions"])
        if errors:
            violations += 1
            print(f"VIOLATION persona_{entry['persona_id']}: {errors}")
    if violations:
        raise SystemExit(f"{violations} personas failed consistency checks")

    manifest = write_persona_dataset(
        out_dir=out,
        personas=personas,
        repo_root=REPO_ROOT,
        kind=f"bench-dev-{args.count}",
        seed=args.seed,
        smoke_persona_id=args.smoke_id,
    )
    if stratum_top_up and args.stratum_min > 0:
        manifest["stratum_top_up"] = {
            "task": args.task,
            "min_per_stratum": args.stratum_min,
            "strata_count": len(stratum_top_up or []),
            "grounding": grounding_meta,
        }
        (out / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"Wrote {manifest['count']} personas to {out}")
    print(f"Smoke: persona_{manifest['smoke_persona_id']}.yaml")
    print(
        f"Dimensions: {manifest.get('dimension_count', len(manifest['dimension_ids']))} fields"
    )
    if stratum_top_up:
        print(
            f"Stratum top-up: {len(stratum_top_up)} cells × min {args.stratum_min} "
            f"from task {args.task}"
        )


if __name__ == "__main__":
    main()
