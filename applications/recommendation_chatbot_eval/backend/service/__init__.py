"""Service layer for RecBot Studio.

Pure-Python (stdlib + optional FastAPI/pydantic at the API layer only) building
blocks that sit between the FastAPI app and the existing in-process
``recbot`` backend:

* :class:`~backend.service.catalog_index.CatalogIndex` -- loads the normalized
  catalog ``items.jsonl`` with stdlib ``json`` (no pandas/numpy) and offers
  cheap search / lookup.
* :class:`~backend.service.config.ConfigManager` -- validates Studio config and
  maps it to ``INTERECAGENT_*`` environment variables.
* :class:`~backend.service.trace_view.TraceView` -- turns a raw
  ``RecBotTurnResult`` dict into the ``TurnView`` the UI renders.
* :class:`~backend.service.session_store.SessionStore` -- JSON persistence for
  sessions on disk.
* :mod:`~backend.service.session` -- :class:`RecBotSession` /
  :class:`SessionManager`, which own conversation state and run turns through
  the backend.

Importing this package adds the ``applications/recommendation_chatbot_eval``
directory to ``sys.path`` so ``import recbot...`` resolves, but it never
imports ``recbot`` itself -- that stays lazy so the API/tests can be exercised
without RecAI installed.
"""

from __future__ import annotations

import os
import sys

__all__ = [
    "ensure_recbot_importable",
    "CatalogIndex",
    "ConfigManager",
    "TraceView",
    "SessionStore",
    "ChatTurn",
    "RecBotSession",
    "SessionManager",
    "JobRegistry",
    "Job",
]


def ensure_recbot_importable() -> str:
    """Make the sibling ``recbot`` package importable.

    The existing backend lives at
    ``applications/recommendation_chatbot_eval/recbot``. This function adds that
    parent directory (``applications/recommendation_chatbot_eval``) to
    ``sys.path`` (idempotently, at the front) so ``import recbot`` works no
    matter the current working directory.

    Returns the directory that was placed on ``sys.path``.
    """
    # .../harness/service/__init__.py -> .../recommendation_chatbot_eval
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    return app_dir


# Wire the import path as a side effect of importing the service package so that
# the lazy ``import recbot`` inside RecBotSession.run_turn_sync resolves.
ensure_recbot_importable()


# Re-export the public service classes. These imports are stdlib-only and safe
# (they do NOT import recbot / numpy / pandas, and creating a JobRegistry — not
# importing the module — is what spins up the thread pool).
from backend.service.catalog_index import CatalogIndex  # noqa: E402
from backend.service.config import ConfigManager  # noqa: E402
from backend.service.jobs import Job, JobRegistry  # noqa: E402
from backend.service.session import ChatTurn, RecBotSession, SessionManager  # noqa: E402
from backend.service.session_store import SessionStore  # noqa: E402
from backend.service.trace_view import TraceView  # noqa: E402
