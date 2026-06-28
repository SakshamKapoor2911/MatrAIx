#!/usr/bin/env python3
"""Synthesize schema-grounded human persona vectors."""

from __future__ import annotations

import argparse
from pathlib import Path

from personabench.persona_synthesis import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_CONSTRAINTS_PATH,
    synthesize_persona_dataset,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GENERATED_DATASETS_DIR = REPO_ROOT / "persona" / "datasets" / "_generated"


def _default_out_dir(count: int) -> Path:
    return DEFAULT_GENERATED_DATASETS_DIR / f"synthetic-human-{count}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Output directory "
            "(default: persona/datasets/_generated/synthetic-human-<count>)"
        ),
    )
    parser.add_argument(
        "--catalog",
        default=DEFAULT_CATALOG_PATH,
        help="Dimension catalog path (default: persona/schema/dimensions.json)",
    )
    parser.add_argument(
        "--constraints",
        default=DEFAULT_CONSTRAINTS_PATH,
        help=(
            "Readable INVALID pair constraints file "
            "(default: persona/schema/dimension_constraints_readable.txt)"
        ),
    )
    parser.add_argument(
        "--max-attempts-per-persona",
        type=int,
        default=1000,
        help="Retry budget before failing a persona slot (default: 1000)",
    )
    args = parser.parse_args()

    out = args.out if args.out is not None else _default_out_dir(args.count)
    if not out.is_absolute():
        out = REPO_ROOT / out

    manifest = synthesize_persona_dataset(
        out_dir=out,
        count=args.count,
        seed=args.seed,
        catalog_path=args.catalog,
        constraints_path=args.constraints,
        root=REPO_ROOT,
        max_attempts_per_persona=args.max_attempts_per_persona,
    )

    constraint_validation = manifest["constraint_validation"]["validation"]
    print(f"Wrote {manifest['count']} synthetic persona vectors to {out}")
    print(f"Schema: {manifest['schema_version']}")
    print(f"Dimensions: {manifest['dimension_count']}")
    print(
        "Constraints: "
        f"{constraint_validation['applicable_to_generated_dimensions_count']} "
        "rules apply to emitted dimensions"
    )
    print(f"Rejected attempts: {constraint_validation['rejected_attempts']}")


if __name__ == "__main__":
    main()
