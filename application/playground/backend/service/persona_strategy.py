"""Load and validate per-task ``persona_strategy.json`` (Playground sampling defaults)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PERSONA_STRATEGY_FILENAME = "persona_strategy.json"
PERSONA_SAMPLING_MODES = frozenset({"single", "random", "stratified"})

# Minimal stub when scaffolding a new task — replace filters with the product cohort.
DEFAULT_PERSONA_STRATEGY: dict[str, Any] = {
    "schemaVersion": "1.0",
    "sources": [],
    "defaultMode": "random",
    "dimensionFilters": {},
}


def persona_strategy_path(task_dir: Path) -> Path:
    return task_dir / PERSONA_STRATEGY_FILENAME


def load_persona_strategy(task_dir: Path) -> dict[str, Any] | None:
    """Return a normalized strategy dict, or ``None`` when the file is absent/invalid.

    Application tasks under ``application/tasks/`` are expected to ship the file
    (CI enforces presence). Loaders still tolerate missing files for ad-hoc paths.
    """
    path = persona_strategy_path(task_dir)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return normalize_persona_strategy(raw)


def normalize_persona_strategy(raw: dict[str, Any]) -> dict[str, Any]:
    schema_version = str(raw.get("schemaVersion") or "1.0").strip() or "1.0"
    pool = str(raw.get("pool") or "").strip() or None
    default_mode = str(raw.get("defaultMode") or "").strip().lower()
    if default_mode not in PERSONA_SAMPLING_MODES:
        default_mode = None

    sources = _as_str_list(raw.get("sources"))
    dimension_filters = _as_dimension_filters(raw.get("dimensionFilters"))
    stratify_fields = _as_str_list(raw.get("stratifyFields"))

    sample_size = raw.get("sampleSize")
    if isinstance(sample_size, bool) or not isinstance(sample_size, (int, float)):
        sample_size = None
    else:
        sample_size = int(sample_size)
        if sample_size < 1:
            sample_size = None

    seed = raw.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, (int, float)):
        seed = None
    else:
        seed = int(seed)

    cohort_id = str(raw.get("cohortId") or "").strip() or None
    sample_size_per_value_group = raw.get("sampleSizePerValueGroup")
    if isinstance(sample_size_per_value_group, bool) or not isinstance(
        sample_size_per_value_group, (int, float)
    ):
        sample_size_per_value_group = None
    else:
        sample_size_per_value_group = int(sample_size_per_value_group)
        if sample_size_per_value_group < 1:
            sample_size_per_value_group = None

    payload: dict[str, Any] = {
        "schemaVersion": schema_version,
        "sources": sources,
        "dimensionFilters": dimension_filters,
    }
    if pool:
        payload["pool"] = pool
    if default_mode:
        payload["defaultMode"] = default_mode
    if stratify_fields:
        payload["stratifyFields"] = stratify_fields
    if sample_size is not None:
        payload["sampleSize"] = sample_size
    if seed is not None:
        payload["seed"] = seed
    if cohort_id:
        payload["cohortId"] = cohort_id
    if sample_size_per_value_group is not None:
        payload["sampleSizePerValueGroup"] = sample_size_per_value_group
    return payload


def validate_persona_strategy_file(
    task_dir: Path,
    *,
    require_cohort: bool = True,
) -> list[str]:
    """Return human-readable errors for a task's ``persona_strategy.json``.

    The file is **required** for application tasks. Field values may use defaults
    (see ``DEFAULT_PERSONA_STRATEGY``), but tasks are expected to declare a
    target cohort via ``dimensionFilters`` and/or ``cohortId`` when
    ``require_cohort`` is true.
    """
    errors: list[str] = []
    path = persona_strategy_path(task_dir)
    rel = str(path)
    if not path.is_file():
        errors.append(
            f"{rel}: missing required persona_strategy.json "
            "(declare Playground sampling defaults / target cohort)"
        )
        return errors

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        errors.append(f"{rel}: cannot read file ({exc})")
        return errors
    except json.JSONDecodeError as exc:
        errors.append(f"{rel}: invalid JSON ({exc})")
        return errors

    if not isinstance(raw, dict):
        errors.append(f"{rel}: root value must be a JSON object")
        return errors

    if "schemaVersion" not in raw or not str(raw.get("schemaVersion") or "").strip():
        errors.append(f'{rel}: schemaVersion is required (use "1.0")')

    normalized = normalize_persona_strategy(raw)
    mode = normalized.get("defaultMode")
    if mode is None:
        errors.append(
            f"{rel}: defaultMode is required "
            f"(one of: {', '.join(sorted(PERSONA_SAMPLING_MODES))})"
        )

    if require_cohort:
        filters = normalized.get("dimensionFilters") or {}
        cohort_id = normalized.get("cohortId")
        has_filters = isinstance(filters, dict) and any(
            isinstance(vals, list) and len(vals) > 0 for vals in filters.values()
        )
        if not has_filters and not cohort_id:
            errors.append(
                f"{rel}: declare a target cohort via non-empty dimensionFilters "
                "and/or cohortId (most tasks filter to a product audience)"
            )

    if mode == "stratified":
        stratify = normalized.get("stratifyFields") or []
        if not stratify:
            errors.append(
                f'{rel}: defaultMode "stratified" requires stratifyFields'
            )
        filters = normalized.get("dimensionFilters") or {}
        sample_size = normalized.get("sampleSize")
        per_cell = normalized.get("sampleSizePerValueGroup")
        if sample_size is not None and per_cell is not None:
            errors.append(
                f"{rel}: stratified sampling uses exactly one quota field — "
                "sampleSize (total N) XOR sampleSizePerValueGroup (N per cell); "
                "do not set both"
            )
        elif sample_size is None and per_cell is None:
            errors.append(
                f"{rel}: stratified mode requires exactly one of sampleSize "
                "(total N) or sampleSizePerValueGroup (N per cell)"
            )
        missing_axes = [
            field
            for field in stratify
            if field not in filters or not filters.get(field)
        ]
        if missing_axes:
            errors.append(
                f"{rel}: every stratifyFields entry must also appear in "
                f"dimensionFilters with allowed values (missing: {', '.join(missing_axes)}); "
                "otherwise Playground cannot guarantee cell coverage or synthesize gaps"
            )
        elif sample_size is not None and per_cell is None:
            # sampleSize-only stratified: total N must cover ≥1 persona per cell.
            try:
                from matraix.persona_generator import (
                    build_filter_strata,
                    filter_feasible_strata,
                )

                stratify_filters = {field: list(filters[field]) for field in stratify}
                strata = build_filter_strata(stratify_filters, max_strata=200)
                feasible, _dropped = filter_feasible_strata(strata)
                min_cells = len(feasible)
                if min_cells and int(sample_size) < min_cells:
                    errors.append(
                        f"{rel}: sampleSize={sample_size} is below the stratified "
                        f"cell count={min_cells} (need ≥1 per combination of "
                        f"{', '.join(stratify)}). Raise sampleSize, or switch to "
                        "sampleSizePerValueGroup instead (and omit sampleSize)."
                    )
            except Exception:  # noqa: BLE001 — soft: skip when schema/generator unavailable
                pass

    return errors


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_dimension_filters(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, raw in value.items():
        dim = str(key).strip()
        if not dim:
            continue
        if isinstance(raw, list):
            values = [str(item).strip() for item in raw if str(item).strip()]
        elif raw is None:
            values = []
        else:
            text = str(raw).strip()
            values = [text] if text else []
        if values:
            out[dim] = values
    return out
