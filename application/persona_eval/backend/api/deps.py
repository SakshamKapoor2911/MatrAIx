"""Process-wide service singletons for the PersonaEval API.

The architecture runs a **single** uvicorn worker (the cached RecAI agent and
the in-memory job registry are module globals — multiple workers would each
rebuild them). This module is therefore the one place that constructs the shared
service-layer objects and hands them to the FastAPI app / route handlers:

* :class:`~backend.service.config.ConfigManager` — config validation + env mapping.
* :class:`~backend.service.catalog_index.CatalogIndex` — the in-memory catalog.
* :class:`~backend.service.session_store.SessionStore` — JSON session persistence.
* :class:`~backend.service.session.SessionManager` — owns sessions and turns; it
  internally owns the one :class:`~backend.service.jobs.JobRegistry` (the async
  turn registry), exposed here via :class:`AppState.jobs` so there is exactly one
  registry process-wide.

Construction is **lazy and cached**: :func:`get_state` builds the singletons on
first use and returns the same :class:`AppState` thereafter. The FastAPI app
(:mod:`backend.api.app`) calls :func:`build_state` once at startup and stores the
result on ``app.state`` so handlers can resolve it per-request via
:func:`state_from_request` without touching the module global. Tests can call
:func:`reset_state` (or build their own :class:`AppState`) for isolation.

Importing this module is cheap and side-effect-light: it does NOT import RecAI /
numpy / pandas. The heavyweight ``recbot.interecagent_bridge.run_turn`` is
lazy-imported inside the service only when a turn actually runs. Catalog loading
uses stdlib ``json`` only.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

# Importing the service package wires
# the task-owned chatbot API source onto ``sys.path`` so the lazy
# ``import recbot...`` resolves later WITHOUT importing recbot itself.
from backend.service import ensure_recbot_importable
from backend.service.bundle_catalog import get_bundle_catalog
from backend.service.catalog_index import CatalogIndex
from backend.service.config import ConfigManager
from backend.service.config import persona_eval_runtime
from backend.service.jobs import JobRegistry
from backend.service.session import SessionManager
from backend.service.session_store import SessionStore

if TYPE_CHECKING:  # pragma: no cover - typing only
    from backend.service.appworld_eval_service import AppWorldEvalService
    from backend.service.persona_eval_service import PersonaEvalService
    from backend.service.survey_eval_service import SurveyEvalService
    from backend.service.web_eval_service import WebEvalService

ensure_recbot_importable()

__all__ = [
    "AppState",
    "resolve_catalog_path",
    "build_persona_eval_service",
    "build_appworld_eval_service",
    "build_web_eval_service",
    "build_state",
    "get_state",
    "reset_state",
    "state_from_request",
]


#: Domain whose catalog backs preflight / persona-eval / manual turns by default.
DEFAULT_DOMAIN = ConfigManager.DEFAULTS["domain"]


def resolve_catalog_path() -> Optional[str]:
    """Explicit catalog ``items.jsonl`` override, if one is configured.

    Returns ``INTERECAGENT_CATALOG_PATH`` when set (used by tests and any caller
    that wants to pin a specific JSONL catalog), else ``None`` — in which case
    the app serves the **real per-domain bundle** catalog (see
    :func:`build_state`) rather than any on-disk stub.
    """
    return os.environ.get("INTERECAGENT_CATALOG_PATH") or None


@dataclass
class AppState:
    """Container for the process-wide service singletons.

    Bundling them in one object keeps the FastAPI wiring tidy (a single
    ``app.state.services``) and makes the dependency surface explicit for
    handlers and tests. ``jobs`` is the :class:`~backend.service.jobs.JobRegistry`
    owned by the :class:`~backend.service.session.SessionManager`, surfaced here
    so there is exactly one registry shared across the app. ``persona_eval`` is the
    single :class:`~backend.service.persona_eval_service.PersonaEvalService` driving the
    persona persona-eval demo (one per process; runs are serialized inside it).
    """

    config: ConfigManager
    catalog: CatalogIndex
    store: SessionStore
    manager: SessionManager
    persona_eval: "PersonaEvalService"
    survey_eval: "SurveyEvalService"
    web_eval: "WebEvalService"
    appworld_eval: "AppWorldEvalService"
    #: Resolves a domain to its catalog index. In production this serves the
    #: real per-domain bundle; with an injected catalog (tests / explicit JSONL)
    #: it serves that one index for every domain.
    catalog_provider: Callable[[str], CatalogIndex]

    def catalog_for(self, domain: Optional[str]) -> CatalogIndex:
        """Return the catalog index for ``domain`` (default domain if ``None``)."""
        return self.catalog_provider(domain or DEFAULT_DOMAIN)

    @property
    def jobs(self) -> JobRegistry:
        """The single async-turn :class:`JobRegistry` (lazily created)."""
        return self.manager.jobs

    def shutdown(self) -> None:
        """Release background resources (the job thread pool)."""
        self.manager.shutdown()


def build_persona_eval_service(
    catalog: CatalogIndex, config: ConfigManager
) -> "PersonaEvalService":
    """Construct the process-wide :class:`PersonaEvalService`.

    Persona-eval runs locally: PersonaEval drives the simulated user and calls
    each application-under-test adapter directly. The service keeps the same
    async job API that the frontend uses, through direct local runners.
    """
    from backend.service.persona_eval_service import PersonaEvalService
    from persona_eval.persona import get_persona
    from persona_eval.sut_descriptions import sut_description_for

    runtime = persona_eval_runtime()
    if runtime == "benchflow":
        from backend.service.benchflow_persona_eval import BenchFlowPersonaEvalRunner

        return PersonaEvalService(
            session_builder=lambda _cfg: type("BenchFlowSession", (), {"turns": []})(),
            get_persona=get_persona,
            sut_for=sut_description_for,
            simulator_factory=lambda *_args: None,
            runner=BenchFlowPersonaEvalRunner(),
        )
    if runtime == "harbor":
        from backend.service.harbor_persona_eval import HarborPersonaEvalRunner

        return PersonaEvalService(
            session_builder=lambda _cfg: type("HarborSession", (), {"turns": []})(),
            get_persona=get_persona,
            sut_for=sut_description_for,
            simulator_factory=lambda *_args: None,
            runner=HarborPersonaEvalRunner(),
        )

    from backend.service.local_chatbot_eval import (
        LocalChatbotEvalRunner,
        build_local_chat_session,
        build_local_user_simulator_for_model,
    )

    return PersonaEvalService(
        session_builder=lambda cfg: build_local_chat_session(
            cfg,
            catalog_provider=lambda domain: get_bundle_catalog(domain)
            if resolve_catalog_path() is None
            else catalog,
            config_manager=config,
        ),
        get_persona=get_persona,
        sut_for=sut_description_for,
        simulator_factory=lambda _engine, gid, domain, persona_model: (
            build_local_user_simulator_for_model(persona_model, gid, domain)
        ),
        runner=LocalChatbotEvalRunner(),
    )


def build_survey_eval_service() -> "SurveyEvalService":
    """Construct the process-wide local survey eval service."""
    from backend.service.survey_eval_service import SurveyEvalService
    from backend.service.survey_instruments import (
        get_survey_instrument,
        list_survey_instruments,
    )
    from persona_eval.persona import get_persona

    runtime = persona_eval_runtime()
    if runtime == "benchflow":
        from backend.service.benchflow_survey_eval import BenchFlowSurveyEvalRunner

        runner = BenchFlowSurveyEvalRunner()
    elif runtime == "harbor":
        from backend.service.harbor_survey_eval import HarborSurveyEvalRunner

        runner = HarborSurveyEvalRunner()
    else:
        from backend.service.local_survey_eval import LocalSurveyEvalRunner

        runner = LocalSurveyEvalRunner()

    return SurveyEvalService(
        get_persona=get_persona,
        get_instrument=get_survey_instrument,
        list_instruments=list_survey_instruments,
        runner=runner,
    )


def build_web_eval_service() -> "WebEvalService":
    """Construct the process-wide local web eval service."""
    from backend.service.web_eval_service import WebEvalService
    from backend.service.web_tasks import get_web_eval_task, list_web_eval_tasks
    from persona_eval.persona import get_persona

    runtime = persona_eval_runtime()
    if runtime == "benchflow":
        from backend.service.benchflow_web_eval import BenchFlowWebEvalRunner

        runner = BenchFlowWebEvalRunner()
    elif runtime == "harbor":
        from backend.service.harbor_web_eval import HarborWebEvalRunner

        runner = HarborWebEvalRunner()
    else:
        from backend.service.local_web_eval import LocalWebEvalRunner

        runner = LocalWebEvalRunner()

    return WebEvalService(
        get_persona=get_persona,
        get_task=get_web_eval_task,
        list_tasks=list_web_eval_tasks,
        runner=runner,
    )


def build_state(catalog_path: Optional[str] = None) -> AppState:
    """Construct a fresh, fully-wired :class:`AppState`.

    Parameters
    ----------
    catalog_path:
        Override for the catalog ``items.jsonl`` location. When ``None`` the
        path is resolved from ``INTERECAGENT_CATALOG_PATH`` or the canonical
        default. A missing file is tolerated (the index is simply empty).

    The returned state is independent of the module-global cache, so the app and
    tests can each own their own instance.

    Catalog sourcing: when an explicit ``catalog_path`` (or
    ``INTERECAGENT_CATALOG_PATH``) is given, that single JSONL index answers for
    every domain (used by tests and pinned setups). Otherwise the app serves the
    **real per-domain bundle** — ``catalog_for(domain)`` lazily loads and caches
    each domain's item table from ``recai/InteRecAgent/resources/<domain>/``.
    """
    explicit = catalog_path if catalog_path is not None else resolve_catalog_path()
    config = ConfigManager()
    if explicit:
        injected = CatalogIndex(explicit)

        def catalog_provider(_domain: str) -> CatalogIndex:
            return injected

        default_catalog = injected
    else:
        catalog_provider = get_bundle_catalog
        default_catalog = get_bundle_catalog(DEFAULT_DOMAIN)
    store = SessionStore()
    manager = SessionManager(catalog=default_catalog, store=store, config_manager=config)
    persona_eval = build_persona_eval_service(default_catalog, config)
    survey_eval = build_survey_eval_service()
    web_eval = build_web_eval_service()
    appworld_eval = build_appworld_eval_service()
    return AppState(
        config=config,
        catalog=default_catalog,
        store=store,
        manager=manager,
        persona_eval=persona_eval,
        survey_eval=survey_eval,
        web_eval=web_eval,
        appworld_eval=appworld_eval,
        catalog_provider=catalog_provider,
    )


# --------------------------------------------------------------------------- #
# Module-global singleton (lazy, thread-safe)
# --------------------------------------------------------------------------- #
_state: Optional[AppState] = None
_state_lock = threading.Lock()


def get_state(catalog_path: Optional[str] = None) -> AppState:
    """Return the process-wide :class:`AppState`, constructing it on first use.

    Thread-safe (double-checked locking). ``catalog_path`` is honoured only the
    first time, when the singleton is built; later calls return the cached state
    regardless of the argument. Use :func:`build_state` for an isolated instance.
    """
    global _state
    if _state is None:
        with _state_lock:
            if _state is None:
                _state = build_state(catalog_path)
    return _state


def reset_state() -> None:
    """Drop the cached singleton (shutting down its job pool).

    Primarily for tests that want a clean process-global between cases.
    """
    global _state
    with _state_lock:
        if _state is not None:
            try:
                _state.shutdown()
            except Exception:  # pragma: no cover - best-effort cleanup
                pass
        _state = None


def state_from_request(request) -> AppState:
    """Resolve the :class:`AppState` for a request.

    The app stores the state on ``app.state.services`` at startup; fall back to
    the module-global singleton if it is not present (e.g. a router mounted
    without the app's startup hook). Typed loosely to avoid importing Starlette
    here.
    """
    services = getattr(request.app.state, "services", None)
    if isinstance(services, AppState):
        return services
    return get_state()
