from __future__ import annotations

from pathlib import Path

# recbot/paths.py -> parents[1] == the chatbot task API source root.
APP_ROOT = Path(__file__).resolve().parents[1]


def default_interecagent_root() -> Path:
    """In-repo RecAI engine root (the `recai/` submodule). No external dependency."""
    return APP_ROOT / "recai" / "InteRecAgent"
