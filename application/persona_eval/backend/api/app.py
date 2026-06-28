"""The PersonaEval FastAPI application.

This wires the pure-python service layer (:mod:`backend.service`) into a single
HTTP app and implements every endpoint of the API contract. It is intentionally
thin: handlers validate input via the pydantic models in
:mod:`backend.api.schemas`, delegate to the shared service singletons created in
:mod:`backend.api.deps`, and shape the JSON response.

Design:

* :func:`create_app` builds the process-wide :class:`~backend.api.deps.AppState`
  (catalog, config, session store, session manager + its one async job
  registry) and stores it on ``app.state.services`` so handlers reach it via
  :func:`~backend.api.deps.state_from_request`.
* Turns use the **async job** pattern: ``POST /api/sessions/{id}/turns`` returns
  a ``jobId`` immediately; the blocking turn runs in the manager's threadpool
  (serialized per session); the client polls ``GET /api/jobs/{jobId}`` for
  ``building -> running -> done | error``.
* CORS is opened for the Vite dev server (``http://localhost:5173`` /
  ``127.0.0.1``) so the SPA can call the API cross-origin in development.
* When a built SPA exists at ``web/dist`` it is mounted (HTML mode) at ``/`` so
  one origin serves both the app and the API in production.

Run it (single worker — the RecAI agent cache and the in-memory job registry
assume one process)::

    uvicorn backend.api.app:app --host 127.0.0.1 --port 8765 --workers 1

(or ``bash application/persona_eval/backend/run_dev.sh``).

Importing this module is cheap: it does NOT import RecAI / numpy / pandas. The
heavyweight ``recbot.interecagent_bridge.run_turn`` is lazy-imported inside the
service only when a turn actually runs, so importing the app (and the tests)
needs just FastAPI + pydantic. Catalog loading uses stdlib ``json`` only.
"""

from __future__ import annotations

import datetime as _dt
import os
import urllib.request
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# Importing backend.api wires the eval package dir onto sys.path so the lazy
# `import recbot...` resolves later (and so `import backend...` works at all).
import backend.api  # noqa: F401  (side effect: sys.path wiring)
from backend.api import schemas
from backend.api.deps import AppState, build_state, state_from_request
from backend.service.config import ConfigError, ConfigManager, persona_model as default_persona_model

__all__ = ["create_app", "app", "preflight_checks", "catalog_item_view"]

#: Origins allowed to call the API cross-origin (the Vite dev server).
DEV_ORIGINS: List[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def _utc_now() -> str:
    """Current UTC timestamp as ``YYYY-MM-DDTHH:MM:SSZ`` (matches the service layer)."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _persona_blurb(persona: Any, max_chars: int = 160) -> str:
    """A short single-line preview of a persona for the picker.

    Prefers the persona's free-text ``context`` (curated datasets), falling back
    to ``summary``. Collapses whitespace and truncates with an ellipsis so the
    card stays compact.
    """
    text = (
        getattr(persona, "context", "") or getattr(persona, "summary", "") or ""
    ).strip()
    text = " ".join(text.split())
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


# --------------------------------------------------------------------------- #
# Dependencies
# --------------------------------------------------------------------------- #
def get_services(request: Request) -> AppState:
    """FastAPI dependency: the process-wide service singletons for this app."""
    return state_from_request(request)


# --------------------------------------------------------------------------- #
# Catalog item adapter (raw items.jsonl line -> wire CatalogItem)
# --------------------------------------------------------------------------- #
def catalog_item_view(item: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt a raw catalog item dict to the camelCase ``CatalogItem`` shape.

    The normalized JSONL uses snake_case keys (``item_id`` / ``display_text``);
    the wire contract is camelCase. Unknown/missing fields degrade to sensible
    empties so a partially-populated catalog still renders.
    """
    categories = item.get("categories")
    if not isinstance(categories, list):
        categories = []
    metadata = item.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "itemId": item.get("item_id"),
        "title": item.get("title"),
        "description": item.get("description"),
        "displayText": item.get("display_text"),
        "categories": [c for c in categories if isinstance(c, str)],
        "metadata": metadata,
    }


