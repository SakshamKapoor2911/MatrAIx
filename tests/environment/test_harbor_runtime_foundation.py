from __future__ import annotations

import pathlib
import tomllib


ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_harbor_version_fallback_imports_from_source_tree(monkeypatch) -> None:
    import harbor
    from harbor.utils import version as version_utils

    def missing_distribution(_distribution_name: str) -> str:
        raise version_utils.importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(
        version_utils.importlib.metadata,
        "version",
        missing_distribution,
    )

    assert harbor.__version__
    assert version_utils.get_harbor_version("fallback-version") == "fallback-version"


def test_harbor_console_scripts_are_registered() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["requires-python"] == ">=3.12"
    assert pyproject["project"]["scripts"] == {
        "harbor": "harbor.cli.main:app",
        "hr": "harbor.cli.main:app",
        "hb": "harbor.cli.main:app",
    }
    assert pyproject["tool"]["setuptools"]["package-dir"] == {
        "harbor": "environment/runtime/harbor",
        "matraix": "src/matraix",
        "matraix.agents": "environment/agents/matraix/agents",
    }
    packages = set(pyproject["tool"]["setuptools"]["packages"])
    assert {
        "harbor",
        "harbor.cli",
        "harbor.environments",
        "matraix",
        "matraix.agents",
        "matraix.agents.persona",
    } <= packages


def test_runtime_import_excludes_raw_snapshot_directories() -> None:
    forbidden_paths = [
        "adapters",
        "jobs",
        "src/harbor",
        "src/matraix/agents",
        "src/matraix/agents",
    ]

    for relative_path in forbidden_paths:
        assert not (ROOT / relative_path).exists(), relative_path

    apps_dir = ROOT / "apps"
    if apps_dir.exists():
        assert sorted(path.name for path in apps_dir.iterdir()) == [
            "README.md",
            "viewer",
        ]


def test_runtime_factory_does_not_reference_deferred_matraix_agents() -> None:
    """Ensure factory.py uses string-based lazy imports, not top-level import statements."""
    factory_source = (
        ROOT / "environment/runtime/harbor/agents/factory.py"
    ).read_text()

    for line in factory_source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        assert not stripped.startswith("import matraix.agents"), line
        assert not stripped.startswith("from matraix.agents"), line


def test_runtime_import_has_no_large_files() -> None:
    viewer_static = ROOT / "environment/runtime/harbor/viewer/static"
    large_files = [
        path
        for path in (ROOT / "environment/runtime/harbor").rglob("*")
        if path.is_file()
        and path.stat().st_size > 1_000_000
        and not path.is_relative_to(viewer_static)
    ]

    assert large_files == []
