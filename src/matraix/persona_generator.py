"""Generate consistent synthetic persona YAML from dimensions.json."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import yaml

from matraix.persona_consistency import (
    CONSTRAINED_DIMENSIONS,
    load_dev_dimension_ids,
    load_dev_dimension_index_order,
    allowed_age_brackets_for_life_stage,
    allowed_education,
    allowed_life_stages,
    allowed_seniorities,
    allowed_years_experience,
    validate_dimensions,
)

DEFAULT_CATALOG_PATH = "persona/schema/dimensions.json"
DEFAULT_PERSONA_VERSION = "1.0"
PERSONA_SOURCES = ("Nemotron", "OASIS", "PersonaHub", "PRIMEX")


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
    if fixed.get("age_bracket"):
        age = fixed["age_bracket"]
    elif age_bracket:
        age = age_bracket
    elif fixed.get("life_stage"):
        # Fixed life_stage without age: pick a compatible bracket first so
        # seniority / education lists are never empty (e.g. Student + 65+).
        age = _pick(rng, allowed_age_brackets_for_life_stage(fixed["life_stage"]))
    else:
        age = _pick(rng, catalog["age_bracket"])

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


def _pick_source(rng: random.Random, sources: tuple[str, ...]) -> str:
    if not sources:
        raise ValueError("sources must not be empty")
    return rng.choice(sources)


def _persona_entry(
    *,
    persona_id: str,
    dimensions: dict[str, str],
    version: str,
    source_rng: random.Random,
    sources: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "persona_id": persona_id,
        "version": version,
        "source": _pick_source(source_rng, sources),
        "dimensions": dimensions,
    }


def top_up_strata(
    personas: list[dict[str, Any]],
    *,
    strata: list[dict[str, str]],
    min_per_stratum: int,
    rng,
    catalog: dict[str, list[str]],
    dev_dimension_ids: tuple[str, ...],
    catalog_path: str,
    persona_version: str = DEFAULT_PERSONA_VERSION,
    sources: tuple[str, ...] = PERSONA_SOURCES,
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
                _persona_entry(
                    persona_id=str(next_index).zfill(4),
                    dimensions=dimensions,
                    version=persona_version,
                    source_rng=rng,
                    sources=sources,
                )
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


def build_filter_strata(
    dimension_filters: dict[str, list[str]],
    *,
    max_strata: int = 2048,
) -> list[dict[str, str]]:
    """Cartesian product of multi-value ``dimensionFilters`` → fixed strata cells.

    Each cell is a ``dict[str, str]`` suitable for ``top_up_strata`` /
    ``generate_persona_dimensions(fixed_dimensions=…)``. Empty filters yield
    no strata (caller should require filters when generating from a strategy).

    Callers should pass the result through ``filter_feasible_strata`` when
    filters may combine constrained dimensions incompatibly (e.g. age × life_stage).
    """
    if not dimension_filters:
        return []

    dims = sorted(
        (
            (
                str(dim).removeprefix("dimensions.").strip(),
                [str(v).strip() for v in values if str(v).strip()],
            )
            for dim, values in dimension_filters.items()
        ),
        key=lambda item: item[0],
    )
    dims = [(dim, values) for dim, values in dims if dim and values]
    if not dims:
        return []

    strata: list[dict[str, str]] = [{}]
    for dim, values in dims:
        next_strata: list[dict[str, str]] = []
        for cell in strata:
            for value in values:
                next_strata.append({**cell, dim: value})
                if len(next_strata) > max_strata:
                    raise ValueError(
                        f"dimensionFilters expand to more than {max_strata} strata; "
                        "narrow filters or raise max_strata"
                    )
        strata = next_strata
    return strata


def filter_feasible_strata(
    strata: list[dict[str, str]],
    *,
    catalog_path: str | Path | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Keep strata that can produce a consistency-valid persona.

    Returns ``(feasible, dropped)``. Dropped cells are usually incompatible
    constrained-dimension combinations from a cartesian filter expand.
    """
    cat_path = str(catalog_path or DEFAULT_CATALOG_PATH)
    catalog = load_catalog_values(cat_path)
    dev_ids = load_dev_dimension_ids(catalog_path=cat_path)
    rng = random.Random(0)
    feasible: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for stratum in strata:
        try:
            generate_persona_dimensions(
                rng=rng,
                catalog=catalog,
                dev_dimension_ids=dev_ids,
                catalog_path=cat_path,
                age_bracket=stratum.get("age_bracket"),
                fixed_dimensions=stratum,
            )
        except (RuntimeError, ValueError):
            dropped.append(stratum)
            continue
        feasible.append(stratum)
    return feasible, dropped