# --------------------------------------------------------------------------- #
# Preflight (user-facing readiness checks)
# --------------------------------------------------------------------------- #
#: The settings.json keys that point at the on-disk files a RecAI domain bundle
#: must ship (item table, column descriptions, ranker checkpoint, similarity
#: matrix). Mirrors ``scripts.setup_recai_resources._REFERENCED_KEYS`` so the
#: preflight validates exactly what the installer wrote.
_BUNDLE_REFERENCED_KEYS = (
    "GAME_INFO_FILE",
    "TABLE_COL_DESC_FILE",
    "MODEL_CKPT_FILE",
    "ITEM_SIM_FILE",
)

#: Domains whose native resource bundle the Studio expects to be installed.
#: Mirrors ``ConfigManager.ALLOWED["domain"]`` — the single ``all_resources``
#: bundle is the source of truth for every selectable domain.
_BUNDLE_DOMAINS = ("movie", "beauty_product", "game")

#: Friendly display labels for the resource domains, so the checklist never shows
#: a raw token like "beauty_product".
_DOMAIN_LABELS = {"movie": "Movies", "beauty_product": "Beauty products", "game": "Games"}


def _sidecar_reachable(base_url: str, timeout: float = 1.5) -> bool:
    """True if a chatbot sidecar answers ``GET /health`` with a 2xx.

    A short timeout keeps the (frequently polled) readiness check snappy; a
    refused connection (the common "not running" case) fails instantly.
    """
    url = "{}/health".format(base_url.rstrip("/"))
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            return 200 <= int(status) < 300
    except Exception:  # noqa: BLE001 - any failure means "not reachable"
        return False


def preflight_checks(
    catalog: Any, domain_sizes: Optional[Dict[str, int]] = None
) -> List[Dict[str, Any]]:
    """Compute the user-facing, interface-aware readiness checklist.

    Reports each probe as ``{"group", "name", "ok", "detail"}`` regardless of
    pass/fail, so the UI can group the overall readiness of the whole system —
    not just the RecAI recommender — in plain language. Groups:

    * **Core** — model credentials and the browsable catalog (any run needs these).
    * **Chatbot** — the RecAI recommender (engine + its native resource bundles,
      collapsed across domains), plus the OpenBB and Medical adapters, which are
      selectable but whose external services are verified at run time.
    * **Survey** / **Web** — the other application interfaces, available to run.

    Check *names* are human-readable and never echo raw environment-variable
    names. Inspection is filesystem-only except for a short ``/health`` probe of
    the optional finance/medical sidecars; it never imports RecAI or any
    application backend.
    """
    checks: List[Dict[str, Any]] = []

    # ---- Core — what any run, on any interface, needs ------------------- #
    openai_key = os.environ.get("OPENAI_API_KEY")
    checks.append(
        {
            "group": "Core",
            "name": "OpenAI credentials",
            "ok": bool(openai_key),
            "detail": (
                "Configured."
                if openai_key
                else "Not configured. Required to run real turns."
            ),
        }
    )

    # Browsable catalog. Readiness is "has items", not a file path. Report every
    # domain's size (movie / beauty / game), so the count never reads as the whole
    # catalog when it is really one domain's corpus.
    size = getattr(catalog, "size", 0)
    if getattr(catalog, "available", False) and size:
        if domain_sizes:
            per = ", ".join(
                "{} {:,}".format(_DOMAIN_LABELS.get(d, d.replace("_", " ").capitalize()), n)
                for d, n in domain_sizes.items()
            )
            detail = "Browsable items by domain: {}.".format(per)
        else:
            detail = "{:,} items loaded.".format(size)
        checks.append({"group": "Core", "name": "Catalog", "ok": True, "detail": detail})
    else:
        checks.append(
            {
                "group": "Core",
                "name": "Catalog",
                "ok": False,
                "detail": "No catalog items available to browse.",
            }
        )

    # ---- Chatbot — RecAI is deeply probed; other adapters are offered --- #
    root = _interecagent_root()
    llm4crs = os.path.join(root, "llm4crs")
    engine_ok = os.path.isdir(root) and os.path.isdir(llm4crs)
    checks.append(
        {
            "group": "Chatbot",
            "name": "Recommendation engine",
            "ok": engine_ok,
            "detail": (
                "InteRecAgent engine found."
                if engine_ok
                else "InteRecAgent engine not found; the recai/ submodule looks "
                "incomplete (missing llm4crs/)."
            ),
        }
    )

    # The RecAI native bundles, collapsed across every supported domain.
    checks.append(_recai_resources_check(root))

    # The finance/medical adapters route to HTTP sidecars. Probe each one's
    # /health so readiness reflects whether it is actually running. They are
    # marked optional: a down sidecar shows here but does not gate overall
    # readiness (RecAI / Survey / Web still run without them).
    from backend.service.local_chatbot_eval import _sidecar_base_url

    finance_url = _sidecar_base_url(
        "CHATBOT_UPSTREAM_FINANCE", "FINANCE_CHATBOT_URL", "http://127.0.0.1:8901"
    )
    finance_ok = _sidecar_reachable(finance_url)
    checks.append(
        {
            "group": "Chatbot",
            "name": "OpenBB (finance)",
            "ok": finance_ok,
            "optional": True,
            "detail": (
                "Finance sidecar reachable at {}.".format(finance_url)
                if finance_ok
                else "Finance sidecar not running at {}. Start it to run a finance chat.".format(
                    finance_url
                )
            ),
        }
    )
    medical_url = _sidecar_base_url(
        "CHATBOT_UPSTREAM_MEDICAL", "MEDICAL_CHATBOT_URL", "http://127.0.0.1:8902"
    )
    medical_ok = _sidecar_reachable(medical_url)
    checks.append(
        {
            "group": "Chatbot",
            "name": "Medical assistant",
            "ok": medical_ok,
            "optional": True,
            "detail": (
                "Medical sidecar reachable at {}.".format(medical_url)
                if medical_ok
                else "Medical sidecar not running at {}. Start it to run a medical chat.".format(
                    medical_url
                )
            ),
        }
    )

    # ---- Survey + Web interfaces --------------------------------------- #
    checks.append(
        {
            "group": "Survey",
            "name": "Survey forms",
            "ok": True,
            "detail": "Survey interface available. Instruments load when you open it.",
        }
    )
    checks.append(
        {
            "group": "Web",
            "name": "Web tasks",
            "ok": True,
            "detail": "Browser and computer-use interface available. It runs when you start a web task.",
        }
    )

    return checks


