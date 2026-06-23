"""Harbor-facing REST API for the RecBot recommendation application.

This module exposes a deliberately small synchronous chat contract for Harbor
persona agents. Internally it delegates to the existing RecBot service layer and
does not provide a mock or fallback recommender path.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api.deps import build_state
from backend.service.config import ConfigError, ConfigManager

SUPPORTED_DOMAINS = tuple(ConfigManager.ALLOWED["domain"])


class SessionRequest(BaseModel):
    """Create a Harbor chat session."""

    title: Optional[str] = None
    domain: str = ConfigManager.DEFAULTS["domain"]
    engine: Optional[str] = None
    botType: Optional[str] = None

    @field_validator("domain")
    @classmethod
    def _known_domain(cls, value: str) -> str:
        if value not in SUPPORTED_DOMAINS:
            raise ValueError(
                "domain must be one of: {}".format(", ".join(SUPPORTED_DOMAINS))
            )
        return value


class MessageRequest(SessionRequest):
    """Send one user message, creating a session when ``sessionId`` is omitted."""

    model_config = ConfigDict(populate_by_name=True)

    message: str
    session_id: Optional[str] = Field(default=None, alias="sessionId")

    @field_validator("message")
    @classmethod
    def _message_not_empty(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("message must not be empty")
        return text


_state_lock = threading.Lock()
_state: Any = None


def reset_state_for_tests() -> None:
    """Clear cached state for isolated API tests."""

    global _state
    with _state_lock:
        _state = None


def get_state() -> Any:
    """Return the process-wide RecBot application state."""

    global _state
    with _state_lock:
        if _state is None:
            _state = build_state()
        return _state


def _config_from_request(body: SessionRequest) -> Dict[str, str]:
    config: Dict[str, object] = {"domain": body.domain}
    if body.engine is not None:
        config["engine"] = body.engine
    if body.botType is not None:
        config["botType"] = body.botType
    try:
        return ConfigManager().normalize(config)
    except ConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _session_payload(session: Any) -> Dict[str, Any]:
    return {
        "sessionId": session.id,
        "config": dict(session.config),
        "session": session.to_dict(),
    }


def _get_session_or_404(session_id: str) -> Any:
    state = get_state()
    session = state.manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


def _recommended_items_from_turns(turns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    items: List[Dict[str, Any]] = []
    for turn in turns:
        for item in turn.get("recommendedItems") or []:
            if not isinstance(item, dict):
                continue
            item_id = item.get("itemId")
            if item_id is None:
                continue
            item_id = str(item_id)
            if item_id in seen:
                continue
            seen.add(item_id)
            normalized = dict(item)
            normalized["itemId"] = item_id
            items.append(normalized)
    return items


def _run_turn(session_id: str, message: str) -> Dict[str, Any]:
    state = get_state()
    try:
        return state.manager.run_turn_sync(session_id, message)
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - surface real RecBot failures cleanly.
        raise HTTPException(status_code=500, detail=str(exc))


app = FastAPI(
    title="MatrAIx Recommender Agent API",
    version="1.0",
)


@app.get("/health")
@app.get("/v1/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "supportedDomains": list(SUPPORTED_DOMAINS)}


@app.post("/v1/session")
def create_session(body: SessionRequest) -> Dict[str, Any]:
    state = get_state()
    config = _config_from_request(body)
    try:
        session = state.manager.create(title=body.title, config=config)
    except ConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _session_payload(session)


@app.post("/v1/messages")
def send_message(body: MessageRequest) -> Dict[str, Any]:
    if body.session_id:
        session = _get_session_or_404(body.session_id)
        session_id = session.id
    else:
        created = create_session(body)
        session_id = created["sessionId"]

    turn = _run_turn(session_id, body.message)
    session = _get_session_or_404(session_id)
    recommended_items = turn.get("recommendedItems") or []
    return {
        "sessionId": session_id,
        "reply": turn.get("assistantMessage") or "",
        "turn": turn,
        "recommendedItems": recommended_items,
        "messages": [dict(message) for message in session.messages],
    }


@app.get("/v1/conversation")
def conversation(session_id: str = Query(alias="sessionId")) -> Dict[str, Any]:
    session = _get_session_or_404(session_id)
    return {
        "sessionId": session.id,
        "messages": [dict(message) for message in session.messages],
        "turns": [dict(turn) for turn in session.turns],
    }


@app.get("/v1/recommendations")
def recommendations(session_id: str = Query(alias="sessionId")) -> Dict[str, Any]:
    session = _get_session_or_404(session_id)
    items = _recommended_items_from_turns([dict(turn) for turn in session.turns])
    return {
        "sessionId": session.id,
        "recommendedItems": items,
        "total": len(items),
    }
