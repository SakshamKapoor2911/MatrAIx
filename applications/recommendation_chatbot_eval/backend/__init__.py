"""RecBot Studio backend.

A developer/research harness that wraps the in-process RecAI movie
recommendation chatbot (``recbot.interecagent_bridge``) with a small service
layer and a FastAPI application so it can be driven from a browser SPA.

Importing this package is intentionally cheap: it does NOT import RecAI,
numpy, or pandas. The heavyweight :func:`recbot.interecagent_bridge.run_turn`
is imported lazily, only when a turn is actually executed (see
:mod:`backend.service.session`).

The package also makes the sibling ``recbot`` package importable by adding the
``applications/recommendation_chatbot_eval`` directory to ``sys.path`` on
import (see :func:`backend.service.ensure_recbot_importable`).
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