def _recai_resources_check(interecagent_root: str) -> Dict[str, Any]:
    """One collapsed readiness check across every RecAI resource domain.

    Validates the real native bundle (``settings.json`` + the files it
    references) for each supported domain via :func:`_bundle_check`, and reports
    a single plain-language line — the per-domain status lives in ``detail`` —
    instead of one row per domain.
    """
    def _label(domain: str) -> str:
        return _DOMAIN_LABELS.get(domain, domain.replace("_", " ").capitalize())

    installed: List[str] = []
    missing: List[str] = []
    for domain in _BUNDLE_DOMAINS:
        if _bundle_check(interecagent_root, domain)["ok"]:
            installed.append(_label(domain))
        else:
            missing.append(_label(domain))
    if not missing:
        ok = True
        detail = "Resource bundles installed for {}.".format(", ".join(installed))
    elif installed:
        ok = False
        detail = "Installed: {}. Missing: {}.".format(", ".join(installed), ", ".join(missing))
    else:
        ok = False
        detail = "Resource bundles not installed for {}.".format(", ".join(missing))
    return {"group": "Chatbot", "name": "RecAI resources", "ok": ok, "detail": detail}


def _interecagent_root() -> str:
    """Absolute path to the RecAI engine root used for resource validation.

    Honors an ``INTERECAGENT_ROOT`` override (the bridge reads the same var) and
    otherwise falls back to the task-owned ``recai/InteRecAgent`` checkout. The
    fallback is computed straight from this module's location so it is unaffected
    by a faked ``recbot`` package in tests.
    """
    override = os.environ.get("INTERECAGENT_ROOT")
    if override:
        return os.path.abspath(override)
    here = os.path.abspath(__file__)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(here), "..", "..", "..", ".."))
    return os.path.join(
        repo_root,
        "application",
        "tasks",
        "recommender-agent_chat_api",
        "environment",
        "recommender-api",
        "recai",
        "InteRecAgent",
    )


