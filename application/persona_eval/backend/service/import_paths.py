"""Helpers for making source-tree imports available at runtime."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_harbor_source_imports() -> None:
    """Make source-tree imports (``backend.*``, ``harbor.*``, ``persona_eval.*``) available."""
    repo_root = Path(__file__).resolve().parents[4]
    required_paths = [
        repo_root,
        repo_root / "environment" / "runtime",
        repo_root / "packages" / "persona-eval" / "src",
        repo_root / "application" / "persona_eval",
    ]
    for path in reversed(required_paths):
        raw = str(path)
        if raw not in sys.path:
            sys.path.insert(0, raw)
