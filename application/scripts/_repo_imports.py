"""Shared repo-root and import-path setup for ``application/scripts/*``."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def ensure_application_script_imports() -> None:
    """Make Harbor, PersonaEval backend, and persona-eval package imports resolvable."""
    required_paths = [
        REPO_ROOT,
        REPO_ROOT / "environment" / "runtime",
        REPO_ROOT / "packages" / "persona-eval" / "src",
        REPO_ROOT / "application" / "persona_eval",
    ]
    for path in reversed(required_paths):
        raw = str(path)
        if raw not in sys.path:
            sys.path.insert(0, raw)
