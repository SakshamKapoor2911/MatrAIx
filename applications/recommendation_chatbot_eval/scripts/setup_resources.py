#!/usr/bin/env python3
"""Set up the RecAI recommendation resources so a teammate can run real recs.

The recommender ranks over Microsoft RecAI's "ready-to-run" resource bundle —
three domains (movie, beauty_product, game), each a small item table plus a
large item-similarity matrix and a SASRec checkpoint. The bundle is ~1.2 GB
unpacked, so it is **never** committed; this script fetches and installs it.

What it does
------------
1. Obtains ``all_resources.zip`` — downloads the official copy (Google Drive,
   from the RecAI InteRecAgent README) or uses a local ``--zip`` you already
   have.
2. Installs each domain under ``recai/InteRecAgent/resources/<domain>/`` exactly
   as RecAI expects (no renaming of the engine's own files).
3. Exports a small, clean **parquet catalog** per domain to ``data/catalogs/``
   (``movie.parquet`` / ``game.parquet`` / ``beauty_product.parquet``). These are
   committed, so the Studio UI + catalog browsing work on a fresh clone with no
   download. ``--catalogs-only`` regenerates just these from an installed bundle.
4. Verifies what landed (item counts + the files a turn needs).

Usage
-----
    python scripts/setup_resources.py                 # download official zip + install
    python scripts/setup_resources.py --zip PATH      # use a local all_resources.zip
    python scripts/setup_resources.py --catalogs-only # rebuild data/catalogs/ only

Downloading needs ``gdown`` (``pip install gdown``); a local ``--zip`` does not.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# The official ready-to-run bundle, per microsoft/RecAI InteRecAgent/README.md
# ("a volunteer has prepared a copy of ready-to-run data resources").
OFFICIAL_GDRIVE_ID = "1nSw2cuoi_WEOnHRg_eIyLWGBAjHdelsg"
OFFICIAL_GDRIVE_URL = f"https://drive.google.com/uc?id={OFFICIAL_GDRIVE_ID}"
RECDRIVE_MIRROR = "https://rec.ustc.edu.cn/share/baa4d930-48e1-11ee-b20c-3fee0ba82bbd"

DOMAINS = ("movie", "beauty_product", "game")

APP_ROOT = Path(__file__).resolve().parents[1]
RESOURCES_DIR = APP_ROOT / "recai" / "InteRecAgent" / "resources"
CATALOGS_DIR = APP_ROOT / "data" / "catalogs"

# The item table is named per-domain inside the bundle; settings.json's
# ``GAME_INFO_FILE`` is authoritative, but these are the known defaults.
_DEFAULT_TABLE = {"movie": "movies.ftr", "beauty_product": "products.ftr", "game": "games.ftr"}


def _log(msg: str) -> None:
    print(f"[setup_resources] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# 1. Obtain the zip
# --------------------------------------------------------------------------- #
def download_official_zip(dest: Path) -> Path:
    """Download the official all_resources.zip from Google Drive via gdown."""
    try:
        import gdown
    except ImportError:
        sys.exit(
            "Downloading needs gdown. Either `pip install gdown`, or download the "
            "zip manually and pass it with --zip.\n"
            f"  Google Drive: {OFFICIAL_GDRIVE_URL}\n"
            f"  RecDrive mirror: {RECDRIVE_MIRROR}"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    _log(f"downloading official bundle → {dest} (~497 MB, one time)…")
    gdown.download(OFFICIAL_GDRIVE_URL, str(dest), quiet=False)
    if not dest.is_file():
        sys.exit("Download did not produce a file; try the manual --zip route.")
    return dest


# --------------------------------------------------------------------------- #
# 2. Install the bundle
# --------------------------------------------------------------------------- #
def install_bundle(zip_path: Path) -> None:
    """Unpack the three domains into ``recai/InteRecAgent/resources/<domain>/``."""
    if not zip_path.is_file():
        sys.exit(f"zip not found: {zip_path}")
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        _log(f"unpacking {zip_path.name}…")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)
        for domain in DOMAINS:
            src = Path(tmp) / domain
            if not src.is_dir():
                sys.exit(f"domain '{domain}' missing from the zip ({zip_path}).")
            dst = RESOURCES_DIR / domain
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            _log(f"installed {domain} → {dst.relative_to(APP_ROOT)}")


# --------------------------------------------------------------------------- #
# 3. Export committed parquet catalogs
# --------------------------------------------------------------------------- #
def _table_path(domain: str) -> Path:
    """The installed item table for a domain (settings.json is authoritative)."""
    import json

    settings = RESOURCES_DIR / domain / "settings.json"
    name = _DEFAULT_TABLE[domain]
    if settings.is_file():
        try:
            name = json.loads(settings.read_text()).get("GAME_INFO_FILE", name)
        except ValueError:
            pass
    return RESOURCES_DIR / domain / name


def export_catalogs() -> None:
    """Write a compact parquet catalog per domain into ``data/catalogs/``."""
    import pandas as pd

    CATALOGS_DIR.mkdir(parents=True, exist_ok=True)
    for domain in DOMAINS:
        table = _table_path(domain)
        if not table.is_file():
            _log(f"skip {domain}: item table not installed ({table.name}).")
            continue
        frame = pd.read_feather(table)
        out = CATALOGS_DIR / f"{domain}.parquet"
        frame.to_parquet(out, index=False, compression="zstd")
        size_kb = out.stat().st_size / 1024
        _log(f"catalog {domain}: {len(frame):,} items → {out.relative_to(APP_ROOT)} ({size_kb:,.0f} KB)")


# --------------------------------------------------------------------------- #
# 4. Verify
# --------------------------------------------------------------------------- #
def verify() -> bool:
    ok = True
    _log("verifying…")
    for domain in DOMAINS:
        bundle = RESOURCES_DIR / domain
        installed = (bundle / "settings.json").is_file()
        catalog = (CATALOGS_DIR / f"{domain}.parquet").is_file()
        _log(f"  {domain:15s} bundle={'yes' if installed else 'NO '}  catalog={'yes' if catalog else 'NO'}")
        ok = ok and catalog
    return ok


# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zip", type=Path, help="Use a local all_resources.zip instead of downloading.")
    parser.add_argument(
        "--catalogs-only",
        action="store_true",
        help="Only (re)build data/catalogs/*.parquet from an already-installed bundle.",
    )
    args = parser.parse_args()

    if args.catalogs_only:
        export_catalogs()
        return 0 if verify() else 1

    zip_path = args.zip if args.zip else download_official_zip(APP_ROOT.parent / "all_resources.zip")
    install_bundle(zip_path)
    export_catalogs()
    ok = verify()
    _log("done." if ok else "done with warnings (see above).")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
