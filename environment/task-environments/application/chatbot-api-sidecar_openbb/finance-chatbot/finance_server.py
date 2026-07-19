"""Finance-only Harbor chatbot API sidecar.

Unlike RecAI's optional in-process bridge, this image only needs a lean ASGI
wrapper over the finance adapter (no Playground Python package deps).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from finance_openbb import FinanceOpenBBApplication

APPLICATION_ID = "finance_openbb"
APPLICATION_CONTEXT = "financial_research"
_application = FinanceOpenBBApplication()


class SessionRequest(BaseModel):
    """Create a Harbor chat session for the finance chatbot."""

    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = None
    application_id: str = Field(default=APPLICATION_ID, alias="applicationId")
    application_context: Optional[str] = Field(
        default=APPLICATION_CONTEXT,
        alias="applicationContext",
    )
    domain: Optional[str] = None
    engine: Optional[str] = None
    botType: Optional[str] = None

    @field_validator("application_id")
    @classmethod
    def _known_application(cls, value: str) -> str:
        if value != APPLICATION_ID:
            raise ValueError("applicationId must be {}".format(APPLICATION_ID))
        return value

    @field_validator("application_context")
    @classmethod
    def _known_context(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value != APPLICATION_CONTEXT:
            raise ValueError("applicationContext must be {}".format(APPLICATION_CONTEXT))
        return value


class MessageRequest(SessionRequest):
    """Send one user message, creating a session when needed."""

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


def _context(body: SessionRequest) -> str:
    return body.application_context or APPLICATION_CONTEXT


app = FastAPI(title="MatrAIx Finance Chatbot API", version="1.0")


@app.get("/health")
@app.get("/v1/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "applications": [
            {
                "applicationId": APPLICATION_ID,
                "label": "FinAI / OpenBB",
                "defaultContext": APPLICATION_CONTEXT,
                "contexts": [APPLICATION_CONTEXT],
            }
        ],
    }


@app.get("/ready")
@app.get("/v1/ready")
def ready(
    application_id: str = Query(default=APPLICATION_ID, alias="applicationId"),
    application_context: Optional[str] = Query(
        default=APPLICATION_CONTEXT,
        alias="applicationContext",
    ),
) -> Dict[str, Any]:
    if application_id != APPLICATION_ID:
        raise HTTPException(
            status_code=422,
            detail="applicationId must be {}".format(APPLICATION_ID),
        )
    context = application_context or APPLICATION_CONTEXT
    try:
        _application.ready(context)
    except Exception as exc:  # noqa: BLE001 - readiness should surface root cause.
        raise HTTPException(status_code=503, detail=str(exc))
    return {
        "status": "ready",
        "applicationId": APPLICATION_ID,
        "applicationContext": context,
        "domain": context,
    }


@app.post("/v1/session")
def create_session(body: SessionRequest) -> Dict[str, Any]:
    return _application.create_session(
        title=body.title,
        context=_context(body),
        engine=body.engine,
        bot_type=body.botType,
    )


@app.post("/v1/messages")
def send_message(body: MessageRequest) -> Dict[str, Any]:
    return _application.send_message(
        session_id=body.session_id,
        message=body.message,
        title=body.title,
        context=_context(body),
        engine=body.engine,
        bot_type=body.botType,
    )


@app.get("/v1/conversation")
def conversation(
    session_id: str = Query(alias="sessionId"),
    application_id: str = Query(default=APPLICATION_ID, alias="applicationId"),
) -> Dict[str, Any]:
    if application_id != APPLICATION_ID:
        raise HTTPException(
            status_code=422,
            detail="applicationId must be {}".format(APPLICATION_ID),
        )
    return _application.conversation(session_id=session_id)


@app.get("/v1/recommendations")
@app.get("/v1/application-result")
def recommendations(
    session_id: str = Query(alias="sessionId"),
    application_id: str = Query(default=APPLICATION_ID, alias="applicationId"),
) -> Dict[str, Any]:
    if application_id != APPLICATION_ID:
        raise HTTPException(
            status_code=422,
            detail="applicationId must be {}".format(APPLICATION_ID),
        )
    return _application.recommendations(session_id=session_id)
