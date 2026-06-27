from __future__ import annotations

import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[3]
VIEWER_ROOT = ROOT / "apps/viewer"


def test_viewer_declares_reproducible_node_runtime() -> None:
    package_json = json.loads((VIEWER_ROOT / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((VIEWER_ROOT / "package-lock.json").read_text(encoding="utf-8"))

    assert package_json["engines"]["node"] == ">=20.19.0"
    assert package_lock["packages"][""]["engines"]["node"] == ">=20.19.0"
    assert (VIEWER_ROOT / ".node-version").read_text(encoding="utf-8").strip() == "20.19.0"
    assert (VIEWER_ROOT / ".nvmrc").read_text(encoding="utf-8").strip() == "20.19.0"


def test_viewer_lockfile_keeps_linux_native_optional_packages() -> None:
    package_lock = json.loads((VIEWER_ROOT / "package-lock.json").read_text(encoding="utf-8"))
    packages = package_lock["packages"]

    assert "node_modules/@esbuild/linux-x64" in packages
    assert "node_modules/@rollup/rollup-linux-x64-gnu" in packages
    assert "node_modules/@tailwindcss/oxide-linux-x64-gnu" in packages
    assert "node_modules/lightningcss-linux-x64-gnu" in packages


def test_viewer_ci_typechecks_with_declared_node_runtime() -> None:
    workflow = (ROOT / ".github/workflows/viewer.yml").read_text(encoding="utf-8")

    assert "node-version-file: apps/viewer/.node-version" in workflow
    assert "cache-dependency-path: apps/viewer/package-lock.json" in workflow
    assert "npm ci" in workflow
    assert "npm run typecheck" in workflow


def test_viewer_docs_use_npm_lockfile_workflow() -> None:
    readme = (VIEWER_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Node.js 20.19.0" in readme
    assert "npm ci" in readme
    assert "npm run typecheck" in readme
    assert "bun install" not in readme
