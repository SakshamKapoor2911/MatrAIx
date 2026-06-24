"""Build a real :class:`RecBotSession` for a persona-eval run.

The persona-eval runner drives **one** in-process :class:`RecBotSession` (the cached
RecAI agent and ``os.environ`` are shared across sessions, so a process serves a
single conversation). This factory constructs that session exactly the way
:meth:`backend.service.session.SessionManager.create` does — a direct
``RecBotSession(...)`` call with a freshly generated ``ses_*`` id — rather than
going through the manager (which would also spin up the async job registry /
thread pool that the headless runner does not need).

The :class:`~persona_eval.types.PersonaEvalConfig` (snake_case engine / ranker_mode /
resource_mode / domain) is translated to the PersonaEval config dict (camelCase keys)
and validated/normalized by :class:`~backend.service.config.ConfigManager` so the
session carries the same shape the API would build.
"""

from __future__ import annotations

from backend.service.catalog_index import CatalogIndex
from backend.service.config import ConfigManager
from backend.service.session import RecBotSession, _new_id
from persona_eval.types import PersonaEvalConfig

__all__ = ["build_session"]


def build_session(
    config: PersonaEvalConfig,
    *,
    catalog: CatalogIndex,
    config_manager: ConfigManager,
    title: str = "persona-eval",
) -> RecBotSession:
    """Return a real :class:`RecBotSession` configured for ``config``.

    The session is built the same way ``SessionManager.create`` builds it: the
    config is normalized/validated by ``config_manager``, an id is minted via the
    backend's ``_new_id("ses")`` helper, and the shared ``catalog`` /
    ``config_manager`` are passed through so ``run_turn_sync`` resolves the
    catalog path and applies the ``INTERECAGENT_*`` env the same as in the API.
    """
    cfg = config_manager.normalize({
        "engine": config.engine,
        "rankerMode": config.ranker_mode,
        "resourceMode": config.resource_mode,
        "domain": config.domain,
        "botType": "chat",
    })
    return RecBotSession(
        id=_new_id("ses"),
        title=title,
        config=cfg,
        catalog=catalog,
        config_manager=config_manager,
    )
