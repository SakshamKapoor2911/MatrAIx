"""Shared fixtures for MatrAIx unit tests."""

from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def personas_0042(repo_root: Path) -> Path:
    return repo_root / "personas" / "examples" / "persona_0042.yaml"
