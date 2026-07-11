"""Service-layer utilities for Playground."""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = ["ensure_recbot_importable"]


def ensure_recbot_importable() -> str:
    """Make the clean task-local recommender API importable when present.

    The historical Playground app expected MatrAIx's
    ``application/tasks/recommender-agent_chat_api`` tree. PersonaBench keeps a slimmer
    smoke sidecar under ``application/tasks/recommender-agent_chat_api`` instead.
    Adding the sidecar directory to ``sys.path`` is harmless when it has no
    importable RecAI bridge, and keeps the full app's lazy import path setup
    compatible with both the old and clean layouts.
    """
    from backend.service.task_environment import resolve_task_environment_dir

    repo_root = Path(__file__).resolve().parents[4]
    task_dir = repo_root / "application" / "tasks" / "recommender-agent_chat_api"
    task_api_dir = (
        resolve_task_environment_dir(task_dir) / "recommender-api"
    )
    path = str(task_api_dir)
    if path not in sys.path:
        sys.path.insert(0, path)
    return path
