#!/usr/bin/env python3
"""Select reproducible high-information categorical projection fields."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GRAPH = REPO_ROOT / "persona/synthesis/graph/full_dag.json"
DEFAULT_SCHEMA = REPO_ROOT / "persona/schema/dimensions.json"
DEFAULT_WIDTHS = (6, 7, 8, 9, 10, 11, 12, 14, 16)


def _entropy(node: dict[str, Any]) -> float:
    values = node.get("values", [])
    prior = node.get("prior", {})
    probabilities = [float(prior.get(value, 0.0)) for value in values] if isinstance(prior, dict) else [float(value) for value in prior]
    total = sum(probabilities)
    if total <= 0:
        return 0.0
    return -sum((p / total) * math.log2(p / total) for p in probabilities if p > 0)


def select_fields(graph: dict[str, Any], schema: dict[str, Any], count: int) -> list[dict[str, Any]]:
    dimensions = {str(item["id"]): item for item in schema["dimensions"]}
    candidates = []
    for node in graph.get("nodes", []):
        field_id = str(node.get("id"))
        if field_id not in dimensions or node.get("emit", True) is False:
            continue
        dimension = dimensions[field_id]
        candidates.append(
            {
                "id": field_id,
                "category": str(dimension.get("category") or node.get("category") or "Uncategorized"),
                "entropy_bits": _entropy(node),
                "value_count": len(dimension.get("values", [])),
            }
        )
    candidates.sort(key=lambda item: (-item["entropy_bits"], item["id"]))

    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        by_category[candidate["category"]].append(candidate)
    category_order = sorted(
        by_category,
        key=lambda category: (-by_category[category][0]["entropy_bits"], category),
    )
    selected: list[dict[str, Any]] = []
    depth = 0
    while len(selected) < count:
        added = False
        for category in category_order:
            values = by_category[category]
            if depth < len(values):
                selected.append(values[depth])
                added = True
                if len(selected) == count:
                    break
        if not added:
            raise ValueError(f"only found {len(selected)} eligible fields")
        depth += 1
    return selected


def build_config(
    graph: dict[str, Any],
    schema: dict[str, Any],
    widths: tuple[int, ...] = DEFAULT_WIDTHS,
    precision: int = 20,
) -> dict[str, Any]:
    if max(widths) > 16:
        raise ValueError("nibble projections support at most 16 fields per uint64 signature")
    selected = select_fields(graph, schema, max(widths))
    return {
        "format": "persona_projection_hll_config",
        "format_version": 1,
        "selection": "descending graph-prior entropy, round-robin across schema categories",
        "hll_precision": precision,
        "hll_registers": 1 << precision,
        "relative_standard_error": 1.04 / math.sqrt(1 << precision),
        "projections": [
            {
                "id": f"entropy_rr_{width}",
                "width": width,
                "fields": selected[:width],
            }
            for width in widths
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--precision", type=int, default=20)
    args = parser.parse_args()
    graph = json.loads(args.graph.read_text(encoding="utf-8"))
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    config = build_config(graph, schema, precision=args.precision)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()