"""Generate consistent synthetic persona YAML from dimensions.json."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import yaml

from personabench.persona_consistency import (
    CONSTRAINED_DIMENSIONS,
    load_dev_dimension_ids,
    load_dev_dimension_index_order,
    allowed_education,
    allowed_life_stages,
    allowed_seniorities,
    allowed_years_experience,
    validate_dimensions,
)

DEFAULT_CATALOG_PATH = "persona/schema/dimensions.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_catalog_values(
    catalog_path: str | Path | None = None,
) -> dict[str, list[str]]:
    path = Path(catalog_path or DEFAULT_CATALOG_PATH)
    if not path.is_file():
        path = _repo_root() / str(catalog_path or DEFAULT_CATALOG_PATH)
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for row in payload.get("dimensions") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        dim_id = str(row["id"])
        out[dim_id] = [str(v) for v in row.get("values") or []]
    return out


def _pick(rng, values: list[str]) -> str:
    if not values:
        raise ValueError("empty value list")
    return rng.choice(values)


def _sort_dimensions(
    dimensions: dict[str, str], *, catalog_path: str
) -> dict[str, str]:
    order = load_dev_dimension_index_order(catalog_path=catalog_path)
    return dict(
        sorted(
            dimensions.items(),
            key=lambda item: (order.get(item[0], 99999), item[0]),
        )
    )


def generate_persona_dimensions(
    *,
    rng,
    catalog: dict[str, list[str]],
    dev_dimension_ids: tuple[str, ...],
    catalog_path: str = DEFAULT_CATALOG_PATH,
    age_bracket: str | None = None,
    fixed_dimensions: dict[str, str] | None = None,
) -> dict[str, str]:
    """Sample one internally consistent dimension assignment."""
    fixed = dict(fixed_dimensions or {})
    age = fixed.get("age_bracket") or age_bracket or _pick(rng, catalog["age_bracket"])
    life = fixed.get("life_stage") or _pick(rng, allowed_life_stages(age))
    seniority = fixed.get("seniority") or _pick(
        rng, allowed_seniorities(life_stage=life, age_bracket=age)
    )
    years = fixed.get("years_experience") or _pick(
        rng, allowed_years_experience(age_bracket=age, seniority=seniority)
    )
    education = fixed.get("highest_education") or _pick(
        rng, allowed_education(age_bracket=age, life_stage=life)
    )

    dimensions: dict[str, str] = {
        "age_bracket": age,
        "life_stage": life,
        "seniority": seniority,
        "years_experience": years,
        "highest_education": education,
    }

    for dim_id in dev_dimension_ids:
        if dim_id in CONSTRAINED_DIMENSIONS:
            continue
        if dim_id in fixed:
            dimensions[dim_id] = fixed[dim_id]
            continue
        if dim_id not in catalog:
            raise KeyError(f"Missing dimension {dim_id!r} in catalog")
        dimensions[dim_id] = _pick(rng, catalog[dim_id])

    dimensions = _sort_dimensions(dimensions, catalog_path=catalog_path)

    errors = validate_dimensions(dimensions)
    if errors:
        raise RuntimeError(f"Generated counterfactual persona: {errors}")
    return dimensions


def _stratum_match(dimensions: dict[str, str], stratum: dict[str, str]) -> bool:
    return all(dimensions.get(key) == value for key, value in stratum.items())


def _count_stratum(personas: list[dict[str, Any]], stratum: dict[str, str]) -> int:
    return sum(1 for entry in personas if _stratum_match(entry["dimensions"], stratum))


def top_up_strata(
    personas: list[dict[str, Any]],
    *,
    strata: list[dict[str, str]],
    min_per_stratum: int,
    rng,
    catalog: dict[str, list[str]],
    dev_dimension_ids: tuple[str, ...],
    catalog_path: str,
    max_attempts_per_stratum: int = 500,
) -> list[dict[str, Any]]:
    """Append consistent personas until each stratum meets *min_per_stratum*."""
    if min_per_stratum < 1:
        return personas

    out = list(personas)
    next_index = max((int(entry["persona_id"]) for entry in out), default=0) + 1

    for stratum in strata:
        attempts = 0
        while _count_stratum(out, stratum) < min_per_stratum:
            attempts += 1
            if attempts > max_attempts_per_stratum:
                raise RuntimeError(
                    f"Could not top up stratum {stratum!r} to {min_per_stratum} "
                    f"after {max_attempts_per_stratum} attempts"
                )
            dimensions = generate_persona_dimensions(
                rng=rng,
                catalog=catalog,
                dev_dimension_ids=dev_dimension_ids,
                catalog_path=catalog_path,
                age_bracket=stratum.get("age_bracket"),
                fixed_dimensions=stratum,
            )
            out.append(
                {
                    "persona_id": str(next_index).zfill(4),
                    "version": "2.0",
                    "dimensions": dimensions,
                }
            )
            next_index += 1
    return out


def build_probe_strata(
    *,
    confounders: dict[str, str],
    probe_dimension: str,
    probe_values: list[str],
) -> list[dict[str, str]]:
    """One fixed combo per probe value (confounders + probe)."""
    probe_key = probe_dimension.removeprefix("dimensions.")
    return [{**confounders, probe_key: value} for value in probe_values]


def generate_persona_pool(
    *,
    count: int,
    seed: int = 42,
    catalog_path: str | Path | None = None,
    smoke_persona_id: str = "0042",
    stratum_top_up: list[dict[str, str]] | None = None,
    min_per_stratum: int = 0,
) -> list[dict[str, Any]]:
    """Build *count* personas with roughly even age_bracket coverage."""
    cat_path = str(catalog_path or DEFAULT_CATALOG_PATH)
    catalog = load_catalog_values(cat_path)
    dev_ids = load_dev_dimension_ids(catalog_path=cat_path)
    rng = random.Random(seed)
    ages = catalog["age_bracket"]
    per_age = count // len(ages)
    extra = count % len(ages)

    personas: list[dict[str, Any]] = []
    persona_index = 1
    for age_index, age in enumerate(ages):
        n = per_age + (1 if age_index < extra else 0)
        for _ in range(n):
            persona_id = str(persona_index).zfill(4)
            dimensions = generate_persona_dimensions(
                rng=rng,
                catalog=catalog,
                dev_dimension_ids=dev_ids,
                catalog_path=cat_path,
                age_bracket=age,
            )
            personas.append(
                {
                    "persona_id": persona_id,
                    "version": "2.0",
                    "dimensions": dimensions,
                }
            )
            persona_index += 1

    if stratum_top_up and min_per_stratum > 0:
        personas = top_up_strata(
            personas,
            strata=stratum_top_up,
            min_per_stratum=min_per_stratum,
            rng=rng,
            catalog=catalog,
            dev_dimension_ids=dev_ids,
            catalog_path=cat_path,
        )

    smoke_rng = random.Random(seed + 42)
    smoke_dims = generate_persona_dimensions(
        rng=smoke_rng,
        catalog=catalog,
        dev_dimension_ids=dev_ids,
        catalog_path=cat_path,
    )
    smoke_entry = {
        "persona_id": smoke_persona_id,
        "version": "2.0",
        "dimensions": smoke_dims,
    }
    for index, entry in enumerate(personas):
        if entry["persona_id"] == smoke_persona_id:
            personas[index] = smoke_entry
            return personas
    personas[int(smoke_persona_id) - 1] = smoke_entry
    return personas


def write_persona_dataset(
    *,
    out_dir: Path,
    personas: list[dict[str, Any]],
    repo_root: Path,
    kind: str,
    seed: int,
    smoke_persona_id: str,
    catalog_path: str = DEFAULT_CATALOG_PATH,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dev_ids = load_dev_dimension_ids(catalog_path=catalog_path)
    manifest_personas: list[dict[str, Any]] = []
    for entry in personas:
        persona_id = entry["persona_id"]
        rel_path = f"{out_dir.relative_to(repo_root)}/persona_{persona_id}.yaml"
        payload = {
            "persona_id": persona_id,
            "version": entry.get("version", "2.0"),
            "dimensions": entry["dimensions"],
        }
        (repo_root / rel_path).write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )
        manifest_personas.append(
            {
                "persona_id": persona_id,
                "path": rel_path,
                "dimensions": entry["dimensions"],
            }
        )

    manifest = {
        "kind": kind,
        "count": len(manifest_personas),
        "seed": seed,
        "schema_version": "2.0",
        "smoke_persona_id": smoke_persona_id,
        "dimension_ids": list(dev_ids),
        "dimension_count": len(dev_ids),
        "personas": manifest_personas,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
