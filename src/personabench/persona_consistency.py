"""Cross-dimension consistency rules for synthetic persona generation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_CATALOG_PATH = "persona/schema/dimensions.json"

# Core catalog block (index 1-47): demographics, career, values, interaction state, etc.
# Excludes fam_* / att_* floods that start at index 48+.
CORE_DEV_MAX_INDEX = 47

# life_stage must be plausible for age_bracket (no counterfactual life arcs).
LIFE_STAGE_BY_AGE: dict[str, list[str]] = {
    "13-17": ["Student"],
    "18-24": ["Student", "Early career"],
    "25-34": ["Early career", "Parent of young kids", "Career change"],
    "35-44": ["Mid-life", "Parent of young kids", "Early career", "Career change"],
    "45-54": ["Mid-life", "Parent of young kids", "Empty nester", "Career change"],
    "55-64": ["Mid-life", "Empty nester", "Career change", "Retirement"],
    "65+": ["Retirement", "Empty nester"],
}

SENIORITY_BY_LIFE_STAGE: dict[str, list[str]] = {
    "Student": ["Student / intern"],
    "Early career": ["Student / intern", "Entry", "Mid"],
    "Parent of young kids": ["Entry", "Mid", "Senior", "Manager"],
    "Mid-life": ["Mid", "Senior", "Lead / Principal", "Manager", "Director"],
    "Career change": ["Entry", "Mid", "Senior"],
    "Empty nester": ["Senior", "Lead / Principal", "Manager", "Director", "VP"],
    "Retirement": ["Retired"],
}

EDUCATION_BY_AGE: dict[str, list[str]] = {
    "13-17": ["No formal", "Primary", "Secondary"],
    "18-24": ["Secondary", "Vocational / cert", "Bachelor's"],
    "25-34": ["Secondary", "Vocational / cert", "Bachelor's", "Master's"],
    "35-44": ["Vocational / cert", "Bachelor's", "Master's", "Doctorate"],
    "45-54": ["Bachelor's", "Master's", "Doctorate", "Vocational / cert"],
    "55-64": ["Secondary", "Vocational / cert", "Bachelor's", "Master's", "Doctorate"],
    "65+": ["Secondary", "Vocational / cert", "Bachelor's", "Master's", "Doctorate"],
}

CONSTRAINED_DIMENSIONS = frozenset(
    {
        "age_bracket",
        "life_stage",
        "seniority",
        "years_experience",
        "highest_education",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=4)
def _load_catalog_rows(catalog_path: str) -> list[dict[str, Any]]:
    path = Path(catalog_path)
    if not path.is_file():
        path = _repo_root() / catalog_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = [
        r
        for r in payload.get("dimensions") or []
        if isinstance(r, dict) and r.get("id")
    ]
    return sorted(rows, key=lambda r: (int(r.get("index") or 99999), str(r["id"])))


def load_dev_dimension_ids(
    *, catalog_path: str = DEFAULT_CATALOG_PATH
) -> tuple[str, ...]:
    """Dev persona fields: core block (index ≤ 47) + all ``cog_*`` communication dims."""
    ids: list[str] = []
    for row in _load_catalog_rows(catalog_path):
        dim_id = str(row["id"])
        index = int(row.get("index") or 99999)
        if index <= CORE_DEV_MAX_INDEX or dim_id.startswith("cog_"):
            ids.append(dim_id)
    return tuple(ids)


@lru_cache(maxsize=4)
def load_dev_dimension_index_order(
    *, catalog_path: str = DEFAULT_CATALOG_PATH
) -> dict[str, int]:
    dev_ids = set(load_dev_dimension_ids(catalog_path=catalog_path))
    order: dict[str, int] = {}
    for row in _load_catalog_rows(catalog_path):
        dim_id = str(row["id"])
        if dim_id in dev_ids:
            order[dim_id] = int(row.get("index") or 99999)
    return order


def allowed_years_experience(*, age_bracket: str, seniority: str) -> list[str]:
    if seniority == "Retired":
        return ["11-20", "20+"]
    if seniority in ("Student / intern",):
        return ["0-2"]
    if seniority == "Entry":
        return ["0-2", "3-5"]
    if age_bracket in ("13-17", "18-24"):
        return ["0-2", "3-5"]
    if age_bracket == "25-34":
        return ["0-2", "3-5", "6-10"]
    if age_bracket in ("35-44", "45-54"):
        return ["3-5", "6-10", "11-20"]
    return ["6-10", "11-20", "20+"]


def allowed_life_stages(age_bracket: str) -> list[str]:
    return list(LIFE_STAGE_BY_AGE.get(age_bracket, []))


def allowed_seniorities(*, life_stage: str, age_bracket: str) -> list[str]:
    options = list(SENIORITY_BY_LIFE_STAGE.get(life_stage, []))
    if age_bracket in ("13-17", "18-24"):
        return [s for s in options if s in ("Student / intern", "Entry", "Mid")]
    if age_bracket == "65+":
        return [
            s
            for s in options
            if s in ("Retired", "Senior", "Lead / Principal", "Director", "VP")
        ]
    return options


def allowed_education(*, age_bracket: str, life_stage: str) -> list[str]:
    base = list(EDUCATION_BY_AGE.get(age_bracket, []))
    if life_stage == "Student" and age_bracket in ("13-17", "18-24"):
        return [
            e
            for e in base
            if e in ("Secondary", "Vocational / cert", "Bachelor's", "Primary")
        ]
    return base


def validate_dimensions(dimensions: dict[str, Any]) -> list[str]:
    """Return human-readable counterfactual violations (empty if consistent)."""
    errors: list[str] = []
    age = dimensions.get("age_bracket")
    life = dimensions.get("life_stage")
    seniority = dimensions.get("seniority")
    years = dimensions.get("years_experience")
    education = dimensions.get("highest_education")

    if isinstance(age, str) and isinstance(life, str):
        allowed = allowed_life_stages(age)
        if life not in allowed:
            errors.append(f"life_stage={life!r} incompatible with age_bracket={age!r}")

    if isinstance(life, str) and isinstance(seniority, str):
        allowed = allowed_seniorities(life_stage=life, age_bracket=str(age or ""))
        if seniority not in allowed:
            errors.append(
                f"seniority={seniority!r} incompatible with life_stage={life!r} "
                f"and age_bracket={age!r}"
            )

    if isinstance(age, str) and isinstance(seniority, str) and isinstance(years, str):
        allowed = allowed_years_experience(age_bracket=age, seniority=seniority)
        if years not in allowed:
            errors.append(
                f"years_experience={years!r} incompatible with age_bracket={age!r} "
                f"and seniority={seniority!r}"
            )

    if isinstance(age, str) and isinstance(life, str) and isinstance(education, str):
        allowed = allowed_education(age_bracket=age, life_stage=life)
        if education not in allowed:
            errors.append(
                f"highest_education={education!r} incompatible with age_bracket={age!r} "
                f"and life_stage={life!r}"
            )

    return errors
