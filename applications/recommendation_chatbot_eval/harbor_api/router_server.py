"""Lightweight Harbor chatbot API router.

The Harbor task always talks to a single service named ``chatbot-api``. This
router keeps that stable contract while letting each application adapter run in
the Python/runtime stack it actually needs.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Mapping, Optional

from fastapi import Body, FastAPI, HTTPException, Query

DEFAULT_APPLICATION_ID = "recai"
FINANCE_APPLICATION_ID = "finance_openbb"
SUPPORTED_APPLICATION_IDS = (DEFAULT_APPLICATION_ID, FINANCE_APPLICATION_ID)
SUPPORTED_DOMAINS = ("movie", "beauty_product", "game")
FINANCE_CONTEXT = "financial_research"

_session_lock = threading.RLock()
_session_applications: Dict[str, str] = {}


def reset_session_routes_for_tests() -> None:
    with _session_lock:
        _session_applications.clear()


def _upstream_base(application_id: str) -> str:
    if application_id == DEFAULT_APPLICATION_ID:
        return os.environ.get("CHATBOT_UPSTREAM_RECAI", "http://recai-api:8000").rstrip("/")
    if application_id == FINANCE_APPLICATION_ID:
        return os.environ.get(
            "CHATBOT_UPSTREAM_FINANCE", "http://finance-api:8000"
        ).rstrip("/")
    raise HTTPException(status_code=422, detail=_application_error())


def _application_error() -> str:
    return "applicationId must be one of: {}".format(
        ", ".join(SUPPORTED_APPLICATION_IDS)
    )


def _application_from_session(session_id: Optional[str]) -> Optional[str]:
    if not session_id:
        return None
    with _session_lock:
        return _session_applications.get(session_id)


def _remember_session(application_id: str, payload: Mapping[str, Any]) -> None:
    session_id = payload.get("sessionId")
    if session_id is None:
        return
    with _session_lock:
        _session_applications[str(session_id)] = application_id


def _application_from_body(body: Mapping[str, Any]) -> str:
    application_id = body.get("applicationId") or body.get("application_id")
    if not application_id:
        application_id = _application_from_session(
            str(body.get("sessionId") or body.get("session_id") or "") or None
        )
    application_id = str(application_id or DEFAULT_APPLICATION_ID)
    if application_id not in SUPPORTED_APPLICATION_IDS:
        raise HTTPException(status_code=422, detail=_application_error())
    return application_id


def _application_from_query(
    *,
    application_id: Optional[str],
    session_id: Optional[str] = None,
) -> str:
    resolved = application_id or _application_from_session(session_id)
    resolved = resolved or DEFAULT_APPLICATION_ID
    if resolved not in SUPPORTED_APPLICATION_IDS:
        raise HTTPException(status_code=422, detail=_application_error())
    return resolved


def _request_json(
    *,
    application_id: str,
    method: str,
    path: str,
    body: Optional[Mapping[str, Any]] = None,
    query: Optional[Mapping[str, Any]] = None,
    timeout: float = 180.0,
) -> Dict[str, Any]:
    base = _upstream_base(application_id)
    query_string = urllib.parse.urlencode(
        {key: value for key, value in (query or {}).items() if value is not None}
    )
    url = "{}{}{}".format(base, path, "?{}".format(query_string) if query_string else "")
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(dict(body)).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    last_error: Optional[BaseException] = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HTTPException(status_code=exc.code, detail=detail) from exc
        except urllib.error.URLError as exc:
            last_error = exc
        except TimeoutError as exc:
            last_error = exc
        if attempt < 5:
            time.sleep(2.0)
    else:
        if isinstance(last_error, urllib.error.URLError):
            raise HTTPException(
                status_code=503,
                detail="{} upstream unavailable: {}".format(
                    application_id, last_error.reason
                ),
            ) from last_error
        raise HTTPException(
            status_code=503,
            detail="{} upstream timed out".format(application_id),
        ) from last_error
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail="{} upstream returned invalid JSON".format(application_id),
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=502,
            detail="{} upstream returned non-object JSON".format(application_id),
        )
    return payload


def _application_views() -> list[Dict[str, Any]]:
    return [
        {
            "applicationId": DEFAULT_APPLICATION_ID,
            "label": "RecAI / InteRecAgent",
            "defaultContext": "movie",
            "contexts": list(SUPPORTED_DOMAINS),
            "upstream": "recai-api",
        },
        {
            "applicationId": FINANCE_APPLICATION_ID,
            "label": "FinAI / OpenBB",
            "defaultContext": FINANCE_CONTEXT,
            "contexts": [FINANCE_CONTEXT],
            "upstream": "finance-api",
        },
    ]


app = FastAPI(title="MatrAIx Chatbot Application Router", version="1.0")


def _json_body(body: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")
    return dict(body)


@app.get("/health")
@app.get("/v1/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "applications": _application_views(),
        "supportedDomains": list(SUPPORTED_DOMAINS),
    }


@app.get("/ready")
@app.get("/v1/ready")
def ready(
    domain: str = Query(default="movie"),
    application_id: str = Query(default=DEFAULT_APPLICATION_ID, alias="applicationId"),
    application_context: Optional[str] = Query(default=None, alias="applicationContext"),
) -> Dict[str, Any]:
    resolved = _application_from_query(application_id=application_id)
    return _request_json(
        application_id=resolved,
        method="GET",
        path="/ready",
        query={
            "domain": domain,
            "applicationId": resolved,
            "applicationContext": application_context,
        },
    )


@app.post("/v1/session")
def create_session(
    body_payload: Optional[Dict[str, Any]] = Body(default=None),
) -> Dict[str, Any]:
    body = _json_body(body_payload)
    application_id = _application_from_body(body)
    payload = _request_json(
        application_id=application_id,
        method="POST",
        path="/v1/session",
        body=body,
    )
    _remember_session(application_id, payload)
    return payload


@app.post("/v1/messages")
def send_message(
    body_payload: Optional[Dict[str, Any]] = Body(default=None),
) -> Dict[str, Any]:
    body = _json_body(body_payload)
    application_id = _application_from_body(body)
    payload = _request_json(
        application_id=application_id,
        method="POST",
        path="/v1/messages",
        body=body,
    )
    _remember_session(application_id, payload)
    return payload


@app.get("/v1/conversation")
def conversation(
    session_id: str = Query(alias="sessionId"),
    application_id: Optional[str] = Query(default=None, alias="applicationId"),
) -> Dict[str, Any]:
    resolved = _application_from_query(
        application_id=application_id, session_id=session_id
    )
    return _request_json(
        application_id=resolved,
        method="GET",
        path="/v1/conversation",
        query={"sessionId": session_id, "applicationId": resolved},
    )


@app.get("/v1/recommendations")
@app.get("/v1/application-result")
def application_result(
    session_id: str = Query(alias="sessionId"),
    application_id: Optional[str] = Query(default=None, alias="applicationId"),
) -> Dict[str, Any]:
    resolved = _application_from_query(
        application_id=application_id, session_id=session_id
    )
    return _request_json(
        application_id=resolved,
        method="GET",
        path="/v1/application-result",
        query={"sessionId": session_id, "applicationId": resolved},
    )
