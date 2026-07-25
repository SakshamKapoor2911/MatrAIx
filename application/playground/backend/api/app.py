"""The Playground FastAPI application.

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

(or ``bash application/playground/backend/run_dev.sh``).

Importing this module is cheap: it does NOT import RecAI / numpy / pandas. The
heavyweight ``recbot.interecagent_bridge.run_turn`` is lazy-imported inside the
service only when a turn actually runs, so importing the app (and the tests)
needs just FastAPI + pydantic. Catalog loading uses stdlib ``json`` only.
"""

from __future__ import annotations

import datetime as _dt
import os
import subprocess
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

# Importing backend.api wires the eval package dir onto sys.path so the lazy
# `import recbot...` resolves later (and so `import backend...` works at all).
import backend.api  # noqa: F401  (side effect: sys.path wiring)
from backend.api import schemas
from backend.api.deps import AppState, build_state, state_from_request

__all__ = ["create_app", "app", "preflight_checks", "catalog_item_view"]

#: Origins allowed to call the API cross-origin (the Vite dev server).
DEV_ORIGINS: List[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class _NoCacheIndexMiddleware(BaseHTTPMiddleware):
    """Prevent browsers from serving a stale SPA shell after frontend rebuilds."""

    async def dispatch(self, request: StarletteRequest, call_next):
        response: StarletteResponse = await call_next(request)
        if request.url.path in {"", "/", "/index.html"}:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response


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


def _sidecar_reachable(base_url: str, timeout: float = 5.0) -> bool:
    """True if a chatbot sidecar answers ``GET /ready`` with a 2xx.

    ``/ready`` means capability readiness (declared chat paths can load), not
    mere process liveness. Refused connections fail quickly; cold medical
    imports may need a few seconds on first probe.
    """
    url = "{}/ready".format(base_url.rstrip("/"))
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            return 200 <= int(status) < 300
    except Exception:  # noqa: BLE001 - any failure means "not ready"
        return False


def _docker_daemon_ok(timeout: float = 2.0) -> bool:
    """True if the local Docker CLI can talk to a running daemon."""
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def preflight_checks() -> List[Dict[str, Any]]:
    """Compute the user-facing, interface-aware readiness checklist.

    Reports each probe as ``{"group", "name", "ok", "detail"}`` regardless of
    pass/fail, so the UI can group the overall readiness of the whole system —
    not just the RecAI recommender — in plain language. Groups:

    * **Core** — model credentials (any run needs these).
    * **Chatbot** — the RecAI recommender (engine + its native resource bundles,
      collapsed across domains), plus the OpenBB and Medical adapters, which are
      selectable but whose external services are verified at run time.
    * **Survey** / **Web** / **OS app** — the other application interfaces,
      available to run.

    Check *names* are human-readable and never echo raw environment-variable
    names. Inspection is filesystem-only except for a short ``/ready`` probe of
    the optional chatbot sidecars; it never imports RecAI or any application
    backend.
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

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    checks.append(
        {
            "group": "Core",
            "name": "Anthropic credentials",
            "ok": bool(anthropic_key),
            "detail": (
                "Configured."
                if anthropic_key
                else "Not configured. Required for Anthropic persona models."
            ),
        }
    )

    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
    checks.append(
        {
            "group": "Core",
            "name": "DashScope (Qwen / DeepSeek)",
            "ok": bool(dashscope_key),
            "optional": True,
            "detail": (
                "Configured."
                if dashscope_key
                else "Not configured. Required for DashScope persona models "
                "(Qwen, DeepSeek via OpenAI-compatible API)."
            ),
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

    from backend.service.chatbot_sidecar_service import (
        resolve_health_url,
        sidecar_port_reachable,
        sidecar_reachable,
    )

    recai_url = resolve_health_url("recai")
    recai_api_ok = sidecar_reachable(recai_url)
    checks.append(
        {
            "group": "Chatbot",
            "name": "RecAI chat API",
            "ok": recai_api_ok,
            "optional": True,
            "applicationId": "recai",
            "detail": (
                "RecAI chat API ready at {}.".format(recai_url)
                if recai_api_ok
                else "RecAI chat API not ready at {}. Start it before a Harbor chat run.".format(
                    recai_url
                )
            ),
        }
    )

    # The finance/medical adapters route to HTTP sidecars. Probe each one's
    # /ready so readiness reflects full capability readiness (not just liveness).
    # Marked optional: a down sidecar shows here but does not gate overall
    # readiness (RecAI / Survey / Web still run without them).
    from playground.inprocess.chatbot_eval import _sidecar_base_url

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
            "applicationId": "finance_openbb",
            "detail": (
                "Finance sidecar ready at {}.".format(finance_url)
                if finance_ok
                else "Finance sidecar not ready at {}. Start it to run a finance chat.".format(
                    finance_url
                )
            ),
        }
    )
    medical_url = _sidecar_base_url(
        "CHATBOT_UPSTREAM_MEDICAL", "MEDICAL_CHATBOT_URL", "http://127.0.0.1:8902"
    )
    medical_ok = _sidecar_reachable(medical_url, timeout=10.0)
    checks.append(
        {
            "group": "Chatbot",
            "name": "Medical assistant",
            "ok": medical_ok,
            "optional": True,
            "applicationId": "medical_assistant",
            "detail": (
                "Medical sidecar ready at {}.".format(medical_url)
                if medical_ok
                else "Medical sidecar not ready at {}. Start it to run a medical chat.".format(
                    medical_url
                )
            ),
        }
    )

    mcp_url = resolve_health_url("acme_support_mcp")
    mcp_ok = sidecar_port_reachable("127.0.0.1", 8903)
    checks.append(
        {
            "group": "Chatbot",
            "name": "Acme MCP support",
            "ok": mcp_ok,
            "optional": True,
            "applicationId": "acme_support_mcp",
            "detail": (
                "MCP server ready at {}.".format(mcp_url)
                if mcp_ok
                else "MCP server not ready at {}. Start it to run the MCP chat task.".format(
                    mcp_url
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
            "detail": "Browser interface available. It runs when you start a web task.",
        }
    )

    docker_ok = _docker_daemon_ok()
    checks.append(
        {
            "group": "OS app",
            "name": "Docker",
            "ok": docker_ok,
            "optional": True,
            "detail": (
                "Docker daemon reachable."
                if docker_ok
                else "Docker not running. Required for Linux and web OS-app tasks."
            ),
        }
    )
    use_computer_key = (os.environ.get("USE_COMPUTER_API_KEY") or "").strip()
    checks.append(
        {
            "group": "OS app",
            "name": "use.computer API",
            "ok": bool(use_computer_key),
            "optional": True,
            "detail": (
                "Configured."
                if use_computer_key
                else "Not configured. Required for macOS and iOS OS-app tasks."
            ),
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
    return {
        "group": "Chatbot",
        "name": "RecAI resources",
        "ok": ok,
        "optional": True,
        "detail": detail,
    }


def _interecagent_root() -> str:
    """Absolute path to the RecAI engine root used for resource validation.

    Honors an ``INTERECAGENT_ROOT`` override (the bridge reads the same var) and
    otherwise falls back to the task-environment ``recai/InteRecAgent`` checkout
    (sparse-cloned on demand via ``scripts/setup_recai_resources.py``). The
    fallback is computed straight from this module's location so it is unaffected
    by a faked ``recbot`` package in tests.
    """
    override = os.environ.get("INTERECAGENT_ROOT")
    if override:
        return os.path.abspath(override)
    from backend.service.task_environment import resolve_chat_endpoint_host_dir

    repo_root = Path(__file__).resolve().parents[4]
    task_dir = repo_root / "application" / "tasks" / "chat_recai"
    host_dir = resolve_chat_endpoint_host_dir(task_dir)
    if host_dir is None:
        base = (
            repo_root
            / "environment"
            / "task-environments"
            / "application"
            / "chatbot-api-sidecar_recai"
            / "recommender-api"
        )
    else:
        candidate = host_dir / "recommender-api"
        base = candidate if candidate.is_dir() else host_dir
    return str(base / "recai" / "InteRecAgent")


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
    Resolved via __file__: app.py -> api -> backend -> playground.
    """
    here = os.path.abspath(__file__)
    # app.py -> api -> backend -> playground (APP_ROOT)
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
        title="Playground API",
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
    app.add_middleware(_NoCacheIndexMiddleware)

    # ----------------------------- health ----------------------------- #
    @app.get("/api/health", response_model=schemas.HealthResponse, tags=["health"])
    def health() -> Dict[str, Any]:
        return {"status": "ok"}

    # ---------------------------- preflight --------------------------- #
    @app.get(
        "/api/preflight", response_model=schemas.PreflightResponse, tags=["health"]
    )
    def preflight() -> Dict[str, Any]:
        checks = preflight_checks()
        # Optional adapters (finance/medical sidecars) report their status but
        # do not gate overall readiness — the core surfaces run without them.
        ready = all(c["ok"] for c in checks if not c.get("optional"))
        return {"ready": ready, "checks": checks}

    @app.get(
        "/api/chatbot-sidecars",
        response_model=schemas.ChatbotSidecarsResponse,
        tags=["health"],
    )
    def chatbot_sidecars() -> Dict[str, Any]:
        from backend.service.chatbot_sidecar_service import list_sidecar_statuses

        return {"sidecars": list_sidecar_statuses()}

    @app.post(
        "/api/chatbot-sidecars/{application_id}/start",
        response_model=schemas.StartChatbotSidecarResponse,
        tags=["health"],
    )
    def start_chatbot_sidecar(application_id: str) -> Dict[str, Any]:
        from backend.service.chatbot_sidecar_service import start_sidecar

        if application_id not in schemas.SUPPORTED_APPLICATION_IDS:
            raise HTTPException(status_code=404, detail="unknown chatbot application")
        try:
            sidecar = start_sidecar(application_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"sidecar": sidecar, "started": bool(sidecar.get("started"))}

    # ------------------------- config options ------------------------- #
    @app.get(
        "/api/config/options",
        response_model=schemas.ConfigOptionsResponse,
        tags=["config"],
    )
    def config_options(services: AppState = Depends(get_services)) -> Dict[str, Any]:
        return services.config.options()

    # ---------------------------- Playground ---------------------------- #
    @app.get(
        "/api/playground/personas",
        response_model=schemas.PlaygroundPersonasResponse,
        tags=["playground"],
    )
    def playground_personas(
        q: str = Query(default=""),
        limit: Optional[int] = Query(default=None, ge=1),
        domain: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        # Lazy-import the stdlib-light persona helpers so importing the app stays
        # cheap, mirroring the lazy backend import on the turn path.
        from playground.persona_catalog import load_personas

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
        # ``domain`` is accepted for backwards compatibility with older clients
        # that still scope persona search by chat domain. Task-backed chatbot
        # flows now source SUT context from task content instead of a global
        # domain registry, so no domain-specific blurb is returned here.
        if domain is not None:
            result["sutDescription"] = None
        return result

    @app.get(
        "/api/playground/personas/{persona_id}",
        response_model=schemas.PlaygroundPersonaDetail,
        tags=["playground"],
    )
    def playground_persona_detail(persona_id: str) -> Dict[str, Any]:
        # The full, humanized persona context — what the catalog's "full
        # persona" view shows. The list ships only a short blurb; this is the
        # complete record. Lazy-import keeps app import cheap (see the list route).
        from playground.persona_catalog import get_persona

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

    # ----------------------------- Harbor batch jobs ---------------------- #
    @app.get(
        "/api/harbor/jobs",
        response_model=schemas.HarborJobsListResponse,
        tags=["harbor-jobs"],
    )
    def list_harbor_jobs(services: AppState = Depends(get_services)) -> Dict[str, Any]:
        return {"jobs": services.harbor_jobs.list_jobs()}

    @app.get(
        "/api/harbor/jobs/{job_name}",
        response_model=schemas.HarborJobDetailView,
        tags=["harbor-jobs"],
    )
    def get_harbor_job(
        job_name: str, services: AppState = Depends(get_services)
    ) -> Dict[str, Any]:
        job = services.harbor_jobs.get_job(job_name)
        if job is None:
            raise HTTPException(status_code=404, detail="harbor job not found")
        return job

    @app.get(
        "/api/harbor/jobs/{job_name}/aggregation",
        tags=["harbor-jobs"],
    )
    def get_harbor_job_aggregation(
        job_name: str, services: AppState = Depends(get_services)
    ) -> Dict[str, Any]:
        try:
            return services.harbor_jobs.get_job_aggregation(job_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/api/harbor/jobs/{job_name}/report.pdf",
        tags=["harbor-jobs"],
    )
    def download_harbor_job_report_pdf(
        job_name: str, services: AppState = Depends(get_services)
    ):
        from fastapi.responses import Response

        from backend.service.report_pdf import build_batch_report_pdf, pdf_filename

        job = services.harbor_jobs.get_job(job_name)
        if job is None:
            raise HTTPException(status_code=404, detail="harbor job not found")
        try:
            aggregation = services.harbor_jobs.get_job_aggregation(job_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        payload = build_batch_report_pdf(
            job_name=job_name,
            job=job,
            aggregation=aggregation,
        )
        filename = pdf_filename(job_name, "batch-report")
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.delete(
        "/api/harbor/jobs/{job_name}",
        tags=["harbor-jobs"],
    )
    def delete_harbor_job(
        job_name: str, services: AppState = Depends(get_services)
    ) -> Dict[str, Any]:
        try:
            services.harbor_jobs.delete_job(job_name)
        except ValueError as exc:
            message = str(exc)
            status = 404 if "not found" in message.lower() else 400
            raise HTTPException(status_code=status, detail=message) from exc
        return {"deleted": True, "jobName": job_name}

    @app.post(
        "/api/harbor/jobs",
        response_model=schemas.HarborJobLaunchResponse,
        tags=["harbor-jobs"],
    )
    def launch_harbor_job(
        body: schemas.HarborJobLaunchRequest,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        from backend.service.harbor_job_service import (
            _read_task_metadata_type,
            resolve_agent_name,
            resolve_trial_profile,
        )

        from backend.service.execution_plane import normalize_execution_plane
        from backend.service.config import default_execution_plane

        try:
            trial_profile = resolve_trial_profile(
                body.taskPath,
                mode=body.mode,
                repo_root=services.harbor_jobs.repo_root,
            )
            agent_name = resolve_agent_name(
                body.taskPath,
                repo_root=services.harbor_jobs.repo_root,
                explicit=body.agentName,
                mode=body.mode,
                trial_profile=trial_profile,
            )
            resolved_plane = normalize_execution_plane(
                body.plane or default_execution_plane()
            )
            job_name = services.harbor_jobs.launch(
                task_path=body.taskPath,
                sample_size=body.sampleSize,
                seed=body.seed,
                persona_pool=body.personaPool,
                persona_ids=body.personaIds,
                agent_name=agent_name,
                persona_model=body.personaModel,
                n_concurrent_trials=body.nConcurrentTrials,
                execution_mode=body.mode,
                execution_plane=resolved_plane,
                job_name=body.jobName,
                os_app_submission_profile=body.osAppSubmissionProfile,
                os_app_backend=body.osAppBackend,
                chat_domain=body.chatDomain,
                chat_application_id=body.chatApplicationId,
                chat_application_context=body.chatApplicationContext,
                chat_max_turns=body.chatMaxTurns,
                persona_sources=body.personaSources,
                persona_filters=body.personaFilters,
                cohort_id=body.cohortId,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        job_detail = services.harbor_jobs.get_job(job_name)
        launch = job_detail.get("launch") if isinstance(job_detail, dict) else None
        config_path = launch.get("configPath") if isinstance(launch, dict) else None
        return {
            "jobName": job_name,
            "configPath": config_path,
            "jobsDir": job_detail.get("jobsDir") if isinstance(job_detail, dict) else None,
            "agentName": agent_name,
            "taskType": _read_task_metadata_type(body.taskPath, repo_root=services.harbor_jobs.repo_root),
            "trialProfile": trial_profile,
            "mode": body.mode,
            "plane": resolved_plane,
        }

    @app.get(
        "/api/harbor/jobs/{job_name}/live",
        tags=["harbor-jobs"],
    )
    def get_harbor_job_live(
        job_name: str,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.harbor_jobs.get_job_live(job_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/api/harbor/jobs/{job_name}/retry-failed",
        tags=["harbor-jobs"],
    )
    def retry_harbor_job_failed(
        job_name: str, services: AppState = Depends(get_services)
    ) -> Dict[str, Any]:
        try:
            return services.harbor_jobs.retry_failed(job_name)
        except ValueError as exc:
            message = str(exc)
            status = 404 if "not found" in message.lower() else 400
            raise HTTPException(status_code=status, detail=message) from exc

    @app.get(
        "/api/harbor/jobs/{job_name}/status",
        tags=["harbor-jobs"],
    )
    def get_harbor_job_status(
        job_name: str,
        since: int = Query(default=0, ge=0),
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.harbor_jobs.get_job_status(job_name, since=since)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/api/harbor/jobs/{job_name}/trials/{trial_name}/events",
        tags=["harbor-jobs"],
    )
    def get_harbor_trial_events(
        job_name: str,
        trial_name: str,
        after: int = Query(default=0, ge=0),
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.harbor_jobs.get_trial_events(
                job_name,
                trial_name,
                after=after,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/api/harbor/jobs/{job_name}/trials/{trial_name}/debrief",
        tags=["harbor-jobs"],
    )
    def get_harbor_trial_debrief(
        job_name: str,
        trial_name: str,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.harbor_jobs.get_trial_debrief(job_name, trial_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/api/harbor/jobs/{job_name}/trials/{trial_name}/report.pdf",
        tags=["harbor-jobs"],
    )
    def download_harbor_trial_report_pdf(
        job_name: str,
        trial_name: str,
        services: AppState = Depends(get_services),
    ):
        from fastapi.responses import Response

        from backend.service.report_pdf import build_trial_report_pdf, pdf_filename

        try:
            debrief = services.harbor_jobs.get_trial_debrief(job_name, trial_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        payload = build_trial_report_pdf(
            job_name=job_name,
            trial_name=trial_name,
            debrief=debrief,
        )
        filename = pdf_filename(job_name, trial_name, "trial-report")
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get(
        "/api/harbor/jobs/{job_name}/trials/{trial_name}/instruction",
        tags=["harbor-jobs"],
    )
    def get_harbor_trial_instruction(
        job_name: str,
        trial_name: str,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.harbor_jobs.get_trial_instruction(job_name, trial_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/api/harbor/jobs/{job_name}/trials/{trial_name}/trace",
        tags=["harbor-jobs"],
    )
    def get_harbor_trial_trace(
        job_name: str,
        trial_name: str,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.harbor_jobs.get_trial_web_trace(job_name, trial_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/api/harbor/jobs/{job_name}/trials/{trial_name}/screenshots/{filename:path}",
        tags=["harbor-jobs"],
    )
    def get_harbor_trial_screenshot(
        job_name: str,
        trial_name: str,
        filename: str,
        services: AppState = Depends(get_services),
    ) -> FileResponse:
        try:
            path = services.harbor_jobs.trial_screenshot_path(job_name, trial_name, filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="screenshot not found") from exc
        media = "image/png"
        lower = filename.lower()
        if lower.endswith(".webp"):
            media = "image/webp"
        elif lower.endswith(".svg"):
            media = "image/svg+xml"
        elif lower.endswith(".jpg") or lower.endswith(".jpeg"):
            media = "image/jpeg"
        return FileResponse(path, media_type=media)

    @app.get(
        "/api/harbor/jobs/{job_name}/trials/{trial_name}/live-screenshot",
        tags=["harbor-jobs"],
    )
    def get_harbor_trial_live_screenshot(
        job_name: str,
        trial_name: str,
        services: AppState = Depends(get_services),
    ):
        from starlette.responses import Response as StarletteResp

        try:
            png = services.harbor_jobs.trial_live_screenshot(job_name, trial_name)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail="screenshot unavailable") from exc
        return StarletteResp(
            content=png,
            media_type="image/png",
            headers={
                "Cache-Control": "no-store",
                "Content-Length": str(len(png)),
            },
        )

    @app.get(
        "/api/harbor/jobs/{job_name}/trials/{trial_name}/recording",
        tags=["harbor-jobs"],
    )
    def get_harbor_trial_recording(
        job_name: str,
        trial_name: str,
        services: AppState = Depends(get_services),
    ) -> FileResponse:
        try:
            path = services.harbor_jobs.trial_recording_path(job_name, trial_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="recording not found") from exc
        return FileResponse(path, media_type="video/mp4", filename="recording.mp4")

    @app.get(
        "/api/persona-pool/datasets",
        response_model=schemas.PersonaDatasetListResponse,
        tags=["persona-pool"],
    )
    def list_persona_datasets(
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        return {
            "datasets": services.persona_pool.list_datasets(),
            "defaultPool": "persona/datasets/bench-dev-sample",
        }

    @app.get(
        "/api/persona-pool/ids",
        response_model=schemas.PersonaPoolIdsResponse,
        tags=["persona-pool"],
    )
    def list_persona_pool_ids(
        pool: str = Query(default="persona/datasets/bench-dev-sample"),
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.persona_pool.list_persona_ids(pool)
        except (ValueError, FileNotFoundError, OSError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/api/persona-pool/catalog",
        response_model=schemas.PersonaPoolCatalogResponse,
        tags=["persona-pool"],
    )
    def get_persona_pool_catalog(
        pool: str = Query(default="persona/datasets/bench-dev-sample"),
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.persona_pool.get_catalog(pool)
        except (ValueError, FileNotFoundError, OSError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/api/persona-pool/sample",
        response_model=schemas.PersonaPoolSampleResponse,
        tags=["persona-pool"],
    )
    def sample_persona_pool(
        body: schemas.PersonaPoolSampleRequest,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.persona_pool.sample_pool(
                persona_pool=body.pool,
                sample_size=body.sampleSize,
                seed=body.seed,
                sources=body.sources,
                dimension_filters=body.dimensionFilters,
                stratify_fields=body.stratifyFields,
                sample_size_per_value_group=body.sampleSizePerValueGroup,
                task_path=body.taskPath,
                auto_ensure_strategy_pool=body.autoEnsureStrategyPool,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get(
        "/api/persona-pool/personas",
        tags=["persona-pool"],
    )
    def list_persona_pool_cards(
        pool: str = Query(default="persona/datasets/bench-dev-sample"),
        limit: int = Query(default=10, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        seed: int = Query(default=42),
        persona_ids: Optional[str] = Query(default=None, alias="personaIds"),
        detail: bool = Query(default=False),
        all: bool = Query(default=False, alias="all"),
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        ids = [part.strip() for part in (persona_ids or "").split(",") if part.strip()]
        try:
            if detail and len(ids) == 1:
                return services.persona_pool.get_persona_detail(ids[0], persona_pool=pool)
            return services.persona_pool.list_persona_cards(
                persona_pool=pool,
                limit=limit,
                offset=offset,
                persona_ids=ids or None,
                seed=seed,
                all_personas=all,
            )
        except (ValueError, FileNotFoundError, OSError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/api/persona-pool/personas/{persona_id}",
        response_model=schemas.PersonaPoolPersonaDetailResponse,
        tags=["persona-pool"],
    )
    def get_persona_pool_persona(
        persona_id: str,
        pool: str = Query(default="persona/datasets/bench-dev-sample"),
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.persona_pool.get_persona_detail(persona_id, persona_pool=pool)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get(
        "/api/tasks/detail",
        response_model=schemas.TaskDetailResponse,
        tags=["tasks"],
    )
    def get_task_detail(
        task_path: str = Query(..., alias="taskPath"),
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        from backend.service.task_detail_service import get_task_detail as load_task_detail

        try:
            return load_task_detail(task_path, repo_root=services.harbor_jobs.repo_root)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get(
        "/api/tasks/persona-strategy",
        response_model=schemas.TaskPersonaStrategyResponse,
        tags=["tasks"],
    )
    def get_task_persona_strategy(
        task_path: str = Query(..., alias="taskPath"),
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        from backend.service.task_persona_strategy_service import (
            get_task_persona_strategy as load_task_persona_strategy,
        )

        try:
            strategy = load_task_persona_strategy(
                task_path,
                repo_root=services.harbor_jobs.repo_root,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"personaStrategy": strategy}

    @app.get(
        "/api/persona-pool/cohorts",
        response_model=schemas.PersonaCohortListResponse,
        tags=["persona-pool"],
    )
    def list_persona_cohorts(
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        return {"cohorts": services.persona_pool.list_cohorts()}

    @app.get(
        "/api/persona-pool/cohorts/{cohort_id}",
        response_model=schemas.PersonaCohortDetailResponse,
        tags=["persona-pool"],
    )
    def get_persona_cohort(
        cohort_id: str,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.persona_pool.get_cohort(cohort_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/api/persona-pool/cohorts",
        response_model=schemas.PersonaCohortDetailResponse,
        tags=["persona-pool"],
    )
    def save_persona_cohort(
        body: schemas.PersonaCohortSaveRequest,
        services: AppState = Depends(get_services),
    ) -> Dict[str, Any]:
        try:
            return services.persona_pool.save_cohort(
                cohort_id=body.cohortId,
                name=body.name,
                description=body.description,
                pool=body.pool,
                kind=body.kind,  # type: ignore[arg-type]
                seed=body.seed,
                sample_size=body.sampleSize,
                sources=body.sources,
                dimension_filters=body.dimensionFilters,
                persona_ids=body.personaIds,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    # ----------------------------- SurveyEval ----------------------------- #
    @app.get(
        "/api/survey-eval/instruments",
        response_model=schemas.SurveyInstrumentsResponse,
        tags=["survey-eval"],
    )
    def survey_eval_instruments(services: AppState = Depends(get_services)) -> Dict[str, Any]:
        from backend.service.survey_questionnaire_catalog import list_survey_questionnaires

        return {"instruments": list_survey_questionnaires(repo_root=services.harbor_jobs.repo_root)}

    @app.get(
        "/api/survey-eval/harbor-tasks",
        response_model=schemas.SurveyHarborTasksResponse,
        tags=["survey-eval"],
    )
    def survey_eval_harbor_tasks(services: AppState = Depends(get_services)) -> Dict[str, Any]:
        from backend.service.survey_harbor_tasks import list_survey_harbor_tasks

        return {"tasks": [task.to_summary_dict() for task in list_survey_harbor_tasks()]}

    # ----------------------------- Chatbot eval --------------------------- #
    @app.get(
        "/api/chatbot-eval/tasks",
        response_model=schemas.ChatbotEvalTasksResponse,
        tags=["chatbot-eval"],
    )
    def chatbot_eval_tasks(services: AppState = Depends(get_services)) -> Dict[str, Any]:
        from backend.service.chatbot_tasks import list_chatbot_eval_tasks

        return {"tasks": [task.to_summary_dict() for task in list_chatbot_eval_tasks()]}

    # ------------------------------- WebEval ------------------------------ #
    @app.get(
        "/api/web-eval/tasks",
        response_model=schemas.WebEvalTasksResponse,
        tags=["web-eval"],
    )
    def web_eval_tasks(services: AppState = Depends(get_services)) -> Dict[str, Any]:
        from backend.service.web_tasks import list_web_eval_tasks

        return {"tasks": [task.to_summary_dict() for task in list_web_eval_tasks()]}

    # ----------------------------- OS app eval ---------------------------- #
    @app.get(
        "/api/os-app-eval/tasks",
        response_model=schemas.OsAppEvalTasksResponse,
        tags=["os-app-eval"],
    )
    def os_app_eval_tasks(services: AppState = Depends(get_services)) -> Dict[str, Any]:
        from backend.service.os_app_tasks import list_os_app_eval_tasks

        return {"tasks": [task.to_summary_dict() for task in list_os_app_eval_tasks()]}

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
