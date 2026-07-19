#!/usr/bin/env python3
"""Validate static properties of the Persona Full DAG."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from persona.synthesis.sampler import DEFAULT_GRAPH_PATH, load_graph  # noqa: E402
from persona.synthesis.sampler.graph_io import save_json  # noqa: E402
from persona.synthesis.sampler.validation import validate_graph  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = validate_graph(load_graph(args.graph))
    if args.out:
        save_json(report, args.out)
    print(json.dumps(report, indent=2))
    if not report.get("validation_passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
