"""Shared verifier path helpers for application task test_state.py modules.

Copy this file into tests/verifier_paths.py when authoring a new task, or import
the logic inline. Kept in task-spec as the canonical reference implementation.
"""

from __future__ import annotations

import os
from pathlib import Path


def verifier_dir() -> Path:
    """Resolve the trial verifier output directory.

    Order:
      1. HARBOR_VERIFIER_DIR (Harbor host, Playground host verifier, pytest harness)
      2. /logs/verifier (in-container default for Harbor docker sandboxes)
    """
    explicit = os.environ.get("HARBOR_VERIFIER_DIR")
    if explicit:
        path = Path(explicit)
        path.mkdir(parents=True, exist_ok=True)
        return path

    container_default = Path("/logs/verifier")
    try:
        container_default.mkdir(parents=True, exist_ok=True)
        return container_default
    except OSError:
        pass

    raise RuntimeError(
        "HARBOR_VERIFIER_DIR is required when running outside a Harbor trial "
        "container. Point it at jobs/<job>/<trial>/verifier for local harness runs."
    )
