#!/usr/bin/env python3
"""Append food/diet/cooking dims to checked-in bench-dev-sample personas.

Preserves existing dimension values. Samples only missing EXTRA / cuis_* fields
from the catalog using a deterministic RNG seeded by (base_seed, persona_id).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from matraix.persona_consistency import (  # noqa: E402
    DEV_FOOD_DIMENSION_IDS,
    load_dev_dimension_ids,
    load_dev_dimension_index_order,
)
from matraix.persona_generator import load_catalog_values  # noqa: E402

DEFAULT_SAMPLE = REPO_ROOT / "persona" / "datasets" / "bench-dev-sample"
DEFAULT_SEED = 42


def _pick(rng: random.Random, values: list[str]) -> str:
    if not values:
        raise ValueError("empty catalog values")
    return rng.choice(values)


def _food_dim_ids(dev_ids: tuple[str, ...]) -> list[str]:
    return [
        dim_id
        for dim_id in dev_ids
        if dim_id in DEV_FOOD_DIMENSION_IDS or dim_id.startswith("cuis_")
    ]


def _augment_dimensions(
    dimensions: dict[str, object],
    *,
    food_ids: list[str],
    catalog: dict[str, list[str]],
    order: dict[str, int],
    rng: random.Random,
) -> dict[str, object]:
    updated = dict(dimensions)
    for dim_id in food_ids:
        if dim_id in updated and updated[dim_id] is not None:
            continue
        updated[dim_id] = _pick(rng, catalog[dim_id])
    return dict(
        sorted(
            updated.items(),
            key=lambda item: (order.get(str(item[0]), 99999), str(item[0])),
        )
    )


def _write_persona_yaml(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        yaml.safe_dump(
            payload,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=120,
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample-dir",
        type=Path,
        default=DEFAULT_SAMPLE,
        help="bench-dev-sample directory",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    sample_dir = args.sample_dir.resolve()
    manifest_path = sample_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"missing manifest: {manifest_path}")

    # Bust cached catalog/order views if this process reuses prior imports.
    load_dev_dimension_index_order.cache_clear()

    catalog = load_catalog_values()
    dev_ids = load_dev_dimension_ids()
    food_ids = _food_dim_ids(dev_ids)
    order = load_dev_dimension_index_order()
    if not food_ids:
        raise SystemExit("no food dims in load_dev_dimension_ids()")
    for dim_id in food_ids:
        if dim_id not in catalog or not catalog[dim_id]:
            raise SystemExit(f"catalog missing values for {dim_id}")

    yaml_paths = sorted(sample_dir.glob("persona_*.yaml"))
    if not yaml_paths:
        raise SystemExit(f"no persona_*.yaml under {sample_dir}")

    for path in yaml_paths:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise SystemExit(f"invalid persona yaml: {path}")
        persona_id = str(payload.get("persona_id") or path.stem.split("_")[-1])
        dims = payload.get("dimensions")
        if not isinstance(dims, dict):
            raise SystemExit(f"missing dimensions: {path}")
        rng = random.Random(f"{args.seed}:{persona_id}:food-dims")
        payload["dimensions"] = _augment_dimensions(
            dims,
            food_ids=food_ids,
            catalog=catalog,
            order=order,
            rng=rng,
        )
        _write_persona_yaml(path, payload)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["dimension_ids"] = list(dev_ids)
    manifest["dimension_count"] = len(dev_ids)

    personas = manifest.get("personas") or []
    by_id: dict[str, Path] = {}
    for path in yaml_paths:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        by_id[str(payload["persona_id"])] = path

    for entry in personas:
        if not isinstance(entry, dict):
            continue
        persona_id = str(entry.get("persona_id") or "")
        path = by_id.get(persona_id)
        if path is None:
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        entry["dimensions"] = dict(payload["dimensions"])
        if "source" in payload:
            entry["source"] = payload["source"]

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"augmented {len(yaml_paths)} personas; "
        f"dimension_count={len(dev_ids)} (+{len(food_ids)} food/cuisine dims)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
