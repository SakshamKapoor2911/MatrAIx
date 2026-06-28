"""Synthesize schema-grounded persona dimension vectors."""

from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CATALOG_PATH = "persona/schema/dimensions.json"
DEFAULT_CONSTRAINTS_PATH = "persona/schema/dimension_constraints_readable.txt"
SYNTHESIS_MODE = "schema_grounded_random_sample_with_pairwise_constraints"
DIMENSION_SET = "all-catalog-dimensions"

_CONSTRAINT_RE = re.compile(
    r"(?P<dim1>[A-Za-z0-9_]+)='(?P<val1>.*?)'\s+\+\s+"
    r"(?P<dim2>[A-Za-z0-9_]+)='(?P<val2>.*?)'\s+INVALID"
)
_DASH_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)


@dataclass(frozen=True)
class IncompatibilityRule:
    dim1: str
    val1: str
    dim2: str
    val2: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_repo_path(path: str | Path, *, root: Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_file():
        return candidate
    return (root or repo_root()) / candidate


def display_path(path: str | Path, *, root: Path | None = None) -> str:
    base = root or repo_root()
    resolved = Path(path)
    if not resolved.is_absolute():
        return resolved.as_posix()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return str(resolved)


def load_dimension_catalog(
    catalog_path: str | Path = DEFAULT_CATALOG_PATH,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    path = resolve_repo_path(catalog_path, root=root)
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalog_values(
    catalog_path: str | Path = DEFAULT_CATALOG_PATH,
    *,
    root: Path | None = None,
) -> dict[str, list[str]]:
    payload = load_dimension_catalog(catalog_path, root=root)
    values: dict[str, list[str]] = {}
    for row in payload.get("dimensions") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        values[str(row["id"])] = [str(value) for value in row.get("values") or []]
    return values


def load_synthesis_dimension_ids(
    catalog_path: str | Path = DEFAULT_CATALOG_PATH,
    *,
    root: Path | None = None,
) -> tuple[str, ...]:
    """Emit every catalog dimension, ordered by the catalog index."""
    payload = load_dimension_catalog(catalog_path, root=root)
    rows = []
    for position, row in enumerate(payload.get("dimensions") or []):
        if isinstance(row, dict) and row.get("id"):
            rows.append((int(row.get("index") or position + 1), position, str(row["id"])))
    return tuple(dim_id for _, _, dim_id in sorted(rows))


def parse_readable_constraints(text: str) -> list[IncompatibilityRule]:
    rules: list[IncompatibilityRule] = []
    for line in text.splitlines():
        match = _CONSTRAINT_RE.search(line)
        if not match:
            continue
        rules.append(
            IncompatibilityRule(
                dim1=match.group("dim1"),
                val1=match.group("val1"),
                dim2=match.group("dim2"),
                val2=match.group("val2"),
            )
        )
    return rules


def load_readable_constraints(
    constraints_path: str | Path = DEFAULT_CONSTRAINTS_PATH,
    *,
    root: Path | None = None,
) -> list[IncompatibilityRule]:
    path = resolve_repo_path(constraints_path, root=root)
    return parse_readable_constraints(path.read_text(encoding="utf-8"))


def validate_schema_values(
    dimensions: dict[str, Any],
    catalog_values: dict[str, list[str]],
) -> list[str]:
    errors: list[str] = []
    for dim_id, raw_value in dimensions.items():
        if dim_id not in catalog_values:
            errors.append(f"{dim_id!r} is not in the dimension catalog")
            continue
        value = str(raw_value)
        if value not in catalog_values[dim_id]:
            errors.append(f"{dim_id!r} has non-catalog value {value!r}")
    return errors


def _constraint_value_key(value: Any) -> str:
    return str(value).translate(_DASH_TRANSLATION)


def violated_constraints(
    dimensions: dict[str, Any],
    rules: list[IncompatibilityRule],
) -> list[IncompatibilityRule]:
    violations: list[IncompatibilityRule] = []
    for rule in rules:
        if (
            _constraint_value_key(dimensions.get(rule.dim1)) == _constraint_value_key(rule.val1)
            and _constraint_value_key(dimensions.get(rule.dim2))
            == _constraint_value_key(rule.val2)
        ):
            violations.append(rule)
    return violations


def summarize_constraint_compatibility(
    *,
    rules: list[IncompatibilityRule],
    catalog_values: dict[str, list[str]],
    generated_dimension_ids: tuple[str, ...],
) -> dict[str, Any]:
    generated = set(generated_dimension_ids)
    catalog_valid = []
    not_in_catalog = []
    applicable = []
    for rule in rules:
        dim1_values = catalog_values.get(rule.dim1)
        dim2_values = catalog_values.get(rule.dim2)
        is_catalog_valid = (
            dim1_values is not None
            and _constraint_value_key(rule.val1)
            in {_constraint_value_key(value) for value in dim1_values}
            and dim2_values is not None
            and _constraint_value_key(rule.val2)
            in {_constraint_value_key(value) for value in dim2_values}
        )
        if is_catalog_valid:
            catalog_valid.append(rule)
        else:
            not_in_catalog.append(rule)
        if is_catalog_valid and rule.dim1 in generated and rule.dim2 in generated:
            applicable.append(rule)

    return {
        "source_rule_count": len(rules),
        "catalog_valid_rule_count": len(catalog_valid),
        "not_in_current_catalog_count": len(not_in_catalog),
        "applicable_to_generated_dimensions_count": len(applicable),
        "not_in_current_catalog_examples": [
            rule.to_dict() for rule in not_in_catalog[:10]
        ],
    }


def _sample_dimensions(
    *,
    rng: random.Random,
    catalog_values: dict[str, list[str]],
    dimension_ids: tuple[str, ...],
) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    for dim_id in dimension_ids:
        values = catalog_values.get(dim_id)
        if not values:
            raise KeyError(f"Missing catalog values for dimension {dim_id!r}")
        dimensions[dim_id] = rng.choice(values)
    return dimensions


def synthesize_persona_vectors(
    *,
    count: int,
    seed: int,
    catalog_path: str | Path = DEFAULT_CATALOG_PATH,
    constraints_path: str | Path = DEFAULT_CONSTRAINTS_PATH,
    root: Path | None = None,
    max_attempts_per_persona: int = 1000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if count < 1:
        raise ValueError("count must be >= 1")
    base = root or repo_root()
    catalog = load_dimension_catalog(catalog_path, root=base)
    catalog_values = load_catalog_values(catalog_path, root=base)
    dimension_ids = load_synthesis_dimension_ids(catalog_path, root=base)
    rules = load_readable_constraints(constraints_path, root=base)
    rng = random.Random(seed)

    personas: list[dict[str, Any]] = []
    rejected_constraints = 0
    rejected_schema = 0
    attempts = 0

    for index in range(1, count + 1):
        for _ in range(max_attempts_per_persona):
            attempts += 1
            dimensions = _sample_dimensions(
                rng=rng,
                catalog_values=catalog_values,
                dimension_ids=dimension_ids,
            )
            schema_errors = validate_schema_values(dimensions, catalog_values)
            if schema_errors:
                rejected_schema += 1
                continue
            violations = violated_constraints(dimensions, rules)
            if violations:
                rejected_constraints += 1
                continue
            personas.append(
                {
                    "persona_id": f"synth_{index:06d}",
                    "version": str(catalog.get("schemaVersion", "2.0")),
                    "dimensions": dimensions,
                }
            )
            break
        else:
            raise RuntimeError(
                f"Could not synthesize persona {index} after "
                f"{max_attempts_per_persona} attempts"
            )

    validation = {
        "schema": {
            "status": "passed",
            "checked_personas": len(personas),
            "rejected_attempts": rejected_schema,
        },
        "constraints": {
            "status": "passed",
            "checked_personas": len(personas),
            "rejected_attempts": rejected_constraints,
            **summarize_constraint_compatibility(
                rules=rules,
                catalog_values=catalog_values,
                generated_dimension_ids=dimension_ids,
            ),
        },
        "attempts": attempts,
    }
    return personas, validation


def write_synthetic_persona_dataset(
    *,
    out_dir: Path,
    personas: list[dict[str, Any]],
    manifest: dict[str, Any],
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or repo_root()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_personas = []
    for entry in personas:
        persona_id = str(entry["persona_id"])
        filename = f"{persona_id}.yaml"
        path = out_dir / filename
        payload = {
            "persona_id": persona_id,
            "version": entry["version"],
            "dimensions": entry["dimensions"],
        }
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        manifest_personas.append(
            {
                "persona_id": persona_id,
                "path": display_path(path, root=base),
                "dimensions": entry["dimensions"],
            }
        )

    manifest = {**manifest, "personas": manifest_personas}
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def synthesize_persona_dataset(
    *,
    out_dir: Path,
    count: int,
    seed: int = 42,
    catalog_path: str | Path = DEFAULT_CATALOG_PATH,
    constraints_path: str | Path = DEFAULT_CONSTRAINTS_PATH,
    root: Path | None = None,
    max_attempts_per_persona: int = 1000,
) -> dict[str, Any]:
    base = root or repo_root()
    personas, validation = synthesize_persona_vectors(
        count=count,
        seed=seed,
        catalog_path=catalog_path,
        constraints_path=constraints_path,
        root=base,
        max_attempts_per_persona=max_attempts_per_persona,
    )
    catalog = load_dimension_catalog(catalog_path, root=base)
    dimension_ids = load_synthesis_dimension_ids(catalog_path, root=base)
    manifest = {
        "kind": "synthetic-human-persona-vectors",
        "mode": SYNTHESIS_MODE,
        "count": len(personas),
        "seed": seed,
        "schema_version": str(catalog.get("schemaVersion", "2.0")),
        "dimension_set": DIMENSION_SET,
        "dimension_ids": list(dimension_ids),
        "dimension_count": len(dimension_ids),
        "schema_grounding": {
            "catalog_path": display_path(
                resolve_repo_path(catalog_path, root=base), root=base
            ),
            "target_dimensions": catalog.get("targetDimensions"),
            "rule": (
                "Every emitted persona dimension id must exist in dimensions.json, "
                "and every emitted value must be one of that dimension's catalog "
                "values."
            ),
            "validation": validation["schema"],
        },
        "constraint_validation": {
            "constraints_path": display_path(
                resolve_repo_path(constraints_path, root=base), root=base
            ),
            "format": "readable incompatible dimension-value pairs",
            "rule": (
                "Reject a sampled persona when it contains both sides of any "
                "INVALID pair in the constraints file."
            ),
            "validation": validation["constraints"],
        },
        "sampling": {
            "method": "seeded uniform random sampling over all catalog dimensions",
            "attempts": validation["attempts"],
        },
    }
    return write_synthetic_persona_dataset(
        out_dir=out_dir,
        personas=personas,
        manifest=manifest,
        root=base,
    )