def _bundle_check(interecagent_root: str, domain: str) -> Dict[str, Any]:
    """Validate one domain's real native bundle (settings.json + its files).

    Mirrors ``scripts.setup_recai_resources._verify_domain``: the bundle lives at
    ``<root>/resources/<domain>/`` and is valid when ``settings.json`` exists and
    every file it references (:data:`_BUNDLE_REFERENCED_KEYS`) is present on disk.
    Reported with a human-readable name; details never leak env-var names.
    """
    name = "Recommendation resources ({})".format(domain)
    domain_dir = os.path.join(interecagent_root, "resources", domain)
    settings_path = os.path.join(domain_dir, "settings.json")
    if not os.path.isfile(settings_path):
        return {
            "name": name,
            "ok": False,
            "detail": "Native resource bundle not installed for {}.".format(domain),
        }
    try:
        import json as _json

        with open(settings_path, "r", encoding="utf-8") as fh:
            settings = _json.load(fh)
    except (OSError, ValueError):
        return {
            "name": name,
            "ok": False,
            "detail": "Resource bundle for {} is unreadable or corrupt.".format(domain),
        }
    missing: List[str] = []
    for key in _BUNDLE_REFERENCED_KEYS:
        ref = settings.get(key) if isinstance(settings, dict) else None
        if not ref or not os.path.isfile(os.path.join(domain_dir, str(ref))):
            missing.append(str(ref) if ref else key)
    if missing:
        return {
            "name": name,
            "ok": False,
            "detail": "Resource bundle for {} is incomplete ({} missing).".format(
                domain, ", ".join(missing)
            ),
        }
    return {"name": name, "ok": True, "detail": "Native resource bundle installed."}


# --------------------------------------------------------------------------- #
# Static SPA
# --------------------------------------------------------------------------- #
def _web_dist_dir() -> str:
    """Absolute path to the built SPA directory (``<app>/frontend/dist``).

    The SPA now lives at ``<app>/frontend/dist``, a sibling of ``backend/``.
    Resolved via __file__: app.py -> api -> backend -> persona_eval.
    """
    here = os.path.abspath(__file__)
    # app.py -> api -> backend -> persona_eval (APP_ROOT)
    app_root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    return os.path.join(app_root, "frontend", "dist")


