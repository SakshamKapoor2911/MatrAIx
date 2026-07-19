#!/usr/bin/env python3
"""Generate a local dev persona pool from the PersonaBench dimension schema.

Modes:
  * Default — even coverage pool (``--count``, default 2000).
  * Grounding top-up — ``--task`` + ``--stratum-min`` (persona grounding cells).
  * Strategy top-up — ``--strategy`` pointing at a task ``persona_strategy.json``
    (or task dir). Expands ``dimensionFilters`` into strata and tops up each
    cell so Playground / CLI sampling does not fail on the 200-persona fixture.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from personabench.persona_consistency import validate_dimensions
from personabench.persona_dimension_catalog import values_for_dimension
from personabench.persona_generator import (
    PERSONA_SOURCES,
    build_filter_strata,
    build_probe_strata,
    filter_feasible_strata,
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
DEFAULT_STRATEGY_STRATUM_MIN = 2
MAX_FILTER_STRATA = 256


def _default_out_dir(count: int) -> Path:
    return DEFAULT_GENERATED_DATASETS_DIR / f"bench-dev-{count}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "strategy"


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


def _resolve_strategy_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if path.is_dir():
        candidate = path / "persona_strategy.json"
        if not candidate.is_file():
            raise SystemExit(f"No persona_strategy.json under {path}")
        return candidate
    if path.is_file():
        return path
    raise SystemExit(f"Strategy path not found: {raw}")


def _load_strategy(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Failed to read strategy {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise SystemExit(f"Strategy {path} must be a JSON object")
    # Prefer shared normalizer when Playground backend is importable.
    try:
        from backend.service.persona_strategy import normalize_persona_strategy

        return normalize_persona_strategy(raw)
    except Exception:  # noqa: BLE001 — CLI fallback without playground on path
        filters = raw.get("dimensionFilters") or {}
        if not isinstance(filters, dict):
            filters = {}
        normalized_filters: dict[str, list[str]] = {}
        for key, values in filters.items():
            dim = str(key).removeprefix("dimensions.").strip()
            if not dim:
                continue
            if isinstance(values, list):
                cleaned = [str(v).strip() for v in values if str(v).strip()]
            else:
                text = str(values).strip()
                cleaned = [text] if text else []
            if cleaned:
                normalized_filters[dim] = cleaned
        sources = raw.get("sources") or []
        if not isinstance(sources, list):
            sources = []
        stratify = raw.get("stratifyFields") or []
        if not isinstance(stratify, list):
            stratify = []
        per_group = raw.get("sampleSizePerValueGroup")
        sample_size = raw.get("sampleSize")
        return {
            "dimensionFilters": normalized_filters,
            "sources": [str(s).strip() for s in sources if str(s).strip()],
            "stratifyFields": [str(s).strip() for s in stratify if str(s).strip()],
            "sampleSizePerValueGroup": per_group if isinstance(per_group, int) else None,
            "sampleSize": sample_size if isinstance(sample_size, int) else None,
        }


def _stratum_top_up_from_strategy(
    strategy_path: Path,
) -> tuple[list[dict[str, str]], dict[str, object], tuple[str, ...], int]:
    strategy = _load_strategy(strategy_path)
    filters = strategy.get("dimensionFilters") or {}
    if not isinstance(filters, dict) or not filters:
        raise SystemExit(
            f"{strategy_path} has no dimensionFilters; nothing to top up. "
            "Add allow-lists for the cohort this task needs."
        )
    try:
        strata = build_filter_strata(
            {str(k): list(v) for k, v in filters.items() if isinstance(v, list)},
            max_strata=MAX_FILTER_STRATA,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    strata, dropped = filter_feasible_strata(strata)
    if dropped:
        print(
            f"WARNING: dropped {len(dropped)} inconsistent filter cells "
            f"(constrained dimensions clash), e.g. {dropped[0]!r}"
        )
    if not strata:
        raise SystemExit(
            f"{strategy_path}: dimensionFilters produced zero feasible strata "
            "after consistency filtering"
        )

    stratify_fields = [
        str(field).removeprefix("dimensions.").strip()
        for field in (strategy.get("stratifyFields") or [])
        if str(field).strip()
    ]
    filter_keys = set(filters)
    uncovered = [field for field in stratify_fields if field not in filter_keys]
    if uncovered:
        print(
            "WARNING: stratifyFields not listed in dimensionFilters will stay "
            f"randomly filled: {uncovered}. Add them to dimensionFilters if "
            "Playground stratified sampling needs guaranteed cell coverage."
        )

    per_group = strategy.get("sampleSizePerValueGroup")
    if isinstance(per_group, int) and per_group >= 1:
        stratum_min = per_group
    else:
        sample_size = strategy.get("sampleSize")
        if isinstance(sample_size, int) and sample_size >= 1 and len(strata) > 0:
            # Enough for at least one full stratified draw across filter cells.
            stratum_min = max(DEFAULT_STRATEGY_STRATUM_MIN, (sample_size + len(strata) - 1) // len(strata))
        else:
            stratum_min = DEFAULT_STRATEGY_STRATUM_MIN

    sources_raw = strategy.get("sources") or []
    if isinstance(sources_raw, list) and sources_raw:
        sources = tuple(str(s).strip() for s in sources_raw if str(s).strip())
    else:
        sources = PERSONA_SOURCES

    meta = {
        "strategy_path": str(strategy_path.relative_to(REPO_ROOT)),
        "dimensionFilters": filters,
        "stratifyFields": stratify_fields,
        "strata_count": len(strata),
    }
    return strata, meta, sources, stratum_min


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help=(
            f"Base pool size before stratum top-up (default: {DEFAULT_COUNT}; "
            "0 when --strategy is set)"
        ),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: persona/datasets/_generated/...)",
    )
    parser.add_argument("--smoke-id", default="0042")
    parser.add_argument(
        "--task",
        default=None,
        help=(
            "Optional Harbor grounding task path; when set with --stratum-min, "
            "top up personas for each catalog confounder × probe value cell"
        ),
    )
    parser.add_argument(
        "--strategy",
        default=None,
        metavar="PATH",
        help=(
            "Task persona_strategy.json (or task directory). Expands "
            "dimensionFilters into strata and tops up each cell under "
            "persona/datasets/_generated/ (gitignored)."
        ),
    )
    parser.add_argument(
        "--stratum-min",
        type=int,
        default=None,
        help=(
            "Minimum personas per stratum when --task or --strategy is set "
            f"(strategy default: {DEFAULT_STRATEGY_STRATUM_MIN} or derived from sampleSize)"
        ),
    )
    args = parser.parse_args()

    if args.task and args.strategy:
        raise SystemExit("Use either --task (grounding) or --strategy, not both")

    stratum_top_up: list[dict[str, str]] | None = None
    grounding_meta: dict[str, object] | None = None
    strategy_meta: dict[str, object] | None = None
    strategy_path: Path | None = None
    sources: tuple[str, ...] = PERSONA_SOURCES
    stratum_min = args.stratum_min if args.stratum_min is not None else 0

    if args.strategy:
        strategy_path = _resolve_strategy_path(args.strategy)
        stratum_top_up, strategy_meta, sources, derived_min = _stratum_top_up_from_strategy(
            strategy_path
        )
        if args.stratum_min is None:
            stratum_min = derived_min
        elif args.stratum_min < 1:
            raise SystemExit("--stratum-min must be >= 1 when --strategy is set")
        else:
            stratum_min = args.stratum_min
        count = 0 if args.count is None else args.count
    elif args.task:
        if stratum_min < 1:
            raise SystemExit("--task requires --stratum-min >= 1")
        stratum_top_up, grounding_meta = _stratum_top_up_from_task(args.task)
        count = DEFAULT_COUNT if args.count is None else args.count
    else:
        count = DEFAULT_COUNT if args.count is None else args.count

    if count < 0:
        raise SystemExit("--count must be >= 0")

    if args.out is not None:
        out = args.out if args.out.is_absolute() else REPO_ROOT / args.out
    elif strategy_path is not None:
        slug = _slug(strategy_path.parent.name)
        out = DEFAULT_GENERATED_DATASETS_DIR / f"strategy-{slug}"
    else:
        out = _default_out_dir(count if count > 0 else DEFAULT_COUNT)

    personas = generate_persona_pool(
        count=count,
        seed=args.seed,
        smoke_persona_id=args.smoke_id,
        stratum_top_up=stratum_top_up,
        min_per_stratum=stratum_min,
        sources=sources,
        include_smoke=count > 0,
    )

    violations = 0
    for entry in personas:
        errors = validate_dimensions(entry["dimensions"])
        if errors:
            violations += 1
            print(f"VIOLATION persona_{entry['persona_id']}: {errors}")
    if violations:
        raise SystemExit(f"{violations} personas failed consistency checks")

    kind = (
        f"strategy-{_slug(strategy_path.parent.name)}"
        if strategy_path is not None
        else f"bench-dev-{count if count > 0 else len(personas)}"
    )
    manifest = write_persona_dataset(
        out_dir=out,
        personas=personas,
        repo_root=REPO_ROOT,
        kind=kind,
        seed=args.seed,
        smoke_persona_id=args.smoke_id,
    )
    if stratum_top_up and stratum_min > 0:
        if grounding_meta is not None:
            manifest["stratum_top_up"] = {
                "task": args.task,
                "min_per_stratum": stratum_min,
                "strata_count": len(stratum_top_up),
                "grounding": grounding_meta,
            }
        if strategy_meta is not None:
            manifest["stratum_top_up"] = {
                "strategy": strategy_meta,
                "min_per_stratum": stratum_min,
                "strata_count": len(stratum_top_up),
            }
        (out / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    rel_out = out.relative_to(REPO_ROOT) if out.is_relative_to(REPO_ROOT) else out
    print(f"Wrote {manifest['count']} personas to {rel_out}")
    if count > 0:
        print(f"Smoke: persona_{manifest['smoke_persona_id']}.yaml")
    print(
        f"Dimensions: {manifest.get('dimension_count', len(manifest['dimension_ids']))} fields"
    )
    if stratum_top_up and args.task:
        print(
            f"Stratum top-up: {len(stratum_top_up)} cells × min {stratum_min} "
            f"from grounding task {args.task}"
        )
    if stratum_top_up and strategy_path is not None:
        print(
            f"Strategy top-up: {len(stratum_top_up)} filter cells × min {stratum_min} "
            f"from {strategy_path.relative_to(REPO_ROOT)}"
        )
        print("Next:")
        print(
            f'  1. Point persona_strategy.json "pool" at "{rel_out}" '
            "(local only; _generated is gitignored),"
        )
        print("  2. Or pass that pool path in Playground / CLI sampling,")
        print("  3. Then sample — do this before Playground/CLI coverage failures.")


if __name__ == "__main__":
    main()
