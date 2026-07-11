#!/usr/bin/env python3
"""Install the native RecAI / InteRecAgent stack for Playground.

This script is the missing piece called out in ``bundle_catalog.py`` and
``app.py`` preflight: it fetches Microsoft's InteRecAgent (``llm4crs/``) and the
``all_resources`` domain bundles, then writes committed-style parquet catalogs
under ``data/catalogs/`` so catalog browse works without loading feathers at
runtime.

Steps (each skippable via flags):
  1. Sparse-clone ``microsoft/RecAI`` → ``recai/InteRecAgent``
  2. Download ``all_resources.zip`` (Google Drive) → ``resources/<domain>/``
  3. Build ``data/catalogs/{movie,game,beauty_product}.parquet`` from feathers

Usage::

    python scripts/setup_recai_resources.py
    python scripts/setup_recai_resources.py --engine-only
    python scripts/setup_recai_resources.py --skip-download   # parquets only
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

REPO_URL = "https://github.com/microsoft/RecAI.git"
# Public mirror of InteRecAgent ready-to-run bundles (see InteRecAgent README).
GDRIVE_FILE_ID = "1nSw2cuoi_WEOnHRg_eIyLWGBAjHdelsg"

DOMAINS = ("movie", "beauty_product", "game")

# Mirrors ``backend.api.app._BUNDLE_REFERENCED_KEYS``.
_REFERENCED_KEYS = (
    "GAME_INFO_FILE",
    "TABLE_COL_DESC_FILE",
    "MODEL_CKPT_FILE",
    "ITEM_SIM_FILE",
)


def api_root() -> Path:
    return Path(__file__).resolve().parents[1]


def interecagent_root() -> Path:
    return api_root() / "recai" / "InteRecAgent"


def catalogs_dir() -> Path:
    return api_root() / "data" / "catalogs"


def _verify_domain(domain_dir: Path) -> dict[str, Any]:
    """Return ``{"ok": bool, "detail": str}`` for one domain bundle."""
    settings_path = domain_dir / "settings.json"
    if not settings_path.is_file():
        return {
            "ok": False,
            "detail": "Native resource bundle not installed for {}.".format(
                domain_dir.name
            ),
        }
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {
            "ok": False,
            "detail": "Resource bundle for {} is unreadable or corrupt.".format(
                domain_dir.name
            ),
        }
    missing: list[str] = []
    for key in _REFERENCED_KEYS:
        ref = settings.get(key) if isinstance(settings, dict) else None
        if not ref or not (domain_dir / str(ref)).is_file():
            missing.append(str(ref) if ref else key)
    if missing:
        return {
            "ok": False,
            "detail": "Resource bundle for {} is incomplete ({} missing).".format(
                domain_dir.name, ", ".join(missing)
            ),
        }
    return {"ok": True, "detail": "ok"}


def verify_all(resources_root: Path) -> bool:
    ok = True
    for domain in DOMAINS:
        result = _verify_domain(resources_root / domain)
        status = "OK" if result["ok"] else "FAIL"
        print("[{}] {} — {}".format(status, domain, result["detail"]))
        ok = ok and result["ok"]
    return ok


def clone_interecagent(*, force: bool = False) -> None:
    dest = interecagent_root()
    llm4crs = dest / "llm4crs"
    if llm4crs.is_dir() and not force:
        print("InteRecAgent already present at {}".format(dest))
        return

    if dest.exists() and force:
        shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="recai-clone-") as tmp:
        clone_root = Path(tmp) / "RecAI"
        print("Cloning {} (sparse InteRecAgent only)…".format(REPO_URL))
        subprocess.run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--sparse",
                "--depth",
                "1",
                REPO_URL,
                str(clone_root),
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(clone_root), "sparse-checkout", "set", "InteRecAgent"],
            check=True,
        )
        shutil.move(str(clone_root / "InteRecAgent"), str(dest))
    if not llm4crs.is_dir():
        raise SystemExit("Clone finished but llm4crs/ is missing under {}".format(dest))
    print("InteRecAgent installed at {}".format(dest))


def _download_with_gdown(zip_path: Path) -> None:
    try:
        import gdown  # type: ignore[import-untyped]
    except ImportError as exc:
        raise SystemExit(
            "gdown is required to fetch all_resources.zip. "
            "Install with: pip install gdown"
        ) from exc
    url = "https://drive.google.com/uc?id={}".format(GDRIVE_FILE_ID)
    print("Downloading all_resources.zip (~1–2 GB) from Google Drive…")
    gdown.download(url, str(zip_path), quiet=False)


def _download_with_curl(zip_path: Path) -> None:
    # Best-effort direct link; Drive may block non-browser clients.
    url = "https://drive.google.com/uc?export=download&id={}".format(GDRIVE_FILE_ID)
    print("Trying curl download (may fail — install gdown if so)…")
    subprocess.run(["curl", "-L", "-o", str(zip_path), url], check=True)


def download_resources(*, force: bool = False) -> None:
    resources_root = interecagent_root() / "resources"
    if not force and all(_verify_domain(resources_root / d)["ok"] for d in DOMAINS):
        print("Resource bundles already installed under {}".format(resources_root))
        return

    resources_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="recai-resources-") as tmp:
        zip_path = Path(tmp) / "all_resources.zip"
        try:
            _download_with_gdown(zip_path)
        except SystemExit:
            raise
        except Exception:
            if zip_path.stat().st_size < 1_000_000:
                zip_path.unlink(missing_ok=True)
                _download_with_curl(zip_path)

        if not zipfile.is_zipfile(zip_path):
            raise SystemExit(
                "Download does not look like a zip file. "
                "Fetch all_resources.zip manually from the InteRecAgent README "
                "and extract movie/, game/, beauty_product/ into {}.".format(
                    resources_root
                )
            )

        print("Extracting resource bundles…")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)
        extracted = Path(tmp)
        # Zip layout: three top-level domain folders.
        for domain in DOMAINS:
            src = extracted / domain
            if not src.is_dir():
                # Some archives nest under all_resources/.
                alt = extracted / "all_resources" / domain
                src = alt if alt.is_dir() else src
            if not src.is_dir():
                raise SystemExit(
                    "Could not find {} folder inside the archive.".format(domain)
                )
            dest = resources_root / domain
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
    print("Resource bundles installed under {}".format(resources_root))


def build_parquets() -> None:
    try:
        import pandas as pd  # noqa: F401
    except ImportError as exc:
        raise SystemExit("pandas + pyarrow required: pip install pandas pyarrow") from exc

    import pandas as pd

    out_dir = catalogs_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    resources_root = interecagent_root() / "resources"

    for domain in DOMAINS:
        domain_dir = resources_root / domain
        check = _verify_domain(domain_dir)
        if not check["ok"]:
            print("[skip] {} — {}".format(domain, check["detail"]))
            continue
        settings = json.loads((domain_dir / "settings.json").read_text(encoding="utf-8"))
        info_file = str(settings.get("GAME_INFO_FILE") or "")
        table_path = domain_dir / info_file
        frame = pd.read_feather(table_path)
        parquet_path = out_dir / "{}.parquet".format(domain)
        frame.to_parquet(parquet_path, index=False)
        print("Wrote {} ({} rows)".format(parquet_path, len(frame)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--engine-only",
        action="store_true",
        help="Only sparse-clone InteRecAgent (llm4crs/).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip all_resources.zip download (use existing resources/).",
    )
    parser.add_argument(
        "--skip-parquets",
        action="store_true",
        help="Do not rebuild data/catalogs/*.parquet.",
    )
    parser.add_argument(
        "--force-clone",
        action="store_true",
        help="Re-clone InteRecAgent even if llm4crs/ exists.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download resource bundles even if already present.",
    )
    args = parser.parse_args(argv)

    clone_interecagent(force=args.force_clone)

    if not args.engine_only:
        if not args.skip_download:
            download_resources(force=args.force_download)
        if not args.skip_parquets:
            build_parquets()

    resources_root = interecagent_root() / "resources"
    print("\nVerification:")
    engine_ok = (interecagent_root() / "llm4crs").is_dir()
    print("[{}] Recommendation engine (llm4crs/)".format("OK" if engine_ok else "FAIL"))
    bundles_ok = verify_all(resources_root) if resources_root.is_dir() else False
    parquets_ok = all((catalogs_dir() / "{}.parquet".format(d)).is_file() for d in DOMAINS)
    print("[{}] Parquet catalogs".format("OK" if parquets_ok else "FAIL"))

    if args.engine_only:
        return 0 if engine_ok else 1

    if engine_ok and bundles_ok and parquets_ok:
        print("\nRecAI native stack is ready. Restart Playground backend and re-check preflight.")
        return 0
    print("\nSome steps are still incomplete — see messages above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
