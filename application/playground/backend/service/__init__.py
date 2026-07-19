"""Service-layer utilities for Playground."""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = ["ensure_recbot_importable"]


def ensure_recbot_importable() -> str:
    """Make the clean task-local recommender API importable when present.

    The historical Playground app expected MatrAIx's
    ``application/tasks/chat_recai`` tree. The system keeps a slimmer
    smoke sidecar under ``application/chatbot-api-sidecar_recai/recommender-api``.
    Adding the sidecar directory to ``sys.path`` is harmless when it has no
    importable RecAI bridge, and keeps the full app's lazy import path setup
    compatible with both the old and clean layouts.
    """
    from backend.service.task_environment import resolve_chat_endpoint_host_dir

    repo_root = Path(__file__).resolve().parents[4]
    task_dir = repo_root / "application" / "tasks" / "chat_recai"
    host_dir = resolve_chat_endpoint_host_dir(task_dir)
    fallback = (
        repo_root
        / "environment"
        / "task-environments"
        / "application"
        / "chatbot-api-sidecar_recai"
        / "recommender-api"
    )
    if host_dir is None:
        task_api_dir = fallback
    else:
        candidate = host_dir / "recommender-api"
        task_api_dir = candidate if candidate.is_dir() else host_dir
    path = str(task_api_dir)
    if path not in sys.path:
        sys.path.insert(0, path)
    return path
