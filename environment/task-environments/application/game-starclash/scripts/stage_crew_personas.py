#!/usr/bin/env python3
"""Verify crew persona YAML is present before ``run_arena.py`` starts.

In Harbor/Docker runs, personas are uploaded from repo-root ``persona/datasets/``
at trial start (see ``harbor.utils.crew_personas``). Local runs resolve the same
paths via directory walk-up. This script fails fast with a clear message when
files are missing.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


def _persona_paths(manifest_path: Path) -> list[str]:
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid crew manifest: {manifest_path}")
    paths = raw.get("persona_paths")
    if not isinstance(paths, list) or not paths:
        raise ValueError(f"No persona_paths in crew manifest: {manifest_path}")
    return [str(item) for item in paths]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify crew persona YAML paths.")
    parser.add_argument(
        "--crew",
        default="/app/input/crew_manifest.yaml",
        help="Path to crew_manifest.yaml",
    )
    parser.add_argument(
        "--workdir",
        default=os.environ.get("STARCLASH_WORKDIR", "/app"),
        help="Container workdir where persona paths resolve (default: /app)",
    )
    args = parser.parse_args()

    manifest = Path(args.crew)
    if not manifest.is_file():
        print(f"[stage_crew_personas] missing crew manifest: {manifest}", file=sys.stderr)
        return 1

    workdir = Path(args.workdir).resolve()
    missing: list[str] = []
    for rel in _persona_paths(manifest):
        target = workdir / rel.replace("\\", "/").lstrip("/")
        if not target.is_file():
            missing.append(f"{rel} -> {target}")

    if missing:
        print(
            "[stage_crew_personas] crew persona files not found in container.\n"
            "PersonaBench loads profiles from repo-root persona/datasets/ at trial "
            "start (never bundled in the task). For Harbor, ensure the oracle/agent "
            "upload step ran; for local dev, run from the MatrAIx repo root.\n"
            "Missing:\n  " + "\n  ".join(missing),
            file=sys.stderr,
        )
        return 1

    print(f"[stage_crew_personas] ok ({len(_persona_paths(manifest))} personas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())