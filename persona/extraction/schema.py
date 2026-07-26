"""Load and index the PersonaWorld dimension taxonomy.

The taxonomy lives in ``persona/schema/dimensions.json``: a flat list of
dimensions, each with an ``id``, human ``label``, ``values`` (the allowed
buckets), a ``category`` (UI grouping only), a ``phrase`` template, and a
``defaultValue``. A persona is one value per dimension; the treiver's job is to
recover a subset of those assignments from free text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

# persona/treiver/schema.py -> persona/schema/dimensions.json
_DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "dimensions.json"


@dataclass(frozen=True)
class Dimension:
    """One dimension of the persona space (e.g. ``age_bracket``)."""

    id: str
    label: str
    category: str
    description: str
    values: tuple[str, ...]
    phrase: str
    default_value: str | None

    @classmethod
    def from_json(cls, obj: dict) -> "Dimension":
        return cls(
            id=obj["id"],
            label=obj.get("label", obj["id"]),
            category=obj.get("category", ""),
            description=obj.get("description", ""),
            values=tuple(obj.get("values", [])),
            phrase=obj.get("phrase", "{value}"),
            default_value=obj.get("defaultValue"),
        )


@dataclass
class DimensionSchema:
    """The full set of dimensions, indexed by id for O(1) lookup."""

    dimensions: list[Dimension]
    _by_id: dict[str, Dimension] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._by_id = {d.id: d for d in self.dimensions}

    def __len__(self) -> int:
        return len(self.dimensions)

    def __iter__(self):
        return iter(self.dimensions)

    def get(self, dimension_id: str) -> Dimension | None:
        return self._by_id.get(dimension_id)

    def is_valid_value(self, dimension_id: str, value: str) -> bool:
        dim = self._by_id.get(dimension_id)
        return dim is not None and value in dim.values


def load_schema(path: str | Path | None = None) -> DimensionSchema:
    """Load the dimension taxonomy from JSON.

    Defaults to the schema bundled in ``persona/schema/dimensions.json``.
    """
    schema_path = Path(path) if path is not None else _DEFAULT_SCHEMA_PATH
    with open(schema_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    dims = [Dimension.from_json(d) for d in raw["dimensions"]]
    return DimensionSchema(dimensions=dims)


@lru_cache(maxsize=1)
def default_schema() -> DimensionSchema:
    """Cached load of the bundled schema (it never changes at runtime)."""
    return load_schema()
