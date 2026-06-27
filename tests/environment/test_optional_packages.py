from __future__ import annotations

import pathlib
import tomllib


ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_legacy_matraix_package_namespace_is_not_restored() -> None:
    assert not (ROOT / "packages/matraix").exists()


def test_harbor_langsmith_package_targets_personabench_distribution() -> None:
    pyproject = tomllib.loads(
        (ROOT / "packages/harbor-langsmith/pyproject.toml").read_text(
            encoding="utf-8"
        )
    )

    dependencies = pyproject["project"]["dependencies"]
    assert "personabench>=0.1.0" in dependencies
    assert "harbor>=0.13.0" not in dependencies
    assert pyproject["project"]["entry-points"]["harbor.plugins"] == {
        "langsmith": "harbor_langsmith:LangSmithPlugin",
    }