# --------------------------------------------------------------------------- #
# App factory
# --------------------------------------------------------------------------- #
def create_app(catalog_path: Optional[str] = None) -> FastAPI:
    """Construct and return a fully-wired :class:`FastAPI` application.

    Parameters
    ----------
    catalog_path:
        Override for the catalog ``items.jsonl`` location. When ``None`` the
        path is resolved from ``INTERECAGENT_CATALOG_PATH`` or the canonical
        default (a missing file is tolerated — the index is simply empty).
    """
    # --- shared singletons (stored on app.state.services) -------------- #
    state = build_state(catalog_path)

    # --- lifespan: release the job thread pool on shutdown ------------- #
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:  # pragma: no cover - lifecycle hook
            state.shutdown()

    app = FastAPI(
        title="PersonaEval API",
        version="0.1.0",
        summary="Developer harness API for persona-driven chatbot evaluation.",
        lifespan=lifespan,
    )
    app.state.services = state

    # --- CORS (Vite dev server) --------------------------------------- #
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ----------------------------- health ----------------------------- #
    @app.get("/api/health", response_model=schemas.HealthResponse, tags=["health"])
    def health() -> Dict[str, Any]:
        return {"status": "ok"}

    # ---------------------------- preflight --------------------------- #
    @app.get(
        "/api/preflight", response_model=schemas.PreflightResponse, tags=["health"]
    )
    def preflight(services: AppState = Depends(get_services)) -> Dict[str, Any]:
        # Per-domain browsable catalog sizes (each cached by get_bundle_catalog),
        # so the Catalog check shows every domain, not just the default (movie).
        domain_sizes: Dict[str, int] = {}
        for domain in _BUNDLE_DOMAINS:
            idx = services.catalog_for(domain)
            if getattr(idx, "available", False) and getattr(idx, "size", 0):
                domain_sizes[domain] = idx.size
        checks = preflight_checks(services.catalog, domain_sizes)
        # Optional adapters (finance/medical sidecars) report their status but
        # do not gate overall readiness — the core surfaces run without them.
        ready = all(c["ok"] for c in checks if not c.get("optional"))
        return {"ready": ready, "checks": checks}

    # ------------------------- config options ------------------------- #
    @app.get(
        "/api/config/options",
        response_model=schemas.ConfigOptionsResponse,
        tags=["config"],
    )
    def config_options(services: AppState = Depends(get_services)) -> Dict[str, Any]:
        return services.config.options()

    # ----------------------------- sessions --------------------------- #
    @app.post("/api/sessions", response_model=schemas.Session, tags=["sessions"])
    def create_session(
        body: schemas.CreateSessionRequest,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            session = services.manager.create(title=body.title, config=body.config)
        except ConfigError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return session.to_dict()

    @app.get(
        "/api/sessions",
        response_model=List[schemas.SessionSummary],
        tags=["sessions"],
    )
    def list_sessions(
        services: AppState = Depends(get_services),
    ) -> List[Dict[str, Any]]:
        return services.manager.list()

    @app.get(
        "/api/sessions/{session_id}",
        response_model=schemas.Session,
        tags=["sessions"],
    )
    def get_session(
        session_id: str, services: AppState = Depends(get_services)
    ) -> Dict[str, Any]:
        session = services.manager.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        return session.to_dict()

    @app.patch(
        "/api/sessions/{session_id}/config",
        response_model=schemas.PatchConfigResponse,
        tags=["sessions"],
    )
    def patch_config(
        session_id: str,
        body: schemas.PatchConfigRequest,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            result = services.manager.patch_config(session_id, body.config)
        except ConfigError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        if result is None:
            raise HTTPException(status_code=404, detail="session not found")
        return {
            "session": result["session"].to_dict(),
            "cacheInvalidated": bool(result["cacheInvalidated"]),
        }

    @app.delete("/api/sessions", tags=["sessions"])
    def clear_sessions(
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        """Delete every saved chat session (memory + disk)."""
        return {"deleted": services.manager.clear()}

    @app.delete("/api/sessions/{session_id}", tags=["sessions"])
    def delete_session(
        session_id: str,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        """Delete one chat session (memory + disk)."""
        if not services.manager.delete(session_id):
            raise HTTPException(status_code=404, detail="session not found")
        return {"deleted": session_id}

    @app.get("/api/sessions/{session_id}/export", tags=["sessions"])
    def export_session(
        session_id: str, services: AppState = Depends(get_services)
    ) -> JSONResponse:
        session = services.manager.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        filename = "personaeval-{}.json".format(session.id)
        return JSONResponse(
            content=session.to_dict(),
            headers={
                "Content-Disposition": 'attachment; filename="{}"'.format(filename)
            },
        )

    # ------------------------- turns & jobs --------------------------- #
    @app.post(
        "/api/sessions/{session_id}/turns",
        response_model=schemas.SubmitTurnResponse,
        tags=["turns"],
    )
    def submit_turn(
        session_id: str,
        body: schemas.SubmitTurnRequest,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        # `submit_turn` dispatches the blocking turn to the manager's threadpool
        # and returns immediately with a job id; backend failures surface later
        # as a job ``error``, not as a 500 here. The session/message are
        # validated up front so the client gets a clean 404 / 422.
        try:
            job_id = services.manager.submit_turn(session_id, body.message)
        except KeyError:
            raise HTTPException(status_code=404, detail="session not found")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return {"jobId": job_id}

    @app.get("/api/jobs/{job_id}", response_model=schemas.JobView, tags=["turns"])
    def get_job(
        job_id: str, services: AppState = Depends(get_services)
    ) -> Dict[str, Any]:
        view = services.manager.get_job(job_id)
        if view is None:
            raise HTTPException(status_code=404, detail="job not found")
        return view

    # ----------------------------- catalog ---------------------------- #
    @app.get(
        "/api/catalog/search",
        response_model=schemas.CatalogSearchResponse,
        tags=["catalog"],
    )
    def catalog_search(
        services: AppState = Depends(get_services),
        q: str = Query(default=""),
        genre: Optional[str] = Query(default=None),
        limit: int = Query(default=50, ge=0, le=500),
        domain: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        catalog = services.catalog_for(domain)
        items = catalog.search(q=q, genre=genre, limit=limit)
        total = catalog.count(q=q, genre=genre)
        return {
            "items": [catalog_item_view(it) for it in items],
            "total": total,
        }

    @app.get(
        "/api/catalog/items/{item_id}",
        response_model=schemas.CatalogItem,
        tags=["catalog"],
    )
    def catalog_item(
        item_id: str,
        services: AppState = Depends(get_services),
        domain: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        item = services.catalog_for(domain).get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="item not found")
        return catalog_item_view(item)

    # ---------------------------- PersonaEval ---------------------------- #
    @app.get(
        "/api/persona-eval/personas",
        response_model=schemas.PersonaEvalPersonasResponse,
        tags=["persona-eval"],
    )
    def persona_eval_personas(
        q: str = Query(default=""),
        limit: Optional[int] = Query(default=None, ge=1),
        domain: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        # Lazy-import the (stdlib-light) persona/SUT helpers so importing the app
        # stays cheap, mirroring the lazy backend import on the turn path.
        from persona_eval.persona import load_personas
        from persona_eval.sut_descriptions import sut_description_for

        # Persona is domain-free: the catalog is un-filtered, honoring an
        # optional substring search (``q``) and a result cap (``limit``).
        personas = [
            {
                "id": p.id,
                "name": p.name,
                "source": p.source,
                "blurb": _persona_blurb(p),
            }
            for p in load_personas(query=q, limit=limit)
        ]
        result: Dict[str, Any] = {"personas": personas}
        # ``sutDescription`` is returned only for an explicitly-passed domain
        # (the per-domain start flow still surfaces the SUT blurb).
        if domain is not None:
            try:
                result["sutDescription"] = sut_description_for(domain)
            except KeyError as exc:
                raise HTTPException(status_code=422, detail=str(exc))
        return result

    @app.get(
        "/api/persona-eval/personas/{persona_id}",
        response_model=schemas.PersonaEvalPersonaDetail,
        tags=["persona-eval"],
    )
    def persona_eval_persona_detail(persona_id: str) -> Dict[str, Any]:
        # The full, humanized persona context — what the catalog's "full
        # persona" view shows. The list ships only a short blurb; this is the
        # complete record. Lazy-import keeps app import cheap (see the list route).
        from persona_eval.persona import get_persona

        try:
            persona = get_persona(persona_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="persona not found")
        return {
            "id": persona.id,
            "name": persona.name,
            "source": persona.source,
            "context": persona.context,
        }

    @app.get(
        "/api/persona-eval/goal-contexts",
        response_model=schemas.GoalContextsResponse,
        tags=["persona-eval"],
    )
    def persona_eval_goal_contexts() -> Dict[str, Any]:
        from persona_eval.goal_contexts import load_goal_contexts

        return {
            "goalContexts": [
                {
                    "id": gc.id,
                    "label": gc.label,
                    "description": gc.description,
                }
                for gc in load_goal_contexts()
            ]
        }

    @app.post(
        "/api/persona-eval",
        response_model=schemas.SubmitPersonaEvalResponse,
        tags=["persona-eval"],
    )
    def start_persona_eval(
        body: schemas.StartPersonaEvalRequest,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        # `start` dispatches the persona-eval onto a daemon thread (serialized
        # process-globally) and returns a job id immediately; a bad
        # persona/domain pairing (or unknown persona) surfaces here as a 422.
        # `engine` selects the application chatbot base model. `personaModel`
        # selects the simulated-user base model. Omitted values fall back to
        # local defaults so existing callers keep working.
        engine = body.engine or ConfigManager.DEFAULTS["engine"]
        persona_model = body.personaModel or default_persona_model()
        run_domain = body.domain or body.applicationContext or ConfigManager.DEFAULTS["domain"]
        try:
            job_id = services.persona_eval.start(
                run_domain,
                body.personaId,
                body.maxTurns,
                body.goalContextId or "scenario_default",
                now=_utc_now,
                engine=engine,
                persona_model=persona_model,
                application_id=body.applicationId,
                application_context=body.applicationContext,
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return {"jobId": job_id}

    @app.get(
        "/api/persona-eval/runs",
        response_model=schemas.PersonaEvalRunsResponse,
        tags=["persona-eval"],
    )
    def list_persona_eval_runs(
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        return {"runs": services.persona_eval.list_runs()}

    @app.get(
        "/api/persona-eval/runs/{run_id}",
        response_model=schemas.PersonaEvalResultView,
        tags=["persona-eval"],
    )
    def get_persona_eval_run(
        run_id: str, services: AppState = Depends(get_services)
    ) -> Dict[str, Any]:
        run = services.persona_eval.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="persona-eval run not found")
        return run

    @app.get(
        "/api/persona-eval/jobs/{job_id}",
        response_model=schemas.PersonaEvalJobView,
        tags=["persona-eval"],
    )
    def get_persona_eval_job(
        job_id: str, services: AppState = Depends(get_services)
    ) -> Dict[str, Any]:
        view = services.persona_eval.view(job_id)
        if view is None:
            raise HTTPException(status_code=404, detail="persona-eval job not found")
        return view

    # ----------------------------- SurveyEval ----------------------------- #
    @app.get(
        "/api/survey-eval/instruments",
        response_model=schemas.SurveyInstrumentsResponse,
        tags=["survey-eval"],
    )
    def survey_eval_instruments(
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        return {"instruments": services.survey_eval.list_instruments()}

    @app.post(
        "/api/survey-eval",
        response_model=schemas.SubmitPersonaEvalResponse,
        tags=["survey-eval"],
    )
    def start_survey_eval(
        body: schemas.StartSurveyEvalRequest,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            job_id = services.survey_eval.start(
                persona_id=body.personaId,
                instrument_id=body.instrumentId,
                persona_model=body.personaModel,
                now=_utc_now,
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return {"jobId": job_id}

    @app.get(
        "/api/survey-eval/jobs/{job_id}",
        response_model=schemas.SurveyEvalJobView,
        tags=["survey-eval"],
    )
    def get_survey_eval_job(
        job_id: str, services: AppState = Depends(get_services)
    ) -> Dict[str, Any]:
        view = services.survey_eval.view(job_id)
        if view is None:
            raise HTTPException(status_code=404, detail="survey-eval job not found")
        return view

    # ------------------------------- WebEval ------------------------------ #
    @app.get(
        "/api/web-eval/tasks",
        response_model=schemas.WebEvalTasksResponse,
        tags=["web-eval"],
    )
    def web_eval_tasks(
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        return {"tasks": services.web_eval.list_tasks()}

    @app.post(
        "/api/web-eval",
        response_model=schemas.SubmitPersonaEvalResponse,
        tags=["web-eval"],
    )
    def start_web_eval(
        body: schemas.StartWebEvalRequest,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            job_id = services.web_eval.start(
                persona_id=body.personaId,
                task_id=body.taskId,
                persona_model=body.personaModel,
                now=_utc_now,
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return {"jobId": job_id}

    @app.get(
        "/api/web-eval/jobs/{job_id}",
        response_model=schemas.WebEvalJobView,
        tags=["web-eval"],
    )
    def get_web_eval_job(
        job_id: str, services: AppState = Depends(get_services)
    ) -> Dict[str, Any]:
        view = services.web_eval.view(job_id)
        if view is None:
            raise HTTPException(status_code=404, detail="web-eval job not found")
        return view

    @app.get(
        "/api/web-eval/jobs/{job_id}/screenshots/{filename:path}",
        tags=["web-eval"],
    )
    def get_web_eval_screenshot(
        job_id: str,
        filename: str,
        services: AppState = Depends(get_services),
    ) -> FileResponse:
        try:
            path = services.web_eval.screenshot_path(job_id, filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except KeyError:
            raise HTTPException(status_code=404, detail="web-eval job not found")
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="screenshot not found")
        media_type = "image/svg+xml" if path.suffix == ".svg" else "image/webp"
        return FileResponse(path, media_type=media_type)

    # --- static SPA (production single-origin) ------------------------- #
    # Mount LAST so it does not shadow the /api routes. Only when a build
    # exists; in dev the Vite server serves the SPA and proxies /api here.
    dist = _web_dist_dir()
    if os.path.isdir(dist):
        # Imported lazily so a missing build dir never costs an import.
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=dist, html=True), name="spa")

    return app


#: Module-level app instance used by the ``uvicorn backend.api.app:app`` entry.
app = create_app()
