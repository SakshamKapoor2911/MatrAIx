"""Unzip the RecAI native resource bundle into the in-repo submodule.

Usage:
    python -m scripts.setup_recai_resources [--zip PATH] [--dest PATH] [--force]
"""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from recbot.paths import APP_ROOT

DEFAULT_ZIP = APP_ROOT.parent / "all_resources.zip"  # applications/all_resources.zip
DEFAULT_DEST = APP_ROOT / "recai" / "InteRecAgent" / "resources"
DOMAINS = ("beauty_product", "movie", "game")
_REFERENCED_KEYS = ("GAME_INFO_FILE", "TABLE_COL_DESC_FILE", "MODEL_CKPT_FILE", "ITEM_SIM_FILE")


def _verify_domain(domain_dir: Path) -> None:
    settings_path = domain_dir / "settings.json"
    if not settings_path.exists():
        raise RuntimeError(f"missing settings.json in {domain_dir}")
    settings = json.loads(settings_path.read_text())
    for key in _REFERENCED_KEYS:
        ref = settings.get(key)
        if not ref or not (domain_dir / ref).exists():
            raise RuntimeError(f"{domain_dir.name}: settings[{key}] -> {ref!r} missing on disk")


def setup_resources(zip_path: Path, resources_dir: Path, *, force: bool = False) -> list[str]:
    zip_path = Path(zip_path)
    resources_dir = Path(resources_dir)
    if not zip_path.exists():
        raise RuntimeError(f"resource bundle not found: {zip_path}")
    resources_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        present = [d for d in DOMAINS if any(n.startswith(f"{d}/") for n in names)]
        if not present:
            raise RuntimeError(f"no known domains {DOMAINS} found inside {zip_path}")
        for domain in present:
            target = resources_dir / domain
            if target.exists() and not force and (target / "settings.json").exists():
                continue
            for member in names:
                if member.startswith(f"{domain}/"):
                    zf.extract(member, resources_dir)

    verified = []
    for domain in present:
        _verify_domain(resources_dir / domain)
        verified.append(domain)
    return verified


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    domains = setup_resources(args.zip, args.dest, force=args.force)
    print(f"RecAI resources ready for: {', '.join(sorted(domains))} -> {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
