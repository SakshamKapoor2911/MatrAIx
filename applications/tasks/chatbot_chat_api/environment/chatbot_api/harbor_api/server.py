"""Harbor-facing REST API for chatbot applications.

This module exposes a deliberately small synchronous chat contract for Harbor
persona agents. Internally it delegates to application adapters. The default
adapter is the existing RecBot / RecAI application; additional adapters share
the same session/message/conversation/application-result contract.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api.deps import build_state
from backend.service.config import ConfigError, ConfigManager

SUPPORTED_DOMAINS = tuple(ConfigManager.ALLOWED["domain"])
DEFAULT_APPLICATION_ID = "recai"
FINANCE_APPLICATION_ID = "finance_openbb"
SUPPORTED_APPLICATION_IDS = (DEFAULT_APPLICATION_ID, FINANCE_APPLICATION_ID)
FINANCE_CONTEXT = "financial_research"


class SessionRequest(BaseModel):
    """Create a Harbor chat session."""

    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = None
    application_id: str = Field(default=DEFAULT_APPLICATION_ID, alias="applicationId")
    application_context: Optional[str] = Field(default=None, alias="applicationContext")
    domain: str = ConfigManager.DEFAULTS["domain"]
    engine: Optional[str] = None
    botType: Optional[str] = None

    @field_validator("application_id")
    @classmethod
    def _known_application(cls, value: str) -> str:
        if value not in SUPPORTED_APPLICATION_IDS:
            raise ValueError(
                "applicationId must be one of: {}".format(
                    ", ".join(SUPPORTED_APPLICATION_IDS)
                )
            )
        return value

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
_ready_lock = threading.Lock()
_ready_keys: set[tuple[str, str]] = set()
_finance_application: Any = None
_finance_lock = threading.Lock()
_recai_turn_lock = threading.Lock()


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


def warm_recommender(domain: str) -> None:
    """Preload the native RecAI agent so health gating covers first-turn cost."""
    with _ready_lock:
        key = (DEFAULT_APPLICATION_ID, domain)
        if key in _ready_keys:
            return
        from recbot.interecagent_bridge import warmup

        warmup(domain)
        _ready_keys.add(key)


def _config_from_request(body: SessionRequest) -> Dict[str, str]:
    config: Dict[str, object] = {
        "applicationId": DEFAULT_APPLICATION_ID,
        "domain": body.domain,
    }
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
    for turn in reversed(turns):
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


def _grounded_items_from_turns(turns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    items: List[Dict[str, Any]] = []
    for turn in reversed(turns):
        raw_items = turn.get("groundedItems") or turn.get("recommendedItems") or []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("itemId", item.get("id"))
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
        with _recai_turn_lock:
            return state.manager.run_turn_sync(session_id, message)
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found")
    except Exception as exc:  # noqa: BLE001 - surface real RecBot failures cleanly.
        raise HTTPException(status_code=500, detail=str(exc))


def _request_context(body: SessionRequest) -> str:
    if body.application_context:
        return body.application_context
    if body.application_id == DEFAULT_APPLICATION_ID:
        return body.domain
    if body.application_id == FINANCE_APPLICATION_ID:
        return FINANCE_CONTEXT
    return body.domain


class RecAIApplication:
    application_id = DEFAULT_APPLICATION_ID
    default_context = ConfigManager.DEFAULTS["domain"]
    contexts = SUPPORTED_DOMAINS

    def ready(self, context: str) -> None:
        if context not in SUPPORTED_DOMAINS:
            raise HTTPException(
                status_code=422,
                detail="applicationContext must be one of: {}".format(
                    ", ".join(SUPPORTED_DOMAINS)
                ),
            )
        get_state()
        warm_recommender(context)

    def create_session(
        self,
        *,
        title: Optional[str],
        context: str,
        engine: Optional[str],
        bot_type: Optional[str],
    ) -> Dict[str, Any]:
        state = get_state()
        body = SessionRequest(
            title=title,
            applicationId=DEFAULT_APPLICATION_ID,
            domain=context,
            engine=engine,
            botType=bot_type,
        )
        config = _config_from_request(body)
        try:
            session = state.manager.create(title=title, config=config)
        except ConfigError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        payload = _session_payload(session)
        payload["applicationId"] = self.application_id
        payload["applicationContext"] = context
        return payload

    def send_message(
        self,
        *,
        session_id: Optional[str],
        message: str,
        title: Optional[str],
        context: str,
        engine: Optional[str],
        bot_type: Optional[str],
    ) -> Dict[str, Any]:
        if session_id:
            session = _get_session_or_404(session_id)
            resolved_session_id = session.id
        else:
            created = self.create_session(
                title=title,
                context=context,
                engine=engine,
                bot_type=bot_type,
            )
            resolved_session_id = created["sessionId"]

        turn = _run_turn(resolved_session_id, message)
        session = _get_session_or_404(resolved_session_id)
        recommended_items = turn.get("recommendedItems") or []
        return {
            "sessionId": resolved_session_id,
            "applicationId": self.application_id,
            "applicationContext": context,
            "reply": turn.get("assistantMessage") or "",
            "turn": turn,
            "recommendedItems": recommended_items,
            "groundedItems": turn.get("groundedItems") or recommended_items,
            "messages": [dict(chat_message) for chat_message in session.messages],
        }

    def conversation(self, *, session_id: str) -> Dict[str, Any]:
        session = _get_session_or_404(session_id)
        context = str(session.config.get("domain") or self.default_context)
        return {
            "sessionId": session.id,
            "applicationId": self.application_id,
            "applicationContext": context,
            "domain": context,
            "messages": [dict(message) for message in session.messages],
            "turns": [dict(turn) for turn in session.turns],
        }

    def recommendations(self, *, session_id: str) -> Dict[str, Any]:
        session = _get_session_or_404(session_id)
        turns = [dict(turn) for turn in session.turns]
        items = _grounded_items_from_turns(turns)
        context = str(session.config.get("domain") or self.default_context)
        return {
            "sessionId": session.id,
            "applicationId": self.application_id,
            "applicationContext": context,
            "domain": context,
            "recommendedItems": items,
            "groundedItems": items,
            "turnsToResult": len(turns),
            "total": len(items),
        }


def _finance_app() -> Any:
    global _finance_application
    with _finance_lock:
        if _finance_application is None:
            from harbor_api.finance_openbb import FinanceOpenBBApplication

            _finance_application = FinanceOpenBBApplication()
        return _finance_application


def get_application(application_id: str) -> Any:
    if application_id == DEFAULT_APPLICATION_ID:
        return RecAIApplication()
    if application_id == FINANCE_APPLICATION_ID:
        return _finance_app()
    raise HTTPException(
        status_code=422,
        detail="applicationId must be one of: {}".format(
            ", ".join(SUPPORTED_APPLICATION_IDS)
        ),
    )


def application_views() -> List[Dict[str, Any]]:
    return [
        {
            "applicationId": DEFAULT_APPLICATION_ID,
            "label": "RecAI / InteRecAgent",
            "defaultContext": ConfigManager.DEFAULTS["domain"],
            "contexts": list(SUPPORTED_DOMAINS),
        },
        {
            "applicationId": FINANCE_APPLICATION_ID,
            "label": "FinAI / OpenBB",
            "defaultContext": FINANCE_CONTEXT,
            "contexts": [FINANCE_CONTEXT],
        },
    ]


app = FastAPI(
    title="MatrAIx Chatbot Application API",
    version="1.0",
)


@app.get("/health")
@app.get("/v1/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "applications": application_views(),
        "supportedDomains": list(SUPPORTED_DOMAINS),
    }


@app.get("/ready")
@app.get("/v1/ready")
def ready(
    domain: str = Query(default=ConfigManager.DEFAULTS["domain"]),
    application_id: str = Query(default=DEFAULT_APPLICATION_ID, alias="applicationId"),
    application_context: Optional[str] = Query(default=None, alias="applicationContext"),
) -> Dict[str, Any]:
    if application_id not in SUPPORTED_APPLICATION_IDS:
        raise HTTPException(
            status_code=422,
            detail="applicationId must be one of: {}".format(
                ", ".join(SUPPORTED_APPLICATION_IDS)
            ),
        )
    context = application_context or (
        domain if application_id == DEFAULT_APPLICATION_ID else FINANCE_CONTEXT
    )
    try:
        get_application(application_id).ready(context)
    except Exception as exc:  # noqa: BLE001 - readiness should surface root cause.
        raise HTTPException(status_code=503, detail=str(exc))
    return {
        "status": "ready",
        "applicationId": application_id,
        "applicationContext": context,
        "domain": domain if application_id == DEFAULT_APPLICATION_ID else context,
    }


@app.post("/v1/session")
def create_session(body: SessionRequest) -> Dict[str, Any]:
    app_adapter = get_application(body.application_id)
    return app_adapter.create_session(
        title=body.title,
        context=_request_context(body),
        engine=body.engine,
        bot_type=body.botType,
    )


@app.post("/v1/messages")
def send_message(body: MessageRequest) -> Dict[str, Any]:
    app_adapter = get_application(body.application_id)
    return app_adapter.send_message(
        session_id=body.session_id,
        message=body.message,
        title=body.title,
        context=_request_context(body),
        engine=body.engine,
        bot_type=body.botType,
    )


@app.get("/v1/conversation")
def conversation(
    session_id: str = Query(alias="sessionId"),
    application_id: str = Query(default=DEFAULT_APPLICATION_ID, alias="applicationId"),
) -> Dict[str, Any]:
    return get_application(application_id).conversation(session_id=session_id)


@app.get("/v1/recommendations")
@app.get("/v1/application-result")
def recommendations(
    session_id: str = Query(alias="sessionId"),
    application_id: str = Query(default=DEFAULT_APPLICATION_ID, alias="applicationId"),
) -> Dict[str, Any]:
    return get_application(application_id).recommendations(session_id=session_id)
