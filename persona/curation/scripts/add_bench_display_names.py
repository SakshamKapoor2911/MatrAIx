#!/usr/bin/env python3
"""Bake synthetic display_name into bench-dev-sample YAML files and manifest.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from personabench.persona_display_name import synthetic_display_name  # noqa: E402

POOL_DIR = REPO_ROOT / "persona" / "datasets" / "bench-dev-sample"
MANIFEST_PATH = POOL_DIR / "manifest.json"


def _yaml_path(persona_id: str) -> Path:
    pid = persona_id.strip()
    candidates = [POOL_DIR / f"persona_{pid}.yaml"]
    if pid.isdigit():
        candidates.append(POOL_DIR / f"persona_{pid.zfill(4)}.yaml")
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    personas = manifest.get("personas")
    if not isinstance(personas, list):
        raise SystemExit("manifest.json is missing personas[]")

    updated = 0
    for entry in personas:
        if not isinstance(entry, dict):
            continue
        persona_id = str(entry.get("persona_id") or "").strip()
        if not persona_id:
            continue
        dims = entry.get("dimensions")
        dimensions = dims if isinstance(dims, dict) else {}
        display_name = synthetic_display_name(persona_id, dimensions)
        entry["display_name"] = display_name

        yaml_path = _yaml_path(persona_id)
        if not yaml_path.is_file():
            continue
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            continue
        raw["display_name"] = display_name
        yaml_path.write_text(
            yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        updated += 1

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Updated display_name for {updated} personas in {POOL_DIR.name}")


if __name__ == "__main__":
    main()