def generate_persona_pool(
    *,
    count: int,
    seed: int = 42,
    catalog_path: str | Path | None = None,
    smoke_persona_id: str = "0042",
    stratum_top_up: list[dict[str, str]] | None = None,
    min_per_stratum: int = 0,
    persona_version: str = DEFAULT_PERSONA_VERSION,
    sources: tuple[str, ...] = PERSONA_SOURCES,
    include_smoke: bool = True,
) -> list[dict[str, Any]]:
    """Build *count* personas with roughly even age_bracket coverage.

    ``count`` may be ``0`` when the caller only wants ``stratum_top_up`` cells
    (e.g. task ``persona_strategy.json`` coverage pools).
    """
    if count < 0:
        raise ValueError("count must be >= 0")
    cat_path = str(catalog_path or DEFAULT_CATALOG_PATH)
    catalog = load_catalog_values(cat_path)
    dev_ids = load_dev_dimension_ids(catalog_path=cat_path)
    rng = random.Random(seed)
    ages = catalog["age_bracket"]
    per_age = count // len(ages) if ages else 0
    extra = count % len(ages) if ages else 0

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
                _persona_entry(
                    persona_id=persona_id,
                    dimensions=dimensions,
                    version=persona_version,
                    source_rng=rng,
                    sources=sources,
                )
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
            persona_version=persona_version,
            sources=sources,
        )

    source_rng = random.Random(seed + 7)
    for entry in personas:
        entry["source"] = _pick_source(source_rng, sources)

    if not include_smoke:
        return personas

    smoke_rng = random.Random(seed + 42)
    smoke_dims = generate_persona_dimensions(
        rng=smoke_rng,
        catalog=catalog,
        dev_dimension_ids=dev_ids,
        catalog_path=cat_path,
    )
    smoke_entry = _persona_entry(
        persona_id=smoke_persona_id,
        dimensions=smoke_dims,
        version=persona_version,
        source_rng=source_rng,
        sources=sources,
    )
    for index, entry in enumerate(personas):
        if entry["persona_id"] == smoke_persona_id:
            personas[index] = smoke_entry
            return personas
    if not personas:
        personas.append(smoke_entry)
        return personas
    smoke_index = int(smoke_persona_id) - 1
    if 0 <= smoke_index < len(personas):
        personas[smoke_index] = smoke_entry
    else:
        personas.append(smoke_entry)
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
    persona_version: str = DEFAULT_PERSONA_VERSION,
    manifest_name: str | None = None,
    manifest_description: str | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dev_ids = load_dev_dimension_ids(catalog_path=catalog_path)
    manifest_personas: list[dict[str, Any]] = []
    for entry in personas:
        persona_id = entry["persona_id"]
        rel_path = f"{out_dir.relative_to(repo_root)}/persona_{persona_id}.yaml"
        payload = {
            "persona_id": persona_id,
            "version": entry.get("version", persona_version),
            "source": entry.get("source"),
            "dimensions": entry["dimensions"],
        }
        (repo_root / rel_path).write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )
        manifest_personas.append(
            {
                "persona_id": persona_id,
                "path": rel_path,
                "source": entry.get("source"),
                "dimensions": entry["dimensions"],
            }
        )

    source_counts: dict[str, int] = {}
    for entry in manifest_personas:
        source = entry.get("source")
        if source:
            source_counts[source] = source_counts.get(source, 0) + 1

    manifest: dict[str, Any] = {
        "kind": kind,
        "count": len(manifest_personas),
        "seed": seed,
        "schema_version": persona_version,
        "smoke_persona_id": smoke_persona_id,
        "dimension_ids": list(dev_ids),
        "dimension_count": len(dev_ids),
        "dimension_categories": "persona/schema/dimension_categories.json",
        "persona_sources": list(PERSONA_SOURCES),
        "source_counts": source_counts,
        "personas": manifest_personas,
    }
    if manifest_name:
        manifest["name"] = manifest_name
    if manifest_description:
        manifest["description"] = manifest_description
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
